"""Local webcam and landmark foundation settings."""

from pathlib import Path

CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 20
FRAME_STALE_SECONDS = 1.0
MAX_FACES = 3
FACE_MODEL_PATH = Path(__file__).resolve().parents[1] / "models/face_landmarker/face_landmarker.task"
