"""Tyndall-scattering-based smoke sensing: adapter interface and calibration."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

_SCALE_EPSILON = 1e-9  # guards against zero-scale in calibration


@dataclass
class ScatteringSample:
    """A single reading from a scattering light sensor.

    timestamp  : seconds (monotonically increasing)
    intensity  : raw scattering intensity in arbitrary sensor units (≥ 0)
    """

    timestamp: float
    intensity: float


@dataclass
class CalibrationParams:
    """Parameters that map raw scattering intensity to smoke density and visibility.

    Density model   : density = clip((intensity - bg) / (max - bg), 0, 1)
    Visibility model: visibility = max_visibility × exp(−extinction_coeff × density)
      — Koschmieder-style exponential decay; visibility is always > 0.

    Defaults:
        bg_scattering    = 0.0   arb. units  — ambient reading with no smoke
        max_scattering   = 1.0   arb. units  — intensity at density = 1
        max_visibility   = 30.0  m           — visibility in clear air
        extinction_coeff = 3.0               — higher → sharper drop in visibility
    """

    bg_scattering: float = 0.0
    max_scattering: float = 1.0
    max_visibility: float = 30.0
    extinction_coeff: float = 3.0


class SensingSource(ABC):
    """Abstract adapter for a scattering-light sensor stream.

    Hardware-specific implementations (real sensor, network feed, …) live
    behind this interface so the pipeline never imports hardware code.
    """

    @abstractmethod
    def read(self) -> ScatteringSample:
        """Return the next sample.  Raises StopIteration when exhausted."""

    @abstractmethod
    def has_data(self) -> bool:
        """Return True while samples remain."""


class ReplaySensingSource(SensingSource):
    """Replay a pre-recorded (or synthetic) scattering stream from arrays.

    Iterates once through the arrays in order; subsequent calls to read()
    after exhaustion raise StopIteration.
    """

    def __init__(
        self,
        timestamps: npt.NDArray[np.float64],
        intensities: npt.NDArray[np.float64],
    ) -> None:
        if len(timestamps) != len(intensities):
            raise ValueError(
                f"timestamps and intensities must have equal length, "
                f"got {len(timestamps)} vs {len(intensities)}"
            )
        self._timestamps = timestamps
        self._intensities = intensities
        self._idx: int = 0

    def has_data(self) -> bool:
        """Return True while unread samples remain."""
        return self._idx < len(self._timestamps)

    def read(self) -> ScatteringSample:
        """Return the next ScatteringSample and advance the internal cursor."""
        if not self.has_data():
            raise StopIteration("ReplaySensingSource is exhausted")
        sample = ScatteringSample(
            timestamp=float(self._timestamps[self._idx]),
            intensity=float(self._intensities[self._idx]),
        )
        self._idx += 1
        return sample


def scattering_to_density(
    intensity: float,
    params: CalibrationParams | None = None,
) -> float:
    """Convert raw scattering intensity to relative smoke particle density [0, 1].

    Uses a linear model with configurable background and saturation points.
    Values outside the calibrated range are clamped to [0, 1].
    """
    p = params if params is not None else CalibrationParams()
    scale = max(p.max_scattering - p.bg_scattering, _SCALE_EPSILON)
    density = (intensity - p.bg_scattering) / scale
    return float(max(0.0, min(1.0, density)))


def density_to_visibility(
    density: float,
    params: CalibrationParams | None = None,
) -> float:
    """Convert smoke density [0, 1] to estimated line-of-sight visibility [metres].

    Koschmieder-style exponential decay:  V = V_max × exp(−k × density).
    Visibility is strictly positive (approaches V_max × e^−k at density = 1).
    """
    p = params if params is not None else CalibrationParams()
    return p.max_visibility * math.exp(-p.extinction_coeff * density)
