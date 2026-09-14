"""Responsive excavator canvas with a lightweight GUI animation timer."""

from PySide6.QtCore import QElapsedTimer, QRectF, QTimer
from PySide6.QtGui import QHideEvent, QPainter, QPaintEvent, QShowEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from visualization.excavator_2d import draw_excavator


class ExcavatorView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 160)
        self.setAccessibleName("Simulated excavator side view")
        self.elapsed_seconds = 0.0
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._advance)

    def _advance(self) -> None:
        self.elapsed_seconds += self._clock.restart() / 1000.0
        self.update()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._clock.start()
        self._timer.start()

    def hideEvent(self, event: QHideEvent) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        draw_excavator(painter, QRectF(self.rect()), self.elapsed_seconds)
        painter.end()
