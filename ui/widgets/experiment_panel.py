"""Read-only experiment summary. Truth appears only in finalized evaluation."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea

class ExperimentPanel(QWidget):
    def __init__(self):
        super().__init__()
        outer=QVBoxLayout(self)
        scroll=QScrollArea();scroll.setWidgetResizable(True);outer.addWidget(scroll)
        content=QWidget();scroll.setWidget(content);layout=QVBoxLayout(content)
        self.label=QLabel("PROTOTYPE / SIMULATION EVALUATION\nNo experiment session")
        self.label.setWordWrap(True);layout.addWidget(self.label);layout.addStretch()

    def display(self, recorder):
        session=recorder.session
        if session is None:return
        lines=["PROTOTYPE / SIMULATION EVALUATION",session.experiment_id,session.scenario_name,
            f"{session.result_status} | {session.duration_s:.1f} s | Events: {len(recorder.events.events)}"]
        summary=recorder.summary
        def show(value,unit=""):
            return "N/A" if value is None else f"{value:.3f}{unit}" if isinstance(value,(int,float)) else str(value)
        if summary:
            detection=summary["detection"];risk=summary["risk"];latency=summary["latency"]
            metadata_lines = lines
            lines = ["EXPERIMENT COMPLETE" if session.result_status=="COMPLETED" else "EXPERIMENT ABORTED",
                "GROUND TRUTH - SIMULATION ONLY",
                "Detection: "+show(detection["outcome"]),
                "True depth: "+show(detection["true_depth_m"]," m"),
                "Estimated depth: "+show(detection["estimated_depth_m"]," m"),
                "Depth error: "+show(detection["depth_error_cm"]," cm"),
                "Minimum estimated distance: "+show(summary["proximity"]["minimum_bucket_utility_distance_m"]," m"),
                "Minimum clearance margin: "+show(summary["proximity"]["minimum_clearance_margin_m"]," m"),
                "Max risk: "+show(risk["max_risk_score"])+" / 100 | "+show(risk["max_risk_level"]),
                "Max fatigue: "+show(summary["guardian"]["max_fatigue_score"]),
                "Final / Highest action: "+show(summary["decision"]["final_decision"])+" / "+show(summary["decision"]["highest_action"]),
                "PROTOTYPE SOFTWARE LATENCY",
                "Risk average: "+show(latency["risk_engine_avg_ms"]," ms"),
                "Decision average: "+show(latency["decision_engine_avg_ms"]," ms")] + metadata_lines
        if recorder.error:lines.append(recorder.error)
        elif summary:
            lines.append("JSON / CSV export saved")
            self.label.setToolTip(str(recorder.directory))
        reliability=summary.get("reliability") if summary else None
        if reliability:
            lines += ["RELIABILITY / SOFTWARE INJECTION ONLY",
                f"Faults: {reliability['fault_count']} | Recovered: {reliability['fault_recovery_count']}",
                "Mean recovery: "+show(reliability["mean_recovery_time_s"]," s"),
                "False-safe: "+str(reliability["false_safe_condition"]),
                "False-restrict: "+str(reliability["false_restrict_condition"])]
        active=list(recorder.events._active_faults.values())
        if active:
            lines += ["FAULT INJECTION ACTIVE"]+[f"{f.source}: {f.fault_type.value} / {f.severity}" for f in active]
        self.label.setText("\n".join(lines))
