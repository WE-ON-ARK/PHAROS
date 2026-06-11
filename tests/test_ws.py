"""WebSocket integration tests for /ws/live and /ws/team endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from hud.server import app

_HUD_REQUIRED_KEYS = {
    "timestamp", "active_hazards", "ranked_scores",
    "cognitive_load", "smoke_density", "visibility",
    "gaze_entropy_hs", "gaze_entropy_ht", "fixation",
}
_TEAM_REQUIRED_KEYS = {"timestamp", "peers", "recent_events"}
_PEER_REQUIRED_KEYS = {"node_id", "position", "cognitive_load", "status"}

_FAST_FPS = 1000.0  # high fps to minimise sleep time in tests


@pytest.fixture(scope="module")
def client() -> TestClient:
    """TestClient with lifespan: pre-computes all caches before tests run."""
    with TestClient(app) as c:
        yield c


# ── /ws/live tests ────────────────────────────────────────────────────────────


def test_ws_live_first_frame_keys(client: TestClient) -> None:
    """First frame from /ws/live contains all required HudState keys."""
    with client.websocket_connect(f"/ws/live?scenario=a&fps={_FAST_FPS}") as ws:
        data = ws.receive_json()
    missing = _HUD_REQUIRED_KEYS - set(data.keys())
    assert not missing, f"Missing keys: {missing}"


def test_ws_live_timestamp_monotone(client: TestClient) -> None:
    """Timestamps from /ws/live are strictly increasing across 5 frames."""
    with client.websocket_connect(f"/ws/live?scenario=a&fps={_FAST_FPS}") as ws:
        frames = [ws.receive_json() for _ in range(5)]
    for i in range(1, len(frames)):
        assert frames[i]["timestamp"] > frames[i - 1]["timestamp"], (
            f"Non-monotone at index {i}: {frames[i-1]['timestamp']} → {frames[i]['timestamp']}"
        )


def test_ws_live_scenario_b_final_ht_less_than_a(client: TestClient) -> None:
    """Scenario B's last streamed Ht is lower than A's — research hypothesis check."""
    n = 200  # read all frames to get the converged final value
    with client.websocket_connect(f"/ws/live?scenario=a&fps={_FAST_FPS}") as ws:
        ht_a = [ws.receive_json()["gaze_entropy_ht"] for _ in range(n)][-1]
    with client.websocket_connect(f"/ws/live?scenario=b&fps={_FAST_FPS}") as ws:
        ht_b = [ws.receive_json()["gaze_entropy_ht"] for _ in range(n)][-1]
    print(f"\n  WS Ht(A)={ht_a:.4f}  Ht(B)={ht_b:.4f}")
    assert ht_b < ht_a, f"Expected Ht(B)={ht_b:.4f} < Ht(A)={ht_a:.4f}"


def test_ws_live_invalid_scenario_returns_error(client: TestClient) -> None:
    """Invalid scenario sends an error payload before closing."""
    with client.websocket_connect(f"/ws/live?scenario=z&fps={_FAST_FPS}") as ws:
        data = ws.receive_json()
    assert "error" in data, f"Expected 'error' key, got: {list(data.keys())}"


def test_ws_live_cognitive_load_in_range(client: TestClient) -> None:
    """cognitive_load values from 10 frames are all in [0, 1]."""
    with client.websocket_connect(f"/ws/live?scenario=a&fps={_FAST_FPS}") as ws:
        frames = [ws.receive_json() for _ in range(10)]
    for f in frames:
        assert 0.0 <= f["cognitive_load"] <= 1.0, f"cli={f['cognitive_load']}"


# ── /ws/team tests ────────────────────────────────────────────────────────────


def test_ws_team_first_snapshot_keys(client: TestClient) -> None:
    """First TeamSnapshot from /ws/team contains required top-level keys."""
    with client.websocket_connect(f"/ws/team?fps={_FAST_FPS}") as ws:
        data = ws.receive_json()
    missing = _TEAM_REQUIRED_KEYS - set(data.keys())
    assert not missing, f"Missing keys: {missing}"


def test_ws_team_three_peers(client: TestClient) -> None:
    """Each TeamSnapshot contains exactly 3 peers."""
    with client.websocket_connect(f"/ws/team?fps={_FAST_FPS}") as ws:
        data = ws.receive_json()
    assert len(data["peers"]) == 3, f"Expected 3 peers, got {len(data['peers'])}"


def test_ws_team_peer_has_required_fields(client: TestClient) -> None:
    """Each peer dict contains node_id, position, cognitive_load, status."""
    with client.websocket_connect(f"/ws/team?fps={_FAST_FPS}") as ws:
        data = ws.receive_json()
    for peer in data["peers"]:
        missing = _PEER_REQUIRED_KEYS - set(peer.keys())
        assert not missing, f"Peer missing keys: {missing}"


def test_ws_team_known_node_ids(client: TestClient) -> None:
    """Default team streams alpha, bravo, charlie as node IDs."""
    with client.websocket_connect(f"/ws/team?fps={_FAST_FPS}") as ws:
        data = ws.receive_json()
    ids = {p["node_id"] for p in data["peers"]}
    assert ids == {"alpha", "bravo", "charlie"}


def test_ws_team_initial_status_ok(client: TestClient) -> None:
    """At simulation start all peers are status 'ok' (no load yet)."""
    with client.websocket_connect(f"/ws/team?fps={_FAST_FPS}") as ws:
        first = ws.receive_json()
    for peer in first["peers"]:
        assert peer["status"] == "ok", f"{peer['node_id']} status={peer['status']}"


def test_ws_team_timestamp_monotone(client: TestClient) -> None:
    """TeamSnapshot timestamps are non-decreasing over 5 frames."""
    with client.websocket_connect(f"/ws/team?fps={_FAST_FPS}") as ws:
        snaps = [ws.receive_json() for _ in range(5)]
    for i in range(1, len(snaps)):
        assert snaps[i]["timestamp"] >= snaps[i - 1]["timestamp"]
