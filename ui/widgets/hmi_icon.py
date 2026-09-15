"""Resolution-independent HMI symbols drawn without external fonts or assets."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class HmiIcon(QWidget):
    def __init__(self, kind, size=32):
        super().__init__()
        self.kind = kind
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.width()/40, self.height()/40)
        p.setPen(QPen(QColor('#71dcff'), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        if self.kind == 'vision':
            for radius in (8, 14, 19):
                p.drawArc(QRectF(20-radius, 20-radius, 2*radius, 2*radius), -65*16, 130*16)
                p.drawArc(QRectF(20-radius, 20-radius, 2*radius, 2*radius), 115*16, 130*16)
            p.setBrush(QColor('#00e6e1'));p.drawEllipse(QPointF(20,20),3,3)
        elif self.kind in ('guardian', 'decision'):
            p.drawEllipse(QRectF(14,3,12,14))
            p.drawRoundedRect(QRectF(9,21,22,17),7,7)
            p.drawLine(14,29,14,38);p.drawLine(26,29,26,38)
        elif self.kind == 'risk':
            p.setBrush(QColor('#48c8f3'))
            for x,h in ((5,12),(16,23),(27,33)):
                p.drawRect(QRectF(x,37-h,7,h))
        elif self.kind == 'excavator':
            p.drawRoundedRect(QRectF(2,29,28,8),4,4)
            p.drawRect(QRectF(5,21,20,7));p.drawRect(QRectF(12,10,10,11))
            p.drawLine(24,22,30,7);p.drawLine(30,7,36,25);p.drawLine(36,25,31,28)
        else:
            p.drawEllipse(QRectF(8,8,24,24))
            p.drawEllipse(QRectF(16,16,8,8))
            for x1,y1,x2,y2 in ((20,2,20,12),(20,28,20,38),(2,20,12,20),(28,20,38,20)):
                p.drawLine(x1,y1,x2,y2)
        p.end()
