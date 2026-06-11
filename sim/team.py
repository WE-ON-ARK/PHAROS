"""Multi-firefighter team simulation for the PHAROS incident command hub."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from pharos.comms.core import TeamCoordinator, TeammateState, TeamSnapshot
from pharos.io.core import ReplayGazeSource, ReplayPupilSource
from pharos.pipeline.core import PharosPipeline
from pharos.sensing.core import ReplaySensingSource
from sim.core import GazeSimulator, SceneSpec, SimFrame, make_default_scene

# Incident-map bounding box (metres) — defines valid position range
BUILDING_WIDTH_M: float = 50.0
BUILDING_HEIGHT_M: float = 40.0

# Default firefighter walking speed through smoke (m/s)
_WALK_SPEED_M_S: float = 1.0

# Pipeline settings — keep consistent with generate_replay defaults
_SCREEN: tuple[int, int] = (800, 600)
_BIN: int = 100
_PUP_WIN: int = 100
_BASELINE: int = 25
_TOP_K: int = 2


@dataclass
class TeamMemberSpec:
    """Specification for one synthetic firefighter.

    node_id   — unique identifier shown on the team map
    start_pos — initial incident-map position (metres)
    waypoints — cyclic patrol path; start_pos should be the first entry
    scenario  — "a" (random gaze, high load) or "b" (UI-guided, low load)
    """

    node_id: str
    start_pos: tuple[float, float]
    waypoints: list[tuple[float, float]]
    scenario: str = "a"


def make_default_team(
    smoke_density: float = 0.3,
    seed: int = 42,
) -> tuple[list[TeamMemberSpec], SceneSpec]:
    """Return a 3-person team spec and the shared scene for the simulation.

    alpha (A-pattern) — south wing search, high cognitive load
    bravo (B-pattern) — east wing search, UI-guided low load
    charlie (A-pattern) — entrance staging and perimeter check
    """
    members: list[TeamMemberSpec] = [
        TeamMemberSpec(
            node_id="alpha",
            start_pos=(5.0, 5.0),
            waypoints=[(5.0, 5.0), (20.0, 5.0), (20.0, 20.0), (5.0, 20.0)],
            scenario="a",
        ),
        TeamMemberSpec(
            node_id="bravo",
            start_pos=(45.0, 5.0),
            waypoints=[(45.0, 5.0), (30.0, 5.0), (30.0, 20.0), (45.0, 20.0)],
            scenario="b",
        ),
        TeamMemberSpec(
            node_id="charlie",
            start_pos=(25.0, 2.0),
            waypoints=[(25.0, 2.0), (25.0, 10.0), (25.0, 2.0)],
            scenario="a",
        ),
    ]
    scene = make_default_scene(smoke_density=smoke_density, seed=seed)
    return members, scene


def _interpolate_position(
    waypoints: list[tuple[float, float]],
    distance: float,
) -> tuple[float, float]:
    """Return the position at `distance` metres along the cyclic waypoint path."""
    n = len(waypoints)
    if n == 1:
        return waypoints[0]

    seg_lengths: list[float] = []
    for i in range(n):
        x0, y0 = waypoints[i]
        x1, y1 = waypoints[(i + 1) % n]
        seg_lengths.append(math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2))

    total = sum(seg_lengths)
    if total < 1e-9:
        return waypoints[0]

    d = distance % total
    for i, seg_len in enumerate(seg_lengths):
        if d <= seg_len:
            if seg_len < 1e-9:
                return waypoints[i]
            t = d / seg_len
            x0, y0 = waypoints[i]
            x1, y1 = waypoints[(i + 1) % n]
            return (x0 + t * (x1 - x0), y0 + t * (y1 - y0))
        d -= seg_len

    return waypoints[-1]


def _make_member_frames(
    spec: TeamMemberSpec,
    scene: SceneSpec,
    n_frames: int,
    dt: float,
) -> list[dict[str, Any]]:
    """Run PharosPipeline for one member and return per-frame HudState dicts."""
    sim = GazeSimulator(scene)
    raw: list[SimFrame] = (
        sim.simulate_a(n_frames=n_frames, dt=dt)
        if spec.scenario.lower() == "a"
        else sim.simulate_b(n_frames=n_frames, dt=dt)
    )

    ts = np.array([f.timestamp for f in raw], dtype=np.float64)
    fxy = np.array([f.fixation for f in raw], dtype=np.float64)
    diams = np.array([f.pupil_diameter for f in raw], dtype=np.float64)
    scatter = np.array([f.scattering_intensity for f in raw], dtype=np.float64)

    pipeline = PharosPipeline(
        ReplayGazeSource(ts, fxy),
        ReplayPupilSource(ts, diams),
        ReplaySensingSource(ts, scatter),
        scene.hazards,
        screen_size=_SCREEN,
        bin_size=_BIN,
        fixation_window=n_frames,  # full window → no sparse-matrix artifact
        pupil_window=_PUP_WIN,
        baseline_n=_BASELINE,
        top_k=_TOP_K,
    )

    result: list[dict[str, Any]] = []
    while pipeline.can_tick():
        result.append(pipeline.tick().to_dict())
    return result


class TeamSimulator:
    """Simulates N firefighters moving through a building and sharing state.

    Each member runs an independent PharosPipeline.  Position is tracked
    via waypoint interpolation on the incident map.  All per-frame states
    are ingested into a TeamCoordinator to produce TeamSnapshots.
    """

    def __init__(
        self,
        members: list[TeamMemberSpec],
        scene: SceneSpec,
        *,
        speed: float = _WALK_SPEED_M_S,
    ) -> None:
        self._members = members
        self._scene = scene
        self._speed = speed

    def simulate(
        self,
        n_frames: int = 200,
        dt: float = 0.05,
    ) -> list[TeamSnapshot]:
        """Run the full simulation and return one TeamSnapshot per frame.

        All member pipelines are pre-computed in parallel (eagerly) and then
        replayed frame by frame through the TeamCoordinator.
        """
        hud_per_member: dict[str, list[dict[str, Any]]] = {
            spec.node_id: _make_member_frames(spec, self._scene, n_frames, dt)
            for spec in self._members
        }

        coord = TeamCoordinator()
        snapshots: list[TeamSnapshot] = []

        for frame_idx in range(n_frames):
            t = float(frame_idx) * dt
            for spec in self._members:
                hud = hud_per_member[spec.node_id][frame_idx]
                pos = _interpolate_position(spec.waypoints, t * self._speed)
                state = TeammateState(
                    node_id=spec.node_id,
                    timestamp=t,
                    position=pos,
                    cognitive_load=float(hud["cognitive_load"]),
                    visibility=float(hud["visibility"]),
                    smoke_density=float(hud["smoke_density"]),
                    active_hazard_count=len(hud["active_hazards"]),
                )
                coord.ingest(state)
            coord.tick(t)
            snapshots.append(coord.snapshot(t))

        return snapshots
