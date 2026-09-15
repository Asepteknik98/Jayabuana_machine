"""Read-only recommended assistance panel; no commands or audio playback."""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame,QGridLayout,QLabel
from core.decision_engine import DecisionState

from ui.status_style import COLORS

ACTION_COLORS = {key: COLORS[key] for key in ("NORMAL","WARN","SLOW","VERIFY","RESTRICT")}


class StatusIndicator(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        self.presentation = False
        layout=QGridLayout(self);layout.setContentsMargins(16,8,48,8);layout.setHorizontalSpacing(24);layout.setVerticalSpacing(4)
        title=QLabel("AI Copilot Decision");title.setObjectName("panelTitle");layout.addWidget(title,0,0)
        subtitle=QLabel("Intelligent Safety Recommendation");subtitle.setObjectName("muted");layout.addWidget(subtitle,1,0)
        self.action_label=QLabel();self.action_label.setMinimumWidth(170);layout.addWidget(self.action_label,0,1,2,1)
        self.message_label=QLabel();self.message_label.setWordWrap(True);layout.addWidget(self.message_label,0,2)
        self.reason_label=QLabel();self.reason_label.setObjectName("muted");self.reason_label.setWordWrap(True);layout.addWidget(self.reason_label,1,2)
        self.guidance_label=QLabel();self.guidance_label.setObjectName("muted");self.guidance_label.setWordWrap(True);layout.addWidget(self.guidance_label,2,0,1,2)
        self.verification_label=QLabel();self.verification_label.setObjectName("muted");self.verification_label.setWordWrap(True);layout.addWidget(self.verification_label,2,2)
        layout.setColumnStretch(2,1)
        self.accent="#00e8b2"

    def paintEvent(self,event):
        super().paintEvent(event)
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color=QColor(self.accent)
        for offset in (14,26,38):
            color.setAlpha(160 if offset==38 else 75)
            p.setPen(QPen(color,1.5));x=self.width()-offset
            p.drawLine(QPointF(x-10,8),QPointF(x+5,self.height()/2))
            p.drawLine(QPointF(x+5,self.height()/2),QPointF(x-10,self.height()-8))
        p.end()

    def display(self, decision: DecisionState) -> None:
        self.action_label.setText("\u25cf  " + decision.action.value)
        self.accent=ACTION_COLORS[decision.action.value]
        tint=QColor(self.accent).darker(700).name()
        self.setStyleSheet(f"QFrame#panel {{border:1px solid {self.accent};background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #03243a,stop:.35 {tint},stop:1 #001b2b);}}")
        self.update()
        self.action_label.setStyleSheet(f"color:{ACTION_COLORS[decision.action.value]};font-size:{26 if self.presentation else 18}px;font-weight:600;")
        self.message_label.setText(decision.message)
        self.reason_label.setText("Reason: " + decision.reason)
        self.guidance_label.setText("Speed Guidance: " + decision.speed_guidance)
        self.verification_label.setText("Verification: " + ("REQUIRED" if decision.verification_required else "NOT REQUESTED"))

    def set_presentation(self, enabled):
        self.presentation=enabled
        self.guidance_label.setVisible(not enabled)
        self.verification_label.setVisible(not enabled)
        self.message_label.setStyleSheet("font-size:18px;" if enabled else "")
