"""Run with python -m unittest discover -s tests -p test_utility_detector.py."""

from dataclasses import replace
import unittest

from adapters.sensor_source import SafeDigState, SensorHealth
from modules.safedig_vision.gpr_simulator import GPRSimulator
from modules.safedig_vision.utility_detector import UtilityDetector
from modules.safedig_vision.utility_model import MachineState, UtilityType


class UtilityDetectorTests(unittest.TestCase):
    def setUp(self):
        self.source = GPRSimulator()
        self.detector = UtilityDetector()

    def detect(self, sensor, now=6, machine=None):
        return self.detector.update(SafeDigState.from_sensor(sensor, now), machine).utility

    def test_low_anomaly_has_no_fabricated_position(self):
        result = self.detect(self.source.read(0), 0)
        self.assertFalse(result.detected)
        self.assertEqual(result.status, 'NO SIGNIFICANT ANOMALY')
        self.assertIsNone(result.estimated_depth_m)
        self.assertIsNone(result.distance_to_bucket_m)

    def test_high_anomaly_estimate_is_repeatable(self):
        sensor = self.source.read(6)
        result = self.detect(sensor)
        self.assertTrue(result.detected)
        self.assertEqual(result.estimated_type, UtilityType.POSSIBLE_FIBER_OPTIC_CONDUIT)
        self.assertEqual(result, self.detect(self.source.read(6)))
        self.assertGreater(result.estimated_depth_m, 1.32)
        self.assertLess(result.estimated_depth_m, 1.38)

    def test_low_confidence_candidate_requires_verification(self):
        self.source.set_soil('WET_CLAY')
        result = self.detect(self.source.read(6))
        self.assertTrue(result.detected)
        self.assertEqual(result.status, 'POSSIBLE UTILITY')
        self.assertEqual(result.confidence_status, 'LOW')
        self.assertEqual(result.verification_info, 'SECONDARY VERIFICATION REQUIRED')

    def test_offline_and_stale_clear_estimate(self):
        for sensor, now in ((None,6), (replace(self.source.read(6),sensor_health=SensorHealth.OFFLINE),6),
                            (self.source.read(6),8)):
            result = self.detect(sensor,now)
            self.assertFalse(result.valid)
            self.assertEqual(result.status,'UTILITY ESTIMATE UNAVAILABLE')
            self.assertEqual(result.estimated_type,UtilityType.UNKNOWN)
            self.assertIsNone(result.estimated_depth_m)

    def test_distance_uses_world_metres_and_negative_z(self):
        sensor = replace(self.source.read(6),estimated_x_m=3,estimated_z_m=-4)
        self.assertEqual(self.detect(sensor,machine=MachineState(0,0)).distance_to_bucket_m,5)
        self.assertEqual(self.detect(sensor,machine=MachineState(3,-3)).distance_to_bucket_m,1)

    def test_unknown_response_and_missing_location(self):
        sensor = replace(self.source.read(6),response_profile='UNRECOGNIZED',estimated_x_m=None)
        result = self.detect(sensor)
        self.assertEqual(result.estimated_type,UtilityType.UNKNOWN)
        self.assertFalse(result.valid)
        self.assertIsNone(result.distance_to_bucket_m)
