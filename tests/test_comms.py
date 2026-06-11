"""Tests for the team-mesh coordination core: status resolution, events, snapshot."""

from __future__ import annotations

import json

from pharos.comms import (
    EventKind,
    PeerStatus,
    TeamCoordinator,
    TeammateState,
    derive_status,
)

# ── helpers ───────────────────────────────────────────────────────────────────


def _state(
    node: str = "alpha",
    t: float = 0.0,
    cli: float = 0.1,
    pos: tuple[float, float] = (10.0, 20.0),
    self_reported: PeerStatus = PeerStatus.OK,
    hazards: int = 2,
    vis: float = 20.0,
    smoke: float = 0.1,
) -> TeammateState:
    return TeammateState(
        node_id=node,
        timestamp=t,
        position=pos,
        cognitive_load=cli,
        visibility=vis,
        smoke_density=smoke,
        active_hazard_count=hazards,
        self_reported=self_reported,
    )


# ── derive_status ───────────────────────────────────────────────────────────────


def test_derive_status_ok_when_normal() -> None:
    """A fresh, low-load, non-distressed peer resolves to OK."""
    assert derive_status(_state(cli=0.2), silent_for=0.0) == PeerStatus.OK


def test_derive_status_overload_when_cli_high() -> None:
    """CLI at/above the overload threshold resolves to OVERLOAD."""
    assert derive_status(_state(cli=0.7), silent_for=0.0) == PeerStatus.OVERLOAD


def test_derive_status_lost_overrides_everything() -> None:
    """Silence beyond the heartbeat timeout dominates even a high-load peer."""
    status = derive_status(_state(cli=0.9), silent_for=10.0)
    assert status == PeerStatus.LOST


def test_derive_status_self_reported_distress_honoured() -> None:
    """A self-reported DISTRESS outranks a derived OVERLOAD."""
    s = _state(cli=0.9, self_reported=PeerStatus.DISTRESS)
    assert derive_status(s, silent_for=0.0) == PeerStatus.DISTRESS


# ── ingest events ───────────────────────────────────────────────────────────────


def test_ingest_overload_emits_alert() -> None:
    """Ingesting an overloaded peer emits exactly one OVERLOAD_ALERT."""
    coord = TeamCoordinator()
    events = coord.ingest(_state(cli=0.8))
    assert len(events) == 1
    assert events[0].kind == EventKind.OVERLOAD_ALERT
    assert events[0].source_node == "alpha"


def test_ingest_self_mayday_emits_mayday() -> None:
    """A self-reported DISTRESS produces a MAYDAY event."""
    coord = TeamCoordinator()
    events = coord.ingest(_state(self_reported=PeerStatus.DISTRESS))
    assert len(events) == 1
    assert events[0].kind == EventKind.MAYDAY


def test_ingest_steady_ok_emits_no_events() -> None:
    """Repeated normal updates produce no duplicate events."""
    coord = TeamCoordinator()
    assert coord.ingest(_state(t=0.0)) == []
    assert coord.ingest(_state(t=0.1)) == []
    assert coord.ingest(_state(t=0.2)) == []


def test_ingest_overload_then_steady_no_duplicate() -> None:
    """Overload alert fires once; staying overloaded does not re-alert."""
    coord = TeamCoordinator()
    first = coord.ingest(_state(t=0.0, cli=0.8))
    second = coord.ingest(_state(t=0.1, cli=0.85))
    assert len(first) == 1
    assert second == []


# ── tick / liveness ─────────────────────────────────────────────────────────────


def test_tick_detects_lost_contact() -> None:
    """A peer silent past the timeout produces a LOST_CONTACT on tick."""
    coord = TeamCoordinator(heartbeat_timeout=5.0)
    coord.ingest(_state(t=0.0))
    events = coord.tick(now=6.0)
    assert len(events) == 1
    assert events[0].kind == EventKind.LOST_CONTACT


def test_tick_no_event_before_timeout() -> None:
    """A recently-seen peer produces no event on tick."""
    coord = TeamCoordinator(heartbeat_timeout=5.0)
    coord.ingest(_state(t=0.0))
    assert coord.tick(now=2.0) == []


def test_recovery_emits_recovered() -> None:
    """A LOST peer that sends a fresh update emits RECOVERED."""
    coord = TeamCoordinator(heartbeat_timeout=5.0)
    coord.ingest(_state(t=0.0))
    coord.tick(now=6.0)  # → LOST
    events = coord.ingest(_state(t=6.5))  # fresh update revives it
    assert len(events) == 1
    assert events[0].kind == EventKind.RECOVERED


# ── multiple peers / snapshot ────────────────────────────────────────────────────


def test_multiple_peers_tracked_independently() -> None:
    """Two peers are resolved independently in the snapshot."""
    coord = TeamCoordinator()
    coord.ingest(_state(node="alpha", t=0.0, cli=0.2))
    coord.ingest(_state(node="bravo", t=0.0, cli=0.9))
    snap = coord.snapshot(now=0.0)
    by_id = {p.state.node_id: p.status for p in snap.peers}
    print(f"\n  alpha={by_id['alpha'].value}  bravo={by_id['bravo'].value}")
    assert by_id["alpha"] == PeerStatus.OK
    assert by_id["bravo"] == PeerStatus.OVERLOAD


def test_snapshot_recomputes_lost_without_tick() -> None:
    """snapshot(now) reflects silence even if tick() has not run."""
    coord = TeamCoordinator(heartbeat_timeout=5.0)
    coord.ingest(_state(t=0.0))
    snap = coord.snapshot(now=10.0)
    assert snap.peers[0].status == PeerStatus.LOST
    assert snap.peers[0].silent_for == 10.0


def test_event_history_is_bounded() -> None:
    """The recent-event feed never exceeds its ring-buffer capacity."""
    coord = TeamCoordinator(event_history=3)
    for i in range(4):  # 4 OVERLOAD→OK cycles → 8 events, capped at 3
        coord.ingest(_state(t=i * 1.0, cli=0.8))
        coord.ingest(_state(t=i * 1.0 + 0.5, cli=0.1))
    snap = coord.snapshot(now=10.0)
    assert len(snap.recent_events) == 3


# ── serialisation ───────────────────────────────────────────────────────────────


def test_snapshot_to_dict_json_serialisable() -> None:
    """A full snapshot (peers + events) serialises to JSON without error."""
    coord = TeamCoordinator()
    coord.ingest(_state(node="alpha", cli=0.8))
    coord.ingest(_state(node="bravo", self_reported=PeerStatus.DISTRESS))
    payload = coord.snapshot(now=1.0).to_dict()
    text = json.dumps(payload)
    assert isinstance(text, str)


def test_peerview_to_dict_is_flat_with_status() -> None:
    """PeerView.to_dict flattens state fields and adds status + silent_for."""
    coord = TeamCoordinator()
    coord.ingest(_state(node="alpha", pos=(3.0, 4.0), cli=0.8))
    pv = coord.snapshot(now=0.0).peers[0]
    d = pv.to_dict()
    assert d["node_id"] == "alpha"
    assert d["position"] == [3.0, 4.0]
    assert d["status"] == "overload"
    assert "silent_for" in d


def test_event_to_dict_uses_wire_strings() -> None:
    """TeamEvent.to_dict renders kind as its lowercase wire value."""
    coord = TeamCoordinator()
    event = coord.ingest(_state(cli=0.8))[0]
    d = event.to_dict()
    assert d["kind"] == "overload_alert"
    assert d["position"] == [10.0, 20.0]
