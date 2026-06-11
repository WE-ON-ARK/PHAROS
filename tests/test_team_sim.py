"""Tests for TeamSimulator: frame structure, position, metrics, events."""

from __future__ import annotations

import json

import pytest
from sim.team import (
    BUILDING_HEIGHT_M,
    BUILDING_WIDTH_M,
    TeamMemberSpec,
    TeamSimulator,
    _interpolate_position,
    make_default_team,
)

_N_FRAMES = 200
_WARMUP = 25


@pytest.fixture(scope="module")
def sim_result() -> list:  # type: ignore[type-arg]
    """Run one 200-frame team simulation; reused across all tests."""
    members, scene = make_default_team(smoke_density=0.3, seed=42)
    sim = TeamSimulator(members, scene)
    return sim.simulate(n_frames=_N_FRAMES)


# ── structure tests ───────────────────────────────────────────────────────────


def test_simulate_frame_count(sim_result: list) -> None:  # type: ignore[type-arg]
    """simulate() returns exactly n_frames TeamSnapshots."""
    assert len(sim_result) == _N_FRAMES


def test_simulate_three_peers(sim_result: list) -> None:  # type: ignore[type-arg]
    """Each snapshot contains exactly 3 peers."""
    for snap in sim_result:
        assert len(snap.peers) == 3, f"expected 3 peers, got {len(snap.peers)}"


def test_peer_node_ids(sim_result: list) -> None:  # type: ignore[type-arg]
    """All snapshots contain alpha, bravo, charlie."""
    for snap in sim_result:
        ids = {p.state.node_id for p in snap.peers}
        assert ids == {"alpha", "bravo", "charlie"}


# ── position tests ────────────────────────────────────────────────────────────


def test_positions_within_building_bounds(sim_result: list) -> None:  # type: ignore[type-arg]
    """Every peer position is within the building footprint at every frame."""
    for snap in sim_result:
        for pv in snap.peers:
            x, y = pv.state.position
            assert 0.0 <= x <= BUILDING_WIDTH_M, f"x={x} out of range"
            assert 0.0 <= y <= BUILDING_HEIGHT_M, f"y={y} out of range"


def test_interpolate_position_single_waypoint() -> None:
    """Single-waypoint path always returns that waypoint."""
    pos = _interpolate_position([(10.0, 20.0)], distance=999.0)
    assert pos == (10.0, 20.0)


def test_interpolate_position_cycles() -> None:
    """Interpolation wraps around the cyclic path."""
    wps = [(0.0, 0.0), (10.0, 0.0)]  # path: 0→10→0→10… total length 20
    p1 = _interpolate_position(wps, 5.0)    # halfway on first segment
    p2 = _interpolate_position(wps, 25.0)   # same position after one full cycle
    assert abs(p1[0] - p2[0]) < 1e-6 and abs(p1[1] - p2[1]) < 1e-6


# ── metrics tests ─────────────────────────────────────────────────────────────


def test_alpha_cli_greater_than_bravo(sim_result: list) -> None:  # type: ignore[type-arg]
    """Mean post-warmup CLI of alpha (scenario A) > bravo (scenario B)."""
    def mean_cli(node_id: str) -> float:
        vals = [
            p.state.cognitive_load
            for snap in sim_result[_WARMUP:]
            for p in snap.peers
            if p.state.node_id == node_id
        ]
        return sum(vals) / len(vals)

    cli_a = mean_cli("alpha")
    cli_b = mean_cli("bravo")
    print(f"\n  mean CLI alpha={cli_a:.4f}  bravo={cli_b:.4f}")
    assert cli_a > cli_b, f"Expected CLI(alpha)={cli_a:.4f} > CLI(bravo)={cli_b:.4f}"


def test_smoke_density_within_range(sim_result: list) -> None:  # type: ignore[type-arg]
    """All peers report smoke_density in [0, 1] and visibility > 0."""
    for snap in sim_result:
        for pv in snap.peers:
            assert 0.0 <= pv.state.smoke_density <= 1.0
            assert pv.state.visibility > 0.0


# ── serialisation ────────────────────────────────────────────────────────────


def test_snapshot_json_serialisable(sim_result: list) -> None:  # type: ignore[type-arg]
    """Final TeamSnapshot serialises to JSON without error."""
    text = json.dumps(sim_result[-1].to_dict())
    assert isinstance(text, str)
    parsed = json.loads(text)
    assert "peers" in parsed
    assert "recent_events" in parsed


# ── make_default_team ─────────────────────────────────────────────────────────


def test_make_default_team_returns_three_members() -> None:
    """make_default_team() returns a list of 3 TeamMemberSpec objects."""
    members, scene = make_default_team()
    assert len(members) == 3
    for m in members:
        assert isinstance(m, TeamMemberSpec)
