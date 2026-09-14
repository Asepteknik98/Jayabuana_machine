"""PROTOTYPE HEAD POSE ESTIMATION from relative face geometry, not calibrated 3D pose."""

from dataclasses import dataclass
from math import atan2, degrees
from config import guardian_config as cfg
from modules.safedig_guardian.eye_detection import image_points, distance


@dataclass(frozen=True)
class HeadPoseResult:
    yaw_deg: float | None = None
    pitch_deg: float | None = None
    roll_deg: float | None = None
    head_pose_status: str = "UNKNOWN"
    valid: bool = False
    confidence: float | None = None
    timestamp: float | None = None


def estimate_head_pose(landmarks, width, height, timestamp):
    points = image_points(landmarks, cfg.HEAD_ANCHORS, width, height)
    if points is None:
        return HeadPoseResult(timestamp=timestamp)
    left, right, nose, chin = points
    span = distance(left, right)
    if span <= cfg.MIN_GEOMETRY_SPAN:
        return HeadPoseResult(timestamp=timestamp)
    ux, uy = (right[0]-left[0])/span, (right[1]-left[1])/span
    mid = ((left[0]+right[0])/2, (left[1]+right[1])/2)
    nose_x = (nose[0]-mid[0])*ux + (nose[1]-mid[1])*uy
    nose_y = -(nose[0]-mid[0])*uy + (nose[1]-mid[1])*ux
    chin_y = -(chin[0]-mid[0])*uy + (chin[1]-mid[1])*ux
    if chin_y <= cfg.MIN_GEOMETRY_SPAN:
        return HeadPoseResult(timestamp=timestamp)
    yaw = max(-cfg.HEAD_MAX_ANGLE_DEG,min(cfg.HEAD_MAX_ANGLE_DEG,nose_x/span*cfg.HEAD_YAW_GAIN_DEG))
    pitch = max(-cfg.HEAD_MAX_ANGLE_DEG,min(cfg.HEAD_MAX_ANGLE_DEG,
                (nose_y/chin_y-cfg.HEAD_PITCH_NEUTRAL_RATIO)*cfg.HEAD_PITCH_GAIN_DEG))
    status = ("LEFT" if yaw < -cfg.HEAD_YAW_LIMIT_DEG else "RIGHT" if yaw > cfg.HEAD_YAW_LIMIT_DEG
              else "UP" if pitch < -cfg.HEAD_PITCH_LIMIT_DEG else "DOWN" if pitch > cfg.HEAD_PITCH_LIMIT_DEG else "FORWARD")
    return HeadPoseResult(yaw,pitch,degrees(atan2(uy,ux)),status,True,cfg.LANDMARK_CONFIDENCE,timestamp)
