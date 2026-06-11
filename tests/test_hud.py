"""Tests for HUD replay generation and FastAPI endpoints."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from hud.core import generate_replay
from hud.server import app
from sim.core import make_default_scene

_SCENE = make_default_scene(smoke_density=0.3, seed=42)
_REQUIRED_KEYS = {
    "timestamp",
    "active_hazards",
    "ranked_scores",
    "cognitive_load",
    "smoke_density",
    "visibility",
    "gaze_entropy_hs",
    "gaze_entropy_ht",
    "fixation",
}


# ── generate_replay() unit tests ─────────────────────────────────────────────


def test_generate_replay_a_length() -> None:
    """generate_replay returns exactly n_frames dicts for scenario A."""
    frames = generate_replay(_SCENE, "A", n_frames=200)
    assert len(frames) == 200


def test_generate_replay_b_length() -> None:
    """generate_replay returns exactly n_frames dicts for scenario B."""
    frames = generate_replay(_SCENE, "B", n_frames=200)
    assert len(frames) == 200


def test_generate_replay_required_keys() -> None:
    """Every frame dict must contain all required HUD keys including fixation."""
    frames = generate_replay(_SCENE, "a", n_frames=5)
    for i, frame in enumerate(frames):
        missing = _REQUIRED_KEYS - set(frame.keys())
        assert not missing, f"Frame {i} missing keys: {missing}"


def test_generate_replay_cognitive_load_range() -> None:
    """cognitive_load is always in [0, 1]."""
    frames = generate_replay(_SCENE, "a", n_frames=200)
    for f in frames:
        assert 0.0 <= f["cognitive_load"] <= 1.0, f"cli={f['cognitive_load']}"


def test_generate_replay_fixation_is_list() -> None:
    """fixation field is a [x, y] list, not a tuple."""
    frames = generate_replay(_SCENE, "a", n_frames=5)
    for f in frames:
        assert isinstance(f["fixation"], list)
        assert len(f["fixation"]) == 2


def test_generate_replay_b_ht_less_than_a() -> None:
    """Final frame: Ht(B) < Ht(A) — research hypothesis via HUD data path."""
    fa = generate_replay(_SCENE, "a", n_frames=200)
    fb = generate_replay(_SCENE, "b", n_frames=200)
    ht_a = fa[-1]["gaze_entropy_ht"]
    ht_b = fb[-1]["gaze_entropy_ht"]
    print(f"\n  HUD Ht(A)={ht_a:.4f}  Ht(B)={ht_b:.4f}")
    assert ht_b < ht_a, f"Expected Ht(B)={ht_b:.4f} < Ht(A)={ht_a:.4f}"


def test_generate_replay_json_serialisable() -> None:
    """generate_replay output can be serialised to JSON without error."""
    frames = generate_replay(_SCENE, "a", n_frames=10)
    json_str = json.dumps(frames)
    assert isinstance(json_str, str)


def test_generate_replay_invalid_scenario() -> None:
    """Passing an invalid scenario name raises ValueError."""
    with pytest.raises(ValueError, match="scenario must be"):
        generate_replay(_SCENE, "c")


# ── FastAPI endpoint tests ────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client() -> TestClient:
    """TestClient with lifespan (precompute cache on startup)."""
    with TestClient(app) as c:
        yield c


def test_api_replay_a_returns_200(client: TestClient) -> None:
    """GET /api/replay/a returns HTTP 200."""
    resp = client.get("/api/replay/a")
    assert resp.status_code == 200


def test_api_replay_a_length(client: TestClient) -> None:
    """GET /api/replay/a returns a list of 200 frames."""
    resp = client.get("/api/replay/a")
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 200


def test_api_replay_b_length(client: TestClient) -> None:
    """GET /api/replay/b returns a list of 200 frames."""
    resp = client.get("/api/replay/b")
    assert resp.status_code == 200
    assert len(resp.json()) == 200


def test_api_scene_returns_200(client: TestClient) -> None:
    """GET /api/scene returns HTTP 200 with hazards list."""
    resp = client.get("/api/scene")
    assert resp.status_code == 200
    data = resp.json()
    assert "hazards" in data
    assert "screen_size" in data
    assert len(data["hazards"]) == 3


def test_api_replay_invalid_scenario(client: TestClient) -> None:
    """GET /api/replay/invalid returns 422."""
    resp = client.get("/api/replay/invalid")
    assert resp.status_code == 422
