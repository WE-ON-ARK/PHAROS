"""HUD replay data generation: runs PharosPipeline and returns serialisable frames."""

from __future__ import annotations

from typing import Any

import numpy as np
from sim.core import GazeSimulator, SceneSpec, SimFrame

from pharos.io.core import ReplayGazeSource, ReplayPupilSource
from pharos.pipeline.core import PharosPipeline
from pharos.sensing.core import ReplaySensingSource


def _make_sources(
    frames: list[SimFrame],
) -> tuple[ReplayGazeSource, ReplayPupilSource, ReplaySensingSource]:
    """Convert a list of SimFrames into the three replay source adapters."""
    ts = np.array([f.timestamp for f in frames], dtype=np.float64)
    fxy = np.array([f.fixation for f in frames], dtype=np.float64)
    diams = np.array([f.pupil_diameter for f in frames], dtype=np.float64)
    scatter = np.array([f.scattering_intensity for f in frames], dtype=np.float64)
    return (
        ReplayGazeSource(ts, fxy),
        ReplayPupilSource(ts, diams),
        ReplaySensingSource(ts, scatter),
    )


def generate_replay(
    scene: SceneSpec,
    scenario: str,
    n_frames: int = 200,
    fixation_window: int = 200,
    baseline_n: int = 25,
) -> list[dict[str, Any]]:
    """Run PharosPipeline for one scenario and return all HudState dicts.

    Each dict is HudState.to_dict() extended with a 'fixation' key so the
    frontend SceneView can render the gaze trail without a separate stream.

    scenario must be "a" or "b" (case-insensitive).
    """
    sim = GazeSimulator(scene)
    if scenario.lower() == "a":
        frames = sim.simulate_a(n_frames=n_frames)
    elif scenario.lower() == "b":
        frames = sim.simulate_b(n_frames=n_frames)
    else:
        raise ValueError(f"scenario must be 'a' or 'b', got {scenario!r}")

    gaze_src, pupil_src, sensing_src = _make_sources(frames)
    pipeline = PharosPipeline(
        gaze_src,
        pupil_src,
        sensing_src,
        scene.hazards,
        screen_size=scene.screen_size,
        fixation_window=fixation_window,
        baseline_n=baseline_n,
        top_k=2,
    )

    result: list[dict[str, Any]] = []
    idx = 0
    while pipeline.can_tick():
        state = pipeline.tick()
        d = state.to_dict()
        d["fixation"] = list(frames[idx].fixation)
        result.append(d)
        idx += 1
    return result
