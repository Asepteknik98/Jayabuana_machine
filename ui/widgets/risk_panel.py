"""Read-only presentation of risk score, data quality and contributions."""

from PySide6.QtWidgets import QFrame,QLabel,QVBoxLayout,QGridLayout,QScrollArea,QWidget,QProgressBar,QHBoxLayout
from PySide6.QtCore import Qt
from ui.widgets.hmi_icon import HmiIcon
from core.risk_engine import RiskState
from visualization.risk_gauge import RiskGauge,RISK_COLORS


class RiskPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        outer=QVBoxLayout(self)
        outer.setContentsMargins(8,4,8,4)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);outer.addWidget(self.scroll)
        content=QWidget();content.setObjectName("riskContent");self.scroll.setWidget(content)
        layout=QVBoxLayout(content);layout.setContentsMargins(0,0,0,0);layout.setSpacing(4)
        title=QLabel("Multimodal AI Risk Engine");title.setWordWrap(True)
        title.setObjectName("panelTitle");title.setStyleSheet("font-size:18px;");head=QHBoxLayout();head.addWidget(HmiIcon("risk",28));head.addWidget(title,1);layout.addLayout(head)
        ring=QGridLayout();self.gauge=RiskGauge();ring.addWidget(self.gauge,0,0)
        self.score_label=QLabel("--");self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setStyleSheet("font-size:48px;font-weight:700;")
        center=QVBoxLayout();center.setSpacing(0);center.addStretch();center.addWidget(self.score_label)
        unit=QLabel("/ 100");unit.setAlignment(Qt.AlignmentFlag.AlignCenter);center.addWidget(unit);center.addStretch();ring.addLayout(center,0,0)
        ring_widget=QWidget();ring_widget.setStyleSheet("QWidget {background:transparent;}");ring_widget.setLayout(ring);ring_widget.setMinimumWidth(130)
        summary=QHBoxLayout();summary.addWidget(ring_widget,2);layout.addLayout(summary,1)
        self.level_label=QLabel("UNAVAILABLE");self.level_label.setAlignment(Qt.AlignmentFlag.AlignCenter);self.level_label.setWordWrap(True);summary.addWidget(self.level_label,3)
        self.fusion_label=QLabel();self.fusion_label.setObjectName("muted");layout.addWidget(self.fusion_label)
        self.bars={}
        for key,name in (("utility","Utility Risk"),("design","Design Conflict"),("fatigue","Fatigue")):
            line=QGridLayout();line.setContentsMargins(0,0,0,0);line.setSpacing(2)
            caption=QLabel(name);caption.setObjectName("muted");line.addWidget(caption,0,0)
            value=QLabel("N/A");value.setAlignment(Qt.AlignmentFlag.AlignRight);line.addWidget(value,0,2)
            bar=QProgressBar();bar.setTextVisible(False);line.addWidget(bar,0,1);line.setColumnStretch(1,1)
            bar.setStyleSheet("QProgressBar::chunk {background:"+{"utility":"#ff505d","design":"#ffbd32","fatigue":"#00c58b"}[key]+";}")
            caption.setMinimumWidth(115);value.setMinimumWidth(38)
            self.bars[key]=(value,bar);layout.addLayout(line)
        self.data_label=QLabel();self.data_label.setWordWrap(True);self.data_label.setObjectName("muted")
        layout.addWidget(self.data_label)
        self.breakdown=QWidget();grid=QGridLayout(self.breakdown);self.values={}
        for row,(key,name) in enumerate((("utility","Utility Risk"),("confidence","Confidence Risk"),
                                        ("velocity","Velocity Risk"),("design","Design Conflict"),("fatigue","Fatigue"))):
            caption=QLabel(name);caption.setObjectName("muted");grid.addWidget(caption,row,0)
            value=QLabel();value.setStyleSheet('font-size:12px;');grid.addWidget(value,row,1);self.values[key]=value
        layout.addWidget(self.breakdown)
        self.driver_label=QLabel();self.driver_label.setObjectName("driver");self.driver_label.setWordWrap(True);layout.addWidget(self.driver_label)
        self.verification_label=QLabel();self.verification_label.setWordWrap(True)
        self.verification_label.setObjectName("muted");layout.addWidget(self.verification_label)

    def display(self, risk: RiskState, fusion=None) -> None:
        if fusion is not None:
            statuses = []
            for name in ("vision", "precision", "guardian"):
                status = "STALE" if name.upper() + "_STALE" in fusion.context_flags else "VALID" if getattr(fusion, name + "_valid") else "UNAVAILABLE"
                statuses.append(f"{name.title()}: {status}")
            self.fusion_label.setText(f"Fusion Confidence: {fusion.fusion_confidence}")
            self.fusion_label.setToolTip(" | ".join(statuses))
        self.score_label.setText(str(risk.total_score) if risk.total_score is not None else "--")
        self.level_label.setText(risk.level.value if risk.level else "UNAVAILABLE")
        color=RISK_COLORS.get(risk.level.value if risk.level else "",'#8294a3')
        self.level_label.setStyleSheet(f'color:{color};font-size:24px;font-weight:700;')
        self.gauge.display(risk.total_score,risk.level)
        confidence=f"{risk.risk_confidence:.0%}" if risk.risk_confidence is not None else "N/A"
        self.data_label.setText(f"{risk.data_status}\nRisk Confidence: {confidence}")
        for key,component in (("utility",risk.utility_risk),("confidence",risk.confidence_risk),
                              ("velocity",risk.velocity_risk),("design",risk.design_conflict_risk),("fatigue",risk.fatigue_risk)):
            if key in self.bars:
                label,bar=self.bars[key];label.setText(f"{component:.0%}" if component is not None else "N/A")
                bar.setValue(round(component*100) if component is not None else 0)
            points=risk.contribution_breakdown.get(key)
            self.values[key].setText(f"{component:.0%} | +{points:.1f}" if component is not None and points is not None else "N/A")
        self.driver_label.setText(f"PRIMARY DRIVER: {risk.primary_risk_driver}")
        self.verification_label.setText("SECONDARY VERIFICATION REQUIRED" if risk.verification_required else "")

    def set_presentation(self, enabled):
        self.breakdown.setVisible(not enabled)
        self.data_label.setVisible(not enabled)
        self.verification_label.setVisible(not enabled)
