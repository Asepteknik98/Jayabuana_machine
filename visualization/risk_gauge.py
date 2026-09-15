"""Read-only score arc. Risk thresholds remain in the engine."""
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QColor,QPainter,QPen
from PySide6.QtWidgets import QWidget,QSizePolicy
from ui.status_style import COLORS
RISK_COLORS={key:COLORS[key] for key in ("SAFE","CAUTION","HIGH","CRITICAL")}
class RiskGauge(QWidget):
    def __init__(self):
        super().__init__();self.score=None;self.color="#8294a3"
        self.setMinimumHeight(100);self.setMaximumHeight(175)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
    def display(self,score,level):
        self.score=score;self.color=RISK_COLORS.get(level.value if level else "","#8294a3");self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        size=min(self.width(),self.height())-12
        rect=QRectF((self.width()-size)/2,(self.height()-size)/2,size,size)
        p.setPen(QPen(QColor("#23394e"),7,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap));p.drawArc(rect,90*16,-360*16)
        p.setPen(QPen(QColor(self.color),7,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        p.drawArc(rect,90*16,-round(360*16*(self.score or 0)/100));p.end()
