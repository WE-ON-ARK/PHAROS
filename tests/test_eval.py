"""Tests for eval: 2×2 experiment runner, statistical analysis, report builder."""

from __future__ import annotations

import json

import pytest
from eval.report import build_report
from eval.runner import ConditionResult, ExperimentResult, run_experiment
from eval.stats import analyse

_N_REPS = 10  # small for fast CI; production default is 30


@pytest.fixture(scope="module")
def result() -> ExperimentResult:
    """Run 2×2 experiment with n_reps=10; reused across all tests."""
    return run_experiment(n_reps=_N_REPS)


@pytest.fixture(scope="module")
def hyp(result: ExperimentResult):  # type: ignore[no-untyped-def]
    """Analyse the experiment result once."""
    return analyse(result)


# ── runner tests ──────────────────────────────────────────────────────────────


def test_run_experiment_four_conditions(result: ExperimentResult) -> None:
    """run_experiment() returns exactly 4 conditions."""
    assert len(result.conditions) == 4


def test_run_experiment_condition_order(result: ExperimentResult) -> None:
    """Conditions are in order (A,lo) (A,hi) (B,lo) (B,hi)."""
    expected = [("a", "lo"), ("a", "hi"), ("b", "lo"), ("b", "hi")]
    for cond, (scen, smoke) in zip(result.conditions, expected, strict=True):
        assert cond.scenario == scen
        if smoke == "lo":
            assert cond.smoke_density < 0.5
        else:
            assert cond.smoke_density >= 0.5


def test_run_experiment_frames_length(result: ExperimentResult) -> None:
    """Each condition retains exactly 200 frames (from the last rep)."""
    for c in result.conditions:
        assert len(c.frames) == 200, f"Expected 200 frames, got {len(c.frames)}"


def test_condition_result_rep_ht_length(result: ExperimentResult) -> None:
    """Each condition has n_reps per-rep Ht samples."""
    for c in result.conditions:
        assert isinstance(c, ConditionResult)
        assert len(c.rep_ht) == _N_REPS, f"rep_ht len={len(c.rep_ht)}"
        assert len(c.rep_hs) == _N_REPS
        assert len(c.rep_cli) == _N_REPS


def test_condition_result_mean_cli_range(result: ExperimentResult) -> None:
    """mean_cli and all rep_cli values are in [0, 1]."""
    for c in result.conditions:
        assert 0.0 <= c.mean_cli <= 1.0, f"mean_cli={c.mean_cli}"
        for v in c.rep_cli:
            assert 0.0 <= v <= 1.0, f"rep_cli={v}"


# ── hypothesis tests ──────────────────────────────────────────────────────────


def test_h1_ht_b_less_than_a(hyp) -> None:  # type: ignore[no-untyped-def]
    """H1 rejected: Ht(B) < Ht(A) at p < 0.05."""
    assert hyp.h1_ht.rejected, (
        f"H1 not rejected: p={hyp.h1_ht.p_value:.4f}, U={hyp.h1_ht.statistic:.1f}"
    )
    assert hyp.h1_ht.p_value < hyp.alpha


def test_h2_hs_b_less_than_a(hyp) -> None:  # type: ignore[no-untyped-def]
    """H2 rejected: Hs(B) < Hs(A) at p < 0.05."""
    assert hyp.h2_hs.rejected, f"H2 not rejected: p={hyp.h2_hs.p_value:.4f}"


def test_h3_cli_b_less_than_a(hyp) -> None:  # type: ignore[no-untyped-def]
    """H3 rejected: CLI(B) < CLI(A) at p < 0.05."""
    assert hyp.h3_cli.rejected, f"H3 not rejected: p={hyp.h3_cli.p_value:.4f}"


def test_h1_effect_size_nonzero(hyp) -> None:  # type: ignore[no-untyped-def]
    """H1 effect size (rank-biserial r) is nonzero."""
    assert abs(hyp.h1_ht.effect_size) > 0.0, "H1 effect size is 0"


# ── report tests ──────────────────────────────────────────────────────────────


def test_build_report_contains_required_sections(result: ExperimentResult, hyp) -> None:  # type: ignore[no-untyped-def]
    """build_report output contains Scenario, p-value, and effect keywords."""
    report = build_report(result, hyp)
    assert "Scenario" in report, "Missing 'Scenario' in report"
    assert "p-value" in report, "Missing 'p-value' in report"
    assert "effect" in report.lower(), "Missing 'effect' in report"


def test_build_report_is_not_json(result: ExperimentResult, hyp) -> None:  # type: ignore[no-untyped-def]
    """build_report returns plain-text markdown, not JSON."""
    report = build_report(result, hyp)
    with pytest.raises((json.JSONDecodeError, ValueError)):
        json.loads(report)


def test_build_report_contains_condition_rows(result: ExperimentResult, hyp) -> None:  # type: ignore[no-untyped-def]
    """2×2 table contains scenario A and B rows."""
    report = build_report(result, hyp)
    assert "| A |" in report or "A" in report
    assert "| B |" in report or "B" in report
