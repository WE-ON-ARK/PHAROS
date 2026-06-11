"""Synthetic simulation harness: scene, frame, and gaze/pupil/scattering generators."""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from pharos.priority.core import Hazard, HazardKind

# ── data structures ───────────────────────────────────────────────────────────


@dataclass
class SceneSpec:
    """Specification for a synthetic fire-scene simulation run.

    hazards       — list of Hazard items placed in the scene
    smoke_density — global smoke density [0, 1] (affects scattering intensity)
    screen_size   — (width, height) in pixels
    seed          — base RNG seed; simulate_a uses seed, simulate_b uses seed+1
    """

    hazards: list[Hazard]
    smoke_density: float = 0.1
    screen_size: tuple[int, int] = (800, 600)
    seed: int = 42


@dataclass
class SimFrame:
    """One synchronised timestep of simulated sensor data.

    timestamp            — seconds since start
    fixation             — (x, y) screen-pixel gaze position
    pupil_diameter       — mm
    scattering_intensity — raw Tyndall-sensor reading [0, 1]
    """

    timestamp: float
    fixation: tuple[float, float]
    pupil_diameter: float
    scattering_intensity: float


# ── default scene factory ─────────────────────────────────────────────────────


def make_default_scene(smoke_density: float = 0.1, seed: int = 42) -> SceneSpec:
    """Return a canonical 3-hazard fire scene for simulation and evaluation.

    Hazard positions are deliberately spread across the 800×600 screen so that
    Scenario B fixations cluster in clearly distinct AOI bins (bin_size=100).
    """
    hazards: list[Hazard] = [
        Hazard(
            id="victim",
            kind=HazardKind.VICTIM,
            priority=0.90,
            salience=0.80,
            expectancy=0.70,
            difficulty=0.30,
            position=(150.0, 100.0),  # top-left bin (1, 1)
        ),
        Hazard(
            id="escape",
            kind=HazardKind.ESCAPE_ROUTE,
            priority=0.75,
            salience=0.60,
            expectancy=0.80,
            difficulty=0.20,
            position=(650.0, 500.0),  # bottom-right bin (6, 5)
        ),
        Hazard(
            id="fire",
            kind=HazardKind.FIRE_POINT,
            priority=0.65,
            salience=0.90,
            expectancy=0.50,
            difficulty=0.40,
            position=(400.0, 300.0),  # centre bin (4, 3)
        ),
    ]
    return SceneSpec(hazards=hazards, smoke_density=smoke_density, seed=seed)


# ── simulator ─────────────────────────────────────────────────────────────────

_BASELINE_MM: float = 4.0   # resting pupil diameter
_SIGMA_FOCUS: float = 35.0  # Gaussian spread around focus zone (px)
_PUPIL_NOISE: float = 0.08  # per-sample Gaussian noise (mm)
_SCATTER_NOISE: float = 0.03  # per-sample Gaussian noise on scattering


class GazeSimulator:
    """Generates synthetic gaze, pupil, and scattering streams for two scenarios.

    Scenario A (no UI): uniformly scattered fixations → high Hs/Ht, high cognitive load.
    Scenario B (UI-guided): structured cycling between hazard zones → low Ht, lower load.
    """

    # Probability that the next fixation stays in the cyclic zone sequence (Scenario B)
    _CYCLE_PROB: float = 0.85

    def __init__(self, scene: SceneSpec) -> None:
        self._scene = scene

    # ── public API ────────────────────────────────────────────────────────────

    def simulate_a(self, n_frames: int = 200, dt: float = 0.05) -> list[SimFrame]:
        """Scenario A: random gaze across screen, high cognitive load (no UI guidance)."""
        rng = np.random.default_rng(self._scene.seed)
        W, H = self._scene.screen_size

        fxy: npt.NDArray[np.float64] = rng.uniform(
            [0.0, 0.0], [float(W - 1), float(H - 1)], size=(n_frames, 2)
        )
        pupils = self._make_pupil(n_frames, task_peak=6.0, rng=rng)
        scattering = self._make_scattering(n_frames, rng)
        timestamps = np.arange(n_frames, dtype=np.float64) * dt
        return _build_frames(timestamps, fxy, pupils, scattering)

    def simulate_b(self, n_frames: int = 200, dt: float = 0.05) -> list[SimFrame]:
        """Scenario B: UI-guided fixations cycling between hazard zones, lower load."""
        # seed+1 keeps A and B independent regardless of call order
        rng = np.random.default_rng(self._scene.seed + 1)

        fxy = self._make_guided_fixations(n_frames, rng)
        pupils = self._make_pupil(n_frames, task_peak=5.0, rng=rng)
        scattering = self._make_scattering(n_frames, rng)
        timestamps = np.arange(n_frames, dtype=np.float64) * dt
        return _build_frames(timestamps, fxy, pupils, scattering)

    def stream(self, frames: list[SimFrame]) -> Generator[SimFrame, None, None]:
        """Yield SimFrames one at a time for pipeline injection."""
        yield from frames

    # ── private helpers ───────────────────────────────────────────────────────

    def _make_guided_fixations(
        self,
        n: int,
        rng: np.random.Generator,
    ) -> npt.NDArray[np.float64]:
        """Generate structured fixations cycling through hazard-position zones."""
        W, H = self._scene.screen_size
        zones = [(h.position[0], h.position[1]) for h in self._scene.hazards[:3]]
        if len(zones) < 2:
            zones = [(W * 0.2, H * 0.2), (W * 0.8, H * 0.8)]
        n_zones = len(zones)

        fxy = np.empty((n, 2), dtype=np.float64)
        state = 0
        for i in range(n):
            cx, cy = zones[state]
            x = float(np.clip(rng.normal(cx, _SIGMA_FOCUS), 0.0, float(W - 1)))
            y = float(np.clip(rng.normal(cy, _SIGMA_FOCUS), 0.0, float(H - 1)))
            fxy[i] = [x, y]
            # transition: cycle with high probability, occasionally jump randomly
            if rng.random() < self._CYCLE_PROB:
                state = (state + 1) % n_zones
            else:
                state = int(rng.integers(0, n_zones))
        return fxy

    def _make_pupil(
        self,
        n: int,
        task_peak: float,
        rng: np.random.Generator,
    ) -> npt.NDArray[np.float64]:
        """Synthesise pupil diameter: flat baseline then linear ramp to task_peak."""
        n_base = n // 4
        n_task = n - n_base
        baseline: npt.NDArray[np.float64] = np.full(n_base, _BASELINE_MM, dtype=np.float64)
        task: npt.NDArray[np.float64] = np.linspace(
            _BASELINE_MM, task_peak, n_task, dtype=np.float64
        )
        signal = np.concatenate([baseline, task])
        noise: npt.NDArray[np.float64] = rng.normal(0.0, _PUPIL_NOISE, n).astype(np.float64)
        return signal + noise

    def _make_scattering(
        self,
        n: int,
        rng: np.random.Generator,
    ) -> npt.NDArray[np.float64]:
        """Synthesise scattering intensity: smoke_density ± small noise."""
        noise: npt.NDArray[np.float64] = rng.normal(0.0, _SCATTER_NOISE, n).astype(np.float64)
        return np.clip(self._scene.smoke_density + noise, 0.0, 1.0)


# ── module-level helper (not exported) ───────────────────────────────────────


def _build_frames(
    timestamps: npt.NDArray[np.float64],
    fxy: npt.NDArray[np.float64],
    pupils: npt.NDArray[np.float64],
    scattering: npt.NDArray[np.float64],
) -> list[SimFrame]:
    return [
        SimFrame(
            timestamp=float(timestamps[i]),
            fixation=(float(fxy[i, 0]), float(fxy[i, 1])),
            pupil_diameter=float(pupils[i]),
            scattering_intensity=float(scattering[i]),
        )
        for i in range(len(timestamps))
    ]
