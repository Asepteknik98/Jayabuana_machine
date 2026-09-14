"""Base industrial HMI with static module placeholders."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget,
)

from config.settings import APP_NAME, MINIMUM_SIZE, TAGLINE, WINDOW_SIZE
from ui.widgets.underground_view import UndergroundView
from modules.safedig_vision.utility_detector import UtilityDetector
from modules.safedig_vision.utility_model import MachineState
from core.safe_envelope import SafeEnvelopeEngine
from core.risk_engine import RiskEngine
from core.decision_engine import DecisionEngine
from ui.widgets.status_indicator import StatusIndicator
from ui.widgets.camera_panel import CameraPanel
from core.app_controller import GuardianController, AssessmentController
from ui.widgets.risk_panel import RiskPanel
from dataclasses import replace
from modules.safedig_precision.design_conflict import DesignConflictEngine, DEFAULT_TRENCH_CENTER_X_M
from ui.widgets.precision_panel import PrecisionPanel
from ui.widgets.gpr_panel import GPRPanel
from modules.safedig_vision.gpr_simulator import GPRSimulator
from modules.safedig_vision.soil_model import SoilType


def make_panel(title: str, subtitle: str, message: str) -> QFrame:
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(10)
    heading = QLabel(title)
    heading.setObjectName("panelTitle")
    heading.setWordWrap(True)
    layout.addWidget(heading)
    description = QLabel(subtitle)
    description.setObjectName("muted")
    description.setWordWrap(True)
    layout.addWidget(description)
    placeholder = QLabel(message)
    placeholder.setObjectName("placeholder")
    placeholder.setWordWrap(True)
    placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(placeholder, 1)
    return panel


class MainWindow(QMainWindow):
    def __init__(self, start_camera: bool = True) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*MINIMUM_SIZE)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        layout.addWidget(title)
        tagline = QLabel(TAGLINE)
        tagline.setObjectName("tagline")
        layout.addWidget(tagline)
        mode = QLabel("ENGINEERING PROTOTYPE / SIMULATION / DEMONSTRATION")
        mode.setObjectName("muted")
        layout.addWidget(mode)

        grid = QGridLayout()
        grid.setSpacing(14)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 6)
        grid.setColumnStretch(2, 3)
        for row in range(3):
            grid.setRowStretch(row, 1)
        self.gpr_source = GPRSimulator()
        self.gpr_panel = GPRPanel(self.gpr_source, [
            (soil.value.replace("_", " ").title(), soil.value) for soil in SoilType
        ])
        self.gpr_panel.soil_selected.connect(self.gpr_source.set_soil)
        grid.addWidget(self.gpr_panel, 0, 0)
        grid.setRowStretch(0, 3)
        self.precision_panel = PrecisionPanel()
        grid.addWidget(self.precision_panel, 1, 0)
        grid.setRowStretch(1, 2)
        self.camera_panel = CameraPanel()
        grid.addWidget(self.camera_panel, 2, 0)
        excavation_panel = make_panel(
            "Excavation View", "2D workspace • SIMULATED MOTION", "",
        )
        excavation_layout = excavation_panel.layout()
        placeholder = excavation_layout.takeAt(2).widget()
        placeholder.deleteLater()
        self.excavator_view = UndergroundView()
        self.utility_detector = UtilityDetector()
        self.envelope_engine = SafeEnvelopeEngine()
        self.design_conflict_engine = DesignConflictEngine()
        self.risk_engine = RiskEngine()
        self.gpr_panel.state_changed.connect(self._update_utility)
        self.excavator_view.geometry_changed.connect(self._update_utility)
        self._update_utility()
        self.excavator_view.geometry_changed.connect(self.precision_panel.update_geometry)
        self.precision_panel.update_geometry(self.excavator_view.geometry)
        excavation_layout.addWidget(self.excavator_view, 1)
        grid.addWidget(excavation_panel, 0, 1, 3, 1)

        self.risk_panel = RiskPanel()
        self.risk_score_label = self.risk_panel.score_label
        self.risk_status_label = self.risk_panel.level_label
        sensor_previews = QTabWidget()
        sensor_previews.addTab(self.gpr_panel.wave, "GPR Scan")
        sensor_previews.addTab(self.camera_panel.preview, "Operator Camera")
        sensor_previews.setCurrentIndex(1)
        grid.addWidget(sensor_previews, 0, 2)
        grid.addWidget(self.risk_panel, 1, 2, 2, 1)
        layout.addLayout(grid, 1)

        self.decision_engine = DecisionEngine()
        self.decision_panel = StatusIndicator()
        self.assessment_controller = AssessmentController(self.risk_engine, self.decision_engine)
        self.gpr_panel.state_changed.connect(self._update_assessment)
        self.excavator_view.geometry_changed.connect(self._assessment_tick)
        self._last_assessment = 0.0
        self._update_assessment()
        layout.addWidget(self.decision_panel)

        self.setStyleSheet("""
            QMainWindow, QWidget { background: #091421; color: #dfebf5;
                font-family: 'Segoe UI'; font-size: 14px; }
            QFrame#panel { background: #10263b; border: 1px solid #24506b;
                border-radius: 8px; }
            QLabel { background: transparent; border: none; }
            QLabel#appTitle { font-size: 30px; font-weight: 700; }
            QLabel#tagline { color: #45d5e7; font-size: 14px;
                font-weight: 600; }
            QLabel#panelTitle { color: #65deef; font-size: 19px;
                font-weight: 600; }
            QLabel#muted { color: #94aec3; font-size: 12px; }
            QLabel#placeholder { color: #809bb1; font-size: 13px; }
            QLabel#riskScore { font-size: 40px; font-weight: 700; }
            QLabel#safeStatus { color: #4cde9a; background: #123c35;
                border: 1px solid #287659; border-radius: 6px;
                padding: 12px; font-size: 22px; font-weight: 700; }
        """)
        self.guardian_controller = GuardianController(self)
        QApplication.instance().aboutToQuit.connect(self.guardian_controller.stop)
        self.guardian_controller.observation_ready.connect(self._update_operator)
        self.camera_panel.retry_requested.connect(self.guardian_controller.start)
        if start_camera:
            self.guardian_controller.start()

    def _update_utility(self, _event=None) -> None:
        bucket = self.excavator_view.bucket_position
        geometry = self.excavator_view.geometry
        machine = MachineState(bucket.x_m, -bucket.depth_m, geometry.target_depth_m,
                               geometry.target_width_m, geometry.target_slope_percent,
                               geometry.current_depth_m, DEFAULT_TRENCH_CENTER_X_M,
                               geometry.bucket_speed_m_s, self.excavator_view.timestamp)
        previous_fusion = self.safe_dig_state.fusion if hasattr(self, "safe_dig_state") else None
        previous_risk = self.safe_dig_state.risk if hasattr(self, "safe_dig_state") else None
        previous_decision = self.safe_dig_state.decision if hasattr(self, "safe_dig_state") else None
        previous_operator = self.safe_dig_state.operator if hasattr(self, "safe_dig_state") else None
        self.safe_dig_state = self.utility_detector.update(self.gpr_panel.state, machine)
        self.safe_dig_state = replace(self.safe_dig_state, risk=previous_risk, decision=previous_decision, operator=previous_operator, fusion=previous_fusion)
        self.safe_dig_state = self.envelope_engine.update(self.safe_dig_state)
        self.safe_dig_state = self.design_conflict_engine.update(self.safe_dig_state)
        self.precision_panel.update_conflict(self.safe_dig_state.design_conflict)
        self.gpr_panel.display_utility(self.safe_dig_state)
        self.excavator_view.set_state(self.safe_dig_state)

    def _assessment_tick(self, _event=None) -> None:
        from time import monotonic
        if monotonic() - self._last_assessment >= 0.2:
            self._update_assessment()

    def _update_assessment(self, _event=None) -> None:
        from time import monotonic
        self._last_assessment = monotonic()
        self.safe_dig_state = self.assessment_controller.update(self.safe_dig_state, self._last_assessment)
        self.risk_panel.display(self.safe_dig_state.risk, self.safe_dig_state.fusion)
        self.decision_panel.display(self.safe_dig_state.decision)
        self.camera_panel.guardian_panel.display_fusion(self.safe_dig_state.fusion)
        self.excavator_view.set_state(self.safe_dig_state)

    def _update_operator(self, state, frame) -> None:
        self.safe_dig_state = replace(self.safe_dig_state, operator=state)
        self.camera_panel.display(self.safe_dig_state.operator, frame)

    def closeEvent(self, event) -> None:
        self.guardian_controller.stop()
        super().closeEvent(event)
