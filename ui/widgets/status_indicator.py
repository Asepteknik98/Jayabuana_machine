"""Read-only recommended assistance panel; no commands or audio playback."""

from PySide6.QtWidgets import QFrame,QGridLayout,QLabel
from core.decision_engine import DecisionState

ACTION_COLORS = {"NORMAL":"#4cde9a", "WARN":"#efc34a", "SLOW":"#ff8c42",
                 "VERIFY":"#ffb347", "RESTRICT":"#ff5353"}


class StatusIndicator(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        layout=QGridLayout(self);layout.setContentsMargins(12,8,12,8);layout.setSpacing(4)
        title=QLabel("AI DECISION & ASSISTANCE • SOFTWARE RECOMMENDATION ONLY")
        title.setObjectName("muted");title.setWordWrap(True);layout.addWidget(title,0,0,1,3)
        self.action_label=QLabel();layout.addWidget(self.action_label,1,0)
        self.message_label=QLabel();self.message_label.setWordWrap(True);layout.addWidget(self.message_label,1,1,1,2)
        self.reason_label=QLabel();self.reason_label.setObjectName("muted");self.reason_label.setWordWrap(True)
        layout.addWidget(self.reason_label,2,0,1,3)
        self.guidance_label=QLabel();self.guidance_label.setObjectName("muted");self.guidance_label.setWordWrap(True)
        layout.addWidget(self.guidance_label,3,0,1,2)
        self.verification_label=QLabel();self.verification_label.setObjectName("muted")
        self.verification_label.setWordWrap(True);layout.addWidget(self.verification_label,3,2)

    def display(self, decision: DecisionState) -> None:
        self.action_label.setText("ACTION: " + decision.action.value)
        self.action_label.setStyleSheet(f"color:{ACTION_COLORS[decision.action.value]};font-size:18px;font-weight:600;")
        self.message_label.setText(decision.message)
        self.reason_label.setText("Reason: " + decision.reason)
        self.guidance_label.setText("Speed Guidance: " + decision.speed_guidance)
        self.verification_label.setText("Verification: " + ("REQUIRED" if decision.verification_required else "NOT REQUESTED"))
