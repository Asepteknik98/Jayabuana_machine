"""Scenario movement reuses the Precision geometry calculations."""
from dataclasses import replace
from modules.safedig_precision.bucket_position import BucketPosition
from modules.safedig_precision.dig_geometry import calculate_geometry

class ExcavatorSimulator:
    def __init__(self):
        self.previous = None
        self.last_time = None

    def sample(self, inputs, excavation, elapsed):
        position = BucketPosition(inputs["bucket_x_m"], inputs["bucket_depth_m"])
        dt = elapsed-self.last_time if self.last_time is not None else 0.
        geometry = calculate_geometry(position, self.previous, max(0., dt))
        geometry = replace(geometry, target_depth_m=excavation["target_depth_m"],
            remaining_depth_m=excavation["target_depth_m"]-geometry.current_depth_m,
            target_width_m=excavation["target_width_m"], target_slope_percent=excavation["target_slope_percent"])
        self.previous, self.last_time = position, elapsed
        return position, geometry
