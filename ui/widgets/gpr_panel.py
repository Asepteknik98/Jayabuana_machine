"""Read a common source at 5 Hz; display prepared sensor state."""

from time import monotonic
import logging
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from adapters.sensor_source import SafeDigState, SensorHealth, SensorSource
from visualization.gpr_wave import GPRWave


class GPRPanel(QFrame):
    soil_selected = Signal(str)
    state_changed = Signal(object)

    def __init__(self, source: SensorSource, soil_options: list[tuple[str, str]]) -> None:
        super().__init__()
        self.external_input = False
        self._source_error = ""
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
        for row, name in enumerate(("Signal Quality", "Confidence", "Anomaly Score", "Sensor Health",
                                    "Utility Status", "Estimated Type", "Estimated Depth",
                                    "Distance From Bucket", "Detection Confidence", "Confidence Status")):
            label = QLabel(name)
            label.setObjectName("muted")
            value = QLabel()
            value.setWordWrap(True)
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
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self.refresh)
        self.soil_combo.currentIndexChanged.connect(self._select_soil)
        self.refresh()

    def _select_soil(self, index: int) -> None:
        self.soil_selected.emit(self.soil_combo.itemData(index))
        self.refresh()

    def refresh(self) -> None:
        if self.external_input:
            return
        now = monotonic()
        try:
            sensor = self.source.read(now)
            self._source_error = ""
        except (OSError, ValueError, RuntimeError, ArithmeticError) as error:
            if str(error) != self._source_error:
                logging.getLogger("safedig").error("SUBSURFACE SOURCE UNAVAILABLE: %s",error)
            self._source_error = str(error)
            sensor = None
        self.state = SafeDigState.from_sensor(sensor, now)
        self.display_sensor(self.state)
        self.state_changed.emit(self.state)

    def display_sensor(self, state) -> None:
        self.state = state
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

    def display_utility(self, state: SafeDigState) -> None:
        utility = state.utility
        if utility is None:
            return
        self.values["Utility Status"].setText(utility.status)
        self.values["Estimated Type"].setText(utility.type_label)
        for name, value in (("Estimated Depth", utility.estimated_depth_m),
                            ("Distance From Bucket", utility.distance_to_bucket_m)):
            self.values[name].setText(f"{value:.2f} m" if value is not None else "--")
        self.values["Detection Confidence"].setText(f"{utility.confidence:.0%}" if utility.confidence is not None else "--")
        self.values["Confidence Status"].setText(utility.confidence_status)
        self.action_label.setText(utility.verification_info)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()
        if not self.external_input:
            self._timer.start()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)
