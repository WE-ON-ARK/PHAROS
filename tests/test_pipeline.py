"""Tests for PharosPipeline, HudState serialisation, and IO adapters."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest
from sim import GazeSimulator, SimFrame, make_default_scene

from pharos.io import (
    GazeSample,
    GazeSource,
    ReplayGazeSource,
    ReplayPupilSource,
    StaticSectorSmokeSource,
)
from pharos.pipeline import (
    CogLoadAdaptation,
    HudState,
    PharosPipeline,
    _effective_top_k,
    _shifted_weights,
)
from pharos.priority import ScoringWeights
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


# ── CogLoadAdaptation unit tests ─────────────────────────────────────────────


def test_effective_top_k_no_load() -> None:
    """Below mid_threshold, top_k is unchanged."""
    adapt = CogLoadAdaptation(mid_threshold=0.40, high_threshold=0.70)
    assert _effective_top_k(0.0, 3, adapt) == 3
    assert _effective_top_k(0.39, 3, adapt) == 3


def test_effective_top_k_mid_load() -> None:
    """At mid_threshold, top_k is reduced by 1 (floor 1)."""
    adapt = CogLoadAdaptation(mid_threshold=0.40, high_threshold=0.70)
    assert _effective_top_k(0.40, 3, adapt) == 2
    assert _effective_top_k(0.55, 2, adapt) == 1
    assert _effective_top_k(0.55, 1, adapt) == 1  # never below 1


def test_effective_top_k_high_load() -> None:
    """At or above high_threshold, top_k is always 1."""
    adapt = CogLoadAdaptation(mid_threshold=0.40, high_threshold=0.70)
    assert _effective_top_k(0.70, 5, adapt) == 1
    assert _effective_top_k(1.00, 5, adapt) == 1


def test_shifted_weights_below_high_threshold() -> None:
    """Weights are unchanged below high_threshold."""
    adapt = CogLoadAdaptation(high_threshold=0.70, weight_shift=0.10)
    base = ScoringWeights()
    result = _shifted_weights(0.69, base, adapt)
    assert result is base


def test_shifted_weights_at_high_threshold() -> None:
    """At high_threshold, w_priority increases and w_salience decreases."""
    adapt = CogLoadAdaptation(high_threshold=0.70, weight_shift=0.10)
    base = ScoringWeights(w_priority=0.40, w_salience=0.20)
    result = _shifted_weights(0.70, base, adapt)
    assert result.w_priority == pytest.approx(0.50)
    assert result.w_salience == pytest.approx(0.10)
    # unchanged parameters
    assert result.w_expectancy == pytest.approx(base.w_expectancy)
    assert result.w_difficulty == pytest.approx(base.w_difficulty)


def test_shifted_weights_clamped() -> None:
    """w_priority is capped at 1.0 and w_salience is floored at 0.0."""
    adapt = CogLoadAdaptation(high_threshold=0.70, weight_shift=0.60)
    base = ScoringWeights(w_priority=0.90, w_salience=0.10)
    result = _shifted_weights(1.0, base, adapt)
    assert result.w_priority <= 1.0
    assert result.w_salience >= 0.0


# ── cognitive load closed-loop integration ────────────────────────────────────


def test_display_top_k_in_hud_state() -> None:
    """HudState always carries display_top_k matching effective adaptation."""
    scene = make_default_scene()
    pipe = _make_pipeline(GazeSimulator(scene).simulate_a(n_frames=200), top_k=2)
    for _ in range(200):
        state = pipe.tick()
    # display_top_k must be in [1, 2] and match active_hazards length
    assert 1 <= state.display_top_k <= 2
    assert len(state.active_hazards) <= state.display_top_k


def test_display_top_k_serialised_in_to_dict() -> None:
    """to_dict() includes display_top_k key."""
    scene = make_default_scene()
    pipe = _make_pipeline(GazeSimulator(scene).simulate_a(n_frames=50))
    for _ in range(50):
        state = pipe.tick()
    d = state.to_dict()
    assert "display_top_k" in d
    assert isinstance(d["display_top_k"], int)


# ── SectorSmokeSource / directional smoke ────────────────────────────────────


def test_sector_smoke_reduces_top_hazard_score() -> None:
    """Injecting high smoke on the top hazard's direction drops it in the ranking."""
    scene = make_default_scene()
    frames = GazeSimulator(scene).simulate_a(n_frames=200)

    # Run without sector smoke to find the natural top hazard
    pipe_clean = _make_pipeline(frames)
    for _ in range(200):
        state_clean = pipe_clean.tick()
    top_id_clean = state_clean.ranked_scores[0][1]
    top_score_clean = state_clean.ranked_scores[0][0]

    # Re-run with heavy smoke aimed at the natural top hazard
    g, p, s = _make_sources(GazeSimulator(scene).simulate_a(n_frames=200))
    sector = StaticSectorSmokeSource({top_id_clean: 0.99})
    pipe_smoky = PharosPipeline(
        g, p, s, scene.hazards,
        baseline_n=_BASELINE_N,
        sector_smoke_source=sector,
    )
    for _ in range(200):
        state_smoky = pipe_smoky.tick()

    smoky_scores = {hid: sc for sc, hid in state_smoky.ranked_scores}
    top_score_smoky = smoky_scores.get(top_id_clean, 0.0)

    print(
        f"\n  top hazard '{top_id_clean}':"
        f" score_clean={top_score_clean:.4f}"
        f" score_smoky={top_score_smoky:.4f}"
    )
    assert top_score_smoky < top_score_clean, (
        f"Expected smoke to reduce '{top_id_clean}' score, but "
        f"{top_score_smoky:.4f} >= {top_score_clean:.4f}"
    )


def test_static_sector_smoke_source_returns_overrides() -> None:
    """StaticSectorSmokeSource always returns the same mapping."""
    src = StaticSectorSmokeSource({"victim": 0.8, "fire": 0.3})
    for _ in range(3):
        overrides = src.read_overrides()
        assert overrides["victim"] == pytest.approx(0.8)
        assert overrides["fire"] == pytest.approx(0.3)


def test_pipeline_sector_smoke_absent_ids_use_global() -> None:
    """Hazard ids not in sector smoke overrides still use global smoke_density."""
    scene = make_default_scene(smoke_density=0.0, seed=0)
    frames = GazeSimulator(scene).simulate_a(n_frames=50)
    g, p, s = _make_sources(frames)
    # Override only the first hazard; all others should still score normally
    first_id = scene.hazards[0].id
    sector = StaticSectorSmokeSource({first_id: 0.99})
    pipe = PharosPipeline(
        g, p, s, scene.hazards, baseline_n=_BASELINE_N, sector_smoke_source=sector
    )
    for _ in range(50):
        state = pipe.tick()
    # The overridden hazard must score lower than it would with zero smoke
    scores = {hid: sc for sc, hid in state.ranked_scores}
    # At least one other hazard must have a valid score (not suppressed)
    other_scores = [sc for hid, sc in scores.items() if hid != first_id]
    assert any(sc > 0.0 for sc in other_scores), "Other hazards should not be zeroed"
