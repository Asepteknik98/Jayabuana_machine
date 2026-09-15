"""Experiment lifecycle metadata independent of UI and assessment."""
from dataclasses import dataclass

@dataclass
class ExperimentState:
    experiment_id: str
    scenario_id: str
    scenario_name: str
    start_time: str
    end_time: str | None
    duration_s: float
    seed: int
    mode: str
    vision_source: str
    guardian_source: str
    machine_source: str
    software_version: str
    result_status: str = "RUNNING"
