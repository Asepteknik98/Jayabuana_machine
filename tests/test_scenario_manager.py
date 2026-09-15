"""Deterministic software scenarios; no webcam, window, or hardware required."""
import ast
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from core.app_controller import ScenarioController
from domain.operator_state import OperatorState
from simulation.scenario_inputs import ScenarioInputs
from simulation.scenario_manager import ScenarioManager, SCENARIO_DIRECTORY


def load(name="critical_scenario"):
    manager = ScenarioManager()
    assert manager.load(SCENARIO_DIRECTORY / (name+".json")), manager.error
    return manager


def run(name="critical_scenario"):
    manager = load(name)
    controller = ScenarioController(manager)
    manager.start()
    states = []
    for tick in range(401):
        states.append(controller.evaluate(100+tick*.1))
        manager.advance()
    return manager, states


class ScenarioTests(unittest.TestCase):
    def test_load_and_start(self):
        manager = load()
        self.assertEqual(manager.state.status, "IDLE")
        manager.start()
        self.assertEqual(manager.state.status, "RUNNING")
        self.assertEqual(manager.dispatched, [0])

    def test_invalid_and_missing(self):
        manager = load()
        self.assertFalse(manager.load("does-not-exist.json"))
        self.assertEqual(manager.state.status, "ERROR")
        with TemporaryDirectory() as directory:
            path = Path(directory)/"bad.json"
            for content in ("{", "null", "[]", '{"name":"x"}'):
                path.write_text(content)
                self.assertFalse(manager.load(path))
                manager.start()
                self.assertEqual(manager.state.status, "ERROR")

    def test_schema_validation(self):
        original = load().definition
        for patch in ({"duration_seconds": 0}, {"duration_seconds": float("nan")},
                {"events": None}, {"events": [{"time_s": -1,"type":"bad"}]},
                {"events": [{"time_s":0,"type":"bad","inputs":{"risk_score":92}}]},
                {"events": [{"time_s":0,"type":"bad","inputs":{"decision":"RESTRICT"}}]}):
            with self.assertRaises((ValueError, TypeError)):
                ScenarioManager.validate(dict(original, **patch))

    def test_pause_resume_reset_stop(self):
        manager = load();manager.start();manager.advance(4.)
        values = manager.inputs()
        manager.pause();manager.advance(10.)
        self.assertEqual(manager.state.elapsed_time_s,4.)
        self.assertEqual(values,manager.inputs())
        manager.resume();manager.advance(.1)
        self.assertEqual(manager.state.elapsed_time_s,4.1)
        manager.reset()
        self.assertEqual(manager.state.elapsed_time_s,0.)
        self.assertEqual(manager.state.current_event_index,-1)
        self.assertEqual(manager.dispatched,[])
        manager.start();manager.stop()
        self.assertEqual(manager.state.status,"IDLE")

    def test_events_once_sorted_complete(self):
        manager = load()
        with TemporaryDirectory() as directory:
            path=Path(directory)/"reverse.json"
            path.write_text(json.dumps(dict(manager.definition,events=list(reversed(manager.definition["events"])))) )
            self.assertTrue(manager.load(path))
        manager.start()
        for _ in range(600):manager.advance()
        self.assertEqual(manager.state.status,"COMPLETED")
        self.assertEqual(manager.state.elapsed_time_s,40.)
        self.assertEqual(manager.dispatched,list(range(len(manager.definition["events"]))))
        self.assertEqual(manager.state.progress,1.)
        manager.start()
        self.assertEqual(manager.state.elapsed_time_s,0.)
        self.assertEqual(manager.dispatched,[0])

    def test_deterministic_and_reset_engine_history(self):
        manager=load();controller=ScenarioController(manager)
        traces=[]
        for replay in range(2):
            manager.start();controller.reset_engines();trace=[]
            for tick in range(401):
                state=controller.evaluate(100+tick*.1)
                trace.append((state.machine.bucket_x_m,state.machine.bucket_z_m,state.machine.bucket_speed_mps,
                    state.sensor.radargram,state.risk.total_score,state.risk.level,state.decision.action))
                manager.advance()
            traces.append(trace)
        self.assertEqual(traces[0],traces[1])
        manager.reset();controller.reset_engines()
        self.assertEqual(controller.evaluate(200).decision.action.value,"NORMAL")

    def test_sources(self):
        manager=load();inputs=ScenarioInputs()
        demo=inputs.sample(manager,100)
        self.assertEqual(inputs.guardian_source,"SIMULATED")
        self.assertEqual(demo.operator.analysis_status,"SIMULATED GUARDIAN INPUT")
        self.assertEqual(demo.operator.landmarks,())
        live=OperatorState(fatigue_score=37.)
        manager.set_demo_mode(False)
        self.assertIs(inputs.sample(manager,101,live).operator,live)
        self.assertIsNone(inputs.sample(manager,102,None).operator)

    def test_scenario_has_no_assessment_writes(self):
        for filename in ("scenario_manager.py","scenario_inputs.py","excavator_simulator.py","machine_sensor_simulator.py"):
            tree=ast.parse((SCENARIO_DIRECTORY.parent/filename).read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Attribute) and isinstance(node.ctx,ast.Store):
                    self.assertNotIn(node.attr,{"risk","risk_score","level","decision","action","total_score"})
        state=ScenarioInputs().sample(load(),100)
        self.assertIsNone(state.risk)
        self.assertIsNone(state.decision)
        self.assertIsNone(state.envelope)

    def test_critical_narrative(self):
        manager,states=run()
        self.assertEqual(states[0].risk.level.value,"SAFE")
        self.assertEqual(states[0].decision.action.value,"NORMAL")
        self.assertTrue(states[50].sensor.anomaly_detected)
        self.assertEqual(states[50].utility.status,"POSSIBLE UTILITY")
        self.assertTrue(states[90].utility.detected)
        self.assertEqual(states[140].design_conflict.status.value,"DESIGN_CONFLICT")
        self.assertEqual(states[200].envelope.status.value,"APPROACHING")
        self.assertGreater(states[260].operator.fatigue_score,states[200].operator.fatigue_score)
        self.assertEqual(states[-1].risk.level.value,"CRITICAL")
        self.assertEqual(states[-1].decision.action.value,"RESTRICT")
        self.assertGreater(states[-1].risk.total_score,states[0].risk.total_score)
        self.assertIn("HIGH",{s.risk.level.value for s in states})
        for previous,current in zip(states,states[1:]):
            distance=((current.machine.bucket_x_m-previous.machine.bucket_x_m)**2+
                      (current.machine.bucket_z_m-previous.machine.bucket_z_m)**2)**.5
            self.assertLess(distance,.02)
            self.assertAlmostEqual(current.machine.bucket_speed_mps,distance/.1)

    def test_other_scenarios(self):
        for name in ("normal_operation","utility_detected","wet_clay","design_conflict","operator_drowsy"):
            _,states=run(name)
            if name=="normal_operation":
                self.assertTrue(all(s.risk.level.value=="SAFE" and s.decision.action.value=="NORMAL" for s in states))
            elif name=="utility_detected":
                self.assertTrue({"SAFE","CAUTION","HIGH"}<={s.risk.level.value for s in states})
                self.assertTrue({"NORMAL","WARN","SLOW"}<={s.decision.action.value for s in states})
            elif name=="wet_clay":
                self.assertTrue(all(s.sensor_health.value=="DEGRADED" and s.decision.action.value=="VERIFY" for s in states))
            elif name=="design_conflict":
                self.assertEqual(states[-1].design_conflict.status.value,"DESIGN_CONFLICT")
                self.assertGreater(states[-1].utility.distance_to_bucket_m,1.)
            else:
                self.assertEqual(states[-1].operator.fatigue_score,80.)
                self.assertTrue(all(s.risk.level.value!="CRITICAL" and s.decision.action.value!="RESTRICT" for s in states))

    def test_negative_observation_does_not_hide_weak_evidence(self):
        from adapters.sensor_source import SensorHealth
        from modules.safedig_precision.design_conflict import DesignConflictEngine
        manager=load("normal_operation");controller=ScenarioController(manager)
        normal=controller.evaluate(100.)
        self.assertEqual(normal.design_conflict.status.value,"NO_CONFLICT")
        self.assertIsNone(normal.design_conflict.planned_clearance_m)
        for state in (replace(normal,sensor=None),
                replace(normal,sensor=replace(normal.sensor,confidence=.2)),
                replace(normal,sensor_health=SensorHealth.DEGRADED),
                replace(normal,utility=replace(normal.utility,sensor_health=SensorHealth.OFFLINE))):
            result=DesignConflictEngine().update(state).design_conflict
            self.assertTrue(result.verification_required)
            self.assertEqual(result.status.value,"UNKNOWN")
