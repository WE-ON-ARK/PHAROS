"""IO adapter interfaces and replay implementations for gaze and pupil sources.

Design mirrors SensingSource in sensing/core.py so all three stream adapters
share the same read() / has_data() contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

# ── Gaze ─────────────────────────────────────────────────────────────────────


@dataclass
class GazeSample:
    """A single timestamped fixation reading.

    timestamp — seconds (monotonically increasing)
    fixation  — (x, y) screen-pixel coordinates
    """

    timestamp: float
    fixation: tuple[float, float]


class GazeSource(ABC):
    """Abstract adapter for a gaze fixation stream."""

    @abstractmethod
    def read(self) -> GazeSample:
        """Return the next fixation sample. Raises StopIteration when exhausted."""

    @abstractmethod
    def has_data(self) -> bool:
        """Return True if at least one sample remains."""


class ReplayGazeSource(GazeSource):
    """Replay adapter backed by pre-recorded numpy arrays.

    timestamps — shape (N,) float64, seconds
    fixations  — shape (N, 2) float64, (x, y) pixels per row
    """

    def __init__(
        self,
        timestamps: npt.NDArray[np.float64],
        fixations: npt.NDArray[np.float64],
    ) -> None:
        self._timestamps = timestamps
        self._fixations = fixations
        self._idx: int = 0

    def has_data(self) -> bool:
        """Return True if unread samples remain."""
        return self._idx < len(self._timestamps)

    def read(self) -> GazeSample:
        """Return next sample; raise StopIteration when exhausted."""
        if not self.has_data():
            raise StopIteration
        sample = GazeSample(
            timestamp=float(self._timestamps[self._idx]),
            fixation=(
                float(self._fixations[self._idx, 0]),
                float(self._fixations[self._idx, 1]),
            ),
        )
        self._idx += 1
        return sample


# ── Pupil ─────────────────────────────────────────────────────────────────────


@dataclass
class PupilSample:
    """A single timestamped pupil-diameter reading.

    timestamp   — seconds (monotonically increasing)
    diameter_mm — measured pupil diameter in millimetres
    """

    timestamp: float
    diameter_mm: float


class PupilSource(ABC):
    """Abstract adapter for a pupil-diameter stream."""

    @abstractmethod
    def read(self) -> PupilSample:
        """Return the next pupil sample. Raises StopIteration when exhausted."""

    @abstractmethod
    def has_data(self) -> bool:
        """Return True if at least one sample remains."""


class ReplayPupilSource(PupilSource):
    """Replay adapter backed by pre-recorded numpy arrays.

    timestamps — shape (N,) float64, seconds
    diameters  — shape (N,) float64, millimetres
    """

    def __init__(
        self,
        timestamps: npt.NDArray[np.float64],
        diameters: npt.NDArray[np.float64],
    ) -> None:
        self._timestamps = timestamps
        self._diameters = diameters
        self._idx: int = 0

    def has_data(self) -> bool:
        """Return True if unread samples remain."""
        return self._idx < len(self._timestamps)

    def read(self) -> PupilSample:
        """Return next sample; raise StopIteration when exhausted."""
        if not self.has_data():
            raise StopIteration
        sample = PupilSample(
            timestamp=float(self._timestamps[self._idx]),
            diameter_mm=float(self._diameters[self._idx]),
        )
        self._idx += 1
        return sample
