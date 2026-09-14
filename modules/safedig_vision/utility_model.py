"""Estimated utility and machine world coordinates (Z positive upward)."""

from dataclasses import dataclass
from enum import Enum

from adapters.sensor_source import SensorHealth
from config.envelope_config import BASE_SAFE_CLEARANCE_M


class UtilityType(str, Enum):
    UNKNOWN = "UNKNOWN"
    CONDUCTIVE_UTILITY = "CONDUCTIVE_UTILITY"
    POSSIBLE_POWER_CABLE = "POSSIBLE_POWER_CABLE"
    POSSIBLE_WATER_PIPE = "POSSIBLE_WATER_PIPE"
    POSSIBLE_GAS_PIPE = "POSSIBLE_GAS_PIPE"
    POSSIBLE_FIBER_OPTIC_CONDUIT = "POSSIBLE_FIBER_OPTIC_CONDUIT"


@dataclass(frozen=True)
class MachineState:
    bucket_x_m: float
    bucket_z_m: float
    target_depth_m: float | None = None
    target_width_m: float | None = None
    target_slope_percent: float | None = None
    current_depth_m: float | None = None
    excavation_center_x_m: float | None = None


@dataclass(frozen=True)
class UtilityState:
    utility_id: str = "UNKNOWN"
    detected: bool = False
    estimated_type: UtilityType = UtilityType.UNKNOWN
    estimated_x_m: float | None = None
    estimated_z_m: float | None = None
    direction: str = "UNKNOWN"
    confidence: float | None = None
    distance_to_bucket_m: float | None = None
    safe_clearance_m: float = BASE_SAFE_CLEARANCE_M
    sensor_health: SensorHealth = SensorHealth.OFFLINE
    valid: bool = False
    timestamp: float | None = None
    status: str = "UTILITY ESTIMATE UNAVAILABLE"
    confidence_status: str = "UNAVAILABLE"
    verification_info: str = "SECONDARY VERIFICATION REQUIRED"

    @property
    def estimated_depth_m(self) -> float | None:
        return -self.estimated_z_m if self.estimated_z_m is not None else None

    @property
    def type_label(self) -> str:
        if self.estimated_type == UtilityType.CONDUCTIVE_UTILITY:
            return "Possible Conductive Utility"
        if self.estimated_type == UtilityType.UNKNOWN:
            return "UNKNOWN"
        return self.estimated_type.value.replace("_", " ").title()
