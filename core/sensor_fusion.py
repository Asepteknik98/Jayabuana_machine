"""Pure snapshot assembly. Never samples sources or recomputes geometry."""
from math import isfinite
from time import monotonic
from config import fusion_config as config
from config.risk_config import VERIFY_THRESHOLD
from domain.fusion_state import FusionState


def finite(value):
    return value is not None and isfinite(value)


def fresh(timestamp, now, threshold):
    return finite(timestamp) and finite(now) and 0 <= now - timestamp <= threshold


class SensorFusion:
    def fuse(self, state, now=None):
        now = monotonic() if now is None else now
        sensor, machine, operator = state.sensor, state.machine, state.operator
        utility, envelope, design = state.utility, state.envelope, state.design_conflict
        flags = set()
        vision_fresh = bool(sensor and fresh(sensor.timestamp, now, config.VISION_STALE_AFTER_S))
        precision_fresh = bool(machine and fresh(machine.timestamp, now, config.PRECISION_STALE_AFTER_S))
        guardian_fresh = bool(operator and all(fresh(t, now, config.GUARDIAN_STALE_AFTER_S)
            for t in (operator.timestamp, operator.last_frame_timestamp, operator.last_detection_timestamp)))
        for name, present, current in (("VISION", sensor, vision_fresh),
                ("PRECISION", machine, precision_fresh), ("GUARDIAN", operator, guardian_fresh)):
            if present and not current:
                flags.add(name + "_STALE")
        health = state.sensor_health.value
        if sensor and sensor.sensor_health.value in ("OFFLINE", "STALE", "DEGRADED"):
            health = sensor.sensor_health.value
        if sensor and not vision_fresh and health != "OFFLINE":
            health = "STALE"
        candidate = bool((sensor and sensor.anomaly_detected) or (utility and utility.detected))
        if candidate and any(item is not None and not fresh(item.timestamp, now, config.VISION_STALE_AFTER_S)
                             for item in (utility, envelope)):
            vision_fresh = False
            flags.add("VISION_STALE")
            if health != "OFFLINE": health = "STALE"
        confidence = utility.confidence if candidate and utility else sensor.confidence if sensor else None
        vision = bool(vision_fresh and health not in ("OFFLINE", "STALE") and sensor
            and all(finite(v) and 0 <= v <= 1 for v in (confidence, sensor.signal_quality, sensor.anomaly_score)))
        if candidate:
            vision = bool(vision and utility and utility.valid and utility.sensor_health.value not in ("OFFLINE", "STALE")
                and envelope and envelope.valid and finite(envelope.effective_clearance_m)
                and envelope.effective_clearance_m > 0 and finite(envelope.distance_to_utility_m)
                and envelope.distance_to_utility_m >= 0)
        precision = bool(precision_fresh and all(finite(v) for v in
            (machine.bucket_x_m, machine.bucket_z_m, machine.bucket_speed_mps)) and machine.bucket_speed_mps >= 0)
        guardian = bool(guardian_fresh and operator.camera_available and operator.camera_health.value == "VALID"
            and operator.valid and operator.face_detected and operator.face_count == 1 and operator.fatigue_valid
            and finite(operator.fatigue_score))
        fatigue = max(0., min(1., operator.fatigue_score / 100)) if guardian else None
        attention = bool(guardian and finite(operator.attention_score) and 0 <= operator.attention_score <= 1)
        env_status = envelope.status.value if envelope and envelope.valid else "UNAVAILABLE"
        design_fresh = bool(design and fresh(design.timestamp, now, config.VISION_STALE_AFTER_S))
        design_status = design.status.value if design and design.valid and design_fresh else "UNKNOWN"
        if design and not design_fresh: flags.add("DESIGN_STALE")
        weak = not finite(confidence) or confidence < VERIFY_THRESHOLD or health == "DEGRADED"
        verify = not vision or not precision or weak or design_status == "UNKNOWN" or bool(design and design.verification_required)
        if weak and candidate: flags.add("LOW_CONFIDENCE_UTILITY")
        if health == "DEGRADED": flags.add("SENSOR_DEGRADED")
        if not guardian: flags.add("GUARDIAN_DATA_UNAVAILABLE")
        if guardian and fatigue >= config.HIGH_FATIGUE_THRESHOLD: flags.add("FATIGUE_HIGH")
        if attention and operator.attention_score < config.LOW_ATTENTION_THRESHOLD: flags.add("LOW_ATTENTION")
        if vision and precision:
            if env_status in ("APPROACHING", "INSIDE"): flags.add("UTILITY_NEAR")
            if env_status == "INSIDE": flags.add("UTILITY_INSIDE_ENVELOPE")
            if design_status == "DESIGN_CONFLICT": flags.add("DESIGN_CONFLICT_ACTIVE")
        if "FATIGUE_HIGH" in flags and flags.intersection(("UTILITY_NEAR", "DESIGN_CONFLICT_ACTIVE")):
            flags.add("MULTI_RISK_CONTEXT")
        usable = vision and precision
        quality = "UNAVAILABLE" if not usable else "LOW" if weak or "GUARDIAN_STALE" in flags else "MEDIUM" if not guardian or verify else "HIGH"
        return FusionState(timestamp=now, vision_valid=vision, precision_valid=precision, guardian_valid=guardian,
            utility_detected=candidate, utility_confidence=confidence,
            utility_distance_m=envelope.distance_to_utility_m if envelope else None, sensor_health=health,
            envelope_status=env_status, clearance_margin_m=envelope.clearance_margin_m if envelope else None,
            effective_clearance_m=envelope.effective_clearance_m if envelope else None,
            bucket_speed_mps=machine.bucket_speed_mps if machine else None, design_conflict_status=design_status,
            fatigue_available=guardian, fatigue_score=operator.fatigue_score if operator else None,
            fatigue_normalized=fatigue, attention_available=attention,
            attention_score=operator.attention_score if operator else None, verification_required=verify,
            fusion_valid=usable, fusion_confidence=quality, context_flags=frozenset(flags),
            signal_quality=sensor.signal_quality if sensor else None)
