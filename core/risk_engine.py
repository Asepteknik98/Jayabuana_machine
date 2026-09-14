"""Prototype engineering logic, NOT a certified functional safety controller."""

from dataclasses import dataclass, field, replace
from enum import Enum
from math import isfinite

from adapters.sensor_source import SafeDigState, SensorHealth
from config import risk_config as config


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class RiskState:
    utility_risk: float | None = None
    confidence_risk: float | None = None
    fatigue_risk: float | None = None
    velocity_risk: float | None = None
    design_conflict_risk: float | None = None
    total_score: int | None = None
    level: RiskLevel | None = None
    risk_valid: bool = False
    risk_confidence: float | None = None
    verification_required: bool = True
    primary_risk_driver: str = "INSUFFICIENT DATA"
    contribution_breakdown: dict[str, float | None] = field(default_factory=dict)
    active_weights: dict[str, float] = field(default_factory=dict)
    timestamp: float | None = None
    fatigue_available: bool = False
    data_status: str = "RISK ESTIMATE DEGRADED / LIMITED"


class RiskEngine:
    def __init__(self) -> None:
        self._level: RiskLevel | None = None

    def level_for_score(self, score: int) -> RiskLevel:
        levels = list(RiskLevel)
        index = levels.index(self._level) if self._level is not None else 0
        while index < 3 and score > config.LEVEL_UP_THRESHOLDS[index]:
            index += 1
        while index > 0 and score < config.LEVEL_DOWN_THRESHOLDS[index - 1]:
            index -= 1
        self._level = levels[index]
        return self._level

    def update(self, state: SafeDigState) -> SafeDigState:
        sensor, utility, envelope, machine = state.sensor, state.utility, state.envelope, state.machine
        unavailable = RiskState(timestamp=sensor.timestamp if sensor else None)
        bad_health = (SensorHealth.OFFLINE, SensorHealth.STALE)
        if (sensor is None or machine is None or state.sensor_health in bad_health
                or sensor.sensor_health in bad_health
                or (utility is not None and utility.sensor_health in bad_health)):
            self._level = None
            return replace(state, risk=unavailable)
        speed = machine.bucket_speed_mps
        if (speed is None or not isfinite(speed) or speed < 0
                or any(not isfinite(v) or not 0 <= v <= 1 for v in
                       (sensor.confidence, sensor.signal_quality, sensor.anomaly_score))):
            self._level = None
            return replace(state, risk=unavailable)
        candidate = sensor.anomaly_detected or (utility is not None and utility.detected)
        confidence = utility.confidence if candidate and utility is not None else sensor.confidence
        if confidence is None or not isfinite(confidence) or not 0 <= confidence <= 1:
            self._level = None
            return replace(state, risk=unavailable)
        weak = confidence < config.VERIFY_THRESHOLD or SensorHealth.DEGRADED in (
            state.sensor_health, sensor.sensor_health, utility.sensor_health if utility else state.sensor_health)
        proximity = 0.0
        if candidate:
            if (envelope is None or not envelope.valid or envelope.effective_clearance_m is None
                    or envelope.distance_to_utility_m is None
                    or not isfinite(envelope.effective_clearance_m) or envelope.effective_clearance_m <= 0
                    or not isfinite(envelope.distance_to_utility_m) or envelope.distance_to_utility_m < 0):
                self._level = None
                return replace(state, risk=unavailable)
            ratio = envelope.distance_to_utility_m / envelope.effective_clearance_m
            proximity = clamp((config.FAR_DISTANCE_RATIO - ratio) /
                              (config.FAR_DISTANCE_RATIO - config.HIGH_DISTANCE_RATIO))
        evidence = confidence if candidate else 0.0
        design = state.design_conflict
        design_key = design.status.value if design is not None and design.valid else "UNKNOWN"
        conflict = config.DESIGN_RISKS[design_key]
        if weak:
            # Uncertainty is positive evidence of limited knowledge, never zero risk.
            proximity = max(proximity, config.UNCERTAINTY_RISK_FLOOR)
            evidence = max(evidence, config.UNCERTAINTY_RISK_FLOOR)
            conflict = max(conflict, config.UNCERTAINTY_RISK_FLOOR)
        components = {"utility": clamp(proximity), "confidence": clamp(evidence),
                      "velocity": clamp(speed / config.VELOCITY_REFERENCE_MPS),
                      "design": clamp(conflict), "fatigue": None}
        active = {k: config.WEIGHTS[k] for k, v in components.items() if v is not None}
        total_weight = sum(active.values())
        active = {k: w / total_weight for k, w in active.items()}
        contributions = {k: (v * active[k] * 100 if v is not None else None) for k, v in components.items()}
        score = round(clamp(sum(v for v in contributions.values() if v is not None), 0, 100))
        driver = max(active, key=lambda key: contributions[key])
        label = config.DRIVER_LABELS[driver]
        if weak and driver in ("utility", "confidence"):
            label = "UNCERTAIN UTILITY DETECTION"
        verification = weak or bool(design and design.verification_required)
        result = RiskState(components["utility"], components["confidence"], None,
                           components["velocity"], components["design"], score,
                           self.level_for_score(score), not weak,
                           min(confidence, sensor.signal_quality), verification, label,
                           contributions, active, sensor.timestamp, False,
                           "RISK ESTIMATE DEGRADED" if weak else "RISK ESTIMATE AVAILABLE • FATIGUE N/A")
        return replace(state, risk=result)
