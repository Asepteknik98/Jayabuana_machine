"""Desktop entry point for XCMG SafeDig AI Copilot."""

import sys

from PySide6.QtWidgets import QApplication

from config.settings import APP_NAME
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
