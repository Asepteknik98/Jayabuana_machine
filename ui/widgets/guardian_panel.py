"""Read-only prototype Guardian indicators; fusion connection status."""

from PySide6.QtWidgets import QWidget,QVBoxLayout,QGridLayout,QLabel,QProgressBar

from ui.status_style import COLORS

LEVEL_COLORS = {"NORMAL":COLORS["NORMAL"],"ELEVATED":COLORS["CAUTION"],"HIGH":COLORS["HIGH"],"UNKNOWN":COLORS["UNKNOWN"]}


class GuardianPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(4)
        note=QLabel("PROTOTYPE ESTIMATE • CALIBRATION REQUIRED")
        note.setObjectName('muted');note.setWordWrap(True);layout.addWidget(note)
        self.fusion_label=QLabel("FUSION: WAITING");self.fusion_label.setWordWrap(True);layout.addWidget(self.fusion_label)
        grid=QGridLayout();self.values={}
        for row,name in enumerate(('Eyes','Closure','Prolonged','Blinks (window)','Yawn','Yawn Count','Head Pose','Attention','Fatigue')):
            caption=QLabel(name);caption.setObjectName('muted');grid.addWidget(caption,row,0)
            value=QLabel();value.setWordWrap(True);grid.addWidget(value,row,1);self.values[name]=value
        layout.addLayout(grid)
        self.attention_bar=QProgressBar();self.attention_bar.setRange(0,100);self.attention_bar.setFixedHeight(16)
        layout.addWidget(self.attention_bar)
        self.fatigue_bar=QProgressBar();self.fatigue_bar.setRange(0,100);self.fatigue_bar.setFixedHeight(16)
        layout.addWidget(self.fatigue_bar)
        self.indicator=QLabel();self.indicator.setWordWrap(True);self.indicator.setObjectName('muted');layout.addWidget(self.indicator)

    def display(self,state):
        self.values['Eyes'].setText('UNKNOWN' if state.eyes_closed is None else 'CLOSED' if state.eyes_closed else 'OPEN')
        self.values['Closure'].setText('--' if state.eye_closure_duration_ms is None else f'{state.eye_closure_duration_ms:.0f} ms')
        self.values['Prolonged'].setText('UNKNOWN' if state.eyes_closed is None else 'YES' if state.prolonged_eye_closure else 'NO')
        self.values['Blinks (window)'].setText('--' if state.blink_count is None else str(state.blink_count))
        self.values['Yawn'].setText('UNKNOWN' if state.yawn_detected is None else 'YES' if state.yawn_detected else 'NO')
        self.values['Yawn Count'].setText('--' if state.yawn_count is None else str(state.yawn_count))
        self.values['Head Pose'].setText(state.head_pose_status)
        self.values['Head Pose'].setToolTip('Approximate yaw / pitch / roll: '+str((state.head_yaw_deg,state.head_pitch_deg,state.head_roll_deg)))
        self.values['Attention'].setText('UNKNOWN' if state.attention_score is None else f'{state.attention_score:.0%} {state.attention_status}')
        self.values['Fatigue'].setText('UNKNOWN' if not state.fatigue_valid else f'{state.fatigue_score:.0f} / 100 • {state.fatigue_level}')
        color=LEVEL_COLORS[state.fatigue_level]
        self.values['Fatigue'].setStyleSheet(f'color:{color};')
        self.fatigue_bar.setStyleSheet(f'QProgressBar::chunk {{background:{color};}}')
        for bar,value,label in ((self.attention_bar,None if state.attention_score is None else state.attention_score*100,'Attention'),
                                (self.fatigue_bar,state.fatigue_score,'Fatigue')):
            bar.setValue(0 if value is None else round(value))
            bar.setFormat(label+': UNKNOWN' if value is None else 'Fatigue: %v / 100' if label=='Fatigue' else 'Attention: %v%')
        confidence='--' if state.fatigue_confidence is None else f'{state.fatigue_confidence:.0%}'
        self.indicator.setText(f'Primary: {state.primary_fatigue_indicator}\nEstimate confidence: {confidence}')

    def display_fusion(self, fusion):
        self.fusion_label.setText("FUSION: CONNECTED" if fusion.guardian_valid else "FUSION: GUARDIAN DATA UNAVAILABLE")
