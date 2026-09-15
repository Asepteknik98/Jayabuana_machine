"""Aspect-correct live preview and read-only Guardian foundation status."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget
from adapters.sensor_source import SensorHealth
from domain.operator_state import OperatorState
from ui.widgets.guardian_panel import GuardianPanel


class CameraPreview(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(140)
        self.image = QImage()
        self.status_text = "CAMERA OFFLINE"
        self.detail_text = "Operator analysis: UNAVAILABLE"
        self.analysis_text = "Fatigue: UNKNOWN | Attention: UNKNOWN"

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if not self.image.isNull():
            size = self.image.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
            x, y = (self.width()-size.width())//2, (self.height()-size.height())//2
            from PySide6.QtCore import QRect
            painter.drawImage(QRect(x,y,size.width(),size.height()),self.image)
        painter.setPen(Qt.GlobalColor.white)
        font = painter.font()
        font.setPixelSize(12)
        painter.setFont(font)
        painter.fillRect(0, self.height()-62, self.width(), 62, Qt.GlobalColor.black)
        painter.drawText(8, self.height()-46, self.status_text)
        painter.drawText(8, self.height()-29, self.detail_text)
        painter.drawText(8, self.height()-12, self.analysis_text)
        painter.end()


class CameraPanel(QFrame):
    retry_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        outer=QVBoxLayout(self);outer.setContentsMargins(8,8,8,8)
        scroll=QScrollArea();scroll.setWidgetResizable(True);outer.addWidget(scroll)
        content=QWidget();scroll.setWidget(content);layout=QVBoxLayout(content);layout.setSpacing(4)
        title=QLabel("SafeDig Guardian");title.setObjectName("panelTitle");title.setWordWrap(True);layout.addWidget(title)
        self.subtitle=subtitle=QLabel("Operator Fatigue & Attention Intelligence\nREAL CAMERA INPUT")
        subtitle.setObjectName("muted");subtitle.setWordWrap(True);layout.addWidget(subtitle)
        self.preview=CameraPreview()
        self.status_label=QLabel();self.status_label.setWordWrap(True);layout.addWidget(self.status_label)
        self.face_label=QLabel();self.face_label.setWordWrap(True);layout.addWidget(self.face_label)
        self.analysis_label=QLabel();self.analysis_label.setWordWrap(True);layout.addWidget(self.analysis_label)
        self.guardian_panel=GuardianPanel();layout.addWidget(self.guardian_panel)
        self.retry_button=QPushButton("RETRY CAMERA");self.retry_button.clicked.connect(self.retry_requested)
        outer.addWidget(self.retry_button)
        self.display(OperatorState(),None)

    def display(self,state: OperatorState,rgb_frame,source="LIVE") -> None:
        simulated = source == "SIMULATED"
        self.subtitle.setText("GUARDIAN SOURCE: " + ("SIMULATED DEMO" if simulated else "LIVE CAMERA"))
        self.retry_button.setEnabled(not simulated)
        online=state.camera_available and state.camera_health==SensorHealth.VALID
        self.status_label.setText("CAMERA ONLINE" if online else f"CAMERA {state.camera_health.value}")
        self.status_label.setStyleSheet("color:#4cde9a;" if online else "color:#a1adba;")
        self.status_label.setToolTip(state.diagnostic)
        count=str(state.face_count) if state.last_detection_timestamp is not None and online else "UNKNOWN"
        self.face_label.setText(f"Face: {state.face_status}\nFace Count: {count}\nLandmarks: "+
                                ("AVAILABLE" if state.landmarks_available else "UNAVAILABLE"))
        self.analysis_label.setText("Operator Analysis: "+state.analysis_status)
        if simulated:
            self.status_label.setText("SIMULATED GUARDIAN INPUT")
            self.face_label.setText("Synthetic operator state / no camera image")
        self.preview.status_text = "SIMULATED GUARDIAN INPUT" if simulated else self.status_label.text() + " / LIVE CAMERA"
        self.preview.detail_text = "GUARDIAN SOURCE: SIMULATED DEMO" if simulated else f"Face: {state.face_status} | Count: {count}"
        self.guardian_panel.display(state)
        fatigue=f'{state.fatigue_score:.0f} / 100 {state.fatigue_level}' if state.fatigue_valid else 'UNKNOWN'
        attention=f'{state.attention_score:.0%}' if state.attention_score is not None else 'UNKNOWN'
        self.preview.analysis_text=f'Fatigue: {fatigue} | Attention: {attention}'
        if online and rgb_frame is not None and not simulated:
            height,width,_=rgb_frame.shape
            self.preview.image=QImage(rgb_frame.data,width,height,rgb_frame.strides[0],QImage.Format.Format_RGB888).copy()
        else:
            self.preview.image=QImage()
        self.preview.update()
