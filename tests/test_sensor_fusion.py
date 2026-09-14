"""Synthetic source-neutral fusion and complete assessment pipeline checks."""
from dataclasses import replace
import unittest
from adapters.sensor_source import SafeDigState, SensorState, SensorHealth
from core.sensor_fusion import SensorFusion
from core.risk_engine import RiskEngine, RiskLevel
from core.decision_engine import DecisionEngine, DecisionAction
from core.safe_envelope import EnvelopeState, EnvelopeStatus
from domain.operator_state import OperatorState
from modules.safedig_vision.utility_model import MachineState, UtilityState
from modules.safedig_precision.design_conflict import DesignConflictState, ConflictStatus


def scenario(fatigue=20, distance=2., conflict=False, speed=0., now=100.):
    env = EnvelopeStatus.INSIDE if distance <= .35 else EnvelopeStatus.APPROACHING if distance <= .5 else EnvelopeStatus.CLEAR
    return SafeDigState(
        SensorState("NORMAL", .95, .91, .8, .8, True, SensorHealth.VALID, now, ()), SensorHealth.VALID, "",
        utility=UtilityState(detected=True, valid=True, confidence=.91, sensor_health=SensorHealth.VALID, timestamp=now),
        machine=MachineState(6.5, -1., 1.5, .8, 2., 1., 6.5, speed, now),
        envelope=EnvelopeState(valid=True, status=env, effective_clearance_m=.35,
            distance_to_utility_m=distance, clearance_margin_m=distance-.35, timestamp=now),
        design_conflict=DesignConflictState(valid=True, verification_required=False,
            status=ConflictStatus.DESIGN_CONFLICT if conflict else ConflictStatus.NO_CONFLICT, timestamp=now),
        operator=OperatorState(camera_available=True, camera_health=SensorHealth.VALID, face_detected=True,
            face_count=1, valid=True, fatigue_valid=True, fatigue_score=fatigue, attention_score=.9,
            timestamp=now, last_frame_timestamp=now, last_detection_timestamp=now))


def pipeline(state, now=100.):
    state = replace(state, fusion=SensorFusion().fuse(state, now))
    return DecisionEngine().update(RiskEngine().update(state))


class FusionTests(unittest.TestCase):
    def test_valid_normal(self):
        state = pipeline(scenario(15))
        self.assertTrue(state.fusion.fusion_valid)
        self.assertTrue(state.fusion.guardian_valid)
        self.assertEqual(state.fusion.fusion_confidence, "HIGH")
        self.assertNotIn("FATIGUE N/A", state.risk.data_status)
        self.assertFalse(any("STALE" in f for f in state.fusion.context_flags))
        self.assertEqual(state.risk.level, RiskLevel.SAFE)
        self.assertEqual(state.decision.action, DecisionAction.NORMAL)

    def test_guardian_offline(self):
        state = pipeline(replace(scenario(distance=.4, conflict=True), operator=OperatorState()))
        self.assertTrue(state.fusion.fusion_valid)
        self.assertFalse(state.fusion.fatigue_available)
        self.assertIsNone(state.fusion.fatigue_normalized)
        self.assertIsNone(state.risk.fatigue_risk)
        self.assertTrue(state.risk.risk_valid)
        self.assertNotIn("fatigue", state.risk.active_weights)
        self.assertAlmostEqual(sum(state.risk.active_weights.values()), 1.)
        self.assertGreater(state.risk.total_score, 0)
        self.assertFalse(state.fusion.verification_required)

    def test_vision_stale_preserves_evidence(self):
        original = scenario()
        old = replace(original, sensor=replace(original.sensor, timestamp=98.))
        state = pipeline(old)
        self.assertEqual(state.sensor.confidence, .91)
        self.assertEqual(state.fusion.utility_confidence, .91)
        self.assertEqual(state.fusion.sensor_health, "STALE")
        self.assertIn("VISION_STALE", state.fusion.context_flags)
        self.assertTrue(state.fusion.verification_required)
        self.assertIsNone(state.risk.total_score)
        self.assertEqual(state.decision.action, DecisionAction.VERIFY)

    def test_normalization(self):
        self.assertEqual(pipeline(scenario(80)).fusion.fatigue_normalized, .8)

    def test_precision_stale_and_future(self):
        for timestamp in (99., 101., None, float("nan")):
            original = scenario()
            state = pipeline(replace(original, machine=replace(original.machine, timestamp=timestamp)))
            self.assertFalse(state.fusion.precision_valid)
            self.assertEqual(state.decision.action, DecisionAction.VERIFY)

    def test_guardian_invalid(self):
        original = scenario(80)
        for changes in ({"timestamp": 98.}, {"last_frame_timestamp": 98.},
                {"last_detection_timestamp": 98.}, {"face_count": 2}, {"valid": False},
                {"face_detected": False}, {"fatigue_valid": False}, {"fatigue_score": float("nan")},
                {"camera_health": SensorHealth.DEGRADED}):
            state = pipeline(replace(original, operator=replace(original.operator, **changes)))
            self.assertFalse(state.fusion.fatigue_available)
            self.assertIsNone(state.risk.fatigue_risk)
            self.assertTrue(state.risk.risk_valid)

    def test_multimodal_flags(self):
        state = pipeline(scenario(80, .4, True))
        self.assertTrue({"FATIGUE_HIGH", "UTILITY_NEAR", "DESIGN_CONFLICT_ACTIVE", "MULTI_RISK_CONTEXT"} <= state.fusion.context_flags)

    def test_context_and_risk_contributions(self):
        low = pipeline(scenario(20, .4, True, .1))
        high = pipeline(scenario(80, .4, True, .1))
        far = pipeline(scenario(80))
        self.assertGreater(high.risk.total_score, low.risk.total_score)
        self.assertGreater(high.risk.total_score, far.risk.total_score + 30)
        self.assertEqual(low.risk.level, RiskLevel.HIGH)
        self.assertEqual(low.decision.action, DecisionAction.SLOW)
        self.assertEqual(far.decision.action, DecisionAction.WARN)
        self.assertNotEqual(far.risk.level, RiskLevel.CRITICAL)
        self.assertAlmostEqual(high.risk.active_weights["fatigue"], .15)
        self.assertEqual(high.risk.total_score, round(sum(high.risk.contribution_breakdown.values())))

    def test_critical(self):
        state = pipeline(scenario(80, .2, True, .3))
        self.assertEqual(state.risk.level, RiskLevel.CRITICAL)
        self.assertEqual(state.decision.action, DecisionAction.RESTRICT)
        self.assertEqual(state.decision.message, "RESTRICT MOTION TOWARD UTILITY")
        self.assertIn("HIGH OPERATOR FATIGUE", state.decision.reason)

    def test_offline_and_degraded_vision(self):
        for health in (SensorHealth.OFFLINE, SensorHealth.DEGRADED):
            state = pipeline(replace(scenario(), sensor_health=health))
            self.assertTrue(state.fusion.verification_required)
            self.assertEqual(state.decision.action, DecisionAction.VERIFY)

    def test_primary_fatigue(self):
        state = pipeline(scenario(100))
        self.assertEqual(state.risk.primary_risk_driver, "OPERATOR FATIGUE")

    def test_bounds(self):
        for fatigue in (-10, 0, 80, 100, 120):
            state = pipeline(scenario(fatigue, .1, True, 100))
            self.assertTrue(0 <= state.risk.total_score <= 100)
            for value in (state.risk.utility_risk, state.risk.confidence_risk, state.risk.fatigue_risk,
                          state.risk.velocity_risk, state.risk.design_conflict_risk):
                self.assertTrue(0 <= value <= 1)

    def test_stale_clears_previous_restrict(self):
        engine = DecisionEngine()
        state = pipeline(scenario(80, .2, True, .3))
        engine.update(state)
        stale = pipeline(state, 102.)
        result = engine.update(stale).decision
        self.assertEqual(result.action, DecisionAction.VERIFY)
        self.assertIsNone(result.restrict_direction)

    def test_stale_derived_evidence(self):
        original = scenario()
        for name in ("utility", "envelope", "design_conflict"):
            state = pipeline(replace(original, **{name: replace(getattr(original, name), timestamp=98.)}))
            self.assertTrue(state.fusion.verification_required)
            self.assertEqual(state.decision.action, DecisionAction.VERIFY)
