"""Synthetic landmark sequences; no physical camera or medical assertions."""

from dataclasses import replace
import unittest

from config import guardian_config as cfg
from domain.operator_state import OperatorState,camera_observation,check_freshness
from modules.safedig_guardian.eye_detection import EyeDetector,EyeResult
from modules.safedig_guardian.yawn_detection import YawnDetector,YawnResult
from modules.safedig_guardian.head_pose import estimate_head_pose,HeadPoseResult
from modules.safedig_guardian.attention import AttentionEstimator,AttentionResult
from modules.safedig_guardian.fatigue_engine import FatigueEngine


def landmarks(closed=False,mouth_open=False,away=False):
    points=[(0.5,0.5,0.0)]*478
    # Pixel-correct ratios for a square synthetic frame.
    for indices,x in ((cfg.LEFT_EYE,.25),(cfg.RIGHT_EYE,.55)):
        height=.005 if closed else .03
        values=((x,.3,0),(x+.03,.3-height,0),(x+.07,.3-height,0),(x+.10,.3,0),
                (x+.07,.3+height,0),(x+.03,.3+height,0))
        for index,value in zip(indices,values):points[index]=value
    points[61]=(.35,.60,0);points[291]=(.55,.60,0)
    gap=.14 if mouth_open else .01
    points[13]=(.45,.60-gap/2,0);points[14]=(.45,.60+gap/2,0)
    points[1]=(.60 if away else .45,.525,0);points[152]=(.45,.80,0)
    return tuple(points)


def observation(t,**kwargs):
    return camera_observation(t,t,(landmarks(**kwargs),))


class FatigueTests(unittest.TestCase):
    def sequence(self,engine,start,end,**kwargs):
        result=None
        for i in range(round(start*10),round(end*10)+1):
            result=engine.update(observation(i/10,**kwargs),1000,1000)
        return result

    def test_open_normal(self):
        result=self.sequence(FatigueEngine(),0,2)
        self.assertTrue(result.fatigue_valid)
        self.assertEqual(result.fatigue_level,'NORMAL')
        self.assertLess(result.fatigue_score,10)

    def test_short_blink(self):
        eyes=EyeDetector()
        eyes.update(landmarks(),1000,1000,0)
        eyes.update(landmarks(closed=True),1000,1000,.1)
        result=eyes.update(landmarks(),1000,1000,.25)
        self.assertTrue(result.blink_detected)
        self.assertEqual(result.blink_count_window,1)
        self.assertFalse(result.prolonged_eye_closure)
        self.assertLess(result.eye_closed_ratio_window,.1)

    def test_prolonged_and_slow_recovery(self):
        engine=FatigueEngine();self.sequence(engine,0,1)
        result=self.sequence(engine,1.1,5,closed=True)
        self.assertTrue(result.prolonged_eye_closure)
        self.assertGreater(result.fatigue_score,50)
        reopened=engine.update(observation(5.1),1000,1000)
        self.assertGreater(reopened.fatigue_score,result.fatigue_score-10)

    def test_yawn_moderate(self):
        engine=FatigueEngine();self.sequence(engine,0,1)
        result=self.sequence(engine,1.1,2.5,mouth_open=True)
        self.assertTrue(result.yawn_detected)
        self.assertEqual(result.yawn_count,1)
        self.assertGreater(result.fatigue_score,0)
        self.assertLess(result.fatigue_score,25)

    def test_repeated_yawns(self):
        engine=FatigueEngine()
        one=self.sequence(engine,0,1.5,mouth_open=True)
        self.sequence(engine,1.6,2)
        self.sequence(engine,2.1,3.5,mouth_open=True)
        self.sequence(engine,3.6,4)
        three=self.sequence(engine,4.1,5.5,mouth_open=True)
        self.assertEqual(three.yawn_count,3)
        self.assertGreater(three.fatigue_score,one.fatigue_score)

    def test_brief_mouth_open_not_yawn(self):
        detector=YawnDetector()
        detector.update(landmarks(mouth_open=True),1000,1000,0)
        result=detector.update(landmarks(),1000,1000,.2)
        self.assertEqual(result.yawn_count_window,0)

    def test_attention_and_head_not_dominant(self):
        engine=FatigueEngine();normal=self.sequence(engine,0,1)
        brief=self.sequence(engine,1.1,1.3,away=True)
        self.assertGreater(brief.attention_score,.75)
        away=self.sequence(engine,1.4,5,away=True)
        self.assertLess(away.attention_score,normal.attention_score)
        self.assertEqual(away.attention_status,'DISTRACTED')
        self.assertLess(away.fatigue_score,25)

    def test_offline_absent_multiple(self):
        for state in (OperatorState(),camera_observation(3,3,()),camera_observation(3,3,(landmarks(),landmarks()))):
            engine=FatigueEngine();self.sequence(engine,0,2,closed=True)
            result=engine.update(state,1000,1000)
            self.assertIsNone(result.fatigue_score)
            self.assertIsNone(result.attention_score)
            self.assertFalse(result.fatigue_valid)

    def test_active_weights(self):
        engine=FatigueEngine()
        result=engine.assess(EyeResult(valid=True,eye_closed_ratio_window=.1),YawnResult(),HeadPoseResult(),AttentionResult(),0)
        self.assertTrue(result.valid)
        self.assertAlmostEqual(sum(result.active_weights.values()),1)
        self.assertNotIn('yawn',result.active_weights)
        self.assertIsNone(result.components['yawn'])

    def test_bounds_smoothing(self):
        engine=FatigueEngine();previous=0
        for i in range(60):
            result=engine.update(observation(i/10,closed=True,mouth_open=True,away=True),1000,1000)
            self.assertTrue(0<=result.fatigue_score<=100)
            self.assertLess(abs(result.fatigue_score-previous),20)
            previous=result.fatigue_score

    def test_gap_and_invalid_eyes(self):
        eyes=EyeDetector();eyes.update(landmarks(closed=True),1000,1000,0)
        result=eyes.update(landmarks(closed=True),1000,1000,5)
        self.assertFalse(result.prolonged_eye_closure)
        self.assertEqual(result.closure_duration_ms,0)
        state=replace(observation(0),landmarks=())
        self.assertIsNone(FatigueEngine().update(state,1000,1000).fatigue_score)

    def test_stale_clears_scores(self):
        state=self.sequence(FatigueEngine(),0,2,closed=True)
        stale=check_freshness(state,4,1)
        self.assertIsNone(stale.fatigue_score)
        self.assertIsNone(stale.eyes_closed)
        self.assertIsNone(stale.attention_score)

    def test_invalid_pose_unknown(self):
        pose=estimate_head_pose((),1000,1000,0)
        self.assertFalse(pose.valid)
        self.assertIsNone(pose.yaw_deg)

    def test_invalid_optional_component_excluded(self):
        result=FatigueEngine().assess(EyeResult(valid=True,eye_closed_ratio_window=.1),
            YawnResult(),HeadPoseResult(),AttentionResult(float('nan'),'UNKNOWN',True),0)
        self.assertNotIn('attention',result.active_weights)
        self.assertIsNone(result.components['attention'])
