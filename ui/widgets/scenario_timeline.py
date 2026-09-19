"""Compact scenario controls and event status; no assessment logic."""
from PySide6.QtCore import Signal, Qt, QRectF, QPointF
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel, QProgressBar, QButtonGroup,QFrame,QStyle
from PySide6.QtGui import QColor, QPainter, QPen
from ui.theme import CARD_PADDING, CARD_GAP, CARD_HEADER_GAP
from simulation.scenario_manager import SCENARIO_DIRECTORY

class TimelineCanvas(QWidget):
    """Event positions are presentation only, read from the scenario manager."""
    def __init__(self):
        super().__init__();self.setMinimumHeight(60);self.events=[];self.active=-1;self.complete=False
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        font=p.font();font.setPixelSize(13);p.setFont(font)
        count=len(self.events)
        if not count:
            p.drawText(self.rect(),Qt.AlignmentFlag.AlignCenter,"SCENARIO UNAVAILABLE");return
        step=self.width()/count
        p.setPen(QPen(QColor("#294257"),2));p.drawLine(QPointF(step/2,12),QPointF(self.width()-step/2,12))
        for i,item in enumerate(self.events):
            done=i<self.active or self.complete
            color=QColor("#65daba" if done else "#45d5e7" if i==self.active else "#758a9e")
            x=(i+.5)*step;p.setBrush(QColor("#102033"));p.setPen(QPen(color,2));p.drawEllipse(QPointF(x,12),8,8)
            if done:
                p.drawLine(QPointF(x-4,12),QPointF(x-1,15));p.drawLine(QPointF(x-1,15),QPointF(x+4,8))
            elif i==self.active:p.setBrush(color);p.drawEllipse(QPointF(x,12),3,3)
            p.setPen(color)
            text=f"{item['time_s']:g}s  "+item['type'].replace('_',' ').title()
            p.drawText(QRectF(i*step+5,27,step-10,self.height()-27),Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop|Qt.TextFlag.TextWordWrap,text)
        p.end()

class ScenarioTimeline(QFrame):
    selected = Signal(str)
    start_requested = Signal()
    pause_requested = Signal()
    reset_requested = Signal()
    mode_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setObjectName("panel")
        self._event_signature = None
        layout = QVBoxLayout(self);layout.setContentsMargins(*CARD_PADDING);layout.setSpacing(CARD_GAP)
        self.controls=QWidget();self.controls.setObjectName("headerControls")
        row=QHBoxLayout(self.controls);row.setContentsMargins(0,0,0,0);row.setSpacing(16)
        mode_column=QVBoxLayout();mode_column.setSpacing(4)
        mode_caption=QLabel("INPUT MODE");mode_caption.setObjectName("headerCaption");mode_column.addWidget(mode_caption)
        mode_segment=QFrame();mode_segment.setObjectName("headerModeSegment");mode_segment.setFixedHeight(38)
        mode_row=QHBoxLayout(mode_segment);mode_row.setContentsMargins(2,2,2,2);mode_row.setSpacing(2)
        mode_column.addWidget(mode_segment);row.addLayout(mode_column)
        scenario_column=QVBoxLayout();scenario_column.setSpacing(4)
        scenario_caption=QLabel("SCENARIO");scenario_caption.setObjectName("headerCaption");scenario_column.addWidget(scenario_caption)
        row.addLayout(scenario_column)
        action_column=QVBoxLayout();action_column.setSpacing(4)
        action_caption=QLabel("RUN CONTROLS");action_caption.setObjectName("headerCaption");action_column.addWidget(action_caption)
        action_row=QHBoxLayout();action_row.setSpacing(8);action_column.addLayout(action_row);row.addLayout(action_column)
        self.scenarios = QComboBox()
        self.scenarios.setObjectName("headerScenario")
        self.scenarios.setMinimumWidth(220)
        self.scenarios.setFixedHeight(38)
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
        self.scenarios.setCurrentIndex(5);scenario_column.addWidget(self.scenarios)
        self.mode = QComboBox(self);self.mode.addItems(["DEMO MODE", "LIVE MODE"]);self.mode.hide()
        self.mode_group=QButtonGroup(self)
        for index,name in enumerate(("DEMO MODE","LIVE MODE")):
            button=QPushButton(name);button.setCheckable(True);button.setChecked(index==0)
            button.setFixedSize(104,32)
            self.mode_group.addButton(button,index);mode_row.addWidget(button)
        self.mode_group.idClicked.connect(self.mode.setCurrentIndex)
        self.mode.currentIndexChanged.connect(lambda index:self.mode_group.button(index).setChecked(True))
        self.start = QPushButton("START");self.pause = QPushButton("PAUSE");self.reset = QPushButton("RESET")
        for button,icon in ((self.start,QStyle.StandardPixmap.SP_MediaPlay),(self.pause,QStyle.StandardPixmap.SP_MediaPause),(self.reset,QStyle.StandardPixmap.SP_BrowserReload)):
            button.setIcon(self.style().standardIcon(icon));button.setFixedSize(100,38);action_row.addWidget(button)
        self.start.setObjectName("startButton")
        info=QHBoxLayout();info.setSpacing(CARD_HEADER_GAP);layout.addLayout(info)
        caption=QLabel("Scenario Timeline");caption.setObjectName("panelTitle");info.addWidget(caption)
        self.time_label=QLabel();info.addWidget(self.time_label,1)
        self.next_label=QLabel();self.next_label.setObjectName("muted");info.addWidget(self.next_label)
        self.source_label = QLabel();self.source_label.setObjectName("muted");layout.addWidget(self.source_label)
        self.progress = QProgressBar();self.progress.setFixedHeight(10);self.progress.setTextVisible(False);layout.addWidget(self.progress)
        self.events=TimelineCanvas();layout.addWidget(self.events)
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
        events=manager.definition["events"] if manager.definition else []
        self.events.events=events;self.events.active=state.current_event_index
        self.events.complete=state.status=="COMPLETED";self.events.update()
        next_index=state.current_event_index+1
        upcoming=events[next_index] if next_index<len(events) and state.status!="COMPLETED" else None
        self.next_label.setText("NEXT: "+upcoming["type"].replace("_"," ").title()+f" ({upcoming['time_s']:g}s)" if upcoming else "END OF TIMELINE")
