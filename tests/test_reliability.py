"""Reliability evaluation and existing pipeline fallbacks; no physical inputs."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from core.app_controller import ScenarioController
from evaluation.ground_truth import GroundTruth
from evaluation.reliability_metrics import classification_metrics,aggregate_experiments,reliability_summary
from services.data_recorder import DataRecorder
from simulation.scenario_manager import ScenarioManager,SCENARIO_DIRECTORY


def run(name):
    manager=ScenarioManager();assert manager.load(SCENARIO_DIRECTORY/(name+".json")),manager.error
    controller=ScenarioController(manager)
    with TemporaryDirectory() as directory:
        controller.recorder=DataRecorder(directory);manager.start();controller.recorder.start(manager.definition)
        states=[]
        for tick in range(round(manager.state.duration_s*10)+1):
            states.append(controller.evaluate(100+tick*.1));manager.advance()
        return states,controller.recorder.summary,controller.recorder.events.events


class ReliabilityTests(unittest.TestCase):
    def test_precision_recall_rates(self):
        result=classification_metrics(8,2,2,8)
        self.assertEqual(result["precision"],.8)
        self.assertEqual(result["recall"],.8)
        self.assertEqual(result["specificity"],.8)
        self.assertEqual(result["false_positive_rate"],.2)
        self.assertEqual(result["false_negative_rate"],.2)
        self.assertTrue(all(value is None for value in classification_metrics(0,0,0,0).values()))

    def test_aggregate_independent_experiments(self):
        a=dict(experiment_id="a",status="COMPLETED",detection={"outcome":"TRUE_POSITIVE"})
        b=dict(experiment_id="b",status="COMPLETED",detection={"outcome":"FALSE_POSITIVE"})
        self.assertIsNone(aggregate_experiments([a,a]))
        self.assertEqual(aggregate_experiments([a,a,b])["precision"],.5)

    def test_false_safe_false_restrict(self):
        truth=GroundTruth(True,"CONDUIT",6.5,1.32,"UNKNOWN","NORMAL","test",100.)
        rows=[dict(simulation_time_s=0.,utility_detected=False,risk_level="SAFE",decision_action="NORMAL",risk_score=3)]
        result=reliability_summary(truth,rows,[],"FALSE_NEGATIVE")
        self.assertTrue(result["false_safe_condition"])
        self.assertEqual(rows[0]["risk_score"],3)
        rows[0].update(utility_detected=True,decision_action="RESTRICT")
        self.assertTrue(reliability_summary(replace(truth,utility_present=False),rows,[],"FALSE_POSITIVE")["false_restrict_condition"])

    def test_recovery_timing(self):
        truth=GroundTruth(False,"UNKNOWN",None,None,"UNKNOWN","NORMAL","test",0.)
        events=[dict(event_type=kind,simulation_time_s=t,data=dict(fault_id="one",source="GPR"))
            for kind,t in (("FAULT_STARTED",3.),("FAULT_CLEARED",8.),("SENSOR_RECOVERED",8.4))]
        rows=[dict(simulation_time_s=3.2,vision_valid=False,decision_action="VERIFY")]
        result=reliability_summary(truth,rows,events,None)
        self.assertAlmostEqual(result["mean_recovery_time_s"],.4)
        self.assertAlmostEqual(result["fault_responses"][0]["time_to_verification_s"],.2)

    def test_fp_fn_independent_from_truth(self):
        for name,outcome in (("fault_false_positive","FALSE_POSITIVE"),("fault_false_negative","FALSE_NEGATIVE")):
            states,summary,events=run(name)
            self.assertEqual(summary["detection"]["outcome"],outcome)
            self.assertEqual(states[40].decision.action.value,"VERIFY")
            self.assertNotEqual(states[40].risk.level.value,"CRITICAL")
            self.assertIn(outcome+"_EVALUATED",[e["event_type"] for e in events])
        for filename in ("core/risk_engine.py","core/decision_engine.py","core/sensor_fusion.py","modules/safedig_vision/utility_detector.py"):
            text=Path(filename).read_text(encoding="utf8")
            self.assertNotIn("evaluation.ground_truth",text)
            self.assertNotIn("utility_ground_truth",text)

    def test_offline_stale_precision_and_conflict(self):
        for name in ("sensor_offline","sensor_stale","machine_stale","sensor_degraded","low_confidence","gnss_degraded","conflicting_evidence"):
            states,summary,events=run("fault_"+name)
            state=states[40]
            self.assertEqual(state.decision.action.value,"VERIFY")
            self.assertFalse(state.risk.risk_valid)
            self.assertIn(state.fusion.fusion_confidence,("LOW","UNAVAILABLE"))
            self.assertEqual(summary["reliability"]["fault_count"],1)
            self.assertEqual(summary["reliability"]["fault_recovery_count"],1)
            self.assertEqual(states[-1].decision.action.value,"NORMAL")

    def test_guardian_faults(self):
        for name in ("guardian_offline","face_lost","multiple_faces","fatigue_stale"):
            states,summary,events=run("fault_"+name)
            self.assertFalse(states[40].fusion.fatigue_available)
            self.assertIsNone(states[40].risk.fatigue_risk)
            self.assertNotIn("fatigue",states[40].risk.active_weights)
            self.assertAlmostEqual(sum(states[40].risk.active_weights.values()),1.)
            self.assertTrue(states[40].risk.risk_valid)
            self.assertTrue(states[-1].fusion.fatigue_available)

    def test_drift_tracks_estimate_and_error(self):
        for name in ("depth_drift","position_drift"):
            states,summary,events=run("fault_"+name)
            state=states[60]
            self.assertEqual(state.envelope.center_x_m,state.utility.estimated_x_m)
            self.assertEqual(state.envelope.center_z_m,state.utility.estimated_z_m)
            key="max_depth_error_m" if name=="depth_drift" else "max_position_error_m"
            self.assertGreater(summary["reliability"][key],.2)

    def test_noise_and_recovery_hysteresis(self):
        states,summary,events=run("fault_noise_spike")
        self.assertNotIn("CRITICAL",[s.risk.level.value for s in states])
        self.assertGreater(summary["reliability"]["max_transient_risk_change"],0.)
        self.assertEqual(sum(e["event_type"]=="FAULT_STARTED" for e in events),1)
        states,summary,events=run("fault_recovery")
        self.assertEqual(states[40].sensor_health.value,"DEGRADED")
        self.assertEqual(states[70].sensor_health.value,"OFFLINE")
        self.assertEqual(states[90].sensor_health.value,"VALID")
        self.assertEqual(states[90].decision.action.value,"VERIFY")
        self.assertEqual(states[92].decision.action.value,"NORMAL")
        self.assertEqual(summary["reliability"]["fault_recovery_count"],2)
