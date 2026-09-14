"""Geometry boundaries, confidence expansion and unavailable inputs."""

from dataclasses import replace
import unittest

from adapters.sensor_source import SafeDigState, SensorHealth
from core.safe_envelope import SafeEnvelopeEngine, EnvelopeStatus
from modules.safedig_vision.utility_model import UtilityState, MachineState


class SafeEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.engine = SafeEnvelopeEngine()
        utility = UtilityState(detected=True, valid=True, estimated_x_m=0,
                               estimated_z_m=-1, confidence=0.75,
                               sensor_health=SensorHealth.VALID, timestamp=1)
        self.state = SafeDigState(None, SensorHealth.VALID, '', utility=utility,
                                  machine=MachineState(0.9, -1))

    def at_distance(self, distance):
        return self.engine.update(replace(self.state,machine=MachineState(distance,-1))).envelope

    def test_clear(self):
        result = self.at_distance(0.9)
        self.assertEqual(result.status,EnvelopeStatus.CLEAR)
        self.assertAlmostEqual(result.clearance_margin_m,0.55)

    def test_approaching(self):
        self.assertEqual(self.at_distance(0.43).status,EnvelopeStatus.APPROACHING)

    def test_inside_and_boundaries(self):
        for distance in (0,0.27,0.35):
            self.assertEqual(self.at_distance(distance).status,EnvelopeStatus.INSIDE)
        self.assertEqual(self.at_distance(0.50).status,EnvelopeStatus.APPROACHING)
        self.assertEqual(self.at_distance(0.5001).status,EnvelopeStatus.CLEAR)

    def test_confidence_expansion(self):
        for confidence, expected in ((1,0.30),(0.75,0.35),(0.5,0.4),(0,0.5)):
            state=replace(self.state,utility=replace(self.state.utility,confidence=confidence))
            self.assertAlmostEqual(self.engine.update(state).envelope.effective_clearance_m,expected)

    def test_invalid_data(self):
        for change in ({'valid':False},{'estimated_x_m':None},{'confidence':None},
                       {'confidence':float('nan')},{'confidence':1.1},{'safe_clearance_m':-1}):
            state=replace(self.state,utility=replace(self.state.utility,**change))
            result=self.engine.update(state).envelope
            self.assertEqual(result.status,EnvelopeStatus.UNAVAILABLE)
            self.assertFalse(result.valid)
            self.assertIsNone(result.effective_clearance_m)
            self.assertEqual(result.information,'SECONDARY VERIFICATION REQUIRED')

    def test_offline_and_stale(self):
        for health in (SensorHealth.OFFLINE,SensorHealth.STALE):
            self.assertEqual(self.engine.update(replace(self.state,sensor_health=health)).envelope.status,
                             EnvelopeStatus.UNAVAILABLE)
            state=replace(self.state,utility=replace(self.state.utility,sensor_health=health))
            self.assertFalse(self.engine.update(state).envelope.valid)

    def test_world_distance_not_cached_distance(self):
        state=replace(self.state,machine=MachineState(3,3),
                      utility=replace(self.state.utility,distance_to_bucket_m=99))
        self.assertAlmostEqual(self.engine.update(state).envelope.distance_to_utility_m,5)

    def test_missing_machine(self):
        self.assertFalse(self.engine.update(replace(self.state,machine=None)).envelope.valid)
