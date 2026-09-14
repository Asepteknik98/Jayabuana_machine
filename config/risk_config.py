"""Prototype engineering parameters, not XCMG production safety settings."""

WEIGHTS = {"utility": 0.35, "confidence": 0.15, "fatigue": 0.15,
           "velocity": 0.10, "design": 0.25}
LEVEL_UP_THRESHOLDS = (30, 60, 80)
LEVEL_DOWN_THRESHOLDS = (25, 55, 75)
VERIFY_THRESHOLD = 0.65
UNCERTAINTY_RISK_FLOOR = 0.40
FAR_DISTANCE_RATIO = 3.0
HIGH_DISTANCE_RATIO = 1.0
VELOCITY_REFERENCE_MPS = 0.30  # SIMULATION REFERENCE ONLY, not an operating limit.
DESIGN_RISKS = {"NO_CONFLICT": 0.0, "POTENTIAL_CONFLICT": 0.55,
                "DESIGN_CONFLICT": 1.0, "UNKNOWN": 0.40}
DRIVER_LABELS = {"utility": "UTILITY PROXIMITY", "confidence": "CONFIDENCE / EVIDENCE",
                 "velocity": "BUCKET VELOCITY", "design": "DESIGN CONFLICT", "fatigue": "OPERATOR FATIGUE"}
