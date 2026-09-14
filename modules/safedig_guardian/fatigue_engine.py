"""Explainable prototype estimation, not diagnosis or fitness-for-duty assessment."""

from dataclasses import dataclass, field, replace
from math import isfinite

from adapters.sensor_source import SensorHealth
from config import guardian_config as cfg
from domain.operator_state import clear_guardian, copy_guardian
from modules.safedig_guardian.eye_detection import EyeDetector
from modules.safedig_guardian.yawn_detection import YawnDetector
from modules.safedig_guardian.head_pose import estimate_head_pose
from modules.safedig_guardian.attention import AttentionEstimator, temporal_alpha


def clamp(value):
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class FatigueResult:
    score: float | None = None
    level: str = "UNKNOWN"
    valid: bool = False
    confidence: float | None = None
    primary_indicator: str = "UNAVAILABLE"
    components: dict = field(default_factory=dict)
    active_weights: dict = field(default_factory=dict)
    timestamp: float | None = None


class FatigueEngine:
    def __init__(self):
        self.eyes = EyeDetector()
        self.yawn = YawnDetector()
        self.attention = AttentionEstimator()
        self._last = self._score = self._observation = None

    def reset(self):
        self.eyes.reset(); self.yawn.reset(); self.attention.reset()
        self._last = self._score = self._observation = None

    def assess(self, eyes, yawn, pose, attention, timestamp):
        if (not eyes.valid or eyes.eye_closed_ratio_window is None
                or not isfinite(eyes.eye_closed_ratio_window) or not 0 <= eyes.eye_closed_ratio_window <= 1
                or not isfinite(timestamp)):
            self._last = self._score = None
            return FatigueResult(timestamp=timestamp)
        yawn_valid = yawn.valid and isfinite(yawn.yawn_count_window) and yawn.yawn_count_window >= 0
        attention_valid = (attention.valid and attention.attention_score is not None
                           and isfinite(attention.attention_score) and 0 <= attention.attention_score <= 1)
        components = {
            "eye_temporal": clamp(eyes.eye_closed_ratio_window/cfg.EYE_RATIO_FULL_RISK),
            "prolonged_closure": float(eyes.prolonged_eye_closure),
            "yawn": max(clamp(yawn.yawn_count_window/cfg.YAWN_FULL_COUNT),
                        cfg.YAWN_ACTIVE_COMPONENT if yawn.yawn_detected else 0.0) if yawn_valid else None,
            "attention": clamp(1-attention.attention_score) if attention_valid else None,
            "head_context": clamp(1-attention.attention_score) if pose.valid and attention_valid
                            and pose.head_pose_status != "FORWARD" else
                            0.0 if pose.valid and attention_valid else None,
        }
        active = {key: cfg.FATIGUE_WEIGHTS[key] for key, value in components.items() if value is not None}
        total = sum(active.values())
        active = {key: weight/total for key, weight in active.items()}
        contributions = {key: components[key]*weight for key, weight in active.items()}
        raw = clamp(sum(contributions.values()))*100
        if self._last is None or timestamp <= self._last or timestamp-self._last > cfg.MAX_SAMPLE_GAP_S:
            self._score = raw
        else:
            alpha = cfg.FATIGUE_SMOOTHING_ALPHA if raw > self._score else cfg.FATIGUE_RECOVERY_ALPHA
            alpha = temporal_alpha(alpha, timestamp-self._last)
            self._score = alpha*raw+(1-alpha)*self._score
        self._last = timestamp
        level = ("HIGH" if self._score >= cfg.FATIGUE_HIGH_THRESHOLD else
                 "ELEVATED" if self._score >= cfg.FATIGUE_CAUTION_THRESHOLD else "NORMAL")
        primary = max(contributions, key=contributions.get)
        if contributions[primary] == 0:
            primary = "NO DOMINANT INDICATOR"
        return FatigueResult(self._score,level,True,cfg.LANDMARK_CONFIDENCE*total,
                             primary.upper().replace('_',' '),components,active,timestamp)

    def update(self, state, width, height):
        timestamp = state.last_frame_timestamp
        if (not state.camera_available or state.camera_health != SensorHealth.VALID
                or not state.face_detected or state.face_count != 1 or not state.landmarks_available
                or timestamp is None or not isfinite(timestamp)):
            self.reset()
            return clear_guardian(state)
        if (self._last is not None and timestamp > self._last
                and timestamp-self._last < cfg.ANALYSIS_INTERVAL_S and self._observation is not None):
            return copy_guardian(state,self._observation)
        eyes = self.eyes.update(state.landmarks,width,height,timestamp)
        yawn = self.yawn.update(state.landmarks,width,height,timestamp)
        pose = estimate_head_pose(state.landmarks,width,height,timestamp)
        attention = self.attention.update(pose,timestamp)
        fatigue = self.assess(eyes,yawn,pose,attention,timestamp)
        result = replace(state,
            eyes_closed=eyes.eyes_closed,left_eye_openness=eyes.left_eye_openness,
            right_eye_openness=eyes.right_eye_openness,eye_closure_duration_ms=eyes.closure_duration_ms,
            prolonged_eye_closure=eyes.prolonged_eye_closure,blink_detected=eyes.blink_detected,
            blink_count=eyes.blink_count_window if eyes.valid else None,
            eye_closed_ratio_window=eyes.eye_closed_ratio_window,yawn_detected=yawn.yawn_detected if yawn.valid else None,
            yawn_count=yawn.yawn_count_window if yawn.valid else None,mouth_openness=yawn.mouth_openness,
            head_yaw_deg=pose.yaw_deg,head_pitch_deg=pose.pitch_deg,head_roll_deg=pose.roll_deg,
            head_pose_status=pose.head_pose_status,attention_score=attention.attention_score,
            attention_status=attention.attention_status,fatigue_score=fatigue.score,fatigue_level=fatigue.level,
            fatigue_confidence=fatigue.confidence,fatigue_valid=fatigue.valid,
            primary_fatigue_indicator=fatigue.primary_indicator,fatigue_components=fatigue.components,
            fatigue_active_weights=fatigue.active_weights,timestamp=timestamp,
            analysis_status="PROTOTYPE ESTIMATE" if fatigue.valid else "UNAVAILABLE")
        self._observation = result
        return result
