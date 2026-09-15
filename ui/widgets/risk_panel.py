"""Read-only presentation of risk score, data quality and contributions."""

from PySide6.QtWidgets import QFrame,QLabel,QVBoxLayout,QGridLayout,QScrollArea,QWidget
from core.risk_engine import RiskState
from visualization.risk_gauge import RiskGauge,RISK_COLORS


class RiskPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        outer=QVBoxLayout(self)
        outer.setContentsMargins(8,8,8,8)
        scroll=QScrollArea();scroll.setWidgetResizable(True);outer.addWidget(scroll)
        content=QWidget();scroll.setWidget(content)
        layout=QVBoxLayout(content);layout.setSpacing(5)
        title=QLabel("MULTIMODAL AI RISK ENGINE");title.setWordWrap(True)
        title.setObjectName("panelTitle");layout.addWidget(title)
        self.fusion_label=QLabel();self.fusion_label.setWordWrap(True);layout.addWidget(self.fusion_label)
        self.score_label=QLabel("-- / 100");self.score_label.setObjectName("riskScore")
        layout.addWidget(self.score_label)
        self.level_label=QLabel("UNAVAILABLE");layout.addWidget(self.level_label)
        self.gauge=RiskGauge();layout.addWidget(self.gauge)
        self.data_label=QLabel();self.data_label.setWordWrap(True);self.data_label.setObjectName("muted")
        layout.addWidget(self.data_label)
        self.breakdown=QWidget();grid=QGridLayout(self.breakdown);self.values={}
        for row,(key,name) in enumerate((("utility","Utility Risk"),("confidence","Confidence Risk"),
                                        ("velocity","Velocity Risk"),("design","Design Conflict"),("fatigue","Fatigue"))):
            caption=QLabel(name);caption.setObjectName("muted");grid.addWidget(caption,row,0)
            value=QLabel();value.setStyleSheet('font-size:12px;');grid.addWidget(value,row,1);self.values[key]=value
        layout.addWidget(self.breakdown)
        self.driver_label=QLabel();self.driver_label.setWordWrap(True);layout.addWidget(self.driver_label)
        self.verification_label=QLabel();self.verification_label.setWordWrap(True)
        self.verification_label.setObjectName("muted");layout.addWidget(self.verification_label)

    def display(self, risk: RiskState, fusion=None) -> None:
        if fusion is not None:
            statuses = []
            for name in ("vision", "precision", "guardian"):
                status = "STALE" if name.upper() + "_STALE" in fusion.context_flags else "VALID" if getattr(fusion, name + "_valid") else "UNAVAILABLE"
                statuses.append(f"{name.title()}: {status}")
            self.fusion_label.setText(" | ".join(statuses) + f"\nFusion Confidence: {fusion.fusion_confidence}")
        self.score_label.setText(f"{risk.total_score} / 100" if risk.total_score is not None else "-- / 100")
        self.level_label.setText(risk.level.value if risk.level else "UNAVAILABLE")
        color=RISK_COLORS.get(risk.level.value if risk.level else "",'#8294a3')
        self.level_label.setStyleSheet(f'color:{color};font-size:20px;font-weight:600;')
        self.gauge.display(risk.total_score,risk.level)
        confidence=f"{risk.risk_confidence:.0%}" if risk.risk_confidence is not None else "N/A"
        self.data_label.setText(f"{risk.data_status}\nRisk Confidence: {confidence}")
        for key,component in (("utility",risk.utility_risk),("confidence",risk.confidence_risk),
                              ("velocity",risk.velocity_risk),("design",risk.design_conflict_risk),("fatigue",risk.fatigue_risk)):
            points=risk.contribution_breakdown.get(key)
            self.values[key].setText(f"{component:.0%} | +{points:.1f}" if component is not None and points is not None else "N/A")
        self.driver_label.setText(f"PRIMARY DRIVER\n{risk.primary_risk_driver}")
        self.verification_label.setText("SECONDARY VERIFICATION REQUIRED" if risk.verification_required else "")

    def set_presentation(self, enabled):
        self.breakdown.setVisible(not enabled)
        self.score_label.setStyleSheet("font-size:56px;font-weight:700;" if enabled else "")
