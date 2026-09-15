"""Planned rectangle versus circular utility envelope in world metres."""

from dataclasses import dataclass, replace
from enum import Enum
from math import hypot, isfinite

from adapters.sensor_source import SafeDigState, SensorHealth

DEFAULT_TRENCH_CENTER_X_M = 6.5  # Fixed demo plan, independent of sensor estimates.
NEAR_CLEARANCE_M = 0.15
MIN_RELIABLE_CONFIDENCE = 0.75


class ConflictStatus(str, Enum):
    NO_CONFLICT = "NO_CONFLICT"
    POTENTIAL_CONFLICT = "POTENTIAL_CONFLICT"
    DESIGN_CONFLICT = "DESIGN_CONFLICT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DesignConflictState:
    status: ConflictStatus = ConflictStatus.UNKNOWN
    conflict_detected: bool = False
    potential_conflict: bool = False
    verification_required: bool = True
    planned_clearance_m: float | None = None
    horizontal_overlap: bool | None = None
    vertical_overlap: bool | None = None
    reason: str = "Insufficient utility, envelope or planned geometry data."
    valid: bool = False
    timestamp: float | None = None
    left_x_m: float | None = None
    right_x_m: float | None = None
    bottom_z_m: float | None = None


class DesignConflictEngine:
    def update(self, state: SafeDigState) -> SafeDigState:
        machine, utility, envelope = state.machine, state.utility, state.envelope
        result = DesignConflictState(timestamp=utility.timestamp if utility else None)
        if machine is None:
            return replace(state, design_conflict=result)
        dimensions = (machine.excavation_center_x_m, machine.target_width_m,
                      machine.target_depth_m, machine.target_slope_percent)
        if (any(v is None or not isfinite(v) for v in dimensions)
                or machine.target_width_m <= 0 or machine.target_depth_m <= 0):
            return replace(state, design_conflict=result)
        # MVP-0 simplified 2D excavation geometry; slope retained but not applied.
        left = machine.excavation_center_x_m - machine.target_width_m / 2
        right = machine.excavation_center_x_m + machine.target_width_m / 2
        bottom = -machine.target_depth_m
        result = replace(result,left_x_m=left,right_x_m=right,bottom_z_m=bottom)
        sensor = state.sensor
        if (sensor and utility and not utility.detected and not sensor.anomaly_detected
                and sensor.anomaly_score < .4 and sensor.confidence >= MIN_RELIABLE_CONFIDENCE
                and state.sensor_health == SensorHealth.VALID and sensor.sensor_health == SensorHealth.VALID
                and utility.sensor_health == SensorHealth.VALID):
            return replace(state, design_conflict=replace(result, status=ConflictStatus.NO_CONFLICT,
                valid=True, verification_required=False, timestamp=sensor.timestamp,
                reason="No significant utility response in current valid observation; not proof of absence."))
        if (utility is None or envelope is None or not utility.valid or not utility.detected
                or not envelope.valid or state.sensor_health in (SensorHealth.OFFLINE,SensorHealth.STALE)
                or utility.sensor_health in (SensorHealth.OFFLINE,SensorHealth.STALE)):
            return replace(state,design_conflict=result)
        x,z,r,c = utility.estimated_x_m,utility.estimated_z_m,envelope.effective_clearance_m,utility.confidence
        if any(v is None or not isfinite(v) for v in (x,z,r,c)) or r < 0 or not 0 <= c <= 1:
            return replace(state,design_conflict=result)
        # Signed point-to-rectangle distance, then subtract circular clearance.
        dx=max(left-x,0.0,x-right)
        dz=max(bottom-z,0.0,z)
        signed=hypot(dx,dz)
        if left <= x <= right and bottom <= z <= 0:
            signed=-min(x-left,right-x,z-bottom,-z)
        clearance=signed-r
        if abs(clearance) < 1e-9:
            clearance=0.0  # Stabilize exact boundary contact against float roundoff.
        horizontal=x+r >= left and x-r <= right
        vertical=z+r >= bottom and z-r <= 0
        uncertain=c < MIN_RELIABLE_CONFIDENCE or SensorHealth.DEGRADED in (state.sensor_health,utility.sensor_health)
        if uncertain:
            status=ConflictStatus.POTENTIAL_CONFLICT
            reason="Low-confidence estimate; secondary verification required."
        elif clearance <= 0:
            status=ConflictStatus.DESIGN_CONFLICT
            reason="Target excavation intersects utility protective envelope."
        elif clearance <= NEAR_CLEARANCE_M:
            status=ConflictStatus.POTENTIAL_CONFLICT
            reason="Planned excavation is close to utility protective envelope."
        else:
            status=ConflictStatus.NO_CONFLICT
            reason="Planned excavation does not intersect utility protective envelope."
        result=replace(result,status=status,conflict_detected=status==ConflictStatus.DESIGN_CONFLICT,
                       potential_conflict=status==ConflictStatus.POTENTIAL_CONFLICT,
                       verification_required=status==ConflictStatus.POTENTIAL_CONFLICT,
                       planned_clearance_m=clearance,horizontal_overlap=horizontal,
                       vertical_overlap=vertical,reason=reason,valid=True)
        return replace(state,design_conflict=result)
