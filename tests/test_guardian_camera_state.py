"""Hardware-independent Guardian state, capture, and failure tests."""

import unittest
from unittest.mock import patch
from threading import Event
from queue import Queue

from adapters.sensor_source import SensorHealth
from domain.operator_state import OperatorState, camera_observation, check_freshness

FACE = ((0.2, 0.3, 0.0), (0.4, 0.5, -0.1))


class GuardianStateTests(unittest.TestCase):
    def test_online_single_face(self):
        state = camera_observation(10, 10.1, (FACE,))
        self.assertTrue(state.camera_available)
        self.assertTrue(state.face_detected)
        self.assertEqual(state.face_count, 1)
        self.assertTrue(state.landmarks_available)
        self.assertEqual(state.landmarks, FACE)

    def test_offline(self):
        state = OperatorState()
        self.assertFalse(state.valid)
        self.assertFalse(state.camera_available)
        self.assertEqual(state.analysis_status, 'UNAVAILABLE')

    def test_no_face(self):
        state = camera_observation(10, 10.1, ())
        self.assertFalse(state.face_detected)
        self.assertEqual(state.face_count, 0)
        self.assertEqual(state.face_status, 'NOT DETECTED')
        self.assertFalse(state.valid)

    def test_multiple_faces(self):
        state = camera_observation(10, 10.1, (FACE, FACE))
        self.assertEqual(state.face_count, 2)
        self.assertEqual(state.face_status, 'MULTIPLE FACES')
        self.assertEqual(state.analysis_status, 'AMBIGUOUS')
        self.assertFalse(state.valid)
        self.assertEqual(state.landmarks, ())

    def test_detector_failure_keeps_camera_online(self):
        state = camera_observation(10, None, (), 'model unavailable')
        self.assertTrue(state.camera_available)
        self.assertEqual(state.face_status, 'FACE ANALYSIS OFFLINE')
        self.assertFalse(state.landmarks_available)

    def test_stale_clears_face(self):
        state = camera_observation(10, 10.1, (FACE,))
        self.assertEqual(check_freshness(state, 10.5, 1), state)
        stale = check_freshness(state, 11.1, 1)
        self.assertEqual(stale.camera_health, SensorHealth.STALE)
        self.assertFalse(stale.valid)
        self.assertFalse(stale.face_detected)
        self.assertEqual(stale.landmarks, ())

    def test_capture_invalid_frame_and_release(self):
        import numpy as np
        from modules.safedig_guardian.camera import Camera
        from unittest.mock import Mock
        capture = Mock()
        capture.isOpened.return_value = True
        capture.read.return_value = (True, np.zeros((0, 0, 3), dtype=np.uint8))
        camera = Camera(capture_factory=lambda index: capture)
        self.assertIsNone(camera.read())
        camera.release()
        capture.release.assert_called_once()

    def test_worker_offline_releases_camera(self):
        from modules.safedig_guardian.camera import capture_worker
        with patch('modules.safedig_guardian.camera.Camera') as cls:
            cls.return_value.available = False
            output = Queue(1)
            capture_worker(Event(), output, 0)
            state, frame = output.get_nowait()
            self.assertFalse(state.camera_available)
            self.assertIsNone(frame)
            cls.return_value.release.assert_called_once()

    def test_worker_detector_failure_still_produces_preview(self):
        import numpy as np
        from modules.safedig_guardian.camera import capture_worker
        stop = Event()
        output = Queue(1)
        with patch('modules.safedig_guardian.camera.Camera') as camera, \
             patch('modules.safedig_guardian.face_detector.FaceDetector', side_effect=RuntimeError('model unavailable')):
            camera.return_value.available = True
            def read():
                stop.set()
                return np.zeros((20, 30, 3), dtype=np.uint8)
            camera.return_value.read.side_effect = read
            capture_worker(stop, output, 0)
            state, frame = output.get_nowait()
            self.assertTrue(state.camera_available)
            self.assertEqual(state.face_status, 'FACE ANALYSIS OFFLINE')
            self.assertEqual(frame.shape, (20, 30, 3))
            camera.return_value.release.assert_called_once()
