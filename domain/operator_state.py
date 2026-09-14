"""Immutable real camera observations and prototype Guardian estimates."""

from dataclasses import dataclass, replace, field
from adapters.sensor_source import SensorHealth


@dataclass(frozen=True)
class OperatorState:
    camera_available: bool = False
    camera_health: SensorHealth = SensorHealth.OFFLINE
    face_detected: bool = False
    face_count: int = 0
    landmarks_available: bool = False
    last_frame_timestamp: float | None = None
    last_detection_timestamp: float | None = None
    valid: bool = False
    face_status: str = "UNKNOWN"
    analysis_status: str = "UNAVAILABLE"
    landmarks: tuple[tuple[float, float, float], ...] = ()
    diagnostic: str = ""
    eyes_closed: bool | None = None
    left_eye_openness: float | None = None
    right_eye_openness: float | None = None
    eye_closure_duration_ms: float | None = None
    prolonged_eye_closure: bool = False
    blink_detected: bool = False
    blink_count: int | None = None
    eye_closed_ratio_window: float | None = None
    yawn_detected: bool | None = None
    yawn_count: int | None = None
    mouth_openness: float | None = None
    head_yaw_deg: float | None = None
    head_pitch_deg: float | None = None
    head_roll_deg: float | None = None
    head_pose_status: str = "UNKNOWN"
    attention_score: float | None = None
    attention_status: str = "UNKNOWN"
    fatigue_score: float | None = None
    fatigue_level: str = "UNKNOWN"
    fatigue_confidence: float | None = None
    fatigue_valid: bool = False
    primary_fatigue_indicator: str = "UNAVAILABLE"
    fatigue_components: dict[str, float | None] = field(default_factory=dict)
    fatigue_active_weights: dict[str, float] = field(default_factory=dict)
    timestamp: float | None = None


GUARDIAN_FIELDS = (
    "eyes_closed", "left_eye_openness", "right_eye_openness", "eye_closure_duration_ms",
    "prolonged_eye_closure", "blink_detected", "blink_count", "eye_closed_ratio_window",
    "yawn_detected", "yawn_count", "mouth_openness", "head_yaw_deg", "head_pitch_deg",
    "head_roll_deg", "head_pose_status", "attention_score", "attention_status",
    "fatigue_score", "fatigue_level", "fatigue_confidence", "fatigue_valid",
    "primary_fatigue_indicator", "fatigue_components", "fatigue_active_weights", "timestamp",
)


def copy_guardian(state: OperatorState, previous: OperatorState) -> OperatorState:
    return replace(state, **{name: getattr(previous, name) for name in GUARDIAN_FIELDS})


def clear_guardian(state: OperatorState) -> OperatorState:
    return copy_guardian(state, OperatorState())


def camera_observation(frame_time: float, detection_time: float | None,
                       faces: tuple, diagnostic: str = "") -> OperatorState:
    available = detection_time is not None
    count = len(faces) if available else 0
    single = available and count == 1
    return OperatorState(
        camera_available=True, camera_health=SensorHealth.VALID,
        face_detected=count > 0, face_count=count,
        landmarks_available=single and bool(faces[0]),
        last_frame_timestamp=frame_time, last_detection_timestamp=detection_time,
        valid=single, face_status=("FACE ANALYSIS OFFLINE" if not available else
                                  "MULTIPLE FACES" if count > 1 else "DETECTED" if single else "NOT DETECTED"),
        analysis_status="AMBIGUOUS" if count > 1 else "FOUNDATION AVAILABLE" if single else "UNAVAILABLE",
        landmarks=faces[0] if single else (), diagnostic=diagnostic,
    )


def check_freshness(state: OperatorState, now: float, stale_seconds: float) -> OperatorState:
    if (state.camera_available and state.last_frame_timestamp is not None
            and now - state.last_frame_timestamp > stale_seconds):
        return clear_guardian(replace(state, camera_available=False, camera_health=SensorHealth.STALE,
                       face_detected=False, face_count=0, landmarks_available=False, landmarks=(),
                       valid=False, face_status="UNKNOWN", analysis_status="UNAVAILABLE"))
    return state
