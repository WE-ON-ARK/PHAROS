"""Camera input path: turn live webcam frames into PharosPipeline samples.

estimate — pure image→estimate functions (gaze, pupil, haze)
camera   — webcam capture + GazeSource/PupilSource/SensingSource adapters
render   — pure HUD overlay drawing
runner   — device-bound live loop (python -m pharos.vision)
"""

from __future__ import annotations

from .camera import (
    CameraFeed,
    CameraGazeSource,
    CameraPupilSource,
    CameraSensingSource,
    VisionFrame,
    load_cascades,
)
from .estimate import (
    EyeReading,
    GazeMapping,
    PupilBlob,
    detect_eyes,
    detect_pupil,
    estimate_haze,
    gaze_point,
    pupil_diameter_mm,
    to_grayscale,
)
from .render import draw_camera_view, encode_jpeg_base64, render_overlay
from .runner import build_pipeline, run_live

__all__ = [
    "CameraFeed",
    "CameraGazeSource",
    "CameraPupilSource",
    "CameraSensingSource",
    "EyeReading",
    "GazeMapping",
    "PupilBlob",
    "VisionFrame",
    "build_pipeline",
    "detect_eyes",
    "detect_pupil",
    "draw_camera_view",
    "encode_jpeg_base64",
    "estimate_haze",
    "gaze_point",
    "load_cascades",
    "pupil_diameter_mm",
    "render_overlay",
    "run_live",
    "to_grayscale",
]
