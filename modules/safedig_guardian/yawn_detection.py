"""Sustained mouth-opening heuristic; brief speech is not a yawn event."""

from collections import deque
from dataclasses import dataclass
from math import isfinite
from config import guardian_config as cfg
from modules.safedig_guardian.eye_detection import image_points, distance


@dataclass(frozen=True)
class YawnResult:
    mouth_openness: float | None = None
    mouth_open: bool | None = None
    yawn_detected: bool = False
    yawn_duration_ms: float | None = None
    yawn_count_window: int = 0
    valid: bool = False
    confidence: float | None = None
    timestamp: float | None = None


class YawnDetector:
    def __init__(self):
        self.reset()

    def reset(self):
        self._start = self._last = None
        self._counted = False
        self._events = deque()

    def update(self, landmarks, width, height, timestamp):
        points = image_points(landmarks, cfg.MOUTH, width, height)
        if points is None or distance(points[0], points[1]) <= cfg.MIN_GEOMETRY_SPAN or not isfinite(timestamp):
            self.reset()
            return YawnResult(timestamp=timestamp)
        if self._last is not None and (timestamp <= self._last or timestamp-self._last > cfg.MAX_SAMPLE_GAP_S):
            self.reset()
        ratio = distance(points[2], points[3]) / distance(points[0], points[1])
        opened = ratio > cfg.YAWN_THRESHOLD
        if opened and self._start is None:
            self._start = timestamp
        if not opened:
            self._start, self._counted = None, False
        duration = (timestamp-self._start)*1000 if self._start is not None else 0.0
        detected = opened and duration >= cfg.YAWN_MIN_DURATION_MS
        if detected and not self._counted:
            self._events.append(timestamp)
            self._counted = True
        while self._events and self._events[0] < timestamp-cfg.YAWN_WINDOW_S:
            self._events.popleft()
        self._last = timestamp
        return YawnResult(ratio, opened, detected, duration, len(self._events), True,
                          cfg.LANDMARK_CONFIDENCE, timestamp)
