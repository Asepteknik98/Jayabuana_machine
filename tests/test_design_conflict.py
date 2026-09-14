"""Planned geometry is independent of current bucket proximity."""

from dataclasses import replace
import unittest
from adapters.sensor_source import SafeDigState,SensorHealth
from modules.safedig_vision.utility_model import UtilityState,MachineState
from core.safe_envelope import SafeEnvelopeEngine,EnvelopeStatus
from modules.safedig_precision.design_conflict import DesignConflictEngine,ConflictStatus


class DesignConflictTests(unittest.TestCase):
    def setUp(self):
        self.utility=UtilityState(detected=True,valid=True,estimated_x_m=4.2,estimated_z_m=-1.32,
                                  confidence=0.9,sensor_health=SensorHealth.VALID,timestamp=1)
        self.machine=MachineState(0,0,1.5,0.8,2,0,4)

    def evaluate(self,**changes):
        machine=changes.get('machine',self.machine)
        utility=changes.get('utility',self.utility)
        state=SafeDigState(None,changes.get('health',SensorHealth.VALID),'',utility=utility,machine=machine)
        return DesignConflictEngine().update(SafeEnvelopeEngine().update(state))

    def test_shallow(self):
        result=self.evaluate(machine=replace(self.machine,target_depth_m=0.7)).design_conflict
        self.assertEqual(result.status,ConflictStatus.NO_CONFLICT)
        self.assertAlmostEqual(result.planned_clearance_m,0.3)

    def test_overlap_while_bucket_clear(self):
        state=self.evaluate()
        self.assertEqual(state.envelope.status,EnvelopeStatus.CLEAR)
        self.assertEqual(state.design_conflict.status,ConflictStatus.DESIGN_CONFLICT)
        self.assertTrue(state.design_conflict.horizontal_overlap)
        self.assertTrue(state.design_conflict.vertical_overlap)
        self.assertLess(state.design_conflict.planned_clearance_m,0)

    def test_horizontal_separation(self):
        state=self.evaluate(utility=replace(self.utility,estimated_x_m=8))
        self.assertEqual(state.design_conflict.status,ConflictStatus.NO_CONFLICT)

    def test_low_confidence(self):
        result=self.evaluate(utility=replace(self.utility,confidence=0.48)).design_conflict
        self.assertEqual(result.status,ConflictStatus.POTENTIAL_CONFLICT)
        self.assertTrue(result.verification_required)

    def test_offline_and_missing(self):
        for state in (self.evaluate(health=SensorHealth.OFFLINE),self.evaluate(health=SensorHealth.STALE),
                      self.evaluate(utility=replace(self.utility,estimated_x_m=None))):
            self.assertEqual(state.design_conflict.status,ConflictStatus.UNKNOWN)
            self.assertTrue(state.design_conflict.verification_required)

    def test_target_change(self):
        shallow=self.evaluate(machine=replace(self.machine,target_depth_m=0.7))
        deep=self.evaluate()
        self.assertNotEqual(shallow.design_conflict.status,deep.design_conflict.status)

    def test_expansion(self):
        machine=replace(self.machine,target_depth_m=0.85)
        high=self.evaluate(machine=machine)
        low=self.evaluate(machine=machine,utility=replace(self.utility,confidence=0.48))
        self.assertGreater(low.envelope.effective_clearance_m,high.envelope.effective_clearance_m)
        self.assertLess(low.design_conflict.planned_clearance_m,high.design_conflict.planned_clearance_m)
        self.assertEqual(low.design_conflict.status,ConflictStatus.POTENTIAL_CONFLICT)

    def test_corner_uses_circle_not_bounding_box(self):
        utility=replace(self.utility,estimated_x_m=4.65,estimated_z_m=-1.75,confidence=1)
        result=self.evaluate(utility=utility).design_conflict
        self.assertTrue(result.horizontal_overlap and result.vertical_overlap)
        self.assertGreater(result.planned_clearance_m,0)
        self.assertFalse(result.conflict_detected)

    def test_near_and_touch(self):
        result=self.evaluate(machine=replace(self.machine,target_depth_m=0.92)).design_conflict
        self.assertEqual(result.status,ConflictStatus.POTENTIAL_CONFLICT)
        result=self.evaluate(machine=replace(self.machine,target_depth_m=1.0)).design_conflict
        self.assertAlmostEqual(result.planned_clearance_m,0)
        self.assertEqual(result.status,ConflictStatus.DESIGN_CONFLICT)

    def test_invalid_plan(self):
        result=self.evaluate(machine=replace(self.machine,target_width_m=-1)).design_conflict
        self.assertEqual(result.status,ConflictStatus.UNKNOWN)
