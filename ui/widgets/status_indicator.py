"""Read-only recommended assistance panel; no commands or audio playback."""

from PySide6.QtWidgets import QFrame,QGridLayout,QLabel
from core.decision_engine import DecisionState

from ui.status_style import COLORS

ACTION_COLORS = {key: COLORS[key] for key in ("NORMAL","WARN","SLOW","VERIFY","RESTRICT")}


class StatusIndicator(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        self.presentation = False
        layout=QGridLayout(self);layout.setContentsMargins(12,8,12,8);layout.setSpacing(4)
        title=QLabel("AI DECISION / SOFTWARE RECOMMENDATION")
        title.setObjectName("muted");title.setWordWrap(True);layout.addWidget(title,0,0)
        self.action_label=QLabel();layout.addWidget(self.action_label,1,0,2,1)
        self.message_label=QLabel();self.message_label.setWordWrap(True);layout.addWidget(self.message_label,0,1,1,2)
        self.reason_label=QLabel();self.reason_label.setObjectName("muted");self.reason_label.setWordWrap(True)
        layout.addWidget(self.reason_label,1,1,2,2)
        self.guidance_label=QLabel();self.guidance_label.setObjectName("muted");self.guidance_label.setWordWrap(True)
        layout.addWidget(self.guidance_label,3,0,1,2)
        self.verification_label=QLabel();self.verification_label.setObjectName("muted")
        self.verification_label.setWordWrap(True);layout.addWidget(self.verification_label,3,2)

    def display(self, decision: DecisionState) -> None:
        self.action_label.setText("\u25cf  " + decision.action.value)
        self.setStyleSheet(f"QFrame#panel {{border-left:4px solid {ACTION_COLORS[decision.action.value]};}}")
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
