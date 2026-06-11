"""Boundary-case tests for stationary (Hs) and transition (Ht) gaze entropy."""

from __future__ import annotations

import math

import numpy as np
import pytest

from pharos.entropy import stationary_entropy, transition_entropy

SCREEN = (400, 300)
BIN = 100

# 400×300 / 100 → 4×3 = 12 total bins; Hmax_s = log2(12)
_TOTAL_BINS = 12
_H_MAX_S = math.log2(_TOTAL_BINS)


def _uniform_fixations() -> np.ndarray:
    """One fixation at the centre of every AOI bin (12 bins, 1 point each)."""
    centers = [
        (float(bx * BIN + BIN // 2), float(by * BIN + BIN // 2))
        for bx in range(4)
        for by in range(3)
    ]
    return np.array(centers, dtype=np.float64)


# ── Stationary entropy (Hs) ───────────────────────────────────────────────────


def test_hs_single_bin_is_zero() -> None:
    """All fixations map to one bin → Hs = 0."""
    fixations = np.full((20, 2), [50.0, 50.0], dtype=np.float64)
    hs = stationary_entropy(fixations, BIN, SCREEN)
    assert hs == pytest.approx(0.0)
    print(f"Hs (single bin): {hs}")


def test_hs_uniform_normalized_is_one() -> None:
    """Fixations spread uniformly over all 12 bins → normalized Hs = 1.0."""
    fixations = _uniform_fixations()
    hs_norm = stationary_entropy(fixations, BIN, SCREEN, normalize=True)
    assert hs_norm == pytest.approx(1.0, abs=1e-9)
    print(f"Hs normalized (uniform 12 bins): {hs_norm:.6f}")


def test_hs_normalized_range() -> None:
    """Normalized Hs must be in [0, 1] for arbitrary inputs."""
    rng = np.random.default_rng(42)
    fixations = rng.uniform([0, 0], [400, 300], size=(300, 2))
    hs_norm = stationary_entropy(fixations, BIN, SCREEN, normalize=True)
    assert 0.0 <= hs_norm <= 1.0
    print(f"Hs normalized (random 300pts): {hs_norm:.4f}")


def test_hs_single_fixation_is_zero() -> None:
    fixations = np.array([[50.0, 50.0]], dtype=np.float64)
    hs = stationary_entropy(fixations, BIN, SCREEN)
    assert hs == pytest.approx(0.0)
    print(f"Hs (1 fixation): {hs}")


# ── Transition entropy (Ht) ───────────────────────────────────────────────────


def test_ht_deterministic_alternation_is_zero() -> None:
    """A→B→A→B (deterministic alternation) → Ht = 0."""
    # bin A: centre (50, 50),  bin B: centre (150, 50)
    pts = np.tile([[50.0, 50.0], [150.0, 50.0]], (10, 1)).astype(np.float64)
    ht = transition_entropy(pts, BIN, SCREEN)
    assert ht == pytest.approx(0.0, abs=1e-9)
    print(f"Ht (A→B→A→B deterministic): {ht}")


def test_ht_random_transitions_are_high() -> None:
    """Pseudo-random fixations across 4 bins → Ht > Hmax/2."""
    # 4 bins in a 2×2 patch; cycling, then shuffled
    pts = np.tile(
        [[50.0, 50.0], [150.0, 50.0], [50.0, 150.0], [150.0, 150.0]], (25, 1)
    ).astype(np.float64)
    rng = np.random.default_rng(0)
    rng.shuffle(pts)
    ht = transition_entropy(pts, BIN, SCREEN)
    h_max = math.log2(3)  # log2(4 states - 1)
    assert ht > h_max / 2
    print(f"Ht (random 4-bin): {ht:.4f}  (Hmax={h_max:.4f})")


def test_ht_normalized_range() -> None:
    """Normalized Ht must be in [0, 1] for arbitrary inputs."""
    rng = np.random.default_rng(99)
    fixations = rng.uniform([0, 0], [400, 300], size=(300, 2))
    ht_norm = transition_entropy(fixations, BIN, SCREEN, normalize=True)
    assert 0.0 <= ht_norm <= 1.0
    print(f"Ht normalized (random 300pts): {ht_norm:.4f}")


def test_ht_single_fixation_is_zero() -> None:
    fixations = np.array([[50.0, 50.0]], dtype=np.float64)
    ht = transition_entropy(fixations, BIN, SCREEN)
    assert ht == pytest.approx(0.0)
    print(f"Ht (1 fixation): {ht}")
