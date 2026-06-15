"""Webcam capture and the gaze/pupil/sensing adapters that wrap it.

A single :class:`CameraFeed` captures and processes one frame per pipeline tick;
the three thin adapters expose that shared frame through the existing
``GazeSource`` / ``PupilSource`` / ``SensingSource`` contracts so the unchanged
``PharosPipeline`` can run on live video.

WHY a shared feed: PharosPipeline.tick() reads gaze, then pupil, then sensing.
Only the gaze adapter advances the camera; the other two return the cached
frame.  This guarantees exactly one capture+inference per tick and keeps the
three streams perfectly synchronised.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import cast

import cv2
import numpy as np

from pharos.io.core import GazeSample, GazeSource, PupilSample, PupilSource
from pharos.sensing.core import ScatteringSample, SensingSource

from .estimate import (
    EyeReading,
    Frame,
    GazeMapping,
    detect_eyes,
    estimate_haze,
    gaze_point,
    pupil_diameter_mm,
)

# Resting pupil diameter (mm) held before the first successful detection.
_DEFAULT_DIAMETER_MM: float = 4.0
# Exponential-smoothing weight on the newest reading (0→frozen, 1→no smoothing).
_DEFAULT_SMOOTHING: float = 0.4


def load_cascades() -> tuple[cv2.CascadeClassifier, cv2.CascadeClassifier]:
    """Load the bundled OpenCV Haar cascades for face and eye detection."""
    base = cv2.data.haarcascades  # type: ignore[attr-defined]
    face = cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml")
    eye = cv2.CascadeClassifier(base + "haarcascade_eye.xml")
    if face.empty() or eye.empty():
        raise RuntimeError("failed to load OpenCV Haar cascades")
    return face, eye


@dataclass
class VisionFrame:
    """One processed camera frame: the estimates plus context for rendering.

    timestamp   — seconds since feed start
    gaze        — (x, y) screen-pixel fixation (smoothed)
    diameter_mm — pupil diameter estimate (smoothed)
    haze        — smoke-scattering proxy [0, 1]
    eyes        — detected eyes this frame (for overlay drawing)
    image       — the raw BGR frame (for overlay drawing)
    detected    — whether at least one eye was found this frame
    """

    timestamp: float
    gaze: tuple[float, float]
    diameter_mm: float
    haze: float
    eyes: list[EyeReading] = field(default_factory=list)
    image: Frame | None = None
    detected: bool = False


class CameraFeed:
    """Captures and processes webcam frames into :class:`VisionFrame` estimates.

    Smooths gaze and pupil diameter with an EMA and holds the last good value
    when a frame yields no detection, so transient detector dropouts do not
    inject spikes into the entropy / cognitive-load buffers.
    """

    def __init__(
        self,
        *,
        camera_index: int = 0,
        screen_size: tuple[int, int] = (800, 600),
        mapping: GazeMapping | None = None,
        smoothing: float = _DEFAULT_SMOOTHING,
        max_frames: int | None = None,
    ) -> None:
        self._screen_size = screen_size
        self._mapping = mapping if mapping is not None else GazeMapping()
        self._smoothing = smoothing
        self._max_frames = max_frames
        self._face_cascade, self._eye_cascade = load_cascades()

        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"could not open camera index {camera_index}")

        self._start = time.monotonic()
        self._emitted = 0
        self._gaze: tuple[float, float] = (screen_size[0] / 2.0, screen_size[1] / 2.0)
        self._diameter_mm = _DEFAULT_DIAMETER_MM
        self._latest: VisionFrame | None = None

    def opened(self) -> bool:
        """Return True while the device is open and the frame budget remains."""
        if self._max_frames is not None and self._emitted >= self._max_frames:
            return False
        return bool(self._cap.isOpened())

    def advance(self) -> VisionFrame:
        """Capture one frame, run inference, and update the smoothed estimates."""
        ok, image = self._cap.read()
        if not ok or image is None:
            raise StopIteration("camera read failed")

        frame: Frame = cast(Frame, image)
        gray = (
            frame
            if frame.ndim == 2
            else cast(Frame, cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        )
        eyes = detect_eyes(gray, self._face_cascade, self._eye_cascade)

        point = gaze_point(eyes, self._screen_size, self._mapping)
        if point is not None:
            self._gaze = self._ema_xy(self._gaze, point)
        if eyes:
            mm = float(
                np.mean(
                    [pupil_diameter_mm(e.diameter_px, e.bbox[2]) for e in eyes]
                )
            )
            self._diameter_mm = self._ema(self._diameter_mm, mm)

        vf = VisionFrame(
            timestamp=time.monotonic() - self._start,
            gaze=self._gaze,
            diameter_mm=self._diameter_mm,
            haze=estimate_haze(frame),
            eyes=eyes,
            image=frame,
            detected=bool(eyes),
        )
        self._latest = vf
        self._emitted += 1
        return vf

    def latest(self) -> VisionFrame:
        """Return the most recent processed frame; advance() must run first."""
        if self._latest is None:
            raise StopIteration("no frame captured yet")
        return self._latest

    def release(self) -> None:
        """Release the underlying capture device."""
        self._cap.release()

    def _ema(self, prev: float, new: float) -> float:
        return self._smoothing * new + (1.0 - self._smoothing) * prev

    def _ema_xy(
        self, prev: tuple[float, float], new: tuple[float, float]
    ) -> tuple[float, float]:
        return (self._ema(prev[0], new[0]), self._ema(prev[1], new[1]))


class CameraGazeSource(GazeSource):
    """Gaze adapter that advances the shared feed (read first each tick)."""

    def __init__(self, feed: CameraFeed) -> None:
        self._feed = feed

    def has_data(self) -> bool:
        """Return True while the shared feed can still produce frames."""
        return self._feed.opened()

    def read(self) -> GazeSample:
        """Advance the feed by one frame and return its gaze sample."""
        vf = self._feed.advance()
        return GazeSample(timestamp=vf.timestamp, fixation=vf.gaze)


class CameraPupilSource(PupilSource):
    """Pupil adapter reading the cached frame the gaze adapter just produced."""

    def __init__(self, feed: CameraFeed) -> None:
        self._feed = feed

    def has_data(self) -> bool:
        """Return True while the shared feed can still produce frames."""
        return self._feed.opened()

    def read(self) -> PupilSample:
        """Return the pupil sample from the feed's latest processed frame."""
        vf = self._feed.latest()
        return PupilSample(timestamp=vf.timestamp, diameter_mm=vf.diameter_mm)


class CameraSensingSource(SensingSource):
    """Scattering adapter reading the haze proxy from the latest frame."""

    def __init__(self, feed: CameraFeed) -> None:
        self._feed = feed

    def has_data(self) -> bool:
        """Return True while the shared feed can still produce frames."""
        return self._feed.opened()

    def read(self) -> ScatteringSample:
        """Return the scattering sample (haze proxy) from the latest frame."""
        vf = self._feed.latest()
        return ScatteringSample(timestamp=vf.timestamp, intensity=vf.haze)
