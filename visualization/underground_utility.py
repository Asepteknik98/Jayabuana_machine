"""Render estimated utility using the existing logical scene transform."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from adapters.sensor_source import SafeDigState
from modules.safedig_precision.bucket_position import PIXELS_PER_METRE
from visualization.excavator_2d import GROUND_Y, SCENE_HEIGHT, SCENE_WIDTH


def world_to_scene(x_m: float, z_m: float) -> QPointF:
    return QPointF(x_m * PIXELS_PER_METRE, GROUND_Y - z_m * PIXELS_PER_METRE)


def draw_utility(painter: QPainter, bounds: QRectF, state: SafeDigState, presentation=False) -> None:
    utility = state.utility
    if utility is None or not utility.detected or not utility.valid:
        return
    painter.save()
    scale = min(bounds.width() / SCENE_WIDTH, bounds.height() / SCENE_HEIGHT)
    painter.translate(bounds.center())
    painter.scale(scale, scale)
    painter.translate(-SCENE_WIDTH / 2, -SCENE_HEIGHT / 2)
    point = world_to_scene(utility.estimated_x_m, utility.estimated_z_m)
    painter.setPen(QPen(QColor("#68deeb"), 7))
    painter.drawLine(point + QPointF(-36, 0), point + QPointF(36, 0))
    if state.machine is not None and utility.distance_to_bucket_m is not None:
        bucket = world_to_scene(state.machine.bucket_x_m, state.machine.bucket_z_m)
        painter.setPen(QPen(QColor("#9bdde8"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(bucket, point)
        if not presentation:painter.drawText((bucket + point) / 2 + QPointF(10,0),f"{utility.distance_to_bucket_m:.2f} m")
    if presentation:
        font=painter.font();font.setPixelSize(15);painter.setFont(font)
        color={"CLEAR":"#65daba","APPROACHING":"#ffb347","INSIDE":"#ff6060"}.get(state.envelope.status.value if state.envelope else "","#94aec3")
        painter.setPen(QColor(color))
        distance=f"{utility.distance_to_bucket_m:.2f} m" if utility.distance_to_bucket_m is not None else "N/A"
        painter.drawText(QPointF(28,72),"BUCKET TO UTILITY  "+distance)
        painter.setPen(QColor("#68deeb"))
        painter.drawText(QPointF(28,470),f"UTILITY DEPTH  {utility.estimated_depth_m:.2f} m")
        painter.restore();return
    # Fixed legend avoids clipping long labels near the edge of the scene.
    painter.fillRect(QRectF(16, 350, 310, 115), QColor("#0b1d2e"))
    painter.setPen(QColor("#a9ecf3"))
    font = painter.font()
    font.setPixelSize(13)
    painter.setFont(font)
    for row, text in enumerate(("SIMULATED ESTIMATE", utility.type_label,
                                f"Estimated Depth: {utility.estimated_depth_m:.2f} m",
                                f"Confidence: {utility.confidence:.0%}")):
        painter.drawText(QPointF(26, 372 + row * 24), text)
    painter.restore()
