"""Geometric eye ratios and time-weighted, prototype closure metric."""

from collections import deque
from dataclasses import dataclass
from math import hypot, isfinite
from config import guardian_config as cfg


def image_points(landmarks, indices, width, height):
    if width <= 0 or height <= 0:
        return None
    try:
        points = tuple((landmarks[i][0] * width, landmarks[i][1] * height) for i in indices)
    except (IndexError, TypeError):
        return None
    return points if all(isfinite(v) for p in points for v in p) else None


def distance(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


def eye_ratio(landmarks, indices, width, height):
    points = image_points(landmarks, indices, width, height)
    if points is None or distance(points[0], points[3]) <= cfg.MIN_GEOMETRY_SPAN:
        return None
    return (distance(points[1], points[5]) + distance(points[2], points[4])) / (2 * distance(points[0], points[3]))


@dataclass(frozen=True)
class EyeResult:
    left_eye_openness: float | None = None
    right_eye_openness: float | None = None
    eyes_closed: bool | None = None
    closure_duration_ms: float | None = None
    prolonged_eye_closure: bool = False
    blink_detected: bool = False
    blink_count_window: int = 0
    eye_closed_ratio_window: float | None = None
    valid: bool = False
    confidence: float | None = None
    timestamp: float | None = None


class EyeDetector:
    def __init__(self):
        self.reset()

    def reset(self):
        self._last = self._closed_since = None
        self._was_closed = False
        self._segments = deque()
        self._blinks = deque()

    def update(self, landmarks, width, height, timestamp):
        left = eye_ratio(landmarks, cfg.LEFT_EYE, width, height)
        right = eye_ratio(landmarks, cfg.RIGHT_EYE, width, height)
        if left is None or right is None or not isfinite(timestamp):
            self.reset()
            return EyeResult(timestamp=timestamp)
        if self._last is not None and (timestamp <= self._last or timestamp - self._last > cfg.MAX_SAMPLE_GAP_S):
            self.reset()
        closed = left < cfg.EYE_CLOSED_THRESHOLD and right < cfg.EYE_CLOSED_THRESHOLD
        if self._last is not None:
            self._segments.append((self._last, timestamp, self._was_closed))
        blink = False
        if closed and self._closed_since is None:
            self._closed_since = timestamp
        duration = (timestamp - self._closed_since) * 1000 if self._closed_since is not None else 0.0
        if not closed and self._closed_since is not None:
            blink = cfg.BLINK_MIN_MS <= duration <= cfg.BLINK_MAX_MS
            if blink:
                self._blinks.append(timestamp)
            self._closed_since = None
            duration = 0.0
        cutoff = timestamp - cfg.EYE_WINDOW_S
        while self._segments and self._segments[0][1] <= cutoff:
            self._segments.popleft()
        while self._blinks and self._blinks[0] < cutoff:
            self._blinks.popleft()
        # PROTOTYPE TEMPORAL EYE-CLOSURE METRIC; not validated PERCLOS.
        observed = sum(end - max(start, cutoff) for start, end, _ in self._segments)
        shut = sum(end - max(start, cutoff) for start, end, was_closed in self._segments if was_closed)
        ratio = shut / max(cfg.EYE_MIN_OBSERVATION_S, observed)
        self._last, self._was_closed = timestamp, closed
        return EyeResult(left, right, closed, duration,
                         closed and duration >= cfg.PROLONGED_EYE_CLOSURE_MS,
                         blink, len(self._blinks), ratio, True, cfg.LANDMARK_CONFIDENCE, timestamp)
