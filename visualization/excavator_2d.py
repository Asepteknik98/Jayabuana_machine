"""Deterministic display animation in logical pixels, not machine telemetry."""

from math import cos, pi, sin, acos, atan2, hypot

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF, QLinearGradient


SCENE_WIDTH = 800
SCENE_HEIGHT = 520
GROUND_Y = 330
CYCLE_SECONDS = 8.0
BUCKET_TIP = (43.0, 48.0)


def excavator_pose(seconds: float) -> tuple[QPointF, QPointF, QPointF, float]:
    """Return boom pivot, elbow, bucket pivot and bucket display angle."""
    phase = 2 * pi * (seconds % CYCLE_SECONDS) / CYCLE_SECONDS
    boom_angle = -0.62 + 0.22 * sin(phase)
    arm_angle = 0.95 + 0.35 * sin(phase)
    pivot = QPointF(285, 265)
    elbow = pivot + QPointF(220 * cos(boom_angle), 220 * sin(boom_angle))
    bucket = elbow + QPointF(180 * cos(arm_angle), 180 * sin(arm_angle))
    return pivot, elbow, bucket, 15 + 25 * sin(phase + 0.5)


def draw_excavator(painter: QPainter, bounds: QRectF, seconds: float, target=None, presentation=False) -> None:
    """Fit the complete side view into the available widget area."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scale = min(bounds.width() / SCENE_WIDTH, bounds.height() / SCENE_HEIGHT)
    painter.translate(bounds.center())
    painter.scale(scale, scale)
    painter.translate(-SCENE_WIDTH / 2, -SCENE_HEIGHT / 2)

    sky=QLinearGradient(0,0,0,GROUND_Y);sky.setColorAt(0,QColor("#10273b"));sky.setColorAt(1,QColor("#1b3a4a"))
    painter.fillRect(QRectF(0,0,800,520),sky)
    painter.fillRect(QRectF(0, GROUND_Y, 800, 190), QColor("#23313a"))
    for y,color in ((375,"#293b42"),(430,"#304047"),(485,"#35444a")):
        painter.fillRect(QRectF(0,y,800,35),QColor(color))
    painter.setPen(QPen(QColor("#30414a"), 1))
    for x in range(0, 800, 40):
        painter.drawLine(x, GROUND_Y + 15, x + 65, 520)
    painter.setPen(QPen(QColor("#75a9b6"), 2))
    painter.drawLine(0, GROUND_Y, 800, GROUND_Y)
    painter.drawText(QPointF(28, GROUND_Y + 30), "GROUND SURFACE")

    # Tracks, upper body and cab stay fixed while the implement moves.
    painter.setPen(QPen(QColor("#7893a7"), 3))
    painter.setBrush(QColor("#172330"))
    painter.drawRoundedRect(QRectF(125, 289, 210, 40), 20, 20)
    painter.setBrush(QColor("#3b5163"))
    for x in range(148, 320, 28):
        painter.drawEllipse(QPointF(x, 309), 10, 10)
    painter.setPen(QPen(QColor("#b98a23"), 3))
    painter.setBrush(QColor("#efb936"))
    painter.drawRoundedRect(QRectF(140, 244, 170, 44), 7, 7)
    painter.drawPolygon(QPolygonF([
        QPointF(210, 244), QPointF(210, 187), QPointF(263, 187),
        QPointF(284, 244),
    ]))
    painter.setPen(QPen(QColor("#61cbdc"), 2))
    painter.setBrush(QColor("#153c53"))
    painter.drawPolygon(QPolygonF([
        QPointF(219, 235), QPointF(219, 196), QPointF(257, 196),
        QPointF(271, 235),
    ]))

    pivot, elbow, bucket, bucket_angle = excavator_pose(seconds)
    if target is not None:
        # Two-link display IK: the rendered tooth follows the same world position as assessment.
        bucket_angle = 0.
        bucket = QPointF(target.x_m*80-BUCKET_TIP[0], GROUND_Y+target.depth_m*80-BUCKET_TIP[1])
        dx, dy = bucket.x()-pivot.x(), bucket.y()-pivot.y()
        distance = hypot(dx,dy)
        angle = atan2(dy,dx)-acos(max(-1.,min(1.,(220**2+distance**2-180**2)/(2*220*max(distance,.001)))))
        elbow = pivot+QPointF(220*cos(angle),220*sin(angle))
    for start, end, width in [(pivot, elbow, 24), (elbow, bucket, 18)]:
        painter.setPen(QPen(QColor("#b98a23"), width + 5,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(start, end)
        painter.setPen(QPen(QColor("#f6c448"), width,
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(start, end)

    painter.save()
    painter.translate(bucket)
    painter.rotate(bucket_angle)
    painter.setPen(QPen(QColor("#e5c576"), 3))
    painter.setBrush(QColor("#99752d"))
    painter.drawPolygon(QPolygonF([
        QPointF(-8, -6), QPointF(25, 5), QPointF(*BUCKET_TIP),
        QPointF(-20, 43), QPointF(-34, 24),
    ]))
    painter.restore()

    painter.setPen(QPen(QColor("#dce9ed"), 2))
    painter.setBrush(QColor("#294353"))
    for point in (pivot, elbow, bucket):
        painter.drawEllipse(point, 7, 7)
    painter.setPen(QColor("#8caabb"))
    if not presentation:painter.drawText(QPointF(28,42),"EXCAVATOR / SIDE VIEW")
    if not presentation:painter.drawText(QPointF(28,490),"SIMULATED MOTION / DISPLAY ONLY")
    painter.restore()
