"""Central presentation palette and typography; no assessment configuration."""
CARD_PADDING = (16, 8, 16, 8)
CARD_GAP = 4
CARD_HEADER_GAP = 8
CARD_BORDER = "#294457"
CARD_RADIUS = 8

STYLE = """
QMainWindow, QWidget { background:#06111f; color:#eaf5ff; font-family:'Segoe UI'; font-size:15px; }
QFrame#panel { background:#091e2e; border:1px solid @card_border; border-radius:@card_radiuspx; }
QFrame#healthStrip { background:#071c2c; border:1px solid #234359; border-radius:8px; }
QWidget#riskContent, QScrollArea#riskScroll, QWidget#riskViewport { background:#091e2e; border:none; }
QWidget#cardBody, QStackedWidget#cardVisual { background:transparent; border:none; }
QLabel { background:transparent; border:none; }
QLabel#appTitle { font-size:30px; font-weight:700; }
QLabel#tagline { color:#53d8d2; font-size:13px; font-weight:600; }
QLabel#panelTitle { color:#b6e5f4; font-size:18px; font-weight:600; }
QLabel#muted { color:#acc2d4; font-size:13px; }
QLabel#metric { font-size:24px; font-weight:600; }
QLabel#driver { background:transparent; border-top:1px solid @card_border; border-radius:0px; padding:6px 0px 0px 0px; font-weight:600; font-size:13px; }
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
/* Header-only styling: other cards and controls keep their existing theme. */
QFrame#dashboardHeader, QWidget#headerControls { background:transparent; border:none; }
QFrame#dashboardHeader QLabel#appTitle { font-size:28px; font-weight:700; }
QFrame#dashboardHeader QLabel#tagline { color:#79c9cc; }
QLabel#headerCaption { color:#91aabf; font-size:13px; font-weight:600; }
QLabel#headerSystemStatus { color:#79cbb3; font-size:13px; }
QFrame#headerModeSegment { background:#091c2c; border:1px solid #2b4b62; border-radius:7px; }
QFrame#headerModeSegment QPushButton { background:transparent; border:1px solid transparent; border-radius:5px; padding:0px 8px; color:#a8bdcf; font-size:13px; }
QFrame#headerModeSegment QPushButton:checked { background:#123c54; border-color:#4199b6; color:#e3f8ff; font-weight:600; }
QFrame#headerModeSegment QPushButton:hover { background:#15354b; color:#e3f8ff; }
QFrame#headerModeSegment QPushButton:focus { border-color:#80dfff; }
QWidget#headerControls QPushButton { padding:0px 8px; }
QComboBox#headerScenario, QComboBox#headerViewMode { background:#0b2134; border-color:#36566e; padding:0px 12px; }
QComboBox#headerScenario:hover, QComboBox#headerViewMode:hover { border-color:#5fdcff; }
QComboBox#headerScenario:focus, QComboBox#headerViewMode:focus { border-color:#80dfff; }
QWidget#headerControls QPushButton#startButton { background:#124537; border-color:#388f70; color:#d6f8e7; }
QWidget#headerControls QPushButton#startButton:hover { background:#1a6049; border-color:#63caa1; }
QWidget#headerControls QPushButton#startButton:pressed { background:#0b352a; }
QWidget#headerControls QPushButton#startButton:focus { border-color:#80dfff; }
QWidget#headerControls QPushButton#startButton:disabled { background:#0a1b2a; border-color:#294154; color:#8399ac; }
""".replace("@card_border", CARD_BORDER).replace("@card_radius", str(CARD_RADIUS))
