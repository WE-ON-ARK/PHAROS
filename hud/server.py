"""FastAPI server for PHAROS HUD: serves pre-computed replay data."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sim.core import make_default_scene

from hud.core import generate_replay

_SCENE = make_default_scene(smoke_density=0.3, seed=42)
_CACHE: dict[str, list[dict[str, Any]]] = {}


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Pre-compute both scenario replays once at server start."""
    for s in ("a", "b"):
        _CACHE[s] = generate_replay(_SCENE, s)
    yield


app = FastAPI(title="PHAROS HUD API", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/replay/{scenario}")
async def get_replay(scenario: str) -> list[dict[str, Any]]:
    """Return all pre-computed HudState frames for a scenario.

    scenario: "a" (random gaze, high load) or "b" (UI-guided, low load)
    """
    key = scenario.lower()
    if key not in ("a", "b"):
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
