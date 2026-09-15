"""Read-only HMI domain cards; all quantities come from existing state."""
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtWidgets import QFrame,QVBoxLayout,QLabel,QWidget,QHBoxLayout,QGridLayout,QProgressBar,QStackedWidget,QSizePolicy
from ui.status_style import COLORS,metres,percent
from visualization.gpr_wave import GPRWave
from modules.safedig_precision.depth_control import remaining_depth

class StatusBadge(QLabel):
    def display(self,text,color=None):
        color=color or COLORS.get(text,COLORS["UNKNOWN"])
        self.setText(text)
        self.setStyleSheet(f"color:{color};background:#14273a;border:1px solid {color};border-radius:4px;padding:3px 7px;font-size:13px;font-weight:600;")

class OperatorSilhouette(QWidget):
    def __init__(self):
        super().__init__();self.setMinimumHeight(70);self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(self.width()/2,self.height()/2);scale=min(self.width()/160,self.height()/100);p.scale(scale,scale)
        p.setPen(QPen(QColor("#3b708a"),1.5));p.setBrush(QColor("#183b51"))
        p.drawRoundedRect(QRectF(-46,15,92,42),22,22)
        p.setBrush(QColor("#366279"));p.drawEllipse(QRectF(-21,-26,42,44))
        p.setBrush(QColor("#e6b33c"));p.setPen(QPen(QColor("#e6b33c"),3))
        p.drawPie(QRectF(-30,-49,60,53),0,180*16);p.drawLine(QPointF(-35,-23),QPointF(35,-23))
        p.setPen(QPen(QColor("#0a1928"),3));p.drawLine(QPointF(0,-47),QPointF(0,-28));p.end()

class PresentationPanel(QFrame):
    def __init__(self,title):
        super().__init__();self.setObjectName("panel")
        self.domain="vision" if "Vision" in title else "precision" if "Precision" in title else "guardian"
        layout=QVBoxLayout(self);layout.setContentsMargins(16,8,16,8);layout.setSpacing(4)
        top=QHBoxLayout();heading=QLabel(title);heading.setObjectName("panelTitle");top.addWidget(heading,1)
        self.badge=StatusBadge();top.addWidget(self.badge);layout.addLayout(top)
        self.source=QLabel();self.source.setObjectName("muted");self.source.setWordWrap(True);layout.addWidget(self.source)
        self.value=QLabel();self.value.setWordWrap(True);self.value.setObjectName("metric")
        self.values={}
        if self.domain=="vision":
            layout.addWidget(self.value)
            names=("Estimated Depth","Distance from Bucket","Detection Confidence")
        elif self.domain=="precision":names=("Target Depth","Current Depth","Remaining","Bucket Speed","Design Conflict")
        else:
            self.visual=QStackedWidget();self.visual.addWidget(OperatorSilhouette())
            names=("Fatigue Score","Attention","Status")
        grid=QGridLayout();grid.setHorizontalSpacing(8);grid.setVerticalSpacing(4)
        for row,name in enumerate(names):
            caption=QLabel(name);caption.setObjectName("muted");grid.addWidget(caption,row,0)
            label=QLabel("N/A");label.setAlignment(Qt.AlignmentFlag.AlignRight);label.setStyleSheet("font-size:19px;font-weight:600;")
            if name in ("Estimated Depth","Current Depth","Fatigue Score"):
                label.setStyleSheet("font-size:24px;font-weight:600;")
            grid.addWidget(label,row,1);self.values[name]=label
        if self.domain=="guardian":
            body=QHBoxLayout();body.addWidget(self.visual,2);body.addLayout(grid,3);layout.addLayout(body,1)
        else:layout.addLayout(grid)
        if self.domain=="vision":
            self.confidence_bar=QProgressBar();self.confidence_bar.setTextVisible(False);layout.addWidget(self.confidence_bar)
            self.wave=GPRWave();self.wave.setMinimumHeight(80);layout.addWidget(self.wave,1)
        elif self.domain=="precision":layout.addStretch()
        self.detail=QLabel();self.detail.setWordWrap(True);self.detail.setObjectName("muted");layout.addWidget(self.detail)

    def attach_preview(self,widget):
        self.visual.addWidget(widget)

    def display(self,state,domain,guardian_source):
        if domain=="vision":
            utility=state.utility;available=bool(utility and utility.valid and utility.detected)
            self.source.setText("Subsurface Sensing / Simulated GPR")
            self.badge.display(state.sensor_health.value)
            self.value.setText(utility.type_label if available else "No current utility estimate")
            confidence=utility.confidence if available else state.sensor.confidence if state.sensor else None
            for key,text in (("Estimated Depth",metres(utility.estimated_depth_m if available else None)),
                ("Distance from Bucket",metres(utility.distance_to_bucket_m if available else None)),("Detection Confidence",percent(confidence))):self.values[key].setText(text)
            self.confidence_bar.setValue(round(confidence*100) if confidence is not None else 0)
            self.wave.samples=state.sensor.radargram if state.sensor and state.sensor_health.value not in ("OFFLINE","STALE") else ();self.wave.update()
            self.detail.setText("SECONDARY VERIFICATION REQUIRED" if state.fusion and state.fusion.verification_required else "")
            self.detail.setVisible(bool(self.detail.text()))
        elif domain=="precision":
            machine=state.machine;fusion=state.fusion
            self.source.setText("Machine Position & Digging Control")
            self.badge.display("VALID" if fusion and fusion.precision_valid else "STALE")
            for key,text in (("Target Depth",metres(machine.target_depth_m if machine else None)),
                ("Current Depth",metres(machine.current_depth_m if machine else None)),
                ("Remaining",metres(remaining_depth(machine.current_depth_m,machine.target_depth_m) if machine and machine.target_depth_m is not None and machine.current_depth_m is not None else None)),
                ("Bucket Speed",f"{machine.bucket_speed_mps:.2f} m/s" if machine and machine.bucket_speed_mps is not None else "N/A")):
                self.values[key].setText(text)
            conflict=state.design_conflict.status.value if state.design_conflict else "UNKNOWN"
            self.values["Design Conflict"].setText({"DESIGN_CONFLICT":"YES","NO_CONFLICT":"NO","POTENTIAL_CONFLICT":"POTENTIAL"}.get(conflict,"UNKNOWN"))
            self.values["Design Conflict"].setStyleSheet("font-size:19px;font-weight:600;color:"+{"DESIGN_CONFLICT":"#ff735e","POTENTIAL_CONFLICT":"#ffb347","NO_CONFLICT":"#65daba"}.get(conflict,"#94aec3")+";")
            self.detail.hide()
        else:
            fusion=state.fusion;valid=bool(fusion and fusion.fatigue_available)
            self.source.setText("Operator Monitoring / "+("Simulated Demo" if guardian_source=="SIMULATED" else "Live Camera"))
            self.visual.setCurrentIndex(0 if guardian_source=="SIMULATED" or self.visual.count()<2 else 1)
            self.badge.display("ACTIVE" if valid else "OFFLINE" if not state.operator or not state.operator.camera_available else "UNKNOWN")
            self.values["Fatigue Score"].setText(f"{fusion.fatigue_score:.0f} / 100" if valid else "UNKNOWN")
            self.values["Attention"].setText(percent(fusion.attention_score if fusion and fusion.attention_available else None))
            level=state.operator.fatigue_level if valid else "UNKNOWN"
            status={"NORMAL":"ALERT","ELEVATED":"ELEVATED","HIGH":"DROWSY"}.get(level,"UNKNOWN")
            self.values["Status"].setText(status);self.values["Status"].setStyleSheet("font-size:19px;font-weight:600;color:"+{"ALERT":"#4cde9a","ELEVATED":"#ff8c42","DROWSY":"#ff5353","UNKNOWN":"#94aec3"}[status]+";")
            self.detail.setText("PROTOTYPE ESTIMATE / NON-MEDICAL")

class SystemHealth(QWidget):
    def __init__(self):
        super().__init__();layout=QHBoxLayout(self);layout.setContentsMargins(4,4,4,4);layout.setSpacing(12)
        self.labels={}
        for name in ("VISION","PRECISION","GUARDIAN","FUSION","RISK ENGINE","DECISION ENGINE"):
            label=QLabel(name);layout.addWidget(label,1);self.labels[name]=label
    def display(self,state):
        fusion=state.fusion
        status={name:"OFFLINE" for name in self.labels}
        if fusion:
            status["VISION"]="ACTIVE" if fusion.vision_valid and fusion.sensor_health=="VALID" else "OFFLINE" if fusion.sensor_health=="OFFLINE" else "DEGRADED"
            status["PRECISION"]="ACTIVE" if fusion.precision_valid and "PRECISION_DEGRADED" not in fusion.context_flags else "DEGRADED"
            status["GUARDIAN"]="ACTIVE" if fusion.guardian_valid else "OFFLINE" if not state.operator or not state.operator.camera_available else "DEGRADED"
            status["FUSION"]="ACTIVE" if fusion.fusion_valid and fusion.fusion_confidence=="HIGH" else "DEGRADED"
            status["RISK ENGINE"]="ACTIVE" if state.risk and state.risk.risk_valid else "DEGRADED"
            status["DECISION ENGINE"]="ACTIVE" if state.decision and state.decision.valid else "DEGRADED"
        for name,label in self.labels.items():
            label.setText(name+"  \u25cf "+status[name]);label.setStyleSheet(f"color:{COLORS[status[name]]};font-size:13px;font-weight:600;")
