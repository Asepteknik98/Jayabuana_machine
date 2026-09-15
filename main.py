"""Desktop entry point for XCMG SafeDig AI Copilot."""

import sys
import logging
from multiprocessing import freeze_support

from PySide6.QtWidgets import QApplication

from config.settings import APP_NAME
from config.validation import validate_configuration
from services.runtime_setup import initialize_runtime
from ui.main_window import MainWindow


def main() -> int:
    initialize_runtime()
    errors=validate_configuration()
    if errors:
        for error in errors:logging.getLogger("safedig").error("CONFIGURATION ERROR: %s",error)
        return 2
    logging.getLogger("safedig").info("Starting MVP-0 software prototype")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    result=app.exec()
    logging.getLogger("safedig").info("Application shutdown complete")
    return result


if __name__ == "__main__":
    freeze_support()
    sys.exit(main())
