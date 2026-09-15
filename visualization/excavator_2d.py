"""Deterministic display animation in logical pixels, not machine telemetry."""

from functools import lru_cache
from random import Random
from math import cos, pi, sin, acos, atan2, hypot

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF, QLinearGradient, QRadialGradient, QImage


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



@lru_cache(maxsize=1)
def _workspace_background():
    """Cache decorative soil texture; it is not a sensor or geometry input."""
    image=QImage(SCENE_WIDTH,SCENE_HEIGHT,QImage.Format.Format_RGB32)
    p=QPainter(image)
    sky=QRadialGradient(390,300,490)
    sky.setColorAt(0,QColor("#337bb0"));sky.setColorAt(.6,QColor("#123f6b"));sky.setColorAt(1,QColor("#031b35"))
    p.fillRect(image.rect(),sky)
    soil=QLinearGradient(0,GROUND_Y,0,SCENE_HEIGHT)
    soil.setColorAt(0,QColor("#655039"));soil.setColorAt(.35,QColor("#3e3329"));soil.setColorAt(.65,QColor("#302a25"));soil.setColorAt(1,QColor("#171b1e"))
    p.fillRect(QRectF(0,GROUND_Y,800,190),soil)
    rng=Random(726)
    for layer in (373,427,478):
        path=QPolygonF([QPointF(x,layer+3*sin(x*.043)) for x in range(0,805,8)])
        p.setPen(QPen(QColor(15,19,20,100),4));p.drawPolyline(path)
    for _ in range(14500):
        x=rng.randrange(800);y=rng.randrange(GROUND_Y,520)
        shade=rng.choice((QColor(165,142,106,45),QColor(7,11,13,75),QColor(110,104,89,55)))
        p.setPen(QPen(shade,rng.choice((1,1,2,3))))
        p.drawPoint(x,y)
    for x in range(0,800,5):
        p.setPen(QPen(QColor(rng.choice(("#a8a28b","#83765c","#635946"))),3))
        p.drawLine(x,GROUND_Y+rng.randrange(-2,2),x+4,GROUND_Y)
    p.end();return image

def draw_excavator(painter: QPainter, bounds: QRectF, seconds: float, target=None, presentation=False) -> None:
    """Fit the complete side view into the available widget area."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    scale = min(bounds.width() / SCENE_WIDTH, bounds.height() / SCENE_HEIGHT)
    painter.translate(bounds.center())
    painter.scale(scale, scale)
    painter.translate(-SCENE_WIDTH / 2, -SCENE_HEIGHT / 2)

    painter.drawImage(QPointF(0,0),_workspace_background())
    painter.setPen(QColor("#dfdfca"))
    painter.drawText(QPointF(16,GROUND_Y+20),"Ground Surface (0.00 m)")

    # Unbranded vector machine with mechanical details and metallic shading.
    painter.setPen(QPen(QColor("#10181c"),3));painter.setBrush(QColor("#111b22"))
    painter.drawRoundedRect(QRectF(122,285,217,43),19,19)
    painter.setPen(QPen(QColor("#637786"),1));painter.setBrush(QColor("#293b48"))
    painter.drawRoundedRect(QRectF(134,291,193,30),14,14)
    for x in range(145,324,27):
        painter.setBrush(QColor("#1a2731"));painter.drawEllipse(QPointF(x,306),12,12)
        painter.setBrush(QColor("#789099"));painter.drawEllipse(QPointF(x,306),5,5)
    painter.setPen(QPen(QColor("#83909a"),2))
    for x in range(136,328,10):
        painter.drawLine(x,286,x-3,291);painter.drawLine(x,322,x-3,327)
    paint=QLinearGradient(0,225,0,282)
    paint.setColorAt(0,QColor("#ffe164"));paint.setColorAt(.55,QColor("#e9ae21"));paint.setColorAt(1,QColor("#936414"))
    painter.setPen(QPen(QColor("#b78217"),2));painter.setBrush(paint)
    painter.drawRoundedRect(QRectF(133,240,172,42),6,6)
    painter.drawRoundedRect(QRectF(134,229,75,45),5,5)
    painter.setPen(QPen(QColor("#664d19"),1))
    for x in range(145,193,4):painter.drawLine(x,242,x,261)
    painter.setPen(QPen(QColor("#30424e"),2));painter.setBrush(QColor("#14252f"))
    painter.drawRoundedRect(QRectF(208,181,65,76),5,5)
    glass=QLinearGradient(211,181,265,248);glass.setColorAt(0,QColor("#759db3"));glass.setColorAt(.4,QColor("#264861"));glass.setColorAt(1,QColor("#0b2336"))
    painter.setBrush(glass);painter.setPen(QPen(QColor("#54889b"),1))
    painter.drawRoundedRect(QRectF(215,188,25,47),2,2);painter.drawRoundedRect(QRectF(246,188,20,47),2,2)
    painter.setPen(QPen(QColor("#aac4cf"),1));painter.drawLine(218,190,233,190)
    painter.setPen(QPen(QColor("#0b1720"),3));painter.drawLine(251,214,261,192)
    painter.setPen(QPen(QColor("#a1a8a2"),2));painter.drawLine(255,242,261,242)
    painter.setPen(QPen(QColor("#38454c"),4));painter.drawLine(183,229,183,211);painter.drawLine(183,211,191,211)
    painter.setPen(QPen(QColor("#929d9e"),2));painter.drawLine(215,262,215,282);painter.drawLine(215,282,242,282)
    painter.drawLine(215,274,239,274)
    painter.setPen(QPen(QColor("#ffdf70"),1));painter.drawLine(140,233,200,233)

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
        direction=end-start;length=max(1,hypot(direction.x(),direction.y()))
        normal=QPointF(-direction.y()/length,direction.x()/length)
        shoulder=start+direction*.35
        profile=QPolygonF([start-normal*width*.5,shoulder-normal*width*.7,end-normal*width*.32,
                          end+normal*width*.35,shoulder+normal*width*.45,start+normal*width*.5])
        metal=QLinearGradient(start-normal*width,end+normal*width)
        metal.setColorAt(0,QColor("#fff080"));metal.setColorAt(.45,QColor("#f5c52c"));metal.setColorAt(1,QColor("#ad7917"))
        painter.setPen(QPen(QColor("#8f681c"),2));painter.setBrush(metal);painter.drawPolygon(profile)
        painter.setPen(QPen(QColor("#fff092"),1));painter.drawLine(start-normal*width*.4,end-normal*width*.25)
        # Cylinder and piston follow the existing linkage, without changing its pose.
        c1=start+direction*.12-normal*(width*.65)
        c2=start+direction*.62-normal*(width*.65)
        c3=end-normal*(width*.45)
        painter.setPen(QPen(QColor("#152b39"),7,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap));painter.drawLine(c1,c2)
        painter.setPen(QPen(QColor("#9faeb6"),3));painter.drawLine(c2,c3)
        painter.setPen(QPen(QColor("#304856"),2));painter.drawLine(start+normal*width*.6,end+normal*width*.6)

    painter.save()
    painter.translate(bucket)
    painter.rotate(bucket_angle)
    painter.setPen(QPen(QColor("#e5c576"), 3))
    bucket_metal=QLinearGradient(-30,0,43,48);bucket_metal.setColorAt(0,QColor("#fbd457"));bucket_metal.setColorAt(1,QColor("#977020"));painter.setBrush(bucket_metal)
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
