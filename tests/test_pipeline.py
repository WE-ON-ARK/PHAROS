"""Tests for PharosPipeline, HudState serialisation, and IO adapters."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest
from sim import GazeSimulator, SimFrame, make_default_scene

from pharos.io import GazeSample, GazeSource, ReplayGazeSource, ReplayPupilSource
from pharos.pipeline import HudState, PharosPipeline
from pharos.sensing import ReplaySensingSource

# ── helpers ───────────────────────────────────────────────────────────────────

_BASELINE_N = 25


def _make_sources(frames: list[SimFrame]) -> tuple[
    ReplayGazeSource, ReplayPupilSource, ReplaySensingSource
]:
    """Build three replay sources from a list of SimFrames."""
    ts = np.array([f.timestamp for f in frames], dtype=np.float64)
    fxy = np.array([f.fixation for f in frames], dtype=np.float64)
    diams = np.array([f.pupil_diameter for f in frames], dtype=np.float64)
    scatter = np.array([f.scattering_intensity for f in frames], dtype=np.float64)
    return (
        ReplayGazeSource(ts, fxy),
        ReplayPupilSource(ts, diams),
        ReplaySensingSource(ts, scatter),
    )


def _make_pipeline(frames: list[SimFrame], **kwargs: object) -> PharosPipeline:
    scene = make_default_scene()
    g, p, s = _make_sources(frames)
    return PharosPipeline(g, p, s, scene.hazards, baseline_n=_BASELINE_N, **kwargs)  # type: ignore[arg-type]


# ── HudState serialisation ────────────────────────────────────────────────────


def test_to_dict_is_json_serialisable() -> None:
    """HudState.to_dict() must survive json.dumps() without TypeError."""
    scene = make_default_scene()
    sim = GazeSimulator(scene)
    pipe = _make_pipeline(sim.simulate_a(n_frames=200))
    for _ in range(200):
        state = pipe.tick()
    json_str = json.dumps(state.to_dict())
    assert isinstance(json_str, str)


def test_to_dict_active_hazards_keys() -> None:
    """Each entry in to_dict()['active_hazards'] must have id, kind, priority."""
    scene = make_default_scene()
    pipe = _make_pipeline(GazeSimulator(scene).simulate_a(n_frames=200))
    for _ in range(200):
        state = pipe.tick()
    d = state.to_dict()
    for item in d["active_hazards"]:  # type: ignore[union-attr]
        assert "id" in item  # type: ignore[operator]
        assert "kind" in item  # type: ignore[operator]
        assert "priority" in item  # type: ignore[operator]


# ── buffer warm-up behaviour ──────────────────────────────────────────────────


def test_first_tick_returns_zero_entropy_and_cogload() -> None:
    """Before buffers fill, entropy and cogload must be 0.0."""
    scene = make_default_scene()
    pipe = _make_pipeline(GazeSimulator(scene).simulate_a(n_frames=200))
    state = pipe.tick()
    assert state.gaze_entropy_hs == 0.0
    assert state.gaze_entropy_ht == 0.0
    assert state.cognitive_load == 0.0


def test_cogload_positive_after_baseline_fills() -> None:
    """cogload > 0 once baseline is full and pupil starts dilating.

    The synthetic pupil is flat for n_frames//4=50 frames then ramps up, so
    we run 60 ticks to ensure both baseline (25 samples) and task dilation
    are inside the buffer before asserting.
    """
    scene = make_default_scene()
    frames = GazeSimulator(scene).simulate_a(n_frames=200)
    pipe = _make_pipeline(frames)
    for _ in range(60):
        state = pipe.tick()
    assert state.cognitive_load > 0.0, f"Expected cogload > 0, got {state.cognitive_load}"


# ── post-warmup value checks ──────────────────────────────────────────────────


def test_entropy_finite_after_200_ticks() -> None:
    """After 200 ticks, Hs and Ht must be finite (no NaN/Inf)."""
    scene = make_default_scene()
    pipe = _make_pipeline(GazeSimulator(scene).simulate_a(n_frames=200))
    for _ in range(200):
        state = pipe.tick()
    assert math.isfinite(state.gaze_entropy_hs), f"Hs={state.gaze_entropy_hs}"
    assert math.isfinite(state.gaze_entropy_ht), f"Ht={state.gaze_entropy_ht}"


def test_active_hazards_count_le_top_k() -> None:
    """active_hazards must never exceed top_k."""
    scene = make_default_scene()
    pipe = _make_pipeline(GazeSimulator(scene).simulate_a(n_frames=200), top_k=2)
    for _ in range(200):
        state = pipe.tick()
    assert len(state.active_hazards) <= 2


def test_ranked_scores_sorted_descending() -> None:
    """ranked_scores must be ordered from highest to lowest score."""
    scene = make_default_scene()
    pipe = _make_pipeline(GazeSimulator(scene).simulate_a(n_frames=200))
    for _ in range(200):
        state = pipe.tick()
    scores = [s for s, _ in state.ranked_scores]
    assert scores == sorted(scores, reverse=True), f"Unsorted scores: {scores}"


# ── smoke density propagation ─────────────────────────────────────────────────


def test_high_smoke_yields_higher_density_than_low() -> None:
    """Pipeline with high-smoke scene produces higher mean smoke_density."""
    def _run_density(smoke: float) -> float:
        scene = make_default_scene(smoke_density=smoke, seed=0)
        frames = GazeSimulator(scene).simulate_a(n_frames=50)
        pipe = _make_pipeline(frames)
        densities: list[float] = []
        while pipe.can_tick():
            densities.append(pipe.tick().smoke_density)
        return float(np.mean(densities))

    d_lo = _run_density(0.1)
    d_hi = _run_density(0.8)
    print(f"\n  mean_density(lo)={d_lo:.4f}  mean_density(hi)={d_hi:.4f}")
    assert d_hi > d_lo


# ── can_tick / source exhaustion ─────────────────────────────────────────────


def test_can_tick_becomes_false_after_exhaustion() -> None:
    """can_tick() returns False once any source runs out of samples."""
    scene = make_default_scene()
    frames = GazeSimulator(scene).simulate_a(n_frames=10)
    pipe = _make_pipeline(frames)
    count = 0
    while pipe.can_tick():
        pipe.tick()
        count += 1
    assert count == 10
    assert not pipe.can_tick()


def test_replay_gaze_source_exhaustion() -> None:
    """ReplayGazeSource.has_data() is False after all samples are read."""
    ts = np.array([0.0, 0.05, 0.10], dtype=np.float64)
    fxy = np.array([[100.0, 200.0], [150.0, 250.0], [200.0, 300.0]], dtype=np.float64)
    src = ReplayGazeSource(ts, fxy)
    assert src.has_data()
    for _ in range(3):
        src.read()
    assert not src.has_data()
    with pytest.raises(StopIteration):
        src.read()


# ── adapter swap (dependency inversion) ─────────────────────────────────────


class _ConstantGazeSource(GazeSource):
    """Always returns the same fixation — for adapter-swap test."""

    def __init__(self, n: int, fixation: tuple[float, float] = (400.0, 300.0)) -> None:
        self._n = n
        self._fixation = fixation
        self._idx = 0

    def has_data(self) -> bool:
        return self._idx < self._n

    def read(self) -> GazeSample:
        if not self.has_data():
            raise StopIteration
        self._idx += 1
        return GazeSample(timestamp=float(self._idx) * 0.05, fixation=self._fixation)


def test_adapter_swap_constant_gaze_source() -> None:
    """Replacing ReplayGazeSource with a custom adapter produces valid HudState."""
    n = 50
    scene = make_default_scene()
    frames = GazeSimulator(scene).simulate_a(n_frames=n)
    ts = np.array([f.timestamp for f in frames], dtype=np.float64)
    diams = np.array([f.pupil_diameter for f in frames], dtype=np.float64)
    scatter = np.array([f.scattering_intensity for f in frames], dtype=np.float64)

    gaze_src = _ConstantGazeSource(n)
    pupil_src = ReplayPupilSource(ts, diams)
    sensing_src = ReplaySensingSource(ts, scatter)

    pipe = PharosPipeline(gaze_src, pupil_src, sensing_src, scene.hazards, baseline_n=_BASELINE_N)
    states: list[HudState] = []
    while pipe.can_tick():
        states.append(pipe.tick())

    assert len(states) == n
    # single fixation → all land in same bin → Hs=0 after warmup
    final = states[-1]
    assert math.isfinite(final.gaze_entropy_hs)
    assert math.isfinite(final.gaze_entropy_ht)


# ── end-to-end research hypothesis ───────────────────────────────────────────


def test_e2e_scenario_b_ht_less_than_a() -> None:
    """After 200 full ticks, Ht(B) < Ht(A) — core research hypothesis via pipeline.

    fixation_window=200 captures all frames so the rolling buffer doesn't cause
    the sparse-matrix artefact that occurs with a small window on a random walk.
    """
    def _run_ht(scenario: str) -> float:
        scene = make_default_scene(seed=42)
        sim = GazeSimulator(scene)
        frames = sim.simulate_a() if scenario == "A" else sim.simulate_b()
        pipe = _make_pipeline(frames, fixation_window=200)
        last: HudState | None = None
        while pipe.can_tick():
            last = pipe.tick()
        assert last is not None
        return last.gaze_entropy_ht

    ht_a = _run_ht("A")
    ht_b = _run_ht("B")
    print(f"\n  pipeline Ht(A)={ht_a:.4f}  Ht(B)={ht_b:.4f}")
    assert ht_b < ht_a, f"Expected Ht(B)={ht_b:.4f} < Ht(A)={ht_a:.4f}"
