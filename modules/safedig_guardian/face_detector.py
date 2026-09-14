"""MediaPipe Face Landmarker adapter; no identity or fatigue processing."""

from config.camera_config import FACE_MODEL_PATH, MAX_FACES


class FaceDetector:
    def __init__(self, model_path=FACE_MODEL_PATH) -> None:
        import mediapipe as mp
        self._mp = mp
        self._last_ms = -1
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=MAX_FACES,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self._detector = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    def detect(self, rgb_frame, timestamp: float) -> tuple:
        timestamp_ms = max(self._last_ms + 1, int(timestamp * 1000))
        self._last_ms = timestamp_ms
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._detector.detect_for_video(image, timestamp_ms)
        return tuple(tuple((point.x, point.y, point.z) for point in face)
                     for face in result.face_landmarks)

    def close(self) -> None:
        self._detector.close()
