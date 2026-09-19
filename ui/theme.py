"""Central presentation palette and typography; no assessment configuration."""
STYLE = """
QMainWindow, QWidget { background:#06111f; color:#eaf5ff; font-family:'Segoe UI'; font-size:15px; }
QFrame#panel { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #092438,stop:1 #061725); border:1px solid #2b526c; border-radius:8px; }
QFrame#healthStrip { background:#071c2c; border:1px solid #234359; border-radius:8px; }
QWidget#riskContent { background:#071c2c; }
QLabel { background:transparent; border:none; }
QLabel#appTitle { font-size:30px; font-weight:700; }
QLabel#tagline { color:#53d8d2; font-size:13px; font-weight:600; }
QLabel#panelTitle { color:#96dfff; font-size:20px; font-weight:600; }
QLabel#muted { color:#acc2d4; font-size:13px; }
QLabel#metric { font-size:24px; font-weight:600; }
QLabel#driver { background:#0b293f; border-radius:5px; padding:6px; font-weight:600; font-size:13px; }
QPushButton,QComboBox { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #102c43,stop:1 #061b2d); border:1px solid #38617d; border-radius:6px; padding:8px 12px; font-size:14px; }
QPushButton:hover,QComboBox:hover { border-color:#5fdcff; background:#103c56; }
QPushButton:focus,QComboBox:focus { border-color:#80dfff; }
QPushButton:pressed { background:#174862; border-color:#80dfff; }
QPushButton:checked { color:#c8faff; background:#004770; border:1px solid #00ceff; }
QPushButton:disabled { color:#8399ac; background:#0a1b2a; border-color:#294154; }
QPushButton#startButton { color:#e6fff4; background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #008859,stop:1 #00402e); border:1px solid #00e6a0; font-weight:700; }
QComboBox::drop-down { border:0px; width:18px; }
QComboBox QAbstractItemView { background:#082c46; selection-background-color:#145573; }
QTabWidget::pane { border:0px; }
QTabBar::tab { background:#08263b; color:#9cbacf; padding:6px 10px; }
QTabBar::tab:hover { background:#10364e; color:#d8efff; }
QTabBar::tab:selected { color:#64d8ec; border-bottom:2px solid #64d8ec; }
QProgressBar { background:#0e293e; border:1px solid #25475e; border-radius:4px; min-height:8px; max-height:10px; }
QProgressBar::chunk { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #21cfff,stop:1 #0693de); border-radius:3px; }
QScrollArea { border:0px; background:transparent; }
QScrollBar:vertical { background:#062238; width:8px; }
QScrollBar::handle:vertical { background:#365c76; min-height:24px; border-radius:4px; }
QScrollBar::handle:vertical:hover { background:#527e99; }
QToolTip { background:#102c43; color:#eaf5ff; border:1px solid #47728e; padding:6px 8px; font-size:13px; }
"""
