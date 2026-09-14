"""MVP-0 software recommendations only; no physical control outputs."""

from dataclasses import dataclass, replace
from enum import Enum
from math import isfinite

from adapters.sensor_source import SafeDigState, SensorHealth
from core.risk_engine import RiskLevel
from core.safe_envelope import EnvelopeStatus
from modules.safedig_precision.design_conflict import ConflictStatus

VERIFY_CONFIDENCE = 0.65
LOW_CLEARANCE_M = 0.05
DEESCALATION_CYCLES = 3


class DecisionAction(str, Enum):
    NORMAL = "NORMAL"
    WARN = "WARN"
    SLOW = "SLOW"
    VERIFY = "VERIFY"
    RESTRICT = "RESTRICT"


PRIORITY = {action: index for index, action in enumerate(DecisionAction)}
MESSAGES = {DecisionAction.NORMAL: "NORMAL OPERATION", DecisionAction.WARN: "PROCEED WITH CAUTION",
            DecisionAction.SLOW: "REDUCE DIGGING SPEED", DecisionAction.VERIFY: "SECONDARY VERIFICATION REQUIRED",
            DecisionAction.RESTRICT: "RESTRICT MOTION TOWARD UTILITY"}
GUIDANCE = {DecisionAction.NORMAL: "NORMAL_SPEED", DecisionAction.WARN: "NORMAL_SPEED",
            DecisionAction.SLOW: "REDUCED_SPEED", DecisionAction.VERIFY: "HOLD_FOR_VERIFICATION",
            DecisionAction.RESTRICT: "RESTRICT_TOWARD_RISK_ZONE"}


@dataclass(frozen=True)
class DecisionState:
    action: DecisionAction
    message: str
    reason: str
    priority: int
    verification_required: bool
    restrict_direction: str | None
    speed_guidance: str
    valid: bool
    timestamp: float | None


class DecisionEngine:
    def __init__(self) -> None:
        self._previous: DecisionState | None = None
        self._pending: DecisionAction | None = None
        self._count = 0

    def update(self, state: SafeDigState) -> SafeDigState:
        risk, utility, envelope, design = state.risk, state.utility, state.envelope, state.design_conflict
        sensor = state.sensor
        offline = (sensor is None or state.sensor_health in (SensorHealth.OFFLINE, SensorHealth.STALE)
                   or sensor.sensor_health in (SensorHealth.OFFLINE, SensorHealth.STALE)
                   or (utility is not None and utility.sensor_health in (SensorHealth.OFFLINE, SensorHealth.STALE)))
        fusion = state.fusion
        offline = offline or bool(fusion and (not fusion.vision_valid or not fusion.precision_valid))
        fatigue_high = bool(fusion and fusion.fatigue_available and "FATIGUE_HIGH" in fusion.context_flags)
        timestamp = risk.timestamp if risk else (sensor.timestamp if sensor else None)
        level = risk.level if risk else None
        known = utility is not None and utility.detected and utility.valid
        confidence = utility.confidence if known else (sensor.confidence if sensor else None)
        low = confidence is None or not isfinite(confidence) or confidence < VERIFY_CONFIDENCE
        env_valid = envelope is not None and envelope.valid
        inside = env_valid and envelope.status == EnvelopeStatus.INSIDE
        approaching = env_valid and envelope.status == EnvelopeStatus.APPROACHING
        conflict = design is not None and design.valid and design.status == ConflictStatus.DESIGN_CONFLICT
        potential = design is not None and design.status == ConflictStatus.POTENTIAL_CONFLICT
        unresolved = bool(sensor and sensor.anomaly_detected and not known)
        risk_missing = risk is None or level is None or risk.total_score is None
        weak = (low or state.sensor_health == SensorHealth.DEGRADED
                or bool(sensor and sensor.sensor_health == SensorHealth.DEGRADED)
                or bool(utility and utility.sensor_health == SensorHealth.DEGRADED)
                or risk_missing or (risk is not None and (not risk.risk_valid or risk.risk_confidence is None
                    or not isfinite(risk.risk_confidence) or risk.risk_confidence < VERIFY_CONFIDENCE)))
        verify = (offline or weak or unresolved or potential or bool(risk and risk.verification_required)
                  or bool(design and design.verification_required) or (known and not env_valid))
        near = (env_valid and envelope.clearance_margin_m is not None
                and isfinite(envelope.clearance_margin_m) and envelope.clearance_margin_m <= LOW_CLEARANCE_M)
        restrict = (not offline and not risk_missing and known and env_valid
                    and ((level == RiskLevel.CRITICAL and (inside or conflict or near))
                         or (inside and level == RiskLevel.HIGH)))
        if restrict:
            action = DecisionAction.RESTRICT
            reason = ("HIGH / CRITICAL RISK + BUCKET INSIDE UTILITY PROTECTIVE ENVELOPE" if inside
                      else "CRITICAL RISK + PLANNED CONFLICT OR LOW UTILITY CLEARANCE")
        elif verify:
            action = DecisionAction.VERIFY
            reason = ("SUBSURFACE SENSOR DATA UNAVAILABLE" if offline else
                      "LOW-CONFIDENCE OR INCOMPLETE UTILITY / RISK DATA" if weak or unresolved else
                      "UTILITY OR PLANNED EXCAVATION REQUIRES SECONDARY VERIFICATION")
        elif level in (RiskLevel.HIGH, RiskLevel.CRITICAL) or conflict or approaching or inside:
            action = DecisionAction.SLOW
            reason = ("PLANNED EXCAVATION INTERSECTS UTILITY ENVELOPE" if conflict else
                      "BUCKET APPROACHING UTILITY ENVELOPE" if approaching else
                      "ELEVATED RISK: " + risk.primary_risk_driver)
        elif level == RiskLevel.CAUTION or fatigue_high:
            action = DecisionAction.WARN
            reason = ("OPERATOR FATIGUE ELEVATED; CONSIDER PAUSE / OPERATOR CHECK" if fatigue_high
                      else "RISK INCREASING: " + risk.primary_risk_driver)
        else:
            action = DecisionAction.NORMAL
            reason = "NO ACTIVE SAFETY CONFLICT IN AVAILABLE INPUTS"
        if fatigue_high and action in (DecisionAction.SLOW, DecisionAction.RESTRICT):
            reason += "; HIGH OPERATOR FATIGUE + UTILITY PROXIMITY"
        result = DecisionState(action, MESSAGES[action], reason, PRIORITY[action], verify,
                               "TOWARD_UTILITY" if action == DecisionAction.RESTRICT else None,
                               GUIDANCE[action], not offline and not weak, timestamp)
        if offline:
            result = replace(result, message="SUBSURFACE SENSOR DATA UNAVAILABLE — SECONDARY VERIFICATION REQUIRED")
        # Do not retain a directional claim after its evidence goes offline.
        if self._previous and result.priority < self._previous.priority and not offline:
            self._count = self._count + 1 if self._pending == action else 1
            self._pending = action
            if self._count < DEESCALATION_CYCLES:
                result = replace(result, action=self._previous.action, priority=self._previous.priority,
                                 message=self._previous.message, restrict_direction=self._previous.restrict_direction,
                                 speed_guidance=self._previous.speed_guidance,
                                 reason="PREVIOUS RECOMMENDATION HELD; WAITING FOR 3 STABLE UPDATES. " + reason)
            else:
                self._pending = None
                self._count = 0
        else:
            self._pending = None
            self._count = 0
        self._previous = result
        return replace(state, decision=result)
