"""STOM-based hazard prioritisation engine for PHAROS."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class HazardKind(Enum):
    """Fire-scenario hazard/task categories in canonical priority order.

    Default priority ranking (high → low):
        VICTIM > ESCAPE_ROUTE > FIRE_POINT > STRUCTURAL > TEAMMATE
    The ordering is only a label convention; the actual score is determined by
    the four STOM parameters on each Hazard instance.
    """

    VICTIM = "victim"
    ESCAPE_ROUTE = "escape"
    FIRE_POINT = "fire"
    STRUCTURAL = "structural"
    TEAMMATE = "teammate"


@dataclass
class Hazard:
    """A single hazard or task item scored via the STOM model.

    STOM parameters (all in [0, 1]):
        priority   — life-criticality (T: Task relevance)
        salience   — perceptual saliency (S: Salience)
        expectancy — probability of relevant info at this location (O: Observer expectancy)
        difficulty — cognitive processing cost; subtracts from score (M: Motor/cognitive cost)

    position — (x, y) in scene/screen coordinates (used for direction lookup in future stages)
    """

    id: str
    kind: HazardKind
    priority: float
    salience: float
    expectancy: float
    difficulty: float
    position: tuple[float, float] = (0.0, 0.0)


@dataclass
class ScoringContext:
    """Environmental context passed to the scoring function each tick.

    smoke_density            — global smoke density [0, 1] from sensing module
    visibility               — estimated line-of-sight visibility [m]
    hazard_smoke_overrides   — per-hazard smoke density overrides keyed by Hazard.id;
                               models direction-specific smoke (higher smoke in the
                               direction of a hazard reduces its effective score).
    """

    smoke_density: float = 0.0
    visibility: float = 30.0
    hazard_smoke_overrides: dict[str, float] = field(default_factory=dict)


@dataclass
class ScoringWeights:
    """STOM feature weights and smoke-visibility sensitivity.

    Defaults:
        w_priority            = 0.40  — life-criticality weight
        w_salience            = 0.20  — perceptual saliency weight
        w_expectancy          = 0.25  — observer expectancy weight
        w_difficulty          = 0.15  — cognitive cost (subtracted from base score)
        visibility_sensitivity = 0.60  — fraction by which full smoke (density=1)
                                         reduces the effective score
    """

    w_priority: float = 0.40
    w_salience: float = 0.20
    w_expectancy: float = 0.25
    w_difficulty: float = 0.15
    visibility_sensitivity: float = 0.60


def score(
    hazard: Hazard,
    context: ScoringContext,
    weights: ScoringWeights | None = None,
) -> float:
    """Compute the effective STOM score for a hazard given environmental context.

    base  = w_p×priority + w_s×salience + w_e×expectancy − w_d×difficulty
    smoke = hazard_smoke_overrides.get(id, smoke_density)
    score = max(0, base) × max(0, 1 − smoke × visibility_sensitivity)
    """
    w = weights if weights is not None else ScoringWeights()

    base = (
        w.w_priority * hazard.priority
        + w.w_salience * hazard.salience
        + w.w_expectancy * hazard.expectancy
        - w.w_difficulty * hazard.difficulty
    )

    local_smoke = context.hazard_smoke_overrides.get(hazard.id, context.smoke_density)
    smoke_multiplier = max(0.0, 1.0 - local_smoke * w.visibility_sensitivity)

    return float(max(0.0, base) * smoke_multiplier)


class PriorityQueueEngine:
    """Scores, sorts, and serialises hazards into a top-k active view.

    Calling update() re-scores all supplied hazards and rebuilds the sorted
    queue.  active_items() returns at most top_k items — the "serialised"
    view that keeps the HUD focused and gaze transitions short.
    """

    def __init__(self, top_k: int = 2, weights: ScoringWeights | None = None) -> None:
        self.top_k = top_k
        self._weights = weights if weights is not None else ScoringWeights()
        self._ranked: list[tuple[float, Hazard]] = []

    def update(self, hazards: list[Hazard], context: ScoringContext) -> None:
        """Re-score every hazard and re-sort the internal queue descending."""
        scored = [
            (score(h, context, self._weights), h) for h in hazards
        ]
        self._ranked = sorted(scored, key=lambda x: x[0], reverse=True)

    def active_items(self) -> list[Hazard]:
        """Return the top-k hazards by current score (serialised HUD view)."""
        return [h for _, h in self._ranked[: self.top_k]]

    def ranked_queue(self) -> list[tuple[float, Hazard]]:
        """Return all hazards paired with their scores, sorted descending."""
        return list(self._ranked)
