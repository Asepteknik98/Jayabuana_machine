"""Transition-only events and a privacy-limited scalar telemetry projection."""
from time import monotonic
from math import isfinite


def value(obj, name):
    result = getattr(obj, name, None)
    return result.value if hasattr(result, "value") else result


def telemetry(state, simulation_time_s, latencies=None):
    machine, utility, envelope = state.machine, state.utility, state.envelope
    design, fusion, risk, decision = state.design_conflict, state.fusion, state.risk, state.decision
    fatigue = bool(fusion and fusion.fatigue_available)
    result = dict(simulation_time_s=simulation_time_s, monotonic_timestamp=monotonic(),
        current_depth_m=value(machine,"current_depth_m"), target_depth_m=value(machine,"target_depth_m"),
        bucket_x_m=value(machine,"bucket_x_m"), bucket_z_m=value(machine,"bucket_z_m"),
        bucket_speed_mps=value(machine,"bucket_speed_mps"), utility_detected=value(utility,"detected"),
        estimated_utility_depth_m=value(utility,"estimated_depth_m"), estimated_utility_x_m=value(utility,"estimated_x_m"),
        utility_confidence=value(utility,"confidence"), distance_to_utility_m=value(utility,"distance_to_bucket_m"),
        envelope_status=value(envelope,"status"), clearance_margin_m=value(envelope,"clearance_margin_m"),
        planned_clearance_m=value(design,"planned_clearance_m"), design_conflict=value(design,"status"),
        fatigue_score=fusion.fatigue_score if fatigue else None,
        attention_score=fusion.attention_score if fusion and fusion.attention_available else None,
        risk_score=value(risk,"total_score"), risk_level=value(risk,"level"), decision_action=value(decision,"action"),
        fusion_confidence=value(fusion,"fusion_confidence"), sensor_health=value(state,"sensor_health"),
        anomaly_detected=value(state.sensor,"anomaly_detected"),
        verification_required=value(fusion,"verification_required"),
        vision_valid=value(fusion,"vision_valid"),precision_valid=value(fusion,"precision_valid"),
        guardian_valid=value(fusion,"guardian_valid"),risk_valid=value(risk,"risk_valid"),
        machine_health=value(machine,"sensor_health"),guardian_health=value(state.operator,"camera_health"),
        precision_stale=bool(fusion and "PRECISION_STALE" in fusion.context_flags),
        guardian_stale=bool(fusion and "GUARDIAN_STALE" in fusion.context_flags and state.operator
            and state.operator.timestamp is not None and state.operator.camera_available),
        detection_available=bool(state.sensor and value(state,"sensor_health") not in ("OFFLINE","STALE")
            and fusion and "VISION_STALE" not in fusion.context_flags),
        fusion_latency_ms=(latencies or {}).get("fusion_latency_ms"),
        risk_latency_ms=(latencies or {}).get("risk_latency_ms"),
        decision_latency_ms=(latencies or {}).get("decision_latency_ms"))
    return {key: None if isinstance(v, float) and not isfinite(v) else v for key,v in result.items()}


class EventLogger:
    def __init__(self):
        self.events = []
        self.previous = {}
        self._active_faults = {}
        self._pending_recovery = {}

    def emit(self, event_type, simulation_time_s, source="Experiment", severity="INFO", message="", data=None):
        self.events.append(dict(simulation_time_s=simulation_time_s, monotonic_timestamp=monotonic(),
            event_type=event_type, source=source, severity=severity, message=message or event_type.replace("_"," "), data=data or {}))

    def observe(self, row):
        checks = {
            "GPR_ANOMALY_DETECTED": (row["anomaly_detected"], "SafeDigVision"),
            "UTILITY_ESTIMATED": (bool(row["utility_detected"] and row["estimated_utility_depth_m"] is not None), "SafeDigVision"),
            "SENSOR_DEGRADED": (row["sensor_health"] == "DEGRADED" or row.get("machine_health")=="DEGRADED", "SensorFusion"),
            "SENSOR_OFFLINE": (row["sensor_health"]=="OFFLINE" or row.get("guardian_health")=="OFFLINE", "SensorFusion"),
            "SENSOR_STALE": (row["sensor_health"]=="STALE" or row.get("precision_stale") or row.get("guardian_stale"), "SensorFusion"),
            "RISK_INVALID": (row.get("risk_valid") is False, "RiskEngine"),
            "DECISION_FALLBACK": (row.get("decision_action")=="VERIFY" and row.get("risk_valid") is False, "DecisionEngine"),
            "DESIGN_CONFLICT_DETECTED": (row["design_conflict"] == "DESIGN_CONFLICT", "SafeDigPrecision"),
            "ENVELOPE_APPROACHING": (row["envelope_status"] == "APPROACHING", "SafeEnvelope"),
            "ENVELOPE_ENTERED": (row["envelope_status"] == "INSIDE", "SafeEnvelope"),
            "FATIGUE_ELEVATED": (row["fatigue_score"] is not None and 30 <= row["fatigue_score"] < 60, "SafeDigGuardian"),
            "FATIGUE_HIGH": (row["fatigue_score"] is not None and row["fatigue_score"] >= 60, "SafeDigGuardian"),
            "VERIFICATION_REQUIRED": (row["verification_required"], "SensorFusion")}
        data = {key: row[key] for key in ("estimated_utility_depth_m","utility_confidence","risk_score","fatigue_score")}
        for event, (active, source) in checks.items():
            if active and not self.previous.get(event):
                self.emit(event,row["simulation_time_s"],source,"WARNING",data=data)
            self.previous[event] = active
        for key, event, source in (("risk_level","RISK_LEVEL_CHANGED","RiskEngine"),
                                    ("decision_action","DECISION_CHANGED","DecisionEngine")):
            current = row[key]
            if current != self.previous.get(key):
                self.emit(event,row["simulation_time_s"],source,data={"from":self.previous.get(key),"to":current})
            self.previous[key] = current

    def observe_faults(self, faults, row):
        current={f.fault_id:f for f in faults if f.active}
        t=row["simulation_time_s"]
        for key,fault in current.items():
            if key not in self._active_faults:
                self.emit("FAULT_STARTED",t,"FaultInjection",data=dict(fault_id=key,
                    fault_type=fault.fault_type.value,source=fault.source,severity=fault.severity))
        for key,fault in self._active_faults.items():
            if key not in current:
                self.emit("FAULT_CLEARED",t,"FaultInjection",data=dict(fault_id=key,source=fault.source))
                self._pending_recovery[key]=fault
        for key,fault in list(self._pending_recovery.items()):
            healthy=(bool(row.get("vision_valid")) and row.get("sensor_health")=="VALID" and row.get("fusion_confidence")!="LOW"
                     if fault.source=="GPR" else bool(row.get("precision_valid")) and row.get("machine_health")=="VALID"
                     if fault.source=="PRECISION" else bool(row.get("guardian_valid")))
            if healthy and not any(f.source==fault.source for f in current.values()):
                self.emit("SENSOR_RECOVERED",t,"SensorFusion",data=dict(fault_id=key,source=fault.source))
                del self._pending_recovery[key]
        self._active_faults=current
