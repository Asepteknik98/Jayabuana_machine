"""Adapt existing bucket geometry to the source-neutral machine contract."""
from modules.safedig_vision.utility_model import MachineState

def machine_state(position, geometry, plan_center, timestamp):
    return MachineState(position.x_m, -position.depth_m, geometry.target_depth_m,
        geometry.target_width_m, geometry.target_slope_percent, geometry.current_depth_m,
        plan_center, geometry.bucket_speed_m_s, timestamp)
