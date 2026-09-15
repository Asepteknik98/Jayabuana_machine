"""Industrial HMI styling only."""
STYLE = """
QMainWindow, QWidget { background:#080f1b; color:#e7f0fa; font-family:'Segoe UI'; font-size:15px; }
QFrame#panel { background:#101e30; border:1px solid #263c53; border-radius:10px; }
QWidget#riskContent { background:#101e30; }
QLabel { background:transparent; border:none; }
QLabel#appTitle { font-size:26px; font-weight:700; letter-spacing:1px; }
QLabel#tagline { color:#52cce4; font-size:13px; font-weight:600; }
QLabel#panelTitle { color:#edf5ff; font-size:20px; font-weight:600; }
QLabel#muted { color:#8ba3ba; font-size:13px; }
QLabel#metric { font-size:25px; font-weight:600; }
QPushButton,QComboBox { background:#152840; border:1px solid #304862; border-radius:6px; padding:6px 12px; font-size:14px; }
QPushButton:hover,QComboBox:hover { background:#1c3652; border-color:#4d829e; }
QPushButton:disabled { color:#53667c; background:#101c2c; }
QPushButton#startButton { color:#6cedbd; background:#12392f; border:1px solid #26735c; font-weight:700; }
QComboBox::drop-down { border:0px; width:18px; }
QComboBox QAbstractItemView { background:#152840; selection-background-color:#23537c; }
QTabWidget::pane { border:1px solid #263c53; border-radius:8px; }
QTabBar::tab { background:#101e30; color:#8ba3ba; padding:6px 10px; }
QTabBar::tab:selected { color:#64d8ec; border-bottom:2px solid #64d8ec; }
QProgressBar { background:#203348; border:0px; border-radius:3px; min-height:5px; max-height:6px; }
QProgressBar::chunk { background:#4dc9e7; border-radius:3px; }
QScrollArea { border:0px; background:transparent; }
QScrollBar:vertical { background:#101e30; width:8px; }
QScrollBar::handle:vertical { background:#36506c; min-height:24px; border-radius:4px; }
"""
