"""Tests for STOM scoring, dynamic reranking, and top-k serialisation."""

from __future__ import annotations

import pytest

from pharos.priority import (
    Hazard,
    HazardKind,
    PriorityQueueEngine,
    ScoringContext,
    ScoringWeights,
    score,
)

# ── helpers ───────────────────────────────────────────────────────────────────


def _hazard(
    hid: str,
    kind: HazardKind = HazardKind.FIRE_POINT,
    priority: float = 0.5,
    salience: float = 0.5,
    expectancy: float = 0.5,
    difficulty: float = 0.2,
) -> Hazard:
    return Hazard(
        id=hid,
        kind=kind,
        priority=priority,
        salience=salience,
        expectancy=expectancy,
        difficulty=difficulty,
    )


_CTX_CLEAR = ScoringContext(smoke_density=0.0, visibility=30.0)


# ── score() unit tests ────────────────────────────────────────────────────────


def test_victim_scores_higher_than_structural() -> None:
    """VICTIM (high priority) outscores STRUCTURAL (low priority) when equal otherwise."""
    victim = _hazard("v", HazardKind.VICTIM, priority=0.9)
    structural = _hazard("s", HazardKind.STRUCTURAL, priority=0.3)
    sv = score(victim, _CTX_CLEAR)
    ss = score(structural, _CTX_CLEAR)
    print(f"\n  score(victim)={sv:.4f}  score(structural)={ss:.4f}")
    assert sv > ss


def test_score_decreases_with_local_smoke() -> None:
    """Adding smoke to a hazard's direction reduces its score."""
    h = _hazard("h1", priority=0.8)
    s_clear = score(h, _CTX_CLEAR)
    ctx_smoky = ScoringContext(
        smoke_density=0.0,
        visibility=5.0,
        hazard_smoke_overrides={"h1": 0.9},
    )
    s_smoky = score(h, ctx_smoky)
    print(f"\n  score(clear)={s_clear:.4f}  score(smoky)={s_smoky:.4f}")
    assert s_smoky < s_clear


def test_score_nonnegative_with_high_difficulty() -> None:
    """Score is always ≥ 0 even when difficulty dominates."""
    h = _hazard("h2", priority=0.0, salience=0.0, expectancy=0.0, difficulty=1.0)
    s = score(h, _CTX_CLEAR)
    print(f"\n  score(max difficulty)={s:.4f}")
    assert s >= 0.0


def test_equal_hazards_have_equal_scores() -> None:
    """Three hazards with identical parameters produce identical scores."""
    hazards = [_hazard(f"e{i}") for i in range(3)]
    scores = [score(h, _CTX_CLEAR) for h in hazards]
    assert scores[0] == pytest.approx(scores[1])
    assert scores[1] == pytest.approx(scores[2])
    print(f"\n  equal scores: {scores}")


def test_custom_weights_respected() -> None:
    """Zero weight on priority means priority differences don't change score."""
    w = ScoringWeights(w_priority=0.0, w_salience=0.5, w_expectancy=0.5, w_difficulty=0.0)
    h_high = _hazard("a", priority=1.0, salience=0.5, expectancy=0.5)
    h_low = _hazard("b", priority=0.0, salience=0.5, expectancy=0.5)
    assert score(h_high, _CTX_CLEAR, w) == pytest.approx(score(h_low, _CTX_CLEAR, w))


# ── PriorityQueueEngine tests ─────────────────────────────────────────────────


def _make_engine_with_5() -> tuple[PriorityQueueEngine, list[Hazard]]:
    engine = PriorityQueueEngine(top_k=2)
    hazards = [
        _hazard("victim", HazardKind.VICTIM, priority=0.95),
        _hazard("escape", HazardKind.ESCAPE_ROUTE, priority=0.75),
        _hazard("fire", HazardKind.FIRE_POINT, priority=0.60),
        _hazard("struct", HazardKind.STRUCTURAL, priority=0.40),
        _hazard("team", HazardKind.TEAMMATE, priority=0.25),
    ]
    engine.update(hazards, _CTX_CLEAR)
    return engine, hazards


def test_active_items_respects_top_k_one() -> None:
    """active_items() with top_k=1 returns exactly 1 item."""
    engine = PriorityQueueEngine(top_k=1)
    engine.update([_hazard("a"), _hazard("b"), _hazard("c")], _CTX_CLEAR)
    active = engine.active_items()
    assert len(active) == 1
    print(f"\n  top-1 active: {active[0].id}")


def test_active_items_respects_top_k_two() -> None:
    """active_items() with top_k=2 returns at most 2 items from 5."""
    engine, _ = _make_engine_with_5()
    active = engine.active_items()
    assert len(active) == 2
    print(f"\n  top-2 active: {[h.id for h in active]}")


def test_victim_is_first_in_active() -> None:
    """The VICTIM hazard (highest priority) should be first in active_items."""
    engine, _ = _make_engine_with_5()
    assert engine.active_items()[0].id == "victim"


def test_dynamic_rerank_on_smoke() -> None:
    """Applying smoke to the top hazard can push it down the queue."""
    engine, hazards = _make_engine_with_5()

    print("\n  === Queue BEFORE smoke ===")
    for s, h in engine.ranked_queue():
        print(f"    [{h.id:10s}]  score={s:.4f}")

    # victim direction becomes very smoky → its score drops
    ctx_smoky = ScoringContext(
        smoke_density=0.0,
        hazard_smoke_overrides={"victim": 0.99},
    )
    engine.update(hazards, ctx_smoky)

    print("\n  === Queue AFTER smoke on victim ===")
    for s, h in engine.ranked_queue():
        print(f"    [{h.id:10s}]  score={s:.4f}")

    # victim must no longer be first
    top_id = engine.ranked_queue()[0][1].id
    assert top_id != "victim", f"Expected victim to drop, but it's still top: {top_id}"


def test_top_k_serialisation_never_exceeds_k() -> None:
    """active_items() never returns more than top_k items for any input size."""
    for k in (1, 2, 3):
        engine = PriorityQueueEngine(top_k=k)
        many = [_hazard(f"h{i}", priority=float(i) / 10) for i in range(20)]
        engine.update(many, _CTX_CLEAR)
        assert len(engine.active_items()) <= k
    print("\n  serialisation constraint verified for k=1,2,3")


def test_empty_hazard_list() -> None:
    """update() with no hazards produces an empty active list."""
    engine = PriorityQueueEngine(top_k=2)
    engine.update([], _CTX_CLEAR)
    assert engine.active_items() == []
    assert engine.ranked_queue() == []
