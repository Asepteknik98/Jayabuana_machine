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
        from core.sensor_fusion import SensorFusion
        fusion = state.fusion or SensorFusion().fuse(state)
        return replace(state, fusion=fusion, risk=self.evaluate(fusion))

    def evaluate(self, fusion) -> RiskState:
        if not fusion.fusion_valid:
            self._level = None
            return RiskState(timestamp=fusion.timestamp)
        speed = fusion.bucket_speed_mps
        confidence = fusion.utility_confidence
        if (speed is None or not isfinite(speed) or speed < 0 or confidence is None
                or not isfinite(confidence) or not 0 <= confidence <= 1
                or fusion.signal_quality is None or not isfinite(fusion.signal_quality)):
            self._level = None
            return RiskState(timestamp=fusion.timestamp)
        weak = confidence < config.VERIFY_THRESHOLD or fusion.sensor_health == "DEGRADED"
        proximity = 0.0
        if fusion.utility_detected:
            radius, distance = fusion.effective_clearance_m, fusion.utility_distance_m
            if (radius is None or distance is None or not isfinite(radius) or not isfinite(distance)
                    or radius <= 0 or distance < 0):
                self._level = None
                return RiskState(timestamp=fusion.timestamp)
            proximity = clamp((config.FAR_DISTANCE_RATIO - distance / radius) /
                              (config.FAR_DISTANCE_RATIO - config.HIGH_DISTANCE_RATIO))
        evidence = confidence if fusion.utility_detected else 0.0
        conflict = config.DESIGN_RISKS.get(fusion.design_conflict_status, config.DESIGN_RISKS["UNKNOWN"])
        fatigue = fusion.fatigue_normalized if fusion.fatigue_available else None
        if fatigue is not None:
            fatigue = clamp(fatigue) if isfinite(fatigue) else None
        if weak:
            # Uncertainty is positive evidence of limited knowledge, never zero risk.
            proximity = max(proximity, config.UNCERTAINTY_RISK_FLOOR)
            evidence = max(evidence, config.UNCERTAINTY_RISK_FLOOR)
            conflict = max(conflict, config.UNCERTAINTY_RISK_FLOOR)
        components = {"utility": clamp(proximity), "confidence": clamp(evidence),
                      "velocity": clamp(speed / config.VELOCITY_REFERENCE_MPS),
                      "design": clamp(conflict), "fatigue": fatigue}
        active = {k: config.WEIGHTS[k] for k, v in components.items() if v is not None}
        total_weight = sum(active.values())
        active = {k: w / total_weight for k, w in active.items()}
        contributions = {k: (v * active[k] * 100 if v is not None else None) for k, v in components.items()}
        score = round(clamp(sum(v for v in contributions.values() if v is not None), 0, 100))
        driver = max(active, key=lambda key: contributions[key])
        label = config.DRIVER_LABELS[driver]
        if weak and driver in ("utility", "confidence"):
            label = "UNCERTAIN UTILITY DETECTION"
        verification = weak or fusion.verification_required
        result = RiskState(components["utility"], components["confidence"], fatigue,
                           components["velocity"], components["design"], score,
                           self.level_for_score(score), not weak,
                           min(confidence, fusion.signal_quality), verification, label,
                           contributions, active, fusion.timestamp, fatigue is not None,
                           "RISK ESTIMATE DEGRADED" if weak else
                           "RISK ESTIMATE AVAILABLE" if fatigue is not None else
                           "GUARDIAN DATA UNAVAILABLE / FATIGUE N/A")
        return result
