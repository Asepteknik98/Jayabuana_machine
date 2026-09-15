"""Readable domain summaries and compact health badges from existing state."""
from PySide6.QtWidgets import QFrame,QVBoxLayout,QLabel,QWidget,QHBoxLayout
from ui.status_style import COLORS,metres,percent

class PresentationPanel(QFrame):
    def __init__(self,title):
        super().__init__();self.setObjectName("panel")
        layout=QVBoxLayout(self);layout.setContentsMargins(12,10,12,10);layout.setSpacing(3)
        heading=QLabel(title);heading.setObjectName("panelTitle");layout.addWidget(heading)
        self.source=QLabel();self.source.setWordWrap(True);self.source.setObjectName("muted");layout.addWidget(self.source)
        self.value=QLabel();self.value.setWordWrap(True);self.value.setStyleSheet("font-size:20px;font-weight:600;");layout.addWidget(self.value)
        self.detail=QLabel();self.detail.setWordWrap(True);self.detail.setStyleSheet("font-size:16px;");layout.addWidget(self.detail)

    def display(self,state,domain,guardian_source):
        if domain=="vision":
            utility=state.utility
            self.source.setText("SIMULATED GPR / ESTIMATED UTILITY")
            available=utility and utility.valid and utility.detected
            self.value.setText(utility.type_label if available else "No current utility estimate")
            self.detail.setText("Depth: "+metres(utility.estimated_depth_m if available else None)+
                " | Distance: "+metres(utility.distance_to_bucket_m if available else None)+
                "\nConfidence: "+percent(utility.confidence if available else state.sensor.confidence if state.sensor else None))
        elif domain=="precision":
            machine=state.machine
            self.source.setText("SIMULATED MACHINE / BUCKET TIP")
            self.value.setText("Depth: "+metres(machine.current_depth_m if machine else None))
            self.detail.setText("Target: "+metres(machine.target_depth_m if machine else None)+
                (f" | Speed: {machine.bucket_speed_mps:.2f} m/s" if machine and machine.bucket_speed_mps is not None else "")+
                "\nDesign conflict: "+(state.design_conflict.status.value.replace("_"," ") if state.design_conflict else "UNKNOWN"))
        else:
            fusion=state.fusion
            valid=fusion and fusion.fatigue_available
            self.source.setText("GUARDIAN SOURCE: "+("SIMULATED DEMO" if guardian_source=="SIMULATED" else "LIVE CAMERA / "+guardian_source))
            self.value.setText(f"Fatigue: {fusion.fatigue_score:.0f} / 100" if valid else "Fatigue: UNKNOWN")
            self.detail.setText("Attention: "+percent(fusion.attention_score if fusion and fusion.attention_available else None)+
                "\nPROTOTYPE ESTIMATE / NON-MEDICAL")

class SystemHealth(QWidget):
    def __init__(self):
        super().__init__();layout=QHBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(8)
        self.labels={}
        for name in ("VISION","PRECISION","GUARDIAN","FUSION","RISK","DECISION"):
            label=QLabel(name+": OFFLINE");label.setWordWrap(True);layout.addWidget(label,1);self.labels[name]=label

    def display(self,state):
        fusion=state.fusion
        status={"VISION":"OFFLINE", "PRECISION":"OFFLINE", "GUARDIAN":"OFFLINE", "FUSION":"OFFLINE", "RISK":"OFFLINE", "DECISION":"OFFLINE"}
        if fusion:
            status["VISION"]="ACTIVE" if fusion.vision_valid and fusion.sensor_health=="VALID" else "OFFLINE" if fusion.sensor_health=="OFFLINE" else "DEGRADED"
            status["PRECISION"]="ACTIVE" if fusion.precision_valid and "PRECISION_DEGRADED" not in fusion.context_flags else "DEGRADED"
            status["GUARDIAN"]="ACTIVE" if fusion.guardian_valid else "OFFLINE" if not state.operator or not state.operator.camera_available else "DEGRADED"
            status["FUSION"]="ACTIVE" if fusion.fusion_valid and fusion.fusion_confidence=="HIGH" else "DEGRADED"
            status["RISK"]="ACTIVE" if state.risk and state.risk.risk_valid else "DEGRADED"
            status["DECISION"]="ACTIVE" if state.decision and state.decision.valid else "DEGRADED"
        for name,label in self.labels.items():
            label.setText(name+": "+status[name]);label.setStyleSheet(f"color:{COLORS[status[name]]};font-size:12px;font-weight:600;")
