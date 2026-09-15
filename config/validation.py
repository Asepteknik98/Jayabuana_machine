"""Small startup checks for consequential prototype parameters."""
from math import isfinite
from config import risk_config, envelope_config, camera_config, fusion_config, simulation_config


def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and isfinite(value)


def validate_configuration():
    errors=[]
    weights=risk_config.WEIGHTS
    if (not isinstance(weights,dict) or set(weights)!={"utility","confidence","fatigue","velocity","design"}
            or any(not finite(v) or v<0 for v in weights.values()) or sum(weights.values())<=0):
        errors.append("Risk weights must contain U/P/F/V/C, be finite and nonnegative, with positive sum")
    up,down=risk_config.LEVEL_UP_THRESHOLDS,risk_config.LEVEL_DOWN_THRESHOLDS
    if (not isinstance(up,(tuple,list)) or not isinstance(down,(tuple,list)) or len(up)!=3 or len(down)!=3 or any(not finite(v) or not 0<=v<=100 for v in (*up,*down))
            or any(a>=b for a,b in zip(up,up[1:])) or any(a>=b for a,b in zip(down,down[1:]))
            or any(a>=b for a,b in zip(down,up))):
        errors.append("Risk thresholds must be ordered; de-escalation must be below escalation")
    for name,value in (("Safe clearance",envelope_config.BASE_SAFE_CLEARANCE_M),
            ("Simulation dt",simulation_config.SIMULATION_DT),("Telemetry interval",simulation_config.TELEMETRY_INTERVAL_S),
            ("Vision stale timeout",fusion_config.VISION_STALE_AFTER_S),
            ("Precision stale timeout",fusion_config.PRECISION_STALE_AFTER_S),
            ("Guardian stale timeout",fusion_config.GUARDIAN_STALE_AFTER_S)):
        if not finite(value) or value<=0:errors.append(name+" must be positive and finite")
    if not isinstance(camera_config.CAMERA_INDEX,int) or camera_config.CAMERA_INDEX<0:
        errors.append("Camera index must be a nonnegative integer")
    return errors
