"""Base industrial HMI with static module placeholders."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QLabel, QMainWindow, QVBoxLayout, QWidget,
)

from config.settings import APP_NAME, MINIMUM_SIZE, TAGLINE, WINDOW_SIZE
from ui.widgets.excavator_view import ExcavatorView
from ui.widgets.precision_panel import PrecisionPanel


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
    def __init__(self) -> None:
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
        grid.addWidget(make_panel(
            "SafeDig Vision", "Underground Utility Intelligence",
            "VISION PLACEHOLDER",
        ), 0, 0)
        self.precision_panel = PrecisionPanel()
        grid.addWidget(self.precision_panel, 1, 0)
        grid.setRowStretch(1, 2)
        grid.addWidget(make_panel(
            "SafeDig Guardian", "Operator Fatigue & Attention Intelligence",
            "GUARDIAN PLACEHOLDER",
        ), 2, 0)
        excavation_panel = make_panel(
            "Excavation View", "2D workspace • SIMULATED MOTION", "",
        )
        excavation_layout = excavation_panel.layout()
        placeholder = excavation_layout.takeAt(2).widget()
        placeholder.deleteLater()
        self.excavator_view = ExcavatorView()
        self.excavator_view.geometry_changed.connect(self.precision_panel.update_geometry)
        self.precision_panel.update_geometry(self.excavator_view.geometry)
        excavation_layout.addWidget(self.excavator_view, 1)
        grid.addWidget(excavation_panel, 0, 1, 3, 1)

        risk_panel = make_panel(
            "Risk Engine", "Static HMI preview", "RISK SCORE",
        )
        risk_layout = risk_panel.layout()
        self.risk_score_label = QLabel("0 / 100")
        self.risk_score_label.setObjectName("riskScore")
        self.risk_score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        risk_layout.addWidget(self.risk_score_label)
        self.risk_status_label = QLabel("SAFE")
        self.risk_status_label.setObjectName("safeStatus")
        self.risk_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        risk_layout.addWidget(self.risk_status_label)
        risk_layout.addStretch()
        grid.addWidget(risk_panel, 0, 2, 3, 1)
        layout.addLayout(grid, 1)

        decision_panel = make_panel(
            "AI Decision & Assistance", "DISPLAY / ALERT / ASSIST",
            "AI DECISION PLACEHOLDER",
        )
        layout.addWidget(decision_panel)

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
