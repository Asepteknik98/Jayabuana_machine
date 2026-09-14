"""Live precision readings from the simulated excavator."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout

from modules.safedig_precision.dig_geometry import DigGeometry


class PrecisionPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        self.setMinimumHeight(190)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        title = QLabel("SafeDig Precision")
        title.setObjectName("panelTitle")
        title.setWordWrap(True)
        layout.addWidget(title)
        subtitle = QLabel("SIMULATED • Bucket tip")
        self.setToolTip("AI Digging Depth & Geometry Assistant")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        readings = QGridLayout()
        readings.setVerticalSpacing(1)
        self.values: dict[str, QLabel] = {}
        for row, name in enumerate((
            "Target Depth", "Current Depth", "Remaining", "Target Width",
            "Target Slope", "Bucket Speed",
        )):
            caption = QLabel(name)
            caption.setObjectName("muted")
            value = QLabel("—")
            value.setStyleSheet("font-size: 12px;")
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            readings.addWidget(caption, row, 0)
            readings.addWidget(value, row, 1)
            self.values[name] = value
        layout.addLayout(readings)
        layout.addStretch()

    def update_geometry(self, geometry: DigGeometry) -> None:
        readings = {
            "Target Depth": f"{geometry.target_depth_m:.2f} m",
            "Current Depth": f"{geometry.current_depth_m:.2f} m",
            "Remaining": f"{geometry.remaining_depth_m:.2f} m",
            "Target Width": f"{geometry.target_width_m:.2f} m",
            "Target Slope": f"{geometry.target_slope_percent:g}%",
            "Bucket Speed": f"{geometry.bucket_speed_m_s:.2f} m/s",
        }
        for name, text in readings.items():
            self.values[name].setText(text)
