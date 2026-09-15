"""Smooth reproducible illustration; no scientific GPR processing."""

from math import cos, exp, isfinite, pi, sin

from adapters.sensor_source import SensorHealth, SensorState
from modules.safedig_vision.soil_model import SOIL_PRESETS, SoilType

ANOMALY_DEPTH_M = 1.32
_TRUE_UTILITY_X_M = 6.5
_DEMO_RESPONSE_PROFILE = "NARROW_CONDUIT"
MAX_DEPTH_M = 2.0
SCAN_PERIOD_SECONDS = 12.0
ANOMALY_THRESHOLD = 0.55
DEGRADED_QUALITY = 0.70


class GPRSimulator:
    def __init__(self) -> None:
        self.soil_type = SoilType.NORMAL_SOIL
        self.online = True

    def set_soil(self, soil_type: str) -> None:
        self.soil_type = SoilType(soil_type)

    def read(self, timestamp: float, *, exposure=None, utility_x_m=_TRUE_UTILITY_X_M,
             utility_depth_m=ANOMALY_DEPTH_M, simulation_time=None) -> SensorState | None:
        if not isfinite(timestamp) or timestamp < 0:
            raise ValueError("Sampling time must be finite and non-negative")
        if not self.online:
            return None
        soil = SOIL_PRESETS[self.soil_type]
        phase_time = timestamp if simulation_time is None else simulation_time
        proximity = (1 - cos(2 * pi * phase_time / SCAN_PERIOD_SECONDS)) / 2 if exposure is None else exposure
        anomaly = 0.12 + 0.80 * proximity * soil.signal_quality
        # Partial scenario scan coverage reduces measurement confidence, not downstream risk.
        confidence = soil.base_confidence
        if exposure is not None and exposure > 0:
            confidence *= .5 + .5 * exposure
        strength = soil.signal_quality * (0.50 + 0.40 * proximity)
        rows = []
        for row in range(32):
            depth = row * MAX_DEPTH_M / 31
            values = []
            for column in range(48):
                x = column / 47
                response_depth = utility_depth_m + 0.7 * (x - 0.5) ** 2
                response = exp(-((depth - response_depth) / 0.09) ** 2)
                response *= exp(-((x - 0.5) / 0.30) ** 2)
                background = 0.07 + 0.05 * sin(column * 0.8 + row * 1.3 + phase_time)
                noise = (1 - soil.signal_quality) * 0.10 * (1 + sin(row * 2 + column))
                values.append(min(1.0, max(0.0, background + noise + response * anomaly)))
            rows.append(tuple(values))
        return SensorState(
            self.soil_type.value, soil.signal_quality, confidence,
            strength, anomaly, anomaly >= ANOMALY_THRESHOLD,
            SensorHealth.VALID if soil.signal_quality >= DEGRADED_QUALITY else SensorHealth.DEGRADED,
            timestamp, tuple(rows),
            # Stable soil-dependent measurement error; truth stays in simulator.
            estimated_x_m=utility_x_m + 0.04 * (1 - soil.signal_quality),
            estimated_z_m=-(utility_depth_m + 0.02 + 0.05 * (1 - soil.signal_quality)),
            response_profile=_DEMO_RESPONSE_PROFILE,
        )
