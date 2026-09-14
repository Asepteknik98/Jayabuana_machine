"""Geometry readings derived from simulated bucket tip positions."""

from dataclasses import dataclass
from math import hypot

from modules.safedig_precision.bucket_position import BucketPosition
from modules.safedig_precision.depth_control import (
    TARGET_DEPTH_M, current_depth, remaining_depth,
)

TARGET_WIDTH_M = 0.80
TARGET_SLOPE_PERCENT = 2.0


@dataclass(frozen=True)
class DigGeometry:
    current_depth_m: float
    remaining_depth_m: float
    bucket_speed_m_s: float
    target_depth_m: float = TARGET_DEPTH_M
    target_width_m: float = TARGET_WIDTH_M
    target_slope_percent: float = TARGET_SLOPE_PERCENT


def calculate_geometry(
    position: BucketPosition, previous: BucketPosition | None = None,
    elapsed_seconds: float = 0.0,
) -> DigGeometry:
    if elapsed_seconds < 0:
        raise ValueError("Elapsed time must not be negative")
    speed = 0.0
    if previous is not None and elapsed_seconds > 0:
        speed = hypot(position.x_m - previous.x_m,
                      position.depth_m - previous.depth_m) / elapsed_seconds
    depth = current_depth(position.depth_m)
    return DigGeometry(depth, remaining_depth(depth), speed)
