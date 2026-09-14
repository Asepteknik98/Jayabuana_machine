"""Convert simulated scene coordinates to metres; no Qt dependency."""

from dataclasses import dataclass
from math import cos, radians, sin

PIXELS_PER_METRE = 80.0  # Prototype scale, independent of window size.


@dataclass(frozen=True)
class BucketPosition:
    x_m: float
    depth_m: float  # Positive below ground, negative above ground.


def bucket_position(
    pivot_x: float, pivot_y: float, angle_degrees: float,
    tip_x: float, tip_y: float, ground_y: float,
) -> BucketPosition:
    angle = radians(angle_degrees)
    x = pivot_x + tip_x * cos(angle) - tip_y * sin(angle)
    y = pivot_y + tip_x * sin(angle) + tip_y * cos(angle)
    return BucketPosition(x / PIXELS_PER_METRE, (y - ground_y) / PIXELS_PER_METRE)
