"""Local deterministic input timeline; no risk or decision outputs."""
from dataclasses import dataclass, replace
import json
from math import isfinite
from pathlib import Path
from time import monotonic

SIMULATION_DT = .1
SCENARIO_DIRECTORY = Path(__file__).resolve().parent / "scenarios"
INPUT_DEFAULTS = dict(bucket_x_m=5., bucket_depth_m=.2, fatigue=20., attention=.9,
                      exposure=0., plan_center_x_m=4.8)

@dataclass(frozen=True)
class ScenarioState:
    scenario_id: str = ""
    scenario_name: str = "UNAVAILABLE"
    status: str = "IDLE"
    elapsed_time_s: float = 0.
    duration_s: float = 0.
    current_event_index: int = -1
    current_event_name: str = ""
    progress: float = 0.
    demo_mode: bool = True
    timestamp: float = 0.

class ScenarioManager:
    def __init__(self):
        self.state = ScenarioState()
        self.definition = None
        self.dispatched = []
        self.error = ""

    def load(self, path):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            self.validate(data)
            data["events"].sort(key=lambda event: event["time_s"])
            self.definition = data
            self.reset()
            return True
        except (OSError, ValueError, TypeError, KeyError) as error:
            self.definition = None
            self.error = str(error)
            self.state = ScenarioState(status="ERROR", current_event_name="SCENARIO LOAD ERROR", timestamp=monotonic())
            return False

    @staticmethod
    def validate(data):
        def number(value):
            return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
        if not isinstance(data, dict) or not all(isinstance(data.get(k), str) and data[k] for k in ("scenario_id", "name")):
            raise ValueError("Scenario ID and name required")
        duration = data.get("duration_seconds")
        if not number(duration) or duration <= 0: raise ValueError("Invalid duration")
        events = data.get("events")
        if not isinstance(events, list) or not events: raise ValueError("Events required")
        for event in events:
            if not isinstance(event, dict) or not number(event.get("time_s")) or not 0 <= event["time_s"] <= duration:
                raise ValueError("Invalid event time")
            if not isinstance(event.get("type"), str): raise ValueError("Event type required")
            if set(event) - {"time_s", "type", "inputs"}: raise ValueError("Only input events allowed")
            values = event.get("inputs", {})
            if not isinstance(values, dict): raise ValueError("Invalid event inputs")
            for key, value in values.items():
                if key not in INPUT_DEFAULTS or not number(value): raise ValueError("Unknown or nonfinite input")
                if key in ("exposure", "attention") and not 0 <= value <= 1: raise ValueError("Input outside 0..1")
                if key == "fatigue" and not 0 <= value <= 100: raise ValueError("Fatigue outside 0..100")
        if min(event["time_s"] for event in events) != 0: raise ValueError("Baseline event required at zero")
        excavation = data["excavation"]
        for key in ("target_depth_m", "target_width_m", "target_slope_percent"):
            if not number(excavation[key]): raise ValueError("Invalid excavation")
        if excavation["target_depth_m"] <= 0 or excavation["target_width_m"] <= 0: raise ValueError("Invalid dimensions")
        from modules.safedig_vision.soil_model import SoilType
        SoilType(data["soil"]["type"])
        truth = data["utility_ground_truth"]
        if not isinstance(truth["enabled"], bool) or not number(truth["x_m"]) or not number(truth["depth_m"]) or truth["depth_m"] <= 0:
            raise ValueError("Invalid simulator truth")

    def reset(self):
        self.dispatched = []
        self.error = ""
        if self.definition:
            self.state = ScenarioState(self.definition["scenario_id"], self.definition["name"],
                duration_s=self.definition["duration_seconds"], demo_mode=self.state.demo_mode, timestamp=monotonic())

    def start(self):
        if not self.definition: return
        if self.state.status == "PAUSED": return self.resume()
        self.reset()
        self.state = replace(self.state, status="RUNNING")
        self._dispatch()

    def pause(self):
        if self.state.status == "RUNNING": self.state = replace(self.state, status="PAUSED")

    def resume(self):
        if self.state.status == "PAUSED": self.state = replace(self.state, status="RUNNING")

    def stop(self):
        self.reset()

    def set_demo_mode(self, enabled):
        self.state = replace(self.state, demo_mode=enabled)

    def advance(self, dt=SIMULATION_DT):
        if not isfinite(dt) or dt < 0: raise ValueError("Invalid simulation step")
        if self.state.status != "RUNNING": return ()
        elapsed = min(self.state.duration_s, round(self.state.elapsed_time_s + dt, 9))
        self.state = replace(self.state, elapsed_time_s=elapsed, progress=elapsed/self.state.duration_s,
            timestamp=monotonic(), status="COMPLETED" if elapsed >= self.state.duration_s else "RUNNING")
        return self._dispatch()

    def _dispatch(self):
        emitted = []
        index = self.state.current_event_index + 1
        events = self.definition["events"]
        while index < len(events) and events[index]["time_s"] <= self.state.elapsed_time_s:
            event = events[index]
            emitted.append(event)
            self.dispatched.append(index)
            self.state = replace(self.state, current_event_index=index, current_event_name=event["type"])
            index += 1
        return tuple(emitted)

    def inputs(self):
        """Interpolate movement/operator keyframes; discrete sensor/plan input events."""
        values = dict(INPUT_DEFAULTS)
        if not self.definition: return values
        t = self.state.elapsed_time_s
        for key, default in values.items():
            points = [(e["time_s"], e["inputs"][key]) for e in self.definition["events"] if key in e.get("inputs", {})]
            if not points: continue
            if points[0][0] > 0: points.insert(0, (0., default))
            values[key] = points[0][1]
            for index, (time, value) in enumerate(points):
                if time <= t: values[key] = value
                elif key in ("bucket_x_m", "bucket_depth_m", "fatigue", "attention"):
                    before, previous = points[index-1]
                    values[key] = previous + (value-previous)*(t-before)/(time-before)
                    break
                else: break
        return values
