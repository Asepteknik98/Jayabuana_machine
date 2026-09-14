"""Source-neutral, confidence-aware prototype inference, not trained ML."""

from dataclasses import dataclass, replace
from math import hypot, isfinite

from adapters.sensor_source import SafeDigState, SensorHealth
from modules.safedig_vision.utility_model import MachineState, UtilityState, UtilityType


@dataclass(frozen=True)
class DetectorConfig:
    candidate_threshold: float = 0.40
    likely_threshold: float = 0.75
    confidence_weights: tuple[float, float, float] = (0.5, 0.3, 0.2)


class UtilityDetector:
    def __init__(self, config: DetectorConfig = DetectorConfig()) -> None:
        weights = config.confidence_weights
        if len(weights) != 3 or any(not isfinite(w) or w < 0 for w in weights) or sum(weights) <= 0:
            raise ValueError("Confidence weights must be three non-negative finite values with positive sum")
        self.config = config

    def update(self, state: SafeDigState, machine: MachineState | None) -> SafeDigState:
        sensor = state.sensor
        health = state.sensor_health
        result = UtilityState(sensor_health=health, timestamp=sensor.timestamp if sensor else None)
        if sensor is None or health in (SensorHealth.OFFLINE, SensorHealth.STALE):
            return replace(state, utility=result, machine=machine)
        inputs = (sensor.confidence, sensor.signal_quality, sensor.anomaly_score)
        if not all(isfinite(x) and 0 <= x <= 1 for x in inputs):
            return replace(state, utility=result, machine=machine)
        weights = self.config.confidence_weights
        confidence = sum(x * w for x, w in zip(inputs, weights)) / sum(weights)
        low = confidence < self.config.likely_threshold or health == SensorHealth.DEGRADED
        result = replace(result, confidence=confidence, confidence_status="LOW" if low else "HIGH")
        if sensor.anomaly_score < self.config.candidate_threshold:
            result = replace(result, status="NO SIGNIFICANT ANOMALY",
                             verification_info="SECONDARY VERIFICATION REQUIRED" if low else "")
            return replace(state, utility=result, machine=machine)
        x, z = sensor.estimated_x_m, sensor.estimated_z_m
        located = x is not None and z is not None and isfinite(x) and isfinite(z) and z <= 0
        # PROTOTYPE HEURISTIC CLASSIFICATION from response, never ground truth.
        kind = {"NARROW_CONDUIT": UtilityType.POSSIBLE_FIBER_OPTIC_CONDUIT,
                "CONDUCTIVE": UtilityType.CONDUCTIVE_UTILITY}.get(sensor.response_profile, UtilityType.UNKNOWN)
        distance = None
        if located and machine is not None and all(isfinite(v) for v in (machine.bucket_x_m, machine.bucket_z_m)):
            distance = hypot(machine.bucket_x_m - x, machine.bucket_z_m - z)
        result = replace(result, utility_id="CANDIDATE-1", detected=True,
                         estimated_type=kind, estimated_x_m=x if located else None,
                         estimated_z_m=z if located else None, distance_to_bucket_m=distance,
                         valid=located, status="POSSIBLE UTILITY" if low else "LIKELY UTILITY",
                         verification_info="SECONDARY VERIFICATION REQUIRED" if low or not located else "")
        return replace(state, utility=result, machine=machine)
