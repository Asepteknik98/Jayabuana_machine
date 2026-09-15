"""Compact scenario controls and event status; no assessment logic."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel, QProgressBar, QListWidget, QListView
from PySide6.QtGui import QColor
from simulation.scenario_manager import SCENARIO_DIRECTORY

class ScenarioTimeline(QWidget):
    selected = Signal(str)
    start_requested = Signal()
    pause_requested = Signal()
    reset_requested = Signal()
    mode_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self._event_signature = None
        layout = QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(3)
        row = QHBoxLayout();layout.addLayout(row)
        self.scenarios = QComboBox()
        for key, name in (("normal_operation","Normal Operation"),("utility_detected","Utility Detected"),
                ("wet_clay","Wet Clay"),("design_conflict","Design Conflict"),("operator_drowsy","Operator Drowsy"),
                ("critical_scenario","Critical Multimodal Demo")):
            self.scenarios.addItem(name, str(SCENARIO_DIRECTORY / (key+".json")))
        import json
        for path in sorted(SCENARIO_DIRECTORY.glob("fault_*.json")):
            try:
                name=json.loads(path.read_text(encoding="utf8"))["name"]
            except (OSError,ValueError,KeyError):
                name="UNAVAILABLE: "+path.stem
            self.scenarios.addItem(name,str(path))
        self.scenarios.setCurrentIndex(5);row.addWidget(self.scenarios)
        self.mode = QComboBox();self.mode.addItems(["DEMO MODE", "LIVE MODE"]);row.addWidget(self.mode)
        self.start = QPushButton("START");self.pause = QPushButton("PAUSE");self.reset = QPushButton("RESET")
        for button in (self.start,self.pause,self.reset):row.addWidget(button)
        self.time_label = QLabel();row.addWidget(self.time_label,1)
        self.source_label = QLabel();layout.addWidget(self.source_label)
        self.progress = QProgressBar();self.progress.setFixedHeight(10);self.progress.setTextVisible(False);layout.addWidget(self.progress)
        self.events = QListWidget();self.events.setFlow(QListView.Flow.LeftToRight);self.events.setWrapping(False)
        self.events.setFixedHeight(65);layout.addWidget(self.events)
        self.scenarios.currentIndexChanged.connect(lambda _: self.selected.emit(self.scenarios.currentData()))
        self.start.clicked.connect(self.start_requested);self.pause.clicked.connect(self.pause_requested)
        self.reset.clicked.connect(self.reset_requested)
        self.mode.currentIndexChanged.connect(lambda index: self.mode_changed.emit(index == 0))

    def display(self, manager):
        state = manager.state
        self.time_label.setText(f"{state.status} | {state.elapsed_time_s:.1f} / {state.duration_s:.1f} s")
        self.time_label.setToolTip(manager.error)
        self.progress.setValue(round(state.progress*100))
        self.pause.setText("RESUME" if state.status == "PAUSED" else "PAUSE")
        self.start.setEnabled(manager.definition is not None)
        self.pause.setEnabled(state.status in ("RUNNING", "PAUSED"))
        self.reset.setEnabled(manager.definition is not None)
        signature=(state.scenario_id,state.status,state.current_event_index,
            tuple((event["time_s"],event["type"]) for event in manager.definition["events"]) if manager.definition else None)
        if signature == self._event_signature:return
        self._event_signature=signature
        self.events.clear()
        if not manager.definition:
            self.events.addItem("SCENARIO LOAD ERROR / UNAVAILABLE")
            return
        for index,event in enumerate(manager.definition["events"]):
            status = "COMPLETED" if index < state.current_event_index or state.status == "COMPLETED" else "ACTIVE" if index == state.current_event_index else "PENDING"
            self.events.addItem(f"{event['time_s']:02g}s {event['type']}\n{status}")
            item = self.events.item(index)
            item.setForeground(QColor("#45d5e7" if status == "ACTIVE" else "#4cde9a" if status == "COMPLETED" else "#94aec3"))
            if status == "ACTIVE":
                item.setBackground(QColor("#24506b"));self.events.setCurrentItem(item)
        if state.current_event_index >= 0:self.events.scrollToItem(self.events.item(state.current_event_index))
