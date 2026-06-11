"""Statistical analysis of experiment results: Mann-Whitney U tests."""

from __future__ import annotations

from dataclasses import dataclass

from scipy import stats  # type: ignore[import-untyped]

from eval.runner import ConditionResult, ExperimentResult

_ALPHA_DEFAULT: float = 0.05


@dataclass
class HypothesisTest:
    """Result of a single one-sided Mann-Whitney U hypothesis test.

    effect_size — rank-biserial correlation r = 1 − 2U / (n1 × n2)
    rejected    — True when p_value < alpha
    """

    name: str
    statistic: float
    p_value: float
    effect_size: float
    rejected: bool


@dataclass
class HypothesisResults:
    """All four hypothesis tests for the 2×2 experiment."""

    alpha: float
    h1_ht: HypothesisTest       # Ht(B) < Ht(A)
    h2_hs: HypothesisTest       # Hs(B) < Hs(A)
    h3_cli: HypothesisTest      # CLI(B) < CLI(A)
    h4_smoke_ht: HypothesisTest  # Ht(A,high) > Ht(A,low) — exploratory


def _group(
    conditions: list[ConditionResult],
    scenario: str,
    attr: str,
) -> list[float]:
    """Pool per-rep samples across smoke levels for one scenario."""
    values: list[float] = []
    for c in conditions:
        if c.scenario == scenario:
            values.extend(getattr(c, attr))
    return values


def _rank_biserial(u: float, n1: int, n2: int) -> float:
    """Rank-biserial correlation as effect size for Mann-Whitney U."""
    denom = n1 * n2
    return float(1.0 - 2.0 * u / denom) if denom > 0 else 0.0


def _test(
    name: str,
    x: list[float],
    y: list[float],
    alternative: str,
    alpha: float,
) -> HypothesisTest:
    """Run Mann-Whitney U and compute effect size."""
    res = stats.mannwhitneyu(x, y, alternative=alternative)
    r = _rank_biserial(float(res.statistic), len(x), len(y))
    return HypothesisTest(
        name=name,
        statistic=float(res.statistic),
        p_value=float(res.pvalue),
        effect_size=r,
        rejected=bool(res.pvalue < alpha),
    )


def analyse(
    result: ExperimentResult,
    alpha: float = _ALPHA_DEFAULT,
    warmup_frames: int = 25,  # kept for API compatibility; rep_* fields are already converged
) -> HypothesisResults:
    """Run all four Mann-Whitney U hypothesis tests on the experiment result.

    H1: Ht(B) < Ht(A)     — UI guidance reduces transition entropy
    H2: Hs(B) < Hs(A)     — UI guidance reduces stationary entropy
    H3: CLI(B) < CLI(A)   — UI guidance reduces cognitive load
    H4: Ht(A,hi) > Ht(A,lo) — smoke raises transition entropy (exploratory)

    Uses per-rep final-frame values (rep_ht, rep_hs, rep_cli) to avoid
    growing-window confounds in the rolling-buffer time series.
    """
    conds = result.conditions

    ht_a = _group(conds, "a", "rep_ht")
    ht_b = _group(conds, "b", "rep_ht")
    hs_a = _group(conds, "a", "rep_hs")
    hs_b = _group(conds, "b", "rep_hs")
    cli_a = _group(conds, "a", "rep_cli")
    cli_b = _group(conds, "b", "rep_cli")

    # H4: smoke effect within scenario A (lo vs hi)
    ht_a_lo = [v for c in conds if c.scenario == "a" and c.smoke_density < 0.5 for v in c.rep_ht]
    ht_a_hi = [v for c in conds if c.scenario == "a" and c.smoke_density >= 0.5 for v in c.rep_ht]

    return HypothesisResults(
        alpha=alpha,
        h1_ht=_test("H1: Ht(B) < Ht(A)", ht_b, ht_a, "less", alpha),
        h2_hs=_test("H2: Hs(B) < Hs(A)", hs_b, hs_a, "less", alpha),
        h3_cli=_test("H3: CLI(B) < CLI(A)", cli_b, cli_a, "less", alpha),
        h4_smoke_ht=_test("H4: Ht(A,hi) > Ht(A,lo)", ht_a_hi, ht_a_lo, "greater", alpha),
    )
