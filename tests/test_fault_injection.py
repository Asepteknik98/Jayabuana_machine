"""Deterministic upstream fault behavior, without windows or webcam."""
import ast
from dataclasses import replace
from pathlib import Path
import unittest
from adapters.sensor_source import SafeDigState,SensorHealth
from modules.safedig_vision.gpr_simulator import GPRSimulator
from modules.safedig_vision.utility_model import MachineState
from domain.operator_state import OperatorState
from simulation.fault_injection import FaultInjectionEngine,FaultType,validate_faults


def spec(kind,start=3,duration=5):
    return dict(id="fault",type=kind.value,start_time_s=start,duration_s=duration,severity="MEDIUM")


def baseline(now=100.):
    return replace(SafeDigState.from_sensor(GPRSimulator().read(now,exposure=1.),now),
        machine=MachineState(5.,-.2,1.5,.8,2.,.2,4.8,.1,now),
        operator=OperatorState(camera_available=True,camera_health=SensorHealth.VALID,face_detected=True,
            face_count=1,valid=True,fatigue_valid=True,fatigue_score=80.,timestamp=now,
            last_frame_timestamp=now,last_detection_timestamp=now))


class FaultTests(unittest.TestCase):
    def test_activation_expiry_recovery_original(self):
        engine=FaultInjectionEngine();original=baseline();fault=[spec(FaultType.GPR_SIGNAL_DEGRADED)]
        for t in (0,2.9,8,10):
            result=engine.apply(original,fault,t,100.)
            self.assertIs(result.sensor,original.sensor)
        bad=engine.apply(original,fault,3.,100.)
        self.assertTrue(engine.states[0].active)
        self.assertLess(bad.sensor.signal_quality,original.sensor.signal_quality)
        restored=engine.apply(original,fault,8.,100.)
        self.assertTrue(engine.states[0].recovered)
        self.assertFalse(engine.states[0].active)
        self.assertEqual(restored.sensor,original.sensor)

    def test_each_fault_and_input_only(self):
        original=replace(baseline(),risk=object(),decision=object())
        for kind in FaultType:
            result=FaultInjectionEngine().apply(original,[spec(kind)],4.,100.)
            self.assertIs(result.risk,original.risk)
            self.assertIs(result.decision,original.decision)
        tree=ast.parse(Path("simulation/fault_injection.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Attribute) and isinstance(node.ctx,ast.Store):
                self.assertNotIn(node.attr,{"risk","decision","total_score","level","action"})

    def test_stale_offline_degraded(self):
        original=baseline()
        offline=FaultInjectionEngine().apply(original,[spec(FaultType.GPR_OFFLINE)],4.,100.)
        self.assertEqual(offline.sensor_health,SensorHealth.OFFLINE)
        engine=FaultInjectionEngine();fault=[spec(FaultType.GPR_STALE)]
        stale=engine.apply(original,fault,4.,100.)
        later=engine.apply(baseline(102.),fault,6.,102.)
        self.assertEqual(stale.sensor_health,SensorHealth.STALE)
        self.assertEqual(later.sensor.timestamp,stale.sensor.timestamp)
        self.assertIs(later.sensor,stale.sensor)

    def test_repeatable_temporary_noise(self):
        fault=[spec(FaultType.SIGNAL_NOISE_SPIKE,3,.2)]
        a,b=FaultInjectionEngine(),FaultInjectionEngine();original=baseline()
        for tick in range(25,36):
            t=tick/10
            self.assertEqual(a.apply(original,fault,t,100.,42).sensor,b.apply(original,fault,t,100.,42).sensor)
        self.assertEqual(a.apply(original,fault,3.2,100.).sensor,original.sensor)

    def test_guardian_faults_do_not_touch_live(self):
        original=baseline()
        for kind in (FaultType.GUARDIAN_OFFLINE,FaultType.FACE_LOST,FaultType.MULTIPLE_FACES,FaultType.FATIGUE_DATA_STALE):
            engine=FaultInjectionEngine()
            result=engine.apply(original,[spec(kind)],4.,100.,demo_mode=False)
            self.assertIs(result.operator,original.operator)
            self.assertFalse(engine.states[0].active)

    def test_validation(self):
        for changes in ({"duration_s":0},{"start_time_s":-1},{"severity":"CRITICAL"},
                {"type":"UNKNOWN"},{"magnitude_m":float("nan")},{"risk_score":99}):
            with self.assertRaises((ValueError,KeyError)):
                validate_faults([dict(spec(FaultType.NONE),**changes)],12.)
