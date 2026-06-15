"""Unit tests for the camera input path (pure estimators + adapter wiring)."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest
from sim.core import make_default_scene

from pharos.io.core import GazeSample, PupilSample
from pharos.sensing.core import ScatteringSample
from pharos.vision import camera as camera_mod
from pharos.vision.camera import (
    CameraFeed,
    CameraGazeSource,
    CameraPupilSource,
    CameraSensingSource,
    VisionFrame,
    load_cascades,
)
from pharos.vision.estimate import (
    EyeReading,
    GazeMapping,
    detect_eyes,
    detect_pupil,
    estimate_haze,
    gaze_point,
    pupil_diameter_mm,
    to_grayscale,
)
from pharos.vision.render import render_overlay
from pharos.vision.runner import build_pipeline


def _eye_roi(
    pupil_center: tuple[int, int], size: tuple[int, int] = (40, 60)
) -> npt.NDArray[np.uint8]:
    """Build a light eye ROI with a dark 12×12 pupil blob at pupil_center (cx, cy)."""
    h, w = size
    roi = np.full((h, w), 200, dtype=np.uint8)
    cx, cy = pupil_center
    roi[cy - 6 : cy + 6, cx - 6 : cx + 6] = 20
    return roi


# ── detect_pupil ──────────────────────────────────────────────────────────────


def test_detect_pupil_finds_centroid() -> None:
    blob = detect_pupil(_eye_roi((30, 20)))
    assert blob is not None
    assert abs(blob.center_xy[0] - 30) < 2.0
    assert abs(blob.center_xy[1] - 20) < 2.0


def test_detect_pupil_diameter_reasonable() -> None:
    blob = detect_pupil(_eye_roi((30, 20)))
    assert blob is not None
    assert 8.0 < blob.diameter_px < 18.0


def test_detect_pupil_uniform_returns_none() -> None:
    assert detect_pupil(np.full((40, 60), 128, dtype=np.uint8)) is None


def test_detect_pupil_empty_returns_none() -> None:
    assert detect_pupil(np.zeros((0, 0), dtype=np.uint8)) is None


# ── pupil_diameter_mm ───────────────────────────────────────────────────────────


def test_pupil_diameter_mm_scaling() -> None:
    # eye_width 24mm wide → px_per_mm == eye_width_px / 24
    assert pupil_diameter_mm(10.0, 60.0) == 4.0


def test_pupil_diameter_mm_zero_width() -> None:
    assert pupil_diameter_mm(10.0, 0.0) == 0.0


# ── gaze_point ──────────────────────────────────────────────────────────────────


def test_gaze_point_empty_returns_none() -> None:
    assert gaze_point([], (800, 600)) is None


def test_gaze_point_centered_pupil_maps_to_centre() -> None:
    eye = EyeReading(bbox=(0, 0, 60, 40), pupil_xy=(30.0, 20.0), diameter_px=10.0)
    pt = gaze_point([eye], (800, 600))
    assert pt is not None
    assert abs(pt[0] - 399.5) < 1.0
    assert abs(pt[1] - 299.5) < 1.0


def test_gaze_point_mirror_flips_x() -> None:
    eye = EyeReading(bbox=(0, 0, 60, 40), pupil_xy=(45.0, 20.0), diameter_px=10.0)
    mirrored = gaze_point([eye], (800, 600), GazeMapping(mirror=True))
    plain = gaze_point([eye], (800, 600), GazeMapping(mirror=False))
    assert mirrored is not None and plain is not None
    # pupil right-of-centre → mirrored maps left, plain maps right
    assert mirrored[0] < 400 < plain[0]


# ── estimate_haze ───────────────────────────────────────────────────────────────


def test_estimate_haze_clear_below_hazy() -> None:
    clear = np.full((50, 50, 3), 10, dtype=np.uint8)
    hazy = np.full((50, 50, 3), 180, dtype=np.uint8)
    assert estimate_haze(clear) < estimate_haze(hazy)


def test_estimate_haze_in_range() -> None:
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, size=(50, 50, 3), dtype=np.uint8)
    h = estimate_haze(img)
    assert 0.0 <= h <= 1.0


def test_estimate_haze_empty_returns_zero() -> None:
    assert estimate_haze(np.zeros((0, 0, 3), dtype=np.uint8)) == 0.0


# ── to_grayscale ────────────────────────────────────────────────────────────────


def test_to_grayscale_reduces_channels() -> None:
    bgr = np.zeros((10, 10, 3), dtype=np.uint8)
    assert to_grayscale(bgr).ndim == 2


def test_to_grayscale_passthrough() -> None:
    gray = np.zeros((10, 10), dtype=np.uint8)
    assert to_grayscale(gray).shape == (10, 10)


# ── detect_eyes ─────────────────────────────────────────────────────────────────


def test_detect_eyes_blank_frame_returns_empty() -> None:
    face, eye = load_cascades()
    blank = np.zeros((120, 120), dtype=np.uint8)
    assert detect_eyes(blank, face, eye) == []


def test_load_cascades_non_empty() -> None:
    face, eye = load_cascades()
    assert not face.empty()
    assert not eye.empty()


# ── render_overlay ──────────────────────────────────────────────────────────────


def _vision_frame(image: npt.NDArray[np.uint8] | None) -> VisionFrame:
    eye = EyeReading(bbox=(10, 10, 60, 40), pupil_xy=(40.0, 30.0), diameter_px=10.0)
    return VisionFrame(
        timestamp=1.0,
        gaze=(400.0, 300.0),
        diameter_mm=4.2,
        haze=0.3,
        eyes=[eye],
        image=image,
        detected=True,
    )


_HUD = {
    "cognitive_load": 0.55,
    "gaze_entropy_hs": 3.2,
    "gaze_entropy_ht": 2.1,
    "smoke_density": 0.3,
    "visibility": 12.0,
    "active_hazards": [{"id": "victim", "kind": "VICTIM", "priority": 0.9}],
    "ranked_scores": [[0.5, "victim"], [0.4, "escape"]],
}


def test_render_overlay_shape_and_dtype() -> None:
    out = render_overlay(_vision_frame(np.zeros((480, 640, 3), dtype=np.uint8)), _HUD)
    assert out.dtype == np.uint8
    assert out.ndim == 3
    assert out.shape[0] == 480


def test_render_overlay_handles_missing_image() -> None:
    out = render_overlay(_vision_frame(None), _HUD)
    assert out.shape[0] == 480


def test_render_overlay_empty_queue() -> None:
    hud = dict(_HUD)
    hud["ranked_scores"] = []
    hud["active_hazards"] = []
    out = render_overlay(_vision_frame(np.zeros((480, 640, 3), dtype=np.uint8)), hud)
    assert out.dtype == np.uint8


# ── adapter delegation (no physical camera) ─────────────────────────────────────


class _FakeFeed:
    """Duck-typed stand-in for CameraFeed so adapters can be tested device-free."""

    def __init__(self) -> None:
        self.advanced = 0
        self._vf = VisionFrame(
            timestamp=2.5, gaze=(100.0, 200.0), diameter_mm=3.7, haze=0.42
        )

    def opened(self) -> bool:
        return True

    def advance(self) -> VisionFrame:
        self.advanced += 1
        return self._vf

    def latest(self) -> VisionFrame:
        return self._vf


def test_gaze_source_advances_feed() -> None:
    feed = _FakeFeed()
    src = CameraGazeSource(feed)  # type: ignore[arg-type]
    sample = src.read()
    assert isinstance(sample, GazeSample)
    assert sample.fixation == (100.0, 200.0)
    assert feed.advanced == 1
    assert src.has_data() is True


def test_pupil_source_reads_cached_without_advancing() -> None:
    feed = _FakeFeed()
    src = CameraPupilSource(feed)  # type: ignore[arg-type]
    sample = src.read()
    assert isinstance(sample, PupilSample)
    assert sample.diameter_mm == 3.7
    assert feed.advanced == 0


def test_sensing_source_reads_haze() -> None:
    feed = _FakeFeed()
    src = CameraSensingSource(feed)  # type: ignore[arg-type]
    sample = src.read()
    assert isinstance(sample, ScatteringSample)
    assert sample.intensity == 0.42
    assert feed.advanced == 0


# ── full pipeline integration with a fake capture device ────────────────────────


class _FakeCapture:
    """Stands in for cv2.VideoCapture: yields a fixed budget of synthetic frames."""

    def __init__(self, _index: int, n_frames: int = 40) -> None:
        self._remaining = n_frames
        self._rng = np.random.default_rng(7)

    def isOpened(self) -> bool:  # noqa: N802 — matches cv2 API
        return self._remaining > 0

    def read(self) -> tuple[bool, npt.NDArray[np.uint8] | None]:
        if self._remaining <= 0:
            return False, None
        self._remaining -= 1
        frame = self._rng.integers(0, 256, size=(240, 320, 3), dtype=np.uint8)
        return True, frame

    def release(self) -> None:
        self._remaining = 0


def test_camera_pipeline_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """CameraFeed → PharosPipeline → render runs frame-to-frame without hardware."""
    monkeypatch.setattr(camera_mod.cv2, "VideoCapture", _FakeCapture)

    scene = make_default_scene()
    feed = CameraFeed(camera_index=0, screen_size=scene.screen_size, max_frames=30)
    pipeline = build_pipeline(feed, scene.hazards, scene.screen_size)

    ticks = 0
    last: dict[str, object] = {}
    try:
        while pipeline.can_tick():
            state = pipeline.tick()
            last = state.to_dict()
            overlay = render_overlay(feed.latest(), last)
            assert overlay.dtype == np.uint8
            ticks += 1
    finally:
        feed.release()

    assert ticks == 30
    assert {"cognitive_load", "smoke_density", "ranked_scores"} <= set(last)
    assert 0.0 <= float(last["cognitive_load"]) <= 1.0  # type: ignore[arg-type]


def test_camera_feed_respects_frame_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(camera_mod.cv2, "VideoCapture", _FakeCapture)
    feed = CameraFeed(camera_index=0, max_frames=5)
    count = 0
    while feed.opened():
        feed.advance()
        count += 1
    assert count == 5
