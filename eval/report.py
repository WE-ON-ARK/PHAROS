"""Markdown report builder for 2×2 experiment results."""

from __future__ import annotations

from eval.runner import ExperimentResult
from eval.stats import HypothesisResults, HypothesisTest


def _rejected_str(h: HypothesisTest) -> str:
    return "YES ✓" if h.rejected else "NO"


def build_report(result: ExperimentResult, hyp: HypothesisResults) -> str:
    """Return a markdown-formatted experiment report.

    Sections: 2×2 condition table, hypothesis table, conclusion paragraph.
    """
    lines: list[str] = []

    lines.append("# PHAROS 2×2 Experiment Report\n")

    # ── 2×2 aggregate table ───────────────────────────────────────────────────
    lines.append("## Condition Aggregates (mean over post-warmup frames)\n")
    lines.append(
        "| Scenario | Smoke | mean Hs | mean Ht | mean CLI | mean Visibility |"
    )
    lines.append("|----------|-------|--------:|--------:|---------:|----------------:|")
    for c in result.conditions:
        smoke_label = "high" if c.smoke_density >= 0.5 else "low"
        lines.append(
            f"| {c.scenario.upper()} | {smoke_label}"
            f" | {c.mean_hs:.4f}"
            f" | {c.mean_ht:.4f}"
            f" | {c.mean_cli:.4f}"
            f" | {c.mean_visibility:.2f} m |"
        )
    lines.append("")

    # ── hypothesis table ──────────────────────────────────────────────────────
    lines.append("## Hypothesis Tests\n")
    lines.append(
        "| Hypothesis | U statistic | p-value | effect (r) | Rejected |"
    )
    lines.append("|------------|------------:|--------:|-----------:|----------|")
    for h in (hyp.h1_ht, hyp.h2_hs, hyp.h3_cli, hyp.h4_smoke_ht):
        lines.append(
            f"| {h.name}"
            f" | {h.statistic:.1f}"
            f" | {h.p_value:.4f}"
            f" | {h.effect_size:+.4f}"
            f" | {_rejected_str(h)} |"
        )
    lines.append("")

    # ── conclusion ────────────────────────────────────────────────────────────
    lines.append("## Conclusion\n")

    any_rejected = any(
        h.rejected for h in (hyp.h1_ht, hyp.h2_hs, hyp.h3_cli)
    )
    if any_rejected:
        supported = [
            h.name.split(":")[0]
            for h in (hyp.h1_ht, hyp.h2_hs, hyp.h3_cli)
            if h.rejected
        ]
        lines.append(
            f"At α = {hyp.alpha}, the following primary hypotheses were **rejected** "
            f"(i.e., the alternative is supported): {', '.join(supported)}. "
            "The HUD-guided scenario (B) shows statistically lower gaze entropy and "
            "cognitive load than the unguided scenario (A)."
        )
    else:
        lines.append(
            f"At α = {hyp.alpha}, none of the primary hypotheses (H1–H3) were rejected. "
            "The data do not provide sufficient evidence that UI guidance reduces "
            "gaze entropy or cognitive load in this synthetic experiment."
        )

    smoke_desc = "supports" if hyp.h4_smoke_ht.rejected else "does not support"
    lines.append(
        f"\nExploratory hypothesis H4 (smoke increases transition entropy) "
        f"{smoke_desc} rejection "
        f"(p = {hyp.h4_smoke_ht.p_value:.4f})."
    )

    return "\n".join(lines) + "\n"
