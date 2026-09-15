import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from evaluation.ground_truth import GroundTruth
from evaluation.experiment_evaluator import ExperimentEvaluator
from services.data_recorder import DataRecorder
from services.logging_service import EventLogger, telemetry
from adapters.sensor_source import SafeDigState, SensorHealth
from dataclasses import replace


def row(t=0., **changes):
    state=SafeDigState(None,SensorHealth.OFFLINE,"")
    result=telemetry(state,t,{"risk_latency_ms":2.,"decision_latency_ms":1.})
    result.update(changes)
    return result


class EvaluatorTests(unittest.TestCase):
    def truth(self,present=True):
        return GroundTruth(present,"CONDUIT",4.2,1.32,"UNKNOWN","NORMAL","test",100.)

    def test_metrics_and_transition_durations(self):
        evaluator=ExperimentEvaluator(self.truth());logger=EventLogger()
        for t,(score,level,action,margin) in enumerate(zip((20,50,72,91),
                ("SAFE","CAUTION","HIGH","CRITICAL"),("NORMAL","WARN","SLOW","RESTRICT"),(.5,.2,.1,-.05))):
            sample=row(t,risk_score=score,risk_level=level,decision_action=action,clearance_margin_m=margin,
                detection_available=True,utility_detected=True,estimated_utility_depth_m=1.36,
                estimated_utility_x_m=4.17,utility_confidence=.84,current_depth_m=1.6,target_depth_m=1.5,
                distance_to_utility_m=.3,bucket_x_m=4.2,bucket_z_m=-1.02)
            evaluator.observe(sample);logger.observe(sample)
        result=evaluator.summarize(logger.events,4.)
        self.assertEqual(result["risk"]["max_risk_score"],91)
        self.assertEqual(result["risk"]["max_risk_level"],"CRITICAL")
        self.assertEqual(result["risk"]["time_to_caution_s"],1.)
        self.assertEqual(result["risk"]["time_to_high_s"],2.)
        self.assertEqual(result["risk"]["time_to_critical_s"],3.)
        self.assertEqual(result["risk"]["time_in_safe_s"],1.)
        self.assertEqual(result["proximity"]["minimum_clearance_margin_m"],-.05)
        self.assertAlmostEqual(result["proximity"]["minimum_true_bucket_utility_distance_m"],.3)
        self.assertAlmostEqual(result["detection"]["depth_error_cm"],4.)
        self.assertAlmostEqual(result["precision"]["overdig_m"],.1)
        self.assertEqual(result["decision"]["highest_action"],"RESTRICT")
        self.assertEqual(result["decision"]["count_restrict_events"],1)
        self.assertIsNone(result["guardian"]["max_fatigue_score"])
        self.assertIsNone(result["guardian"]["time_fatigue_high_s"])

    def test_fatigue_and_no_event_spam(self):
        evaluator=ExperimentEvaluator(self.truth());logger=EventLogger()
        for t in range(10):
            sample=row(t,risk_level="HIGH",decision_action="SLOW",fatigue_score=80.,verification_required=True)
            evaluator.observe(sample);logger.observe(sample)
        summary=evaluator.summarize(logger.events,10.)
        self.assertEqual(summary["guardian"]["max_fatigue_score"],80.)
        self.assertEqual(summary["guardian"]["average_fatigue_score"],80.)
        self.assertEqual(summary["guardian"]["time_fatigue_high_s"],10.)
        self.assertEqual(sum(e["event_type"]=="FATIGUE_HIGH" for e in logger.events),1)
        self.assertEqual(summary["decision"]["count_slow_events"],1)
        self.assertIsNone(summary["detection"]["outcome"])

    def test_missing_values_export_and_file_failure(self):
        from simulation.scenario_manager import ScenarioManager,SCENARIO_DIRECTORY
        manager=ScenarioManager();manager.load(SCENARIO_DIRECTORY/"critical_scenario.json")
        with TemporaryDirectory() as directory:
            recorder=DataRecorder(directory)
            first=recorder.start(manager.definition).experiment_id
            state=SafeDigState(None,SensorHealth.OFFLINE,"")
            recorder.observe(state,0.,{"risk_latency_ms":2.,"decision_latency_ms":1.})
            recorder.observe(state,.1)
            recorder.observe(state,.5)
            recorder.finalize("ABORTED")
            for name in ("metadata.json","events.json","metrics.json","summary.json"):
                json.loads((recorder.directory/name).read_text())
            with (recorder.directory/"telemetry.csv").open(newline="") as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[0]["fatigue_score"],"")
            self.assertEqual(rows[0]["estimated_utility_depth_m"],"")
            self.assertNotEqual(recorder.start(manager.definition).experiment_id,first)
            recorder.finalize("ABORTED")
            blocked=Path(directory)/"file";blocked.write_text("not a directory")
            broken=DataRecorder(blocked)
            broken.start(manager.definition);broken.observe(state,0.)
            summary=broken.finalize()
            self.assertIsNotNone(summary)
            self.assertIn("DATA RECORDING ERROR",broken.error)

    def test_privacy_projection(self):
        from domain.operator_state import OperatorState
        state=SafeDigState(None,SensorHealth.OFFLINE,"",operator=OperatorState(landmarks=((1.,2.,3.),),fatigue_score=80.))
        sample=telemetry(state,0.)
        self.assertIsNone(sample["fatigue_score"])
        for key in ("landmarks","image","frame","video","operator"):
            self.assertNotIn(key,sample)

    def test_critical_export_and_independent_estimate(self):
        from simulation.scenario_manager import ScenarioManager,SCENARIO_DIRECTORY
        from core.app_controller import ScenarioController
        manager=ScenarioManager();manager.load(SCENARIO_DIRECTORY/"critical_scenario.json")
        controller=ScenarioController(manager)
        with TemporaryDirectory() as directory:
            controller.recorder=DataRecorder(directory)
            manager.start();controller.recorder.start(manager.definition)
            for tick in range(401):
                state=controller.evaluate(100.+tick*.1)
                manager.advance()
            recorder=controller.recorder;summary=recorder.summary
            self.assertEqual(summary["status"],"COMPLETED")
            self.assertEqual(summary["detection"]["outcome"],"TRUE_POSITIVE")
            self.assertGreater(summary["detection"]["depth_error_cm"],0.)
            self.assertEqual(summary["decision"]["highest_action"],"RESTRICT")
            self.assertEqual(summary["risk"]["max_risk_level"],"CRITICAL")
            self.assertGreaterEqual(summary["latency"]["risk_engine_avg_ms"],0.)
            self.assertGreaterEqual(summary["latency"]["decision_engine_avg_ms"],0.)
            self.assertEqual(len(recorder.rows),81)
            self.assertLess(len(recorder.events.events),80)
            self.assertEqual(len(list(recorder.directory.iterdir())),5)
            self.assertEqual(summary["duration_s"],40.)
            self.assertAlmostEqual(sum(summary["risk"]["time_in_"+level+"_s"] for level in ("safe","caution","high","critical")),40.)
