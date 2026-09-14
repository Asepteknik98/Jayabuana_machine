"""Render source-provided radargram intensities without detection logic."""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


class GPRWave(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(110)
        self.samples: tuple[tuple[float, ...], ...] = ()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#081725"))
        left, top = 40, 30
        width, height = max(1, self.width() - left - 4), max(1, self.height() - top - 10)
        if self.samples:
            for row, values in enumerate(self.samples):
                for column, value in enumerate(values):
                    color = QColor(int(30 + 140 * value), int(45 + 205 * value), int(70 + 185 * value))
                    painter.fillRect(QRectF(left + column * width / len(values),
                                           top + row * height / len(self.samples),
                                           width / len(values) + 0.5, height / len(self.samples) + 0.5), color)
        painter.setPen(QColor("#9bcada"))
        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)
        painter.drawText(4, 12, "SIMULATED GPR SCAN")
        for index in range(5):
            painter.drawText(2, int(top + index * height / 4), f"{index * 0.5:.1f} m")
        painter.end()
