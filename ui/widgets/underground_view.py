"""Add estimated utility drawing without modifying excavator animation."""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter

from adapters.sensor_source import SafeDigState
from ui.widgets.excavator_view import ExcavatorView
from visualization.underground_utility import draw_utility


class UndergroundView(ExcavatorView):
    def __init__(self) -> None:
        super().__init__()
        self.safe_dig_state: SafeDigState | None = None

    def set_state(self, state: SafeDigState) -> None:
        self.safe_dig_state = state
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.safe_dig_state is not None:
            painter = QPainter(self)
            draw_utility(painter, QRectF(self.rect()), self.safe_dig_state)
            painter.end()
