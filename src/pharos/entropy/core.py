"""Gaze entropy computation: stationary (Hs) and transition (Ht)."""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt


def _fixations_to_bin_ids(
    fixations: npt.NDArray[np.float64],
    bin_size: int,
    screen_size: tuple[int, int],
) -> npt.NDArray[np.intp]:
    """Map (x, y) pixel coordinates to flat AOI bin indices.

    Coordinates are clamped to screen bounds before discretisation.
    flat_id = bin_x * n_bins_y + bin_y, where bin_x = floor(x / bin_size).
    """
    width, height = screen_size
    n_bins_y: int = math.ceil(height / bin_size)

    x_clipped: npt.NDArray[np.float64] = np.clip(
        fixations[:, 0], 0.0, float(width - 1)
    )
    y_clipped: npt.NDArray[np.float64] = np.clip(
        fixations[:, 1], 0.0, float(height - 1)
    )

    bin_x: npt.NDArray[np.intp] = (x_clipped // bin_size).astype(np.intp)
    bin_y: npt.NDArray[np.intp] = (y_clipped // bin_size).astype(np.intp)

    return (bin_x * n_bins_y + bin_y).astype(np.intp)


def stationary_entropy(
    fixations: npt.NDArray[np.float64],
    bin_size: int,
    screen_size: tuple[int, int],
    normalize: bool = False,
) -> float:
    """Shannon entropy of fixation distribution over AOI grid (Hs).

    Hs = -Σ p(i) log₂ p(i), where p(i) = fixations in bin i / total fixations.
    Unoccupied bins contribute 0 (0 log 0 ≡ 0 by convention).
    normalize=True divides by log₂(total_bins) → result in [0, 1].
    """
    if len(fixations) == 0:
        return 0.0

    bin_ids = _fixations_to_bin_ids(fixations, bin_size, screen_size)
    _, counts = np.unique(bin_ids, return_counts=True)

    p: npt.NDArray[np.float64] = counts.astype(np.float64) / float(len(fixations))
    hs = float(-np.sum(p * np.log2(p)))

    if normalize:
        width, height = screen_size
        n_bins_x = math.ceil(width / bin_size)
        n_bins_y = math.ceil(height / bin_size)
        total_bins = n_bins_x * n_bins_y
        h_max = math.log2(total_bins) if total_bins > 1 else 1.0
        hs = hs / h_max

    return hs


def transition_entropy(
    fixations: npt.NDArray[np.float64],
    bin_size: int,
    screen_size: tuple[int, int],
    normalize: bool = False,
) -> float:
    """First-order Markov conditional entropy of fixation transitions (Ht).

    Ht = -Σ_i p(i) Σ_{j≠i} p(j|i) log₂ p(j|i).
    Self-transitions (same bin → same bin) are excluded from counting.
    normalize=True divides by log₂(n_occupied_states − 1) → result in [0, 1].
    Returns 0.0 when fewer than 2 fixations exist or no inter-bin transitions occur.
    """
    if len(fixations) < 2:
        return 0.0

    bin_ids = _fixations_to_bin_ids(fixations, bin_size, screen_size)

    src = bin_ids[:-1]
    dst = bin_ids[1:]

    mask: npt.NDArray[np.bool_] = src != dst
    src_valid: npt.NDArray[np.intp] = src[mask]
    dst_valid: npt.NDArray[np.intp] = dst[mask]

    if len(src_valid) == 0:
        return 0.0

    all_states: npt.NDArray[np.intp] = np.unique(
        np.concatenate([src_valid, dst_valid])
    ).astype(np.intp)
    n_states = int(all_states.shape[0])

    # compact-index transitions with searchsorted (all_states is sorted)
    si: npt.NDArray[np.intp] = np.searchsorted(all_states, src_valid).astype(np.intp)
    di: npt.NDArray[np.intp] = np.searchsorted(all_states, dst_valid).astype(np.intp)

    # build transition count matrix via bincount on flat indices
    flat_idx: npt.NDArray[np.intp] = (si * n_states + di).astype(np.intp)
    trans_count: npt.NDArray[np.float64] = (
        np.bincount(flat_idx, minlength=n_states * n_states)
        .reshape(n_states, n_states)
        .astype(np.float64)
    )

    # marginal p(i) from the full fixation sequence
    unique_all, counts_all = np.unique(bin_ids, return_counts=True)
    state_idx: npt.NDArray[np.intp] = np.searchsorted(unique_all, all_states).astype(
        np.intp
    )
    p_marginal: npt.NDArray[np.float64] = counts_all[state_idx].astype(np.float64)
    p_marginal = p_marginal / p_marginal.sum()

    # row-normalise → p(j|i); rows with no outgoing transitions get 0 entropy
    row_sums_1d: npt.NDArray[np.float64] = trans_count.sum(axis=1)
    row_sums_2d: npt.NDArray[np.float64] = row_sums_1d[:, np.newaxis]
    safe_sums: npt.NDArray[np.float64] = np.where(row_sums_2d > 0.0, row_sums_2d, 1.0)
    p_cond: npt.NDArray[np.float64] = trans_count / safe_sums

    # np.where evaluates both branches; errstate suppresses the expected log(0) warning
    with np.errstate(divide="ignore", invalid="ignore"):
        log_p: npt.NDArray[np.float64] = np.where(
            p_cond > 0.0, np.log2(p_cond), 0.0
        )
    h_per_state: npt.NDArray[np.float64] = -np.sum(p_cond * log_p, axis=1)
    h_per_state = np.where(row_sums_1d > 0.0, h_per_state, 0.0)

    ht = float(np.dot(p_marginal, h_per_state))

    if normalize:
        # with ≤2 states and no self-transitions, transition is deterministic → Ht = 0
        if n_states <= 2:
            return 0.0
        h_max = math.log2(n_states - 1)
        ht = ht / h_max

    return ht
