# Guardian face landmark model

`face_landmarker/face_landmarker.task` is Google's pretrained MediaPipe
Face Landmarker model, float16 version 1. Used locally for face presence
and landmark coordinates; no identity or fatigue inference.

Source: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task

Guide: https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python

SHA256: `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`

The application does not download models at runtime or record camera frames.
Camera index, resolution and model path are in `config/camera_config.py`.
