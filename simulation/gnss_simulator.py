"""Local machine origin only; no geographic or physical GNSS implementation."""
from dataclasses import dataclass

@dataclass(frozen=True)
class PositionState:
    machine_x: float
    machine_y: float
    valid: bool
    timestamp: float

class GNSSSimulator:
    def read(self, timestamp):
        return PositionState(0., 0., True, timestamp)
