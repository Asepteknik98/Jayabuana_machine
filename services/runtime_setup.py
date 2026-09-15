"""Startup directories and bounded lifecycle logging, with console fallback."""
import logging
from pathlib import Path

OUTPUT_ROOT=Path(__file__).resolve().parents[1]/"output"


def initialize_runtime(output_root=OUTPUT_ROOT):
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    errors=[]
    for name in ("logs","experiments","screenshots"):
        try:(Path(output_root)/name).mkdir(parents=True,exist_ok=True)
        except OSError as error:
            errors.append(f"OUTPUT DIRECTORY ERROR ({name}): {error}")
    logger=logging.getLogger("safedig")
    target=Path(output_root)/"logs"/"application.log"
    if not any(isinstance(h,logging.FileHandler) and Path(h.baseFilename)==target for h in logger.handlers):
        try:
            from logging.handlers import RotatingFileHandler
            handler=RotatingFileHandler(target,maxBytes=1_000_000,backupCount=1,encoding="utf8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
        except OSError as error:
            errors.append("APPLICATION LOG UNAVAILABLE: "+str(error))
    for error in errors:logger.error(error)
    return errors
