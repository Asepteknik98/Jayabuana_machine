from dataclasses import replace
import unittest
from adapters.sensor_source import SafeDigState,SensorHealth
from core.decision_engine import DecisionEngine,DecisionAction,PRIORITY
from core.risk_engine import RiskState,RiskLevel
from core.safe_envelope import EnvelopeState,EnvelopeStatus
from modules.safedig_precision.design_conflict import DesignConflictState,ConflictStatus
from modules.safedig_vision.gpr_simulator import GPRSimulator
from modules.safedig_vision.utility_model import UtilityState,MachineState

class DecisionTests(unittest.TestCase):
 def state(self,level=RiskLevel.SAFE,env=EnvelopeStatus.CLEAR,conflict=ConflictStatus.NO_CONFLICT):
  return SafeDigState(GPRSimulator().read(6),SensorHealth.VALID,'',
   utility=UtilityState(detected=True,valid=True,confidence=.9,sensor_health=SensorHealth.VALID),
   machine=MachineState(0,0,bucket_speed_mps=.1),
   envelope=EnvelopeState(valid=True,status=env,clearance_margin_m=.5),
   design_conflict=DesignConflictState(valid=True,status=conflict,verification_required=False),
   risk=RiskState(total_score=50,level=level,risk_valid=True,risk_confidence=.9,verification_required=False,timestamp=6))
 def action(self,state):return DecisionEngine().update(state).decision.action
 def test_normal(self):self.assertEqual(self.action(self.state()),DecisionAction.NORMAL)
 def test_warn(self):self.assertEqual(self.action(self.state(RiskLevel.CAUTION)),DecisionAction.WARN)
 def test_slow(self):self.assertEqual(self.action(self.state(RiskLevel.HIGH,EnvelopeStatus.APPROACHING)),DecisionAction.SLOW)
 def test_verify(self):
  s=self.state(RiskLevel.CAUTION);s=replace(s,risk=replace(s.risk,verification_required=True,risk_confidence=.43))
  self.assertEqual(self.action(s),DecisionAction.VERIFY)
 def test_restrict(self):self.assertEqual(self.action(self.state(RiskLevel.CRITICAL,EnvelopeStatus.INSIDE)),DecisionAction.RESTRICT)
 def test_offline(self):
  for h in (SensorHealth.OFFLINE,SensorHealth.STALE):self.assertEqual(self.action(replace(self.state(),sensor_health=h)),DecisionAction.VERIFY)
 def test_future_conflict(self):self.assertEqual(self.action(self.state(RiskLevel.HIGH,conflict=ConflictStatus.DESIGN_CONFLICT)),DecisionAction.SLOW)
 def test_low_conflict(self):
  s=self.state(RiskLevel.HIGH,conflict=ConflictStatus.DESIGN_CONFLICT)
  self.assertEqual(self.action(replace(s,utility=replace(s.utility,confidence=.4))),DecisionAction.VERIFY)
 def test_priority(self):
  self.assertEqual(list(PRIORITY.values()),[0,1,2,3,4])
  s=self.state(RiskLevel.CRITICAL,EnvelopeStatus.INSIDE)
  s=replace(s,risk=replace(s.risk,verification_required=True))
  self.assertEqual(self.action(s),DecisionAction.RESTRICT)
 def test_deescalation(self):
  e=DecisionEngine();e.update(self.state(RiskLevel.CRITICAL,EnvelopeStatus.INSIDE))
  self.assertEqual([e.update(self.state()).decision.action for _ in range(3)],
                   [DecisionAction.RESTRICT,DecisionAction.RESTRICT,DecisionAction.NORMAL])
  self.assertEqual(e.update(self.state(RiskLevel.HIGH)).decision.action,DecisionAction.SLOW)
 def test_stability_reset(self):
  e=DecisionEngine();e.update(self.state(RiskLevel.HIGH))
  for level in (RiskLevel.SAFE,RiskLevel.CAUTION,RiskLevel.SAFE,RiskLevel.CAUTION):
   self.assertEqual(e.update(self.state(level)).decision.action,DecisionAction.SLOW)
 def test_risk_unchanged_reason(self):
  s=self.state();r=DecisionEngine().update(s)
  self.assertIs(r.risk,s.risk);self.assertTrue(r.decision.reason)
 def test_critical_requires_context(self):self.assertEqual(self.action(self.state(RiskLevel.CRITICAL)),DecisionAction.SLOW)
 def test_missing(self):self.assertEqual(self.action(SafeDigState(None,SensorHealth.OFFLINE,'')),DecisionAction.VERIFY)
 def test_offline_clears_restriction(self):
  e=DecisionEngine();e.update(self.state(RiskLevel.CRITICAL,EnvelopeStatus.INSIDE))
  d=e.update(replace(self.state(),sensor_health=SensorHealth.OFFLINE)).decision
  self.assertEqual(d.action,DecisionAction.VERIFY);self.assertIsNone(d.restrict_direction)
