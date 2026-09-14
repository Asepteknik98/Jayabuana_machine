"""Risk behavior and missing-input semantics for the MVP-0 engine."""

from dataclasses import replace
import unittest

from adapters.sensor_source import SafeDigState,SensorHealth
from core.risk_engine import RiskEngine,RiskLevel
from core.safe_envelope import EnvelopeState,EnvelopeStatus
from modules.safedig_vision.gpr_simulator import GPRSimulator
from modules.safedig_vision.utility_model import UtilityState,MachineState
from modules.safedig_precision.design_conflict import DesignConflictState,ConflictStatus


class RiskEngineTests(unittest.TestCase):
    def state(self,distance=1.5,speed=0,design=ConflictStatus.NO_CONFLICT,confidence=0.9):
        return SafeDigState(GPRSimulator().read(6),SensorHealth.VALID,'',
            utility=UtilityState(detected=True,valid=True,confidence=confidence,sensor_health=SensorHealth.VALID),
            machine=MachineState(0,0,bucket_speed_mps=speed),
            envelope=EnvelopeState(effective_clearance_m=0.35,distance_to_utility_m=distance,valid=True,
                                   status=EnvelopeStatus.CLEAR),
            design_conflict=DesignConflictState(status=design,valid=True,verification_required=False))

    def risk(self,**kwargs):
        return RiskEngine().update(self.state(**kwargs)).risk

    def test_safe(self):
        self.assertEqual(self.risk().level,RiskLevel.SAFE)

    def test_approaching(self):
        risk=self.risk(distance=0.6,design=ConflictStatus.POTENTIAL_CONFLICT)
        self.assertGreater(risk.total_score,self.risk().total_score)
        self.assertEqual(risk.level,RiskLevel.CAUTION)

    def test_high_and_critical(self):
        self.assertEqual(self.risk(distance=0.6,design=ConflictStatus.DESIGN_CONFLICT).level,RiskLevel.HIGH)
        self.assertEqual(self.risk(distance=0.2,speed=0.3,design=ConflictStatus.DESIGN_CONFLICT).level,RiskLevel.CRITICAL)

    def test_velocity(self):
        self.assertGreater(self.risk(speed=0.2).total_score,self.risk(speed=0).total_score)

    def test_design(self):
        self.assertGreater(self.risk(design=ConflictStatus.DESIGN_CONFLICT).total_score,self.risk().total_score)

    def test_low_confidence(self):
        risk=self.risk(confidence=0.2)
        self.assertGreater(risk.total_score,30)
        self.assertTrue(risk.verification_required)
        self.assertFalse(risk.risk_valid)

    def test_offline_and_stale(self):
        engine=RiskEngine();engine.update(self.state())
        for health in (SensorHealth.OFFLINE,SensorHealth.STALE):
            risk=engine.update(replace(self.state(),sensor_health=health)).risk
            self.assertIsNone(risk.total_score)
            self.assertIsNone(risk.level)
            self.assertFalse(risk.risk_valid)
            self.assertTrue(risk.verification_required)

    def test_fatigue_unavailable_and_weights(self):
        risk=self.risk()
        self.assertFalse(risk.fatigue_available)
        self.assertIsNone(risk.fatigue_risk)
        self.assertIsNone(risk.contribution_breakdown['fatigue'])
        self.assertNotIn('fatigue',risk.active_weights)
        self.assertAlmostEqual(sum(risk.active_weights.values()),1)
        self.assertEqual(risk.total_score,round(sum(v for v in risk.contribution_breakdown.values() if v is not None)))

    def test_bounds(self):
        for distance in (0,0.1,1,100):
            for speed in (0,0.1,100):
                risk=self.risk(distance=distance,speed=speed)
                self.assertTrue(0<=risk.total_score<=100)
                for value in (risk.utility_risk,risk.confidence_risk,risk.velocity_risk,risk.design_conflict_risk):
                    self.assertTrue(0<=value<=1)

    def test_hysteresis(self):
        engine=RiskEngine()
        self.assertEqual([engine.level_for_score(s) for s in (30,31,30,26,25,24)],
                         [RiskLevel.SAFE,RiskLevel.CAUTION,RiskLevel.CAUTION,RiskLevel.CAUTION,RiskLevel.CAUTION,RiskLevel.SAFE])
        self.assertEqual([engine.level_for_score(s) for s in (61,60,55,54,81,80,75,74)],
                         [RiskLevel.HIGH,RiskLevel.HIGH,RiskLevel.HIGH,RiskLevel.CAUTION,
                          RiskLevel.CRITICAL,RiskLevel.CRITICAL,RiskLevel.CRITICAL,RiskLevel.HIGH])

    def test_missing_and_invalid_inputs(self):
        for state in (replace(self.state(),sensor=None),replace(self.state(),machine=None),
                      replace(self.state(),machine=MachineState(0,0,bucket_speed_mps=float('nan'))),
                      replace(self.state(),envelope=None)):
            self.assertIsNone(RiskEngine().update(state).risk.total_score)

    def test_degraded_and_explainability(self):
        risk=RiskEngine().update(replace(self.state(),sensor_health=SensorHealth.DEGRADED)).risk
        self.assertFalse(risk.risk_valid)
        self.assertTrue(risk.verification_required)
        self.assertGreater(risk.confidence_risk,0)
        self.assertTrue(risk.primary_risk_driver)
