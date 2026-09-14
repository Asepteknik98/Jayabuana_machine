"""Duration-aware attention context, not gaze tracking."""

from dataclasses import dataclass
from config import guardian_config as cfg


def temporal_alpha(alpha, elapsed):
    return 1 - (1-alpha) ** (elapsed/cfg.TEMPORAL_REFERENCE_S)


@dataclass(frozen=True)
class AttentionResult:
    attention_score: float | None = None
    attention_status: str = "UNKNOWN"
    valid: bool = False
    timestamp: float | None = None


class AttentionEstimator:
    def __init__(self):
        self.reset()

    def reset(self):
        self._away_since = self._last = self._score = None

    def update(self, pose, timestamp):
        if not pose.valid:
            self.reset()
            return AttentionResult(timestamp=timestamp)
        if self._last is not None and (timestamp<=self._last or timestamp-self._last>cfg.MAX_SAMPLE_GAP_S):
            self.reset()
        if pose.head_pose_status == 'FORWARD':
            self._away_since = None
        elif self._away_since is None:
            self._away_since = timestamp
        away = timestamp-self._away_since if self._away_since is not None else 0
        target = (1.0 if away < cfg.ATTENTION_AWAY_GRACE_S else
                  cfg.ATTENTION_PARTIAL_TARGET if away < cfg.ATTENTION_DISTRACTED_AFTER_S else cfg.ATTENTION_DISTRACTED_TARGET)
        alpha = temporal_alpha(cfg.ATTENTION_SMOOTHING_ALPHA,timestamp-self._last) if self._last is not None else 1
        self._score = target if self._score is None else alpha*target+(1-alpha)*self._score
        self._last = timestamp
        status = ('ATTENTIVE' if self._score >= cfg.ATTENTION_ATTENTIVE_THRESHOLD else
                  'PARTIAL' if self._score >= cfg.ATTENTION_PARTIAL_THRESHOLD else 'DISTRACTED')
        return AttentionResult(self._score,status,True,timestamp)
