"""Responsive excavator canvas with a lightweight GUI animation timer."""

from time import monotonic

from PySide6.QtCore import QElapsedTimer, QRectF, QTimer, Signal
from PySide6.QtGui import QHideEvent, QPainter, QPaintEvent, QShowEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from visualization.excavator_2d import BUCKET_TIP, GROUND_Y, draw_excavator, excavator_pose
from modules.safedig_precision.bucket_position import bucket_position
from modules.safedig_precision.dig_geometry import calculate_geometry


class ExcavatorView(QWidget):
    geometry_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 160)
        self.setAccessibleName("Simulated excavator side view")
        self.scenario_position = None
        self.elapsed_seconds = 0.0
        self.bucket_position = self._position()
        self.geometry = calculate_geometry(self.bucket_position)
        self.timestamp = monotonic()
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._advance)

    def _advance(self) -> None:
        elapsed = self._clock.restart() / 1000.0
        self.elapsed_seconds += elapsed
        position = self._position()
        self.geometry = calculate_geometry(position, self.bucket_position, elapsed)
        self.bucket_position = position
        self.timestamp = monotonic()
        self.geometry_changed.emit(self.geometry)
        self.update()

    def _position(self):
        _, _, pivot, angle = excavator_pose(self.elapsed_seconds)
        return bucket_position(pivot.x(), pivot.y(), angle, *BUCKET_TIP, GROUND_Y)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._clock.start()
        if self.scenario_position is None:
            self._timer.start()

    def hideEvent(self, event: QHideEvent) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        draw_excavator(painter, QRectF(self.rect()), self.elapsed_seconds, self.scenario_position, getattr(self,"presentation",False))
        painter.end()
