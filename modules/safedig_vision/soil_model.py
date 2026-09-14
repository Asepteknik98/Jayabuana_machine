"""Prototype simulation parameters, not measured GPR performance."""

from dataclasses import dataclass
from enum import Enum


class SoilType(str, Enum):
    DRY_SOIL = "DRY_SOIL"
    NORMAL_SOIL = "NORMAL_SOIL"
    WET_SOIL = "WET_SOIL"
    CLAY_SOIL = "CLAY_SOIL"
    WET_CLAY = "WET_CLAY"


@dataclass(frozen=True)
class SoilModel:
    signal_quality: float
    base_confidence: float


SOIL_PRESETS = {
    SoilType.DRY_SOIL: SoilModel(0.90, 0.88),
    SoilType.NORMAL_SOIL: SoilModel(0.85, 0.82),
    SoilType.WET_SOIL: SoilModel(0.68, 0.72),
    SoilType.CLAY_SOIL: SoilModel(0.58, 0.64),
    SoilType.WET_CLAY: SoilModel(0.48, 0.58),
}
