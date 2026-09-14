"""World-coordinate proximity only; no risk scoring or machine commands."""

from dataclasses import dataclass, replace
from enum import Enum
from math import hypot, isfinite

from adapters.sensor_source import SafeDigState, SensorHealth
from config.envelope_config import MAX_UNCERTAINTY_MARGIN_M, APPROACHING_MARGIN_M


class EnvelopeStatus(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    CLEAR = "CLEAR"
    APPROACHING = "APPROACHING"
    INSIDE = "INSIDE"


@dataclass(frozen=True)
class EnvelopeState:
    base_clearance_m: float | None = None
    uncertainty_margin_m: float | None = None
    effective_clearance_m: float | None = None
    distance_to_utility_m: float | None = None
    clearance_margin_m: float | None = None
    status: EnvelopeStatus = EnvelopeStatus.UNAVAILABLE
    valid: bool = False
    timestamp: float | None = None
    center_x_m: float | None = None
    center_z_m: float | None = None
    information: str = "SECONDARY VERIFICATION REQUIRED"


class SafeEnvelopeEngine:
    def __init__(self, max_uncertainty_margin_m: float = MAX_UNCERTAINTY_MARGIN_M,
                 approaching_margin_m: float = APPROACHING_MARGIN_M) -> None:
        if any(not isfinite(v) or v < 0 for v in (max_uncertainty_margin_m, approaching_margin_m)):
            raise ValueError("Envelope margins must be finite and non-negative")
        self.max_uncertainty_margin_m = max_uncertainty_margin_m
        self.approaching_margin_m = approaching_margin_m

    def update(self, state: SafeDigState) -> SafeDigState:
        utility, machine = state.utility, state.machine
        unavailable = EnvelopeState(timestamp=utility.timestamp if utility else None)
        bad_health = (SensorHealth.OFFLINE, SensorHealth.STALE)
        if (utility is None or machine is None or not utility.valid or not utility.detected
                or state.sensor_health in bad_health or utility.sensor_health in bad_health):
            return replace(state, envelope=unavailable)
        values = (utility.estimated_x_m, utility.estimated_z_m, utility.confidence,
                  utility.safe_clearance_m, machine.bucket_x_m, machine.bucket_z_m)
        if (any(v is None or not isfinite(v) for v in values)
                or not 0 <= utility.confidence <= 1 or utility.safe_clearance_m < 0
                or utility.estimated_z_m > 0):
            return replace(state, envelope=unavailable)
        uncertainty = (1 - utility.confidence) * self.max_uncertainty_margin_m
        effective = utility.safe_clearance_m + uncertainty
        distance = hypot(machine.bucket_x_m - utility.estimated_x_m,
                         machine.bucket_z_m - utility.estimated_z_m)
        margin = distance - effective
        if distance <= effective:
            status = EnvelopeStatus.INSIDE
        elif distance <= effective + self.approaching_margin_m:
            status = EnvelopeStatus.APPROACHING
        else:
            status = EnvelopeStatus.CLEAR
        result = EnvelopeState(utility.safe_clearance_m, uncertainty, effective, distance,
                               margin, status, True, utility.timestamp,
                               utility.estimated_x_m, utility.estimated_z_m, "")
        return replace(state, envelope=result)
