"""Real capture worker. All camera and inference work stays outside the GUI."""

import logging
from queue import Empty, Full
from time import monotonic

from config.camera_config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS
from domain.operator_state import OperatorState, camera_observation

logger = logging.getLogger(__name__)


class Camera:
    def __init__(self, index: int = CAMERA_INDEX, capture_factory=None) -> None:
        import cv2
        self._cv = cv2
        self._capture = (capture_factory or cv2.VideoCapture)(index)
        try:
            if self._capture.isOpened():
                self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                self._capture.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        except Exception:
            self._capture.release()
            raise

    @property
    def available(self) -> bool:
        return self._capture.isOpened()

    def read(self):
        ok, frame = self._capture.read()
        if not ok or frame is None or frame.size == 0 or frame.ndim != 3 or frame.shape[2] != 3:
            return None
        return frame

    def release(self) -> None:
        self._capture.release()


def publish_latest(output, packet) -> None:
    try:
        output.put_nowait(packet)
    except Full:
        try:
            output.get_nowait()
        except Empty:
            return  # Feeder still transferring; skip this frame, never queue indefinitely.
        try:
            output.put_nowait(packet)
        except Full:
            return


def capture_worker(stop, output, index: int) -> None:
    camera = detector = None
    try:
        import cv2
        from modules.safedig_guardian.face_detector import FaceDetector
        from modules.safedig_guardian.fatigue_engine import FatigueEngine
        guardian = FatigueEngine()
        camera = Camera(index)
        if not camera.available:
            publish_latest(output, (OperatorState(diagnostic="Camera could not open"), None))
            return
        logger.info("Camera started")
        diagnostic = ""
        try:
            detector = FaceDetector()
        except Exception as error:
            # Third-party model/backend errors must not interrupt live preview.
            diagnostic = f"Face analysis initialization failed: {error}"
            logger.warning(diagnostic)
        while not stop.is_set():
            started = monotonic()
            frame = camera.read()
            if frame is None:
                publish_latest(output, (OperatorState(diagnostic="Frame read failed or camera disconnected"), None))
                break
            frame_time = monotonic()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces, detection_time = (), None
            if detector is not None:
                try:
                    faces = detector.detect(rgb, frame_time)
                    detection_time = monotonic()
                except Exception as error:
                    diagnostic = f"Face analysis failed: {error}"
                    logger.warning(diagnostic)
                    detector.close()
                    detector = None
            state = camera_observation(frame_time, detection_time, faces, diagnostic)
            state = guardian.update(state, rgb.shape[1], rgb.shape[0])
            publish_latest(output, (state, rgb))
            stop.wait(max(0, 1 / CAMERA_FPS - (monotonic() - started)))
    except Exception as error:
        logger.warning("Camera worker error: %s", error)
        publish_latest(output, (OperatorState(diagnostic=f"Camera error: {error}"), None))
    finally:
        if camera is not None:
            camera.release()
        if detector is not None:
            try:
                detector.close()
            except Exception as error:
                logger.warning("Face detector cleanup failed: %s", error)
        logger.info("Camera stopped")
