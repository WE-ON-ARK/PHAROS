"""2×2 experiment runner: (scenario A|B) × (smoke low|high) × n_reps seeds."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hud.core import generate_replay
from sim.core import make_default_scene

_SMOKE_LOW: float = 0.1
_SMOKE_HIGH: float = 0.8
_N_FRAMES: int = 200
_SEED: int = 42
_N_REPS: int = 30
_WARMUP: int = 25  # frames excluded when computing per-run post-warmup means


@dataclass
class ConditionResult:
    """Single (scenario × smoke) condition.

    ``frames`` holds the last rep's full frame list (for display/tests).
    ``rep_ht``, ``rep_hs``, ``rep_cli`` hold per-rep final-frame or mean values
    for statistical comparison (length == n_reps).
    """

    scenario: str
    smoke_density: float
    frames: list[dict[str, Any]]
    mean_hs: float
    mean_ht: float
    mean_cli: float
    mean_visibility: float
    final_ht: float
    # per-rep samples: final converged value from each independent simulation
    rep_ht: list[float] = field(default_factory=list)
    rep_hs: list[float] = field(default_factory=list)
    rep_cli: list[float] = field(default_factory=list)


@dataclass
class ExperimentResult:
    """All four 2×2 conditions in fixed order: (A,lo) (A,hi) (B,lo) (B,hi)."""

    conditions: list[ConditionResult]


def _post_warmup_mean(frames: list[dict[str, Any]], key: str, warmup: int) -> float:
    """Mean of ``key`` over post-warmup frames."""
    post = frames[warmup:]
    if not post:
        return 0.0
    return sum(float(f[key]) for f in post) / len(post)


def run_experiment(
    n_reps: int = _N_REPS,
    seed: int = _SEED,
    n_frames: int = _N_FRAMES,
    smoke_low: float = _SMOKE_LOW,
    smoke_high: float = _SMOKE_HIGH,
) -> ExperimentResult:
    """Run generate_replay for all 4 conditions × n_reps independent seeds.

    Condition order: (A, low), (A, high), (B, low), (B, high).
    Per-rep samples use the final (converged) frame Ht/Hs and post-warmup mean CLI
    to avoid growing-window artifacts in the statistical comparison.
    """
    # Accumulate per-rep values before building ConditionResults
    rep_data: dict[tuple[str, float], dict[str, list[float]]] = {}
    last_frames: dict[tuple[str, float], list[dict[str, Any]]] = {}

    for scenario in ("a", "b"):
        for smoke in (smoke_low, smoke_high):
            key = (scenario, smoke)
            rep_data[key] = {"ht": [], "hs": [], "cli": []}

    for rep in range(n_reps):
        rep_seed = seed + rep
        for scenario in ("a", "b"):
            for smoke in (smoke_low, smoke_high):
                key = (scenario, smoke)
                scene = make_default_scene(smoke_density=smoke, seed=rep_seed)
                frames = generate_replay(
                    scene, scenario, n_frames=n_frames, fixation_window=n_frames
                )
                # Final-frame entropy (window fully saturated at frame n_frames)
                rep_data[key]["ht"].append(float(frames[-1]["gaze_entropy_ht"]))
                rep_data[key]["hs"].append(float(frames[-1]["gaze_entropy_hs"]))
                # Post-warmup mean CLI (pupil signal is stable after warm-up)
                rep_data[key]["cli"].append(_post_warmup_mean(frames, "cognitive_load", _WARMUP))
                last_frames[key] = frames  # keep last rep for display

    conditions: list[ConditionResult] = []
    for scenario in ("a", "b"):
        for smoke in (smoke_low, smoke_high):
            key = (scenario, smoke)
            frames = last_frames[key]
            ht_vals = rep_data[key]["ht"]
            hs_vals = rep_data[key]["hs"]
            cli_vals = rep_data[key]["cli"]
            conditions.append(
                ConditionResult(
                    scenario=scenario,
                    smoke_density=smoke,
                    frames=frames,
                    mean_hs=sum(hs_vals) / len(hs_vals),
                    mean_ht=sum(ht_vals) / len(ht_vals),
                    mean_cli=sum(cli_vals) / len(cli_vals),
                    mean_visibility=_post_warmup_mean(frames, "visibility", _WARMUP),
                    final_ht=ht_vals[-1],
                    rep_ht=ht_vals,
                    rep_hs=hs_vals,
                    rep_cli=cli_vals,
                )
            )
    return ExperimentResult(conditions=conditions)
