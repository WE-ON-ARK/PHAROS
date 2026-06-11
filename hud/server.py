"""FastAPI server for PHAROS HUD: replay REST endpoints + live WebSocket streams."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sim.core import make_default_scene
from sim.team import TeamSimulator, make_default_team

from hud.core import generate_replay

_SCENE = make_default_scene(smoke_density=0.3, seed=42)
_CACHE: dict[str, list[dict[str, Any]]] = {}
_TEAM_CACHE: list[dict[str, Any]] = []

_VALID_SCENARIOS: frozenset[str] = frozenset({"a", "b"})


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Pre-compute scenario replays and team snapshot sequence at server start."""
    for s in ("a", "b"):
        _CACHE[s] = generate_replay(_SCENE, s)
    members, team_scene = make_default_team(smoke_density=0.3, seed=42)
    team_sim = TeamSimulator(members, team_scene)
    _TEAM_CACHE.extend(snap.to_dict() for snap in team_sim.simulate())
    yield


app = FastAPI(title="PHAROS HUD API", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ── REST endpoints ────────────────────────────────────────────────────────────


@app.get("/api/replay/{scenario}")
async def get_replay(scenario: str) -> list[dict[str, Any]]:
    """Return all pre-computed HudState frames for a scenario.

    scenario: "a" (random gaze, high load) or "b" (UI-guided, low load)
    """
    key = scenario.lower()
    if key not in _VALID_SCENARIOS:
        raise HTTPException(status_code=422, detail="scenario must be 'a' or 'b'")
    return _CACHE[key]


@app.get("/api/scene")
async def get_scene() -> dict[str, Any]:
    """Return hazard positions and scene dimensions for the frontend SceneView."""
    return {
        "screen_size": list(_SCENE.screen_size),
        "smoke_density": _SCENE.smoke_density,
        "hazards": [
            {
                "id": h.id,
                "kind": h.kind.name,
                "priority": h.priority,
                "position": list(h.position),
            }
            for h in _SCENE.hazards
        ],
    }


# ── WebSocket endpoints ───────────────────────────────────────────────────────


@app.websocket("/ws/live")
async def ws_live(ws: WebSocket, scenario: str = "a", fps: float = 20.0) -> None:
    """Stream single-node HudState frames at `fps` Hz for the given scenario.

    scenario: "a" or "b" (default "a")
    fps:      stream rate in Hz (default 20)

    The connection is closed with code 1008 and an error payload if scenario
    is invalid.  All 200 pre-computed frames are sent, then the connection
    closes normally.
    """
    await ws.accept()
    key = scenario.lower()
    if key not in _VALID_SCENARIOS:
        await ws.send_json({"error": f"invalid scenario: {scenario!r}"})
        await ws.close(code=1008)
        return
    interval = 1.0 / max(fps, 0.1)
    try:
        for frame in _CACHE[key]:
            await ws.send_json(frame)
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/team")
async def ws_team(ws: WebSocket, fps: float = 10.0) -> None:
    """Stream TeamSnapshot frames at `fps` Hz.

    Each message is a TeamSnapshot.to_dict() payload containing peers and
    recent_events for the pre-simulated 3-person default team.
    All 200 pre-computed snapshots are sent, then the connection closes.
    """
    await ws.accept()
    interval = 1.0 / max(fps, 0.1)
    try:
        for snap in _TEAM_CACHE:
            await ws.send_json(snap)
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        pass
