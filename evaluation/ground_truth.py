"""Evaluation-only truth loaded from scenario configuration, never estimates."""
from dataclasses import dataclass

@dataclass(frozen=True)
class GroundTruth:
    utility_present: bool
    utility_type: str
    utility_x_m: float | None
    utility_depth_m: float | None
    utility_direction: str
    soil_type: str
    scenario_id: str
    timestamp: float
    operator_ground_truth: dict | None = None

    @classmethod
    def from_scenario(cls, scenario, timestamp):
        truth = scenario["utility_ground_truth"]
        return cls(truth["enabled"], truth.get("type", "UNKNOWN"), truth.get("x_m"),
            truth.get("depth_m"), truth.get("direction", "UNKNOWN"), scenario["soil"]["type"],
            scenario["scenario_id"], timestamp, scenario.get("operator_ground_truth"))
