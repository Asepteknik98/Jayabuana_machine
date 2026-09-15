"""Lightweight risk display; thresholds are owned by the engine."""

from PySide6.QtWidgets import QProgressBar

from ui.status_style import COLORS

RISK_COLORS = {key: COLORS[key] for key in ("SAFE","CAUTION","HIGH","CRITICAL")}


class RiskGauge(QProgressBar):
    def __init__(self) -> None:
        super().__init__()
        self.setRange(0, 100)
        self.setTextVisible(False)
        self.setFixedHeight(16)

    def display(self, score, level) -> None:
        color = RISK_COLORS.get(level.value if level else "", "#8294a3")
        self.setValue(score if score is not None else 0)
        self.setStyleSheet(f"QProgressBar {{background:#172e40;border:1px solid #375365;}} "
                          f"QProgressBar::chunk {{background:{color};}}")
