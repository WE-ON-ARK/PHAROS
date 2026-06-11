"""Team mesh coordination: peer state, sudden-change events, and the coordinator core.

Pure synchronous logic with no transport dependency — the WebSocket hub (a later
stage) wraps this core, exactly as the pipeline wraps the estimation modules.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum

# Liveness / alert thresholds (named to avoid magic numbers)
_HEARTBEAT_TIMEOUT_S: float = 5.0  # no update for longer than this → LOST contact
_OVERLOAD_CLI_THRESHOLD: float = 0.7  # cognitive_load at/above this → OVERLOAD
_EVENT_HISTORY_MAX: int = 50  # ring-buffer size for the recent-event feed


class PeerStatus(Enum):
    """Resolved operational status of a teammate.

    OK / OVERLOAD / LOST are coordinator-derived; DISTRESS / DOWN may also be
    self-reported by the peer (manual MAYDAY).  Severity order, low → high:
        OK < OVERLOAD < DISTRESS < DOWN < LOST
    """

    OK = "ok"
    OVERLOAD = "overload"
    DISTRESS = "distress"
    DOWN = "down"
    LOST = "lost"


class EventKind(Enum):
    """Discrete broadcast events — the 'sudden change' (돌변상황) taxonomy."""

    MAYDAY = "mayday"
    FLASHOVER_WARNING = "flashover_warning"
    STRUCTURAL_COLLAPSE = "structural_collapse"
    NEW_VICTIM = "new_victim"
    LOST_CONTACT = "lost_contact"
    OVERLOAD_ALERT = "overload_alert"
    EVACUATE = "evacuate"
    RECOVERED = "recovered"


# Statuses a peer is allowed to self-report; others are coordinator-only.
_SELF_REPORTABLE: frozenset[PeerStatus] = frozenset(
    {PeerStatus.OK, PeerStatus.DISTRESS, PeerStatus.DOWN}
)

# Maps a (worsening) resolved status to the alert it raises on transition.
_STATUS_ALERT: dict[PeerStatus, EventKind] = {
    PeerStatus.OVERLOAD: EventKind.OVERLOAD_ALERT,
    PeerStatus.DISTRESS: EventKind.MAYDAY,
    PeerStatus.DOWN: EventKind.MAYDAY,
    PeerStatus.LOST: EventKind.LOST_CONTACT,
}


@dataclass
class TeammateState:
    """One firefighter's broadcast state — the per-tick mesh contract.

    position             — (x, y) on the shared incident map, in metres
    cognitive_load       — [0, 1] pupil-based load index from the peer's pipeline
    visibility           — metres, peer's local Koschmieder estimate
    smoke_density        — [0, 1] peer's local Tyndall reading
    active_hazard_count  — number of hazards in the peer's priority queue
    self_reported        — peer-raised status; only OK / DISTRESS / DOWN are honoured
    """

    node_id: str
    timestamp: float
    position: tuple[float, float]
    cognitive_load: float
    visibility: float
    smoke_density: float
    active_hazard_count: int
    self_reported: PeerStatus = PeerStatus.OK

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict (position as a [x, y] list)."""
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "position": [self.position[0], self.position[1]],
            "cognitive_load": self.cognitive_load,
            "visibility": self.visibility,
            "smoke_density": self.smoke_density,
            "active_hazard_count": self.active_hazard_count,
            "self_reported": self.self_reported.value,
        }


@dataclass
class TeamEvent:
    """A discrete sudden-change broadcast originating from one node."""

    event_id: str
    kind: EventKind
    source_node: str
    timestamp: float
    position: tuple[float, float]
    message: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict (kind as its wire string)."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "source_node": self.source_node,
            "timestamp": self.timestamp,
            "position": [self.position[0], self.position[1]],
            "message": self.message,
        }


@dataclass
class PeerView:
    """Coordinator's resolved view of one peer at snapshot time."""

    state: TeammateState
    status: PeerStatus
    silent_for: float

    def to_dict(self) -> dict[str, object]:
        """Flat dict (state fields + resolved status) for direct HUD rendering."""
        flat = self.state.to_dict()
        flat["status"] = self.status.value
        flat["silent_for"] = self.silent_for
        return flat


@dataclass
class TeamSnapshot:
    """Aggregated team view — the JSON contract for the command HUD.

    Parallels HudState, but for the whole team rather than one operator.
    """

    timestamp: float
    peers: list[PeerView] = field(default_factory=list)
    recent_events: list[TeamEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict of peers and the recent-event feed."""
        return {
            "timestamp": self.timestamp,
            "peers": [p.to_dict() for p in self.peers],
            "recent_events": [e.to_dict() for e in self.recent_events],
        }


def derive_status(
    state: TeammateState,
    silent_for: float,
    *,
    overload_threshold: float = _OVERLOAD_CLI_THRESHOLD,
    heartbeat_timeout: float = _HEARTBEAT_TIMEOUT_S,
) -> PeerStatus:
    """Resolve a peer's status from its state and how long it has been silent.

    Silence beyond the heartbeat timeout dominates everything (we have lost the
    teammate regardless of their last self-report).  Otherwise a self-reported
    MAYDAY (DISTRESS/DOWN) outranks a derived OVERLOAD, which outranks OK.
    """
    if silent_for > heartbeat_timeout:
        return PeerStatus.LOST
    if state.self_reported in (PeerStatus.DOWN, PeerStatus.DISTRESS):
        return state.self_reported
    if state.cognitive_load >= overload_threshold:
        return PeerStatus.OVERLOAD
    return PeerStatus.OK


class TeamCoordinator:
    """Aggregates teammate states and derives sudden-change events.

    Pure and synchronous: ingest() folds in a peer update, tick() runs the
    time-based liveness sweep, and snapshot() renders the current team view.
    Status-transition events are emitted once per change (no duplicate spam),
    and the recent-event feed is a bounded ring buffer.
    """

    def __init__(
        self,
        *,
        heartbeat_timeout: float = _HEARTBEAT_TIMEOUT_S,
        overload_threshold: float = _OVERLOAD_CLI_THRESHOLD,
        event_history: int = _EVENT_HISTORY_MAX,
    ) -> None:
        self._heartbeat_timeout = heartbeat_timeout
        self._overload_threshold = overload_threshold
        self._peers: dict[str, TeammateState] = {}
        self._status: dict[str, PeerStatus] = {}
        self._events: deque[TeamEvent] = deque(maxlen=event_history)
        self._seq: int = 0

    def ingest(self, state: TeammateState) -> list[TeamEvent]:
        """Register/update one peer; return events for any status transition.

        A fresh update sets silent_for = 0, so ingesting always revives a peer
        from LOST (the recovery path).
        """
        prev = self._status.get(state.node_id, PeerStatus.OK)
        new = derive_status(
            state,
            0.0,
            overload_threshold=self._overload_threshold,
            heartbeat_timeout=self._heartbeat_timeout,
        )
        self._peers[state.node_id] = state
        self._status[state.node_id] = new
        return self._record(self._transition_event(prev, new, state, state.timestamp))

    def tick(self, now: float) -> list[TeamEvent]:
        """Run the liveness sweep at time `now`; emit events for status changes."""
        emitted: list[TeamEvent] = []
        for node_id, state in self._peers.items():
            silent_for = now - state.timestamp
            prev = self._status[node_id]
            new = derive_status(
                state,
                silent_for,
                overload_threshold=self._overload_threshold,
                heartbeat_timeout=self._heartbeat_timeout,
            )
            self._status[node_id] = new
            event = self._transition_event(prev, new, state, now)
            if event is not None:
                emitted.append(event)
        for event in emitted:
            self._events.append(event)
        return emitted

    def snapshot(self, now: float) -> TeamSnapshot:
        """Render the current team view, recomputing each peer's status at `now`."""
        views: list[PeerView] = []
        for state in self._peers.values():
            silent_for = now - state.timestamp
            status = derive_status(
                state,
                silent_for,
                overload_threshold=self._overload_threshold,
                heartbeat_timeout=self._heartbeat_timeout,
            )
            views.append(PeerView(state=state, status=status, silent_for=silent_for))
        return TeamSnapshot(
            timestamp=now,
            peers=views,
            recent_events=list(self._events),
        )

    # ── private helpers ───────────────────────────────────────────────────────

    def _record(self, event: TeamEvent | None) -> list[TeamEvent]:
        """Append a single optional event to the history and return it as a list."""
        if event is None:
            return []
        self._events.append(event)
        return [event]

    def _transition_event(
        self,
        prev: PeerStatus,
        new: PeerStatus,
        state: TeammateState,
        when: float,
    ) -> TeamEvent | None:
        """Build the event a status change implies, or None for no change."""
        if new == prev:
            return None
        if new == PeerStatus.OK:
            # Returned to normal from a degraded state.
            return self._make_event(EventKind.RECOVERED, state, when)
        kind = _STATUS_ALERT.get(new)
        return self._make_event(kind, state, when) if kind is not None else None

    def _make_event(self, kind: EventKind, state: TeammateState, when: float) -> TeamEvent:
        """Construct a TeamEvent with a monotonic id and a readable message."""
        self._seq += 1
        return TeamEvent(
            event_id=f"evt-{self._seq:06d}",
            kind=kind,
            source_node=state.node_id,
            timestamp=when,
            position=state.position,
            message=_event_message(kind, state),
        )


def _event_message(kind: EventKind, state: TeammateState) -> str:
    """Human-readable Korean message shown in the command HUD event feed."""
    node = state.node_id
    if kind == EventKind.OVERLOAD_ALERT:
        return f"{node} 인지 과부하 (CLI={state.cognitive_load:.2f})"
    if kind == EventKind.MAYDAY:
        return f"{node} MAYDAY — 대원 위급"
    if kind == EventKind.LOST_CONTACT:
        return f"{node} 연락 두절"
    if kind == EventKind.RECOVERED:
        return f"{node} 상태 정상 복귀"
    return f"{node} {kind.value}"
