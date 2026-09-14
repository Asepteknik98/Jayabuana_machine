"""Compact source-neutral assessment snapshot; absent values remain unknown."""
from dataclasses import dataclass

@dataclass(frozen=True)
class FusionState:
    timestamp: float
    vision_valid: bool = False
    precision_valid: bool = False
    guardian_valid: bool = False
    utility_detected: bool = False
    utility_confidence: float | None = None
    utility_distance_m: float | None = None
    sensor_health: str = "OFFLINE"
    envelope_status: str = "UNAVAILABLE"
    clearance_margin_m: float | None = None
    effective_clearance_m: float | None = None
    bucket_speed_mps: float | None = None
    design_conflict_status: str = "UNKNOWN"
    fatigue_available: bool = False
    fatigue_score: float | None = None
    fatigue_normalized: float | None = None
    attention_available: bool = False
    attention_score: float | None = None
    verification_required: bool = True
    fusion_valid: bool = False
    fusion_confidence: str = "UNAVAILABLE"
    context_flags: frozenset[str] = frozenset()
    signal_quality: float | None = None
