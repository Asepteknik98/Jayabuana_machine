"""Read a common source at 5 Hz; display prepared sensor state."""

from PySide6.QtCore import QElapsedTimer, QTimer, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from adapters.sensor_source import SafeDigState, SensorHealth, SensorSource
from visualization.gpr_wave import GPRWave


class GPRPanel(QFrame):
    soil_selected = Signal(str)

    def __init__(self, source: SensorSource, soil_options: list[tuple[str, str]]) -> None:
        super().__init__()
        self.source = source
        self.setObjectName("panel")
        self.setMinimumHeight(210)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        for text, name in (("SafeDig Vision", "panelTitle"),
                           ("Underground Utility Intelligence", "muted"),
                           ("SIMULATED SUBSURFACE SENSOR", "muted")):
            label = QLabel(text)
            label.setObjectName(name)
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addWidget(QLabel("Soil Condition"))
        self.soil_combo = QComboBox()
        for label, value in soil_options:
            self.soil_combo.addItem(label, value)
        self.soil_combo.setCurrentIndex(self.soil_combo.findData("NORMAL_SOIL"))
        layout.addWidget(self.soil_combo)
        self.wave = GPRWave()
        grid = QGridLayout()
        self.values = {}
        for row, name in enumerate(("Signal Quality", "Confidence", "Anomaly Score", "Sensor Health")):
            label = QLabel(name)
            label.setObjectName("muted")
            value = QLabel()
            grid.addWidget(label, row, 0)
            grid.addWidget(value, row, 1)
            self.values[name] = value
        layout.addLayout(grid)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.action_label = QLabel()
        self.action_label.setObjectName("muted")
        self.action_label.setWordWrap(True)
        layout.addWidget(self.action_label)
        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self.refresh)
        self.soil_combo.currentIndexChanged.connect(self._select_soil)
        self.refresh()

    def _select_soil(self, index: int) -> None:
        self.soil_selected.emit(self.soil_combo.itemData(index))
        self.refresh()

    def refresh(self) -> None:
        now = self._clock.elapsed() / 1000.0
        self.state = SafeDigState.from_sensor(self.source.read(now), now)
        sensor = self.state.sensor
        available = sensor is not None and self.state.sensor_health not in (SensorHealth.OFFLINE, SensorHealth.STALE)
        for name, field in (("Signal Quality", "signal_quality"), ("Confidence", "confidence"),
                            ("Anomaly Score", "anomaly_score")):
            self.values[name].setText(f"{getattr(sensor, field):.0%}" if available else "—")
        self.values["Sensor Health"].setText(self.state.sensor_health.value)
        self.status_label.setText(self.state.status)
        self.action_label.setText(self.state.action_info)
        self.wave.samples = sensor.radargram if available else ()
        self.wave.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()
        self._timer.start()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)
