"""Depth measurements only; does not control machine motion."""

TARGET_DEPTH_M = 1.50


def current_depth(signed_depth_m: float) -> float:
    return max(0.0, signed_depth_m)


def remaining_depth(current_depth_m: float, target_depth_m: float = TARGET_DEPTH_M) -> float:
    """Keep negative remaining depth to indicate excavation beyond target."""
    return target_depth_m - current_depth_m
