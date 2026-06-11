"""Pupil-diameter-based cognitive load estimation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


@dataclass
class PupilFeatures:
    """Pupil-derived features for cognitive load estimation.

    All values are computed relative to a pre-task baseline window.
    """

    percent_change: float
    """(task_median - baseline_median) / baseline_median × 100  [%]."""

    peak_dilation: float
    """task_max - baseline_median  [same units as input diameter]."""

    peak_latency: float
    """Seconds from baseline end to peak dilation in task period  [s]."""


@dataclass
class LoadWeights:
    """Feature weights and per-feature normalisation clip ranges.

    Default weights sum to 1.0.  max_* values define the saturation point —
    any feature value at or above max_* maps to 1.0 in the normalised space.

    Defaults:
        w_percent_change = 0.50  (most direct proxy for pupil load response)
        w_peak_dilation  = 0.30  (absolute peak magnitude)
        w_peak_latency   = 0.20  (timing of the peak)
        max_percent_change = 50.0  %
        max_peak_dilation  = 1.0   mm (or whatever unit is used)
        max_peak_latency   = 5.0   s
    """

    w_percent_change: float = 0.50
    w_peak_dilation: float = 0.30
    w_peak_latency: float = 0.20
    max_percent_change: float = 50.0
    max_peak_dilation: float = 1.0
    max_peak_latency: float = 5.0


def preprocess_pupil(
    timestamps: npt.NDArray[np.float64],
    diameters: npt.NDArray[np.float64],
    blink_threshold: float = 0.5,
) -> npt.NDArray[np.float64]:
    """Detect and linearly interpolate over blink / dropout artefacts.

    A sample is marked as a blink when its diameter is zero, negative, or
    below blink_threshold × median(valid samples).  The gap is filled with
    np.interp over sample indices so the surrounding valid signal is preserved.

    If no valid samples exist the input is returned unchanged.
    """
    if len(diameters) == 0:
        return diameters.copy()

    positive_vals = diameters[diameters > 0.0]
    if positive_vals.size == 0:
        return diameters.copy()

    global_median = float(np.median(positive_vals))
    blink_mask: npt.NDArray[np.bool_] = (diameters <= 0.0) | (
        diameters < blink_threshold * global_median
    )

    if not blink_mask.any():
        return diameters.copy()

    valid_idx: npt.NDArray[np.intp] = np.where(~blink_mask)[0].astype(np.intp)
    if valid_idx.size == 0:
        return diameters.copy()

    all_idx: npt.NDArray[np.intp] = np.arange(len(diameters), dtype=np.intp)
    interpolated: npt.NDArray[np.float64] = np.interp(
        all_idx.astype(np.float64),
        valid_idx.astype(np.float64),
        diameters[valid_idx],
    )
    return interpolated


def extract_features(
    timestamps: npt.NDArray[np.float64],
    diameters: npt.NDArray[np.float64],
    baseline_interval: tuple[float, float],
) -> PupilFeatures:
    """Extract pupil features relative to a baseline window.

    diameters should already be blink-preprocessed before calling this function.
    baseline_interval = (t_start, t_end) in the same time unit as timestamps.
    The task period is everything at timestamps >= t_end.
    """
    t0, t1 = baseline_interval

    baseline_mask: npt.NDArray[np.bool_] = (timestamps >= t0) & (timestamps < t1)
    task_mask: npt.NDArray[np.bool_] = timestamps >= t1

    baseline_vals = diameters[baseline_mask]
    task_vals = diameters[task_mask]
    task_times = timestamps[task_mask]

    if baseline_vals.size == 0 or task_vals.size == 0:
        return PupilFeatures(percent_change=0.0, peak_dilation=0.0, peak_latency=0.0)

    baseline_median = float(np.median(baseline_vals))

    # guard against zero-baseline to avoid division by zero
    if baseline_median == 0.0:
        return PupilFeatures(percent_change=0.0, peak_dilation=0.0, peak_latency=0.0)

    task_median = float(np.median(task_vals))
    percent_change = (task_median - baseline_median) / baseline_median * 100.0

    peak_idx = int(np.argmax(task_vals))
    peak_dilation = float(task_vals[peak_idx]) - baseline_median
    peak_latency = float(task_times[peak_idx]) - t1

    return PupilFeatures(
        percent_change=percent_change,
        peak_dilation=peak_dilation,
        peak_latency=peak_latency,
    )


def cognitive_load_index(
    features: PupilFeatures,
    weights: LoadWeights | None = None,
) -> float:
    """Combine pupil features into a single normalised cognitive load index.

    Each feature is clipped to [0, max_*] then divided by max_* → [0, 1].
    Negative feature values (pupil contraction) are clamped to 0.
    The weighted sum is divided by the total weight sum so the result stays
    in [0, 1] regardless of the chosen weights.
    """
    w = weights if weights is not None else LoadWeights()

    norm_pct = float(np.clip(features.percent_change / w.max_percent_change, 0.0, 1.0))
    norm_peak = float(np.clip(features.peak_dilation / w.max_peak_dilation, 0.0, 1.0))
    norm_lat = float(np.clip(features.peak_latency / w.max_peak_latency, 0.0, 1.0))

    w_sum = w.w_percent_change + w.w_peak_dilation + w.w_peak_latency
    raw = (
        w.w_percent_change * norm_pct
        + w.w_peak_dilation * norm_peak
        + w.w_peak_latency * norm_lat
    ) / w_sum

    return float(np.clip(raw, 0.0, 1.0))
