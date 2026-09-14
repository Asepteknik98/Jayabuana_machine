"""Smooth reproducible illustration; no scientific GPR processing."""

from math import cos, exp, isfinite, pi, sin

from adapters.sensor_source import SensorHealth, SensorState
from modules.safedig_vision.soil_model import SOIL_PRESETS, SoilType

ANOMALY_DEPTH_M = 1.32
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

    def read(self, timestamp: float) -> SensorState | None:
        if not isfinite(timestamp) or timestamp < 0:
            raise ValueError("Sampling time must be finite and non-negative")
        if not self.online:
            return None
        soil = SOIL_PRESETS[self.soil_type]
        proximity = (1 - cos(2 * pi * timestamp / SCAN_PERIOD_SECONDS)) / 2
        anomaly = 0.12 + 0.80 * proximity * soil.signal_quality
        strength = soil.signal_quality * (0.50 + 0.40 * proximity)
        rows = []
        for row in range(32):
            depth = row * MAX_DEPTH_M / 31
            values = []
            for column in range(48):
                x = column / 47
                response_depth = ANOMALY_DEPTH_M + 0.7 * (x - 0.5) ** 2
                response = exp(-((depth - response_depth) / 0.09) ** 2)
                response *= exp(-((x - 0.5) / 0.30) ** 2)
                background = 0.07 + 0.05 * sin(column * 0.8 + row * 1.3 + timestamp)
                noise = (1 - soil.signal_quality) * 0.10 * (1 + sin(row * 2 + column))
                values.append(min(1.0, max(0.0, background + noise + response * anomaly)))
            rows.append(tuple(values))
        return SensorState(
            self.soil_type.value, soil.signal_quality, soil.base_confidence,
            strength, anomaly, anomaly >= ANOMALY_THRESHOLD,
            SensorHealth.VALID if soil.signal_quality >= DEGRADED_QUALITY else SensorHealth.DEGRADED,
            timestamp, tuple(rows),
        )
