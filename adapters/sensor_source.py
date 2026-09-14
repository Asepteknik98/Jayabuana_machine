"""Source-neutral subsurface contract for software and future adapters."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from core.safe_envelope import EnvelopeState
    from modules.safedig_vision.utility_model import MachineState, UtilityState


class SensorHealth(str, Enum):
    VALID = "VALID"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    OFFLINE = "OFFLINE"


@dataclass(frozen=True)
class SensorState:
    soil_type: str
    signal_quality: float
    confidence: float
    signal_strength: float
    anomaly_score: float
    anomaly_detected: bool
    sensor_health: SensorHealth
    timestamp: float  # Seconds in the sampling clock supplied to read().
    radargram: tuple[tuple[float, ...], ...]
    estimated_x_m: float | None = None
    estimated_z_m: float | None = None
    response_profile: str = "UNKNOWN"


class SensorSource(Protocol):
    def read(self, timestamp: float) -> SensorState | None: ...


@dataclass(frozen=True)
class SafeDigState:
    sensor: SensorState | None
    sensor_health: SensorHealth
    status: str
    action_info: str = ""
    utility: "UtilityState | None" = None
    machine: "MachineState | None" = None
    envelope: "EnvelopeState | None" = None

    @classmethod
    def from_sensor(cls, sensor: SensorState | None, now: float) -> "SafeDigState":
        if sensor is None:
            return cls(None, SensorHealth.OFFLINE, "SENSOR OFFLINE",
                       "SECONDARY VERIFICATION REQUIRED")
        health = sensor.sensor_health
        if health != SensorHealth.OFFLINE and now - sensor.timestamp > 1.0:
            health = SensorHealth.STALE
        if health in (SensorHealth.OFFLINE, SensorHealth.STALE):
            return cls(sensor, health, f"SENSOR {health.value}",
                       "SECONDARY VERIFICATION REQUIRED")
        weak = sensor.confidence < 0.65 or health == SensorHealth.DEGRADED
        if sensor.anomaly_detected:
            return cls(sensor, health, "POSSIBLE ANOMALY",
                       "SECONDARY VERIFICATION REQUIRED" if weak else "")
        if weak:
            return cls(sensor, health, "LOW SENSOR CONFIDENCE",
                       "SECONDARY VERIFICATION MAY BE REQUIRED")
        return cls(sensor, health, "NO SIGNIFICANT ANOMALY")
