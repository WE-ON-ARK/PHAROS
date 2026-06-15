"""Live camera loop: drive PharosPipeline from the webcam and show the HUD.

This is the device-bound entry point — it owns the OpenCV window and the
capture lifetime.  All inference and drawing live in the pure modules
(estimate / render); this file only wires them to a real camera.
"""

from __future__ import annotations

import cv2
from sim.core import make_default_scene

from pharos.pipeline.core import PharosPipeline
from pharos.priority.core import Hazard

from .camera import (
    CameraFeed,
    CameraGazeSource,
    CameraPupilSource,
    CameraSensingSource,
)
from .estimate import GazeMapping
from .render import render_overlay

_WINDOW = "PHAROS — Live Camera"
_ESC = 27


def build_pipeline(
    feed: CameraFeed,
    hazards: list[Hazard],
    screen_size: tuple[int, int],
) -> PharosPipeline:
    """Wire the three camera adapters around a shared feed into a pipeline."""
    return PharosPipeline(
        CameraGazeSource(feed),
        CameraPupilSource(feed),
        CameraSensingSource(feed),
        hazards,
        screen_size=screen_size,
        fixation_window=100,
        pupil_window=100,
        baseline_n=25,
        top_k=2,
    )


def run_live(camera_index: int = 0, gaze_gain: float = 1.6) -> None:
    """Open the webcam, run the pipeline, and display the HUD until ESC.

    Reuses the canonical 3-hazard scene so the priority queue and smoke model
    match the simulation path — only the input source changes.
    """
    scene = make_default_scene()
    feed = CameraFeed(
        camera_index=camera_index,
        screen_size=scene.screen_size,
        mapping=GazeMapping(gain=gaze_gain),
    )
    pipeline = build_pipeline(feed, scene.hazards, scene.screen_size)

    try:
        while pipeline.can_tick():
            state = pipeline.tick()
            overlay = render_overlay(feed.latest(), state.to_dict())
            cv2.imshow(_WINDOW, overlay)
            if cv2.waitKey(1) & 0xFF == _ESC:
                break
    finally:
        feed.release()
        cv2.destroyAllWindows()
