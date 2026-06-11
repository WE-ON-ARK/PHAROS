"""Boundary-case tests for pupil-based cognitive load estimation."""

from __future__ import annotations

import numpy as np
import pytest

from pharos.cogload import (
    LoadWeights,
    cognitive_load_index,
    extract_features,
    preprocess_pupil,
)

# ── helpers ───────────────────────────────────────────────────────────────────

_BASELINE = (0.0, 2.0)  # seconds 0–2 are baseline, 2+ are task


def _signal(
    baseline_val: float,
    task_val: float,
    n_baseline: int = 20,
    n_task: int = 40,
    peak_offset: int = 20,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a synthetic (timestamps, diameters) pair.

    Baseline is flat at baseline_val.  Task period ramps from baseline_val
    to task_val at sample peak_offset, then holds.
    """
    t_baseline = np.linspace(0.0, 2.0, n_baseline, endpoint=False)
    t_task = np.linspace(2.0, 6.0, n_task)
    timestamps = np.concatenate([t_baseline, t_task]).astype(np.float64)

    d_baseline = np.full(n_baseline, baseline_val)
    d_task = np.concatenate([
        np.linspace(baseline_val, task_val, peak_offset),
        np.full(n_task - peak_offset, task_val),
    ])
    diameters = np.concatenate([d_baseline, d_task]).astype(np.float64)
    return timestamps, diameters


def _cli(baseline_val: float, task_val: float, **kw: int) -> float:
    ts, ds = _signal(baseline_val, task_val, **kw)
    clean = preprocess_pupil(ts, ds)
    feat = extract_features(ts, clean, _BASELINE)
    idx = cognitive_load_index(feat)
    print(
        f"  baseline={baseline_val}, task={task_val} → "
        f"pct_chg={feat.percent_change:.1f}%, "
        f"peak_dil={feat.peak_dilation:.3f}, "
        f"peak_lat={feat.peak_latency:.2f}s, "
        f"CLI={idx:.4f}"
    )
    return idx


# ── preprocess_pupil tests ────────────────────────────────────────────────────


def test_preprocess_no_blinks_unchanged() -> None:
    """Clean signal passes through unchanged."""
    _, diameters = _signal(4.0, 5.0)
    ts = np.linspace(0.0, 6.0, len(diameters))
    out = preprocess_pupil(ts, diameters)
    np.testing.assert_allclose(out, diameters)


def test_preprocess_removes_zero_spikes() -> None:
    """Zero-valued blink samples are replaced by interpolated values."""
    _, diameters = _signal(4.0, 4.0)  # flat signal
    ts = np.linspace(0.0, 6.0, len(diameters))
    blinky = diameters.copy()
    blinky[25:28] = 0.0  # inject 3 blink samples
    out = preprocess_pupil(ts, blinky)
    assert (out > 0.0).all(), "All values should be positive after blink removal"
    np.testing.assert_allclose(out[25:28], 4.0, atol=0.1)


# ── cognitive_load_index boundary cases ───────────────────────────────────────


def test_cli_flat_signal_is_near_zero() -> None:
    """Flat signal (no dilation) → CLI ≈ 0."""
    idx = _cli(4.0, 4.0)
    assert idx == pytest.approx(0.0, abs=1e-6)


def test_cli_large_dilation_is_high() -> None:
    """50% dilation after baseline → CLI > 0.7."""
    idx = _cli(4.0, 6.0)  # 50% increase (6/4 - 1 = 0.5)
    assert idx > 0.7


def test_cli_monotone_with_difficulty() -> None:
    """Increasing task dilation → strictly increasing CLI."""
    easy = _cli(4.0, 4.4)    # 10% dilation
    medium = _cli(4.0, 5.2)   # 30% dilation
    hard = _cli(4.0, 6.0)     # 50% dilation
    print(f"  easy={easy:.4f} < medium={medium:.4f} < hard={hard:.4f}")
    assert easy < medium < hard


def test_cli_blink_robust() -> None:
    """Blink spikes do not significantly shift CLI vs clean signal."""
    ts, diameters = _signal(4.0, 6.0)
    clean_feat = extract_features(ts, diameters, _BASELINE)
    cli_clean = cognitive_load_index(clean_feat)

    blinky = diameters.copy()
    blinky[30:33] = 0.0  # 3 blink samples mid-task
    preprocessed = preprocess_pupil(ts, blinky)
    blinky_feat = extract_features(ts, preprocessed, _BASELINE)
    cli_blinky = cognitive_load_index(blinky_feat)

    print(f"  CLI clean={cli_clean:.4f}, CLI blinky-preprocessed={cli_blinky:.4f}")
    assert abs(cli_clean - cli_blinky) < 0.05


def test_cli_range_is_zero_to_one() -> None:
    """CLI must be in [0, 1] for arbitrary positive feature values."""
    rng = np.random.default_rng(7)
    for _ in range(50):
        ts = np.sort(rng.uniform(0.0, 10.0, size=100))
        ds = rng.uniform(2.0, 8.0, size=100).astype(np.float64)
        clean = preprocess_pupil(ts, ds)
        feat = extract_features(ts, clean, (0.0, 2.0))
        idx = cognitive_load_index(feat)
        assert 0.0 <= idx <= 1.0


def test_cli_custom_weights() -> None:
    """Custom weights still produce a valid [0, 1] result."""
    ts, ds = _signal(4.0, 6.0)
    feat = extract_features(ts, preprocess_pupil(ts, ds), _BASELINE)
    w = LoadWeights(w_percent_change=1.0, w_peak_dilation=0.0, w_peak_latency=0.0)
    idx = cognitive_load_index(feat, weights=w)
    assert 0.0 <= idx <= 1.0
    print(f"  CLI (pct_change only): {idx:.4f}")
