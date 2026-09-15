"""Small buffered experiment export. No images, video, or raw landmarks."""
import csv
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
from time import monotonic
from uuid import uuid4

from config.settings import APP_VERSION
from config.risk_config import WEIGHTS
from domain.experiment_state import ExperimentState
from evaluation.ground_truth import GroundTruth
from evaluation.experiment_evaluator import ExperimentEvaluator
from services.logging_service import EventLogger, telemetry

OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output" / "experiments"
SNAPSHOT_INTERVAL_S = .5


def json_value(value):
    if is_dataclass(value): return asdict(value)
    if isinstance(value, Enum): return value.value
    raise TypeError(f"Unsupported export type: {type(value).__name__}")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class DataRecorder:
    def __init__(self, output_directory=OUTPUT_DIRECTORY):
        self.output_directory = Path(output_directory)
        self.session = None
        self.summary = None
        self.error = ""
        self.active = False
        self.rows = []
        self.last_time = 0.
        self.events = EventLogger()

    def start(self, scenario, demo_mode=True, guardian_source=None):
        if self.active: self.finalize("ABORTED")
        self.error = ""
        self.summary = None
        self.rows = []
        self.last_time = 0.
        self.next_snapshot = 0.
        self.events = EventLogger()
        experiment_id = datetime.now(timezone.utc).strftime("EXP_%Y%m%d_%H%M%S_") + uuid4().hex[:10]
        self.session = ExperimentState(experiment_id, scenario["scenario_id"],scenario["name"],utc_now(),None,0.,
            scenario.get("seed",42),"DEMO" if demo_mode else "LIVE","SIMULATED_GPR",
            guardian_source or ("SIMULATED" if demo_mode else "LIVE"),"SIMULATED_MACHINE",APP_VERSION)
        self.directory = self.output_directory / experiment_id
        self.truth = GroundTruth.from_scenario(scenario,monotonic())
        self.evaluator = ExperimentEvaluator(self.truth)
        self.configuration = dict(configuration_version="MVP0_STAGE15_V1",risk_weights=dict(WEIGHTS),
            scenario_sha256=hashlib.sha256(json.dumps(scenario,sort_keys=True).encode()).hexdigest(),
            scenario=scenario)
        self.active = True
        self.events.emit("SCENARIO_STARTED",0.)
        try:
            self.directory.mkdir(parents=True,exist_ok=False)
            self._json("metadata.json",self.metadata())
        except (OSError, ValueError, TypeError) as error:
            self.error = "DATA RECORDING ERROR: " + str(error)
        return self.session

    def metadata(self):
        return dict(asdict(self.session),configuration=self.configuration,
            evaluation_label="PROTOTYPE / SIMULATION EVALUATION",
            ground_truth_label="GROUND TRUTH - SIMULATION ONLY",ground_truth=asdict(self.truth),
            telemetry_rate_hz=2,metrics_sampling="All assessment updates; simulation-time duration integration")

    def observe(self, state, simulation_time_s, latencies=None, guardian_source=None,fault_states=()):
        if not self.active: return
        if simulation_time_s <= self.last_time and self.evaluator.history: return
        row = telemetry(state,simulation_time_s,latencies)
        row["guardian_source"] = guardian_source or self.session.guardian_source
        self.last_time = simulation_time_s
        self.session.duration_s = simulation_time_s
        self.events.observe_faults(fault_states,row)
        self.events.observe(row)
        self.evaluator.observe(row)
        if simulation_time_s + 1e-9 >= self.next_snapshot:
            self.rows.append(row)
            self.next_snapshot = simulation_time_s + SNAPSHOT_INTERVAL_S

    def _json(self, filename, data):
        # Atomic replacement prevents partially written JSON documents.
        temporary = self.directory / (filename+".tmp")
        temporary.write_text(json.dumps(data,indent=2,default=json_value,allow_nan=False)+"\n",encoding="utf8")
        temporary.replace(self.directory / filename)

    def finalize(self, status="COMPLETED"):
        if not self.active: return self.summary
        self.active = False
        self.session.result_status = status
        self.session.end_time = utc_now()
        self.events.emit("SCENARIO_COMPLETED" if status=="COMPLETED" else "EXPERIMENT_ABORTED",self.last_time,
            data={"status":status})
        metrics = self.evaluator.summarize(self.events.events,self.last_time)
        from evaluation.reliability_metrics import reliability_summary
        reliability = reliability_summary(self.truth,self.evaluator.history,self.events.events,metrics["detection"]["outcome"])
        metrics["reliability"] = reliability
        for event,active in (("FALSE_POSITIVE_EVALUATED",reliability["false_positive_count"]),
                ("FALSE_NEGATIVE_EVALUATED",reliability["false_negative_count"]),
                ("FALSE_SAFE_EVALUATED",reliability["false_safe_condition"]),
                ("FALSE_RESTRICT_EVALUATED",reliability["false_restrict_condition"])):
            if active:self.events.emit(event,self.last_time,"Evaluator",severity="WARNING")
        self.summary = dict(experiment_id=self.session.experiment_id,scenario=self.session.scenario_id,
            scenario_name=self.session.scenario_name,status=status,**metrics)
        # Include the last state even for runs aborted between periodic snapshots.
        if self.evaluator.history and (not self.rows or self.rows[-1]["simulation_time_s"] != self.last_time):
            self.rows.append(self.evaluator.history[-1])
        try:
            self._json("metadata.json",self.metadata())
            self._json("events.json",self.events.events)
            self._json("metrics.json",metrics)
            self._json("summary.json",self.summary)
            with (self.directory / "telemetry.csv").open("w",encoding="utf8",newline="") as stream:
                columns=list(self.rows[0]) if self.rows else ["simulation_time_s"]
                writer=csv.DictWriter(stream,fieldnames=columns)
                writer.writeheader();writer.writerows(self.rows)
        except (OSError, ValueError, TypeError) as error:
            self.error = "DATA RECORDING ERROR: " + str(error)
        return self.summary
