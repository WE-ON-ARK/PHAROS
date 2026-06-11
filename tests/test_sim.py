"""Tests for simulation harness: Scenario A vs B gaze entropy, pupil load, smoke."""

from __future__ import annotations

import numpy as np
import pytest
from sim import GazeSimulator, SimFrame, make_default_scene

from pharos.cogload import cognitive_load_index, extract_features
from pharos.entropy import transition_entropy
from pharos.entropy.core import stationary_entropy
from pharos.priority import PriorityQueueEngine, ScoringContext
from pharos.sensing import ReplaySensingSource, density_to_visibility, scattering_to_density

# ── helpers ───────────────────────────────────────────────────────────────────

BIN_SIZE = 100
SCREEN = (800, 600)
BASELINE_INTERVAL = (0.0, 2.0)  # first 2 s = 40 frames × 0.05 s


def _fixations(frames: list[SimFrame]) -> np.ndarray:
    return np.array([f.fixation for f in frames], dtype=np.float64)


def _pupil(frames: list[SimFrame]) -> tuple[np.ndarray, np.ndarray]:
    ts = np.array([f.timestamp for f in frames], dtype=np.float64)
    dd = np.array([f.pupil_diameter for f in frames], dtype=np.float64)
    return ts, dd


# ── core gaze-entropy tests ───────────────────────────────────────────────────


def test_ht_b_less_than_a_fixed_seed() -> None:
    """Ht(B) < Ht(A) with default seed=42 — the primary research hypothesis."""
    scene = make_default_scene(smoke_density=0.1, seed=42)
    sim = GazeSimulator(scene)
    frames_a = sim.simulate_a(n_frames=200)
    frames_b = sim.simulate_b(n_frames=200)

    ht_a = transition_entropy(_fixations(frames_a), BIN_SIZE, SCREEN)
    ht_b = transition_entropy(_fixations(frames_b), BIN_SIZE, SCREEN)
    print(f"\n  Ht(A)={ht_a:.4f}  Ht(B)={ht_b:.4f}")
    assert ht_b < ht_a, f"Expected Ht(B)={ht_b:.4f} < Ht(A)={ht_a:.4f}"


def test_hs_b_le_hs_a() -> None:
    """Hs(B) ≤ Hs(A): B fixations concentrate on fewer bins than A."""
    scene = make_default_scene(seed=42)
    sim = GazeSimulator(scene)
    hs_a = stationary_entropy(_fixations(sim.simulate_a()), BIN_SIZE, SCREEN)
    hs_b = stationary_entropy(_fixations(sim.simulate_b()), BIN_SIZE, SCREEN)
    print(f"\n  Hs(A)={hs_a:.4f}  Hs(B)={hs_b:.4f}")
    assert hs_b <= hs_a, f"Expected Hs(B)={hs_b:.4f} ≤ Hs(A)={hs_a:.4f}"


# ── frame count and field range ───────────────────────────────────────────────


@pytest.mark.parametrize("n", [50, 200])
def test_frame_count_matches_n_frames(n: int) -> None:
    sim = GazeSimulator(make_default_scene())
    assert len(sim.simulate_a(n_frames=n)) == n
    assert len(sim.simulate_b(n_frames=n)) == n


def test_fixations_within_screen_bounds() -> None:
    sim = GazeSimulator(make_default_scene())
    for frames in (sim.simulate_a(), sim.simulate_b()):
        for f in frames:
            x, y = f.fixation
            assert 0.0 <= x <= 799.0, f"x={x} out of range"
            assert 0.0 <= y <= 599.0, f"y={y} out of range"


def test_pupil_diameters_positive() -> None:
    sim = GazeSimulator(make_default_scene())
    for frames in (sim.simulate_a(), sim.simulate_b()):
        for f in frames:
            assert f.pupil_diameter > 0.0, f"pupil={f.pupil_diameter} ≤ 0"


# ── pupil cognitive load monotonicity ─────────────────────────────────────────


def test_cli_a_greater_than_cli_b() -> None:
    """Scenario A (50% peak dilation) yields higher cognitive load than B (25%)."""
    scene = make_default_scene(seed=42)
    sim = GazeSimulator(scene)
    ts_a, dd_a = _pupil(sim.simulate_a())
    ts_b, dd_b = _pupil(sim.simulate_b())

    feat_a = extract_features(ts_a, dd_a, BASELINE_INTERVAL)
    feat_b = extract_features(ts_b, dd_b, BASELINE_INTERVAL)
    cli_a = cognitive_load_index(feat_a)
    cli_b = cognitive_load_index(feat_b)
    print(f"\n  CLI(A)={cli_a:.4f}  CLI(B)={cli_b:.4f}")
    assert cli_a > cli_b, f"Expected CLI(A)={cli_a:.4f} > CLI(B)={cli_b:.4f}"


# ── stream generator ───────────────────────────────────────────────────────────


def test_stream_yields_all_frames() -> None:
    sim = GazeSimulator(make_default_scene())
    frames = sim.simulate_a(n_frames=30)
    streamed = list(sim.stream(frames))
    assert len(streamed) == 30
    assert streamed[0] is frames[0]
    assert streamed[-1] is frames[-1]


# ── smoke condition comparison ────────────────────────────────────────────────


def test_high_smoke_scattering_greater_than_low() -> None:
    """High-smoke scene produces higher mean scattering than low-smoke."""
    sim_lo = GazeSimulator(make_default_scene(smoke_density=0.1, seed=0))
    sim_hi = GazeSimulator(make_default_scene(smoke_density=0.8, seed=0))
    mean_lo = float(np.mean([f.scattering_intensity for f in sim_lo.simulate_a()]))
    mean_hi = float(np.mean([f.scattering_intensity for f in sim_hi.simulate_a()]))
    print(f"\n  mean_scatter(lo)={mean_lo:.4f}  mean_scatter(hi)={mean_hi:.4f}")
    assert mean_hi > mean_lo


# ── end-to-end integration ────────────────────────────────────────────────────


def test_end_to_end_all_modules() -> None:
    """Full pipeline: sim → entropy → cogload → sensing → priority, all produce values."""
    scene = make_default_scene(smoke_density=0.3, seed=7)
    sim = GazeSimulator(scene)

    results: dict[str, dict[str, float]] = {}

    for label, frames in (("A", sim.simulate_a()), ("B", sim.simulate_b())):
        # entropy
        ht = transition_entropy(_fixations(frames), BIN_SIZE, SCREEN)
        hs = stationary_entropy(_fixations(frames), BIN_SIZE, SCREEN)

        # cogload
        ts, dd = _pupil(frames)
        feats = extract_features(ts, dd, BASELINE_INTERVAL)
        cli = cognitive_load_index(feats)

        # sensing (use first frame's scattering)
        scatter_vals = np.array([f.scattering_intensity for f in frames], dtype=np.float64)
        ts_scatter = np.array([f.timestamp for f in frames], dtype=np.float64)
        replay = ReplaySensingSource(ts_scatter, scatter_vals)
        sample = replay.read()
        density = scattering_to_density(sample.intensity)
        visibility = density_to_visibility(density)

        # priority
        ctx = ScoringContext(smoke_density=density, visibility=visibility)
        engine = PriorityQueueEngine(top_k=2)
        engine.update(scene.hazards, ctx)
        top = engine.active_items()

        results[label] = {"hs": hs, "ht": ht, "cli": cli, "density": density}
        print(
            f"\n  [{label}] Hs={hs:.4f}  Ht={ht:.4f}  CLI={cli:.4f}"
            f"  density={density:.3f}  top_hazard={top[0].id if top else 'none'}"
        )

    # both scenarios must produce valid float outputs
    for label, vals in results.items():
        for name, v in vals.items():
            assert np.isfinite(v), f"{label}.{name} = {v} is not finite"


# ── 4-condition summary table ──────────────────────────────────────────────────


def test_four_conditions_summary() -> None:
    """Print Hs, Ht, CLI for A/B × low/high smoke; verify Ht(B) < Ht(A) in both."""
    print("\n  === 4-condition summary ===")
    print(f"  {'Scenario':<10} {'Smoke':<6} {'Hs':>8} {'Ht':>8} {'CLI':>8}")
    print(f"  {'-'*42}")

    for smoke_label, smoke in (("low", 0.1), ("high", 0.8)):
        scene = make_default_scene(smoke_density=smoke, seed=42)
        sim = GazeSimulator(scene)

        ht_vals: dict[str, float] = {}
        for scen_label, frames in (("A", sim.simulate_a()), ("B", sim.simulate_b())):
            hs = stationary_entropy(_fixations(frames), BIN_SIZE, SCREEN)
            ht = transition_entropy(_fixations(frames), BIN_SIZE, SCREEN)
            ts, dd = _pupil(frames)
            cli = cognitive_load_index(extract_features(ts, dd, BASELINE_INTERVAL))
            ht_vals[scen_label] = ht
            print(f"  {scen_label:<10} {smoke_label:<6} {hs:>8.4f} {ht:>8.4f} {cli:>8.4f}")

        assert ht_vals["B"] < ht_vals["A"], (
            f"smoke={smoke}: Ht(B)={ht_vals['B']:.4f} ≥ Ht(A)={ht_vals['A']:.4f}"
        )
