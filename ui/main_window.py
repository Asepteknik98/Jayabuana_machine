"""MVP-0 engineering and presentation views over the same SafeDig state."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QLabel, QMainWindow, QScrollArea, QStackedWidget, QComboBox, QHBoxLayout, QTabWidget, QVBoxLayout, QWidget,
)

from config.settings import APP_NAME, MINIMUM_SIZE, TAGLINE, WINDOW_SIZE
from config.simulation_config import SIMULATION_DT
from ui.theme import STYLE, CARD_PADDING, CARD_HEADER_GAP
from ui.widgets.hmi_icon import HmiIcon
from ui.widgets.underground_view import UndergroundView
from modules.safedig_vision.utility_detector import UtilityDetector
from modules.safedig_vision.utility_model import MachineState
from core.safe_envelope import SafeEnvelopeEngine
from core.risk_engine import RiskEngine
from core.decision_engine import DecisionEngine
from ui.widgets.status_indicator import StatusIndicator
from ui.widgets.camera_panel import CameraPanel
from core.app_controller import GuardianController, AssessmentController, ScenarioController
from simulation.scenario_manager import ScenarioManager
from ui.widgets.scenario_timeline import ScenarioTimeline
from ui.widgets.experiment_panel import ExperimentPanel
from ui.widgets.risk_panel import RiskPanel
from ui.widgets.presentation_panel import PresentationPanel, SystemHealth
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
    layout.setContentsMargins(*CARD_PADDING)
    layout.setSpacing(CARD_HEADER_GAP)
    heading = QLabel(title)
    heading.setObjectName("panelTitle")
    heading.setWordWrap(True)
    heading_row=QHBoxLayout();heading_row.setSpacing(CARD_HEADER_GAP);heading_row.addWidget(HmiIcon("excavator",28));heading_row.addWidget(heading,1);layout.addLayout(heading_row)
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
        self.scenario_active = False
        self._camera_enabled = start_camera
        self._closed = False
        self.presentation_stacks = []
        self.presentation_cards = []
        self.live_operator = None
        self.live_frame = None
        self.setWindowTitle("SafeDig AI Copilot")
        QApplication.instance().setApplicationDisplayName("SafeDig AI Copilot")
        self.resize(*WINDOW_SIZE)
        self.setMinimumSize(*MINIMUM_SIZE)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(12)

        header_frame = QFrame()
        header_frame.setObjectName("dashboardHeader")
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(24)
        brand = QVBoxLayout()
        brand.setSpacing(4)
        brand.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title = QLabel("SafeDig AI Copilot"); title.setObjectName("appTitle")
        tagline = QLabel(TAGLINE); tagline.setObjectName("tagline")
        brand.addWidget(title); brand.addWidget(tagline)
        header.addLayout(brand, 1)
        self.scenario_panel = ScenarioTimeline()
        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.addWidget(self.scenario_panel.controls)
        options = QVBoxLayout()
        options.setSpacing(4)
        online = QLabel("SYSTEM ONLINE  /  MVP-0 SOFTWARE")
        online.setObjectName("headerSystemStatus")
        online.setAlignment(Qt.AlignmentFlag.AlignRight)
        options.addWidget(online)
        self.view_mode = QComboBox()
        self.view_mode.setObjectName("headerViewMode")
        self.view_mode.setFixedHeight(38)
        self.view_mode.addItems(["PRESENTATION MODE", "ENGINEERING MODE"])
        options.addWidget(self.view_mode)
        controls.addLayout(options)
        header.addLayout(controls)
        layout.addWidget(header_frame)
        self.scenario_manager = ScenarioManager()
        self.scenario_manager.load(self.scenario_panel.scenarios.currentData())
        self.scenario_controller = ScenarioController(self.scenario_manager)
        self.scenario_panel.display(self.scenario_manager)
        self.scenario_panel.source_label.setText("GUARDIAN SOURCE: LIVE CAMERA | Select START for scenario inputs")
        self.scenario_timer = QTimer(self)
        self.scenario_timer.setInterval(round(SIMULATION_DT*1000))
        self.scenario_timer.timeout.connect(self._scenario_step)
        self.scenario_panel.selected.connect(self._scenario_load)
        self.scenario_panel.start_requested.connect(self._scenario_start)
        self.scenario_panel.pause_requested.connect(self._scenario_pause)
        self.scenario_panel.reset_requested.connect(self._scenario_reset)
        self.scenario_panel.mode_changed.connect(self._scenario_mode)

        self.system_health = SystemHealth()
        layout.addWidget(self.system_health)

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setColumnStretch(0, 24)
        grid.setColumnStretch(1, 52)
        grid.setColumnStretch(2, 24)
        for row in range(3):
            grid.setRowStretch(row, 1)
        self.gpr_source = GPRSimulator()
        self.gpr_panel = GPRPanel(self.gpr_source, [
            (soil.value.replace("_", " ").title(), soil.value) for soil in SoilType
        ])
        self.gpr_panel.soil_selected.connect(self.gpr_source.set_soil)
        self.gpr_panel.setMinimumHeight(120)
        left = QVBoxLayout(); left.setSpacing(16)
        left.addWidget(self._presentation_stack(self.gpr_panel,"SafeDig Vision"), 3)
        grid.setRowStretch(0, 3)
        self.precision_panel = PrecisionPanel()
        precision_scroll = QScrollArea()
        precision_scroll.setWidgetResizable(True)
        precision_scroll.setWidget(self.precision_panel)
        left.addWidget(self._presentation_stack(precision_scroll,"SafeDig Precision"), 2)
        grid.addLayout(left, 0, 0, 3, 1)
        grid.setRowStretch(1, 3)
        self.camera_panel = CameraPanel()
        guardian_stack = self._presentation_stack(self.camera_panel,"SafeDig Guardian")
        self.presentation_cards[-1].attach_preview(self.camera_panel.preview)
        grid.setRowStretch(2,3)
        excavation_panel = make_panel(
            "Excavation View", "SIMULATED WORKSPACE / SIDE VIEW", "",
        )
        excavation_panel.setObjectName("excavationWorkspace")
        excavation_layout = excavation_panel.layout()
        excavation_layout.setContentsMargins(12, 12, 12, 12)
        excavation_layout.setSpacing(8)
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
        self.sensor_previews = sensor_previews = QTabWidget()
        self.experiment_panel = ExperimentPanel()
        sensor_previews.addTab(self.risk_panel, "Risk Overview")
        sensor_previews.addTab(self.experiment_panel, "Experiment Summary")
        sensor_previews.addTab(self.gpr_panel.wave, "GPR Scan")
        right = QVBoxLayout(); right.setSpacing(16)
        right.addWidget(sensor_previews, 2)
        right.addWidget(guardian_stack, 1)
        grid.addLayout(right, 0, 2, 3, 1)
        layout.addLayout(grid, 1)

        self.decision_engine = DecisionEngine()
        self.decision_panel = StatusIndicator()
        self.assessment_controller = AssessmentController(self.risk_engine, self.decision_engine)
        self.gpr_panel.state_changed.connect(self._update_assessment)
        self.excavator_view.geometry_changed.connect(self._assessment_tick)
        self._last_assessment = 0.0
        self._update_assessment()
        bottom = QVBoxLayout()
        bottom.setSpacing(8)
        bottom.addWidget(self.decision_panel)

        bottom.addWidget(self.scenario_panel)
        layout.addLayout(bottom)
        self.setStyleSheet(STYLE)
        self.guardian_controller = GuardianController(self)
        QApplication.instance().aboutToQuit.connect(self._shutdown)
        self.guardian_controller.observation_ready.connect(self._update_operator)
        self.camera_panel.retry_requested.connect(self.guardian_controller.start)
        self.view_mode.currentIndexChanged.connect(self._presentation_mode)
        self._scenario_reset()
        self._presentation_mode(0)


    def _presentation_stack(self, engineering_widget, title):
        stack=QStackedWidget();card=PresentationPanel(title)
        from PySide6.QtWidgets import QSizePolicy
        engineering_widget.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Ignored)
        stack.addWidget(card);stack.addWidget(engineering_widget)
        self.presentation_stacks.append(stack);self.presentation_cards.append(card)
        return stack

    def _presentation_mode(self, index):
        enabled=index==0
        self.sensor_previews.tabBar().setVisible(not enabled)
        if enabled:self.sensor_previews.setCurrentIndex(0)
        self.excavator_view.presentation = enabled
        self.excavator_view.update()
        preview = self.camera_panel.preview
        preview.compact = enabled
        if enabled:
            self.presentation_cards[-1].attach_preview(preview)
        else:
            self.camera_panel.layout().addWidget(preview)

        for stack in self.presentation_stacks:stack.setCurrentIndex(0 if enabled else 1)
        self.risk_panel.set_presentation(enabled)
        self.decision_panel.set_presentation(enabled)
        self.decision_panel.display(self.safe_dig_state.decision)
        # Fault scenarios remain available in Engineering Mode; no source labels are hidden.
        combo=self.scenario_panel.scenarios
        for row in range(combo.count()):
            is_fault="fault_" in (combo.itemData(row) or "")
            combo.view().setRowHidden(row,enabled and is_fault and row!=combo.currentIndex())

    def _update_utility(self, _event=None) -> None:
        if self.scenario_active:
            return
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
        if self.scenario_active:
            return
        from time import monotonic
        if monotonic() - self._last_assessment >= 0.2:
            self._update_assessment()

    def _update_assessment(self, _event=None) -> None:
        if self.scenario_active:
            return
        from time import monotonic
        self._last_assessment = monotonic()
        self.safe_dig_state = self.assessment_controller.update(self.safe_dig_state, self._last_assessment)
        self.risk_panel.display(self.safe_dig_state.risk, self.safe_dig_state.fusion)
        self.decision_panel.display(self.safe_dig_state.decision)
        self.camera_panel.guardian_panel.display_fusion(self.safe_dig_state.fusion)
        self.excavator_view.set_state(self.safe_dig_state)

    def _update_operator(self, state, frame) -> None:
        self.live_operator, self.live_frame = state, frame
        if self.scenario_active:
            if not self.scenario_manager.state.demo_mode:
                self.camera_panel.display(state, frame)
            return
        self.safe_dig_state = replace(self.safe_dig_state, operator=state)
        self.camera_panel.display(self.safe_dig_state.operator, frame)

    def _scenario_activate(self):
        self.scenario_active = True
        self.gpr_panel.external_input = True
        self.gpr_panel._timer.stop()
        self.gpr_panel.soil_combo.setEnabled(False)
        self.excavator_view._timer.stop()

    def _scenario_load(self, path):
        self.scenario_controller.recorder.finalize("ABORTED")
        self.scenario_timer.stop()
        self.scenario_manager.load(path)
        self._scenario_reset()

    def _scenario_start(self):
        if not self.scenario_manager.definition:
            return
        paused = self.scenario_manager.state.status == "PAUSED"
        self._scenario_activate()
        self.scenario_manager.start()
        if not paused:
            self.scenario_controller.recorder.start(self.scenario_manager.definition,self.scenario_manager.state.demo_mode,
                "SIMULATED" if self.scenario_manager.state.demo_mode else "LIVE" if self.live_operator and self.live_operator.camera_available else "OFFLINE")
            self.scenario_controller.reset_engines()
            self._scenario_render()
        self.scenario_timer.start()
        self.scenario_panel.display(self.scenario_manager)

    def _scenario_pause(self):
        if self.scenario_manager.state.status == "PAUSED":
            self.scenario_manager.resume()
            self.scenario_timer.start()
        else:
            self.scenario_manager.pause()
            self.scenario_timer.stop()
        self.scenario_panel.display(self.scenario_manager)

    def _scenario_reset(self):
        self.scenario_controller.recorder.reset()
        self.scenario_timer.stop()
        if self.scenario_manager.definition:
            self._scenario_activate()
            self.scenario_manager.reset()
            self.scenario_controller.reset_engines()
            self._scenario_render()
        self.scenario_panel.display(self.scenario_manager)

    def _scenario_mode(self, demo):
        running = self.scenario_manager.state.status == "RUNNING"
        self.scenario_controller.recorder.finalize("ABORTED")
        self.scenario_manager.set_demo_mode(demo)
        if demo:
            self.guardian_controller.stop()
            self.live_operator = self.live_frame = None
        elif self._camera_enabled and self.guardian_controller._process is None:
            self.guardian_controller.start()
        if self.scenario_active and self.scenario_manager.definition:
            self._scenario_reset()
            if running:
                self._scenario_start()

    def _scenario_step(self):
        self.scenario_manager.advance()
        self._scenario_render()
        if self.scenario_manager.state.status == "COMPLETED":
            self.scenario_timer.stop()

    def _scenario_render(self):
        self.safe_dig_state = self.scenario_controller.evaluate(live_operator=self.live_operator)
        inputs = self.scenario_controller.inputs
        view = self.excavator_view
        view.scenario_position = view.bucket_position = inputs.position
        view.geometry = inputs.geometry
        view.timestamp = self.safe_dig_state.machine.timestamp
        self.precision_panel.update_geometry(inputs.geometry)
        self.precision_panel.update_conflict(self.safe_dig_state.design_conflict)
        self.gpr_panel.display_sensor(self.safe_dig_state)
        self.gpr_panel.display_utility(self.safe_dig_state)
        soil = self.scenario_manager.definition["soil"]["type"]
        combo = self.gpr_panel.soil_combo
        combo.blockSignals(True);combo.setCurrentIndex(combo.findData(soil));combo.blockSignals(False)
        view.set_state(self.safe_dig_state)
        from domain.operator_state import OperatorState, clear_guardian
        display_operator = self.safe_dig_state.operator or OperatorState()
        if not self.safe_dig_state.fusion.guardian_valid:
            display_operator = clear_guardian(display_operator)
        self.camera_panel.display(display_operator,
            None if self.scenario_manager.state.demo_mode else self.live_frame, inputs.guardian_source)
        self.camera_panel.guardian_panel.display_fusion(self.safe_dig_state.fusion)
        self.risk_panel.display(self.safe_dig_state.risk, self.safe_dig_state.fusion)
        self.decision_panel.display(self.safe_dig_state.decision)
        self.scenario_panel.source_label.setText("VISION: SIMULATED GPR | MACHINE: SIMULATED | GUARDIAN SOURCE: " +
            ("SIMULATED DEMO" if inputs.guardian_source == "SIMULATED" else "LIVE CAMERA / " + inputs.guardian_source))
        self.scenario_panel.display(self.scenario_manager)
        self.experiment_panel.display(self.scenario_controller.recorder)
        self.system_health.display(self.safe_dig_state)
        for card,domain in zip(self.presentation_cards,("vision","precision","guardian")):
            card.display(self.safe_dig_state,domain,inputs.guardian_source)
        if self.scenario_controller.recorder.error:
            self.scenario_panel.source_label.setText(self.scenario_panel.source_label.text()+" | DATA RECORDING ERROR")

    def _shutdown(self):
        if self._closed:return
        self._closed=True
        self.scenario_controller.recorder.finalize("ABORTED")
        for timer in self.findChildren(QTimer):timer.stop()
        self.guardian_controller.stop()

    def closeEvent(self, event) -> None:
        self._shutdown()
        super().closeEvent(event)
