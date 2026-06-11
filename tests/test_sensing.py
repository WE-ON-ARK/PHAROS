"""Monotonicity, range, and adapter-swap tests for the sensing module."""

from __future__ import annotations

import math

import numpy as np
import pytest

from pharos.sensing import (
    CalibrationParams,
    ReplaySensingSource,
    ScatteringSample,
    SensingSource,
    density_to_visibility,
    scattering_to_density,
)

_P = CalibrationParams()  # default params


# ── scattering_to_density ─────────────────────────────────────────────────────


def test_density_zero_at_background() -> None:
    """intensity = bg → density = 0.0."""
    assert scattering_to_density(0.0) == pytest.approx(0.0)
    print(f"density(0.0) = {scattering_to_density(0.0)}")


def test_density_one_at_max() -> None:
    """intensity = max_scattering → density = 1.0."""
    assert scattering_to_density(1.0) == pytest.approx(1.0)
    print(f"density(1.0) = {scattering_to_density(1.0)}")


def test_density_monotone_increasing() -> None:
    """Higher scattering → strictly higher density."""
    intensities = np.linspace(0.0, 1.0, 10)
    densities = [scattering_to_density(float(i)) for i in intensities]
    print("\n  intensity → density:")
    for i_val, d_val in zip(intensities, densities, strict=False):
        print(f"    {i_val:.2f} → {d_val:.4f}")
    for a, b in zip(densities, densities[1:], strict=False):
        assert b >= a, f"density not monotone: {a} followed by {b}"


def test_density_clamps_below_zero() -> None:
    """Intensity below background → density = 0 (not negative)."""
    assert scattering_to_density(-5.0) == pytest.approx(0.0)


def test_density_clamps_above_one() -> None:
    """Intensity above max_scattering → density = 1 (not > 1)."""
    assert scattering_to_density(999.0) == pytest.approx(1.0)


# ── density_to_visibility ─────────────────────────────────────────────────────


def test_visibility_max_at_zero_density() -> None:
    """density = 0 → visibility = max_visibility."""
    vis = density_to_visibility(0.0)
    assert vis == pytest.approx(_P.max_visibility)
    print(f"\nvisibility(density=0.0) = {vis:.2f} m")


def test_visibility_monotone_decreasing() -> None:
    """Higher density → strictly lower visibility."""
    densities = np.linspace(0.0, 1.0, 10)
    visibilities = [density_to_visibility(float(d)) for d in densities]
    print("\n  density → visibility (m):")
    for d_val, v_val in zip(densities, visibilities, strict=False):
        print(f"    {d_val:.2f} → {v_val:.3f}")
    for a, b in zip(visibilities, visibilities[1:], strict=False):
        assert b <= a, f"visibility not monotone: {a} followed by {b}"


def test_visibility_always_positive() -> None:
    """Visibility must be strictly positive for any density in [0, 1]."""
    for d in np.linspace(0.0, 1.0, 20):
        v = density_to_visibility(float(d))
        assert v > 0.0, f"visibility {v} ≤ 0 at density {d}"


def test_visibility_range() -> None:
    """visibility at density=1 equals max_visibility × exp(−k)."""
    expected = _P.max_visibility * math.exp(-_P.extinction_coeff)
    assert density_to_visibility(1.0) == pytest.approx(expected)
    print(f"\nvisibility(density=1.0) = {density_to_visibility(1.0):.3f} m "
          f"(max={_P.max_visibility}, k={_P.extinction_coeff})")


# ── end-to-end: scattering → density → visibility ────────────────────────────


def test_full_pipeline_monotone() -> None:
    """Scattering↑ → density↑ → visibility↓ across 10 steps."""
    intensities = np.linspace(0.0, 1.0, 10)
    visibilities = [
        density_to_visibility(scattering_to_density(float(i))) for i in intensities
    ]
    print("\n  intensity → density → visibility:")
    for i_val, v_val in zip(intensities, visibilities, strict=False):
        d = scattering_to_density(float(i_val))
        print(f"    scatter={i_val:.2f}  density={d:.3f}  vis={v_val:.2f}m")
    for a, b in zip(visibilities, visibilities[1:], strict=False):
        assert b <= a


# ── ReplaySensingSource ───────────────────────────────────────────────────────


def test_replay_streams_all_samples() -> None:
    """ReplaySensingSource yields every sample in order."""
    ts = np.array([0.0, 1.0, 2.0])
    intensities = np.array([0.1, 0.5, 0.9])
    src = ReplaySensingSource(ts, intensities)
    samples: list[ScatteringSample] = []
    while src.has_data():
        samples.append(src.read())
    assert len(samples) == 3
    assert samples[1].timestamp == pytest.approx(1.0)
    assert samples[2].intensity == pytest.approx(0.9)
    print(f"\nReplayed {len(samples)} samples, last={samples[-1]}")


def test_replay_exhausted_has_data_false() -> None:
    """After all samples consumed, has_data() returns False."""
    src = ReplaySensingSource(np.array([0.0]), np.array([0.5]))
    src.read()
    assert not src.has_data()


def test_replay_read_when_exhausted_raises() -> None:
    """read() on an exhausted source raises StopIteration."""
    src = ReplaySensingSource(np.array([0.0]), np.array([0.5]))
    src.read()
    with pytest.raises(StopIteration):
        src.read()


# ── adapter swap (dependency-injection) ───────────────────────────────────────


class _ConstantSensingSource(SensingSource):
    """Fake source that always returns the same intensity — used for DI tests."""

    def __init__(self, intensity: float, count: int) -> None:
        self._intensity = intensity
        self._remaining = count

    def has_data(self) -> bool:
        return self._remaining > 0

    def read(self) -> ScatteringSample:
        if not self.has_data():
            raise StopIteration
        self._remaining -= 1
        return ScatteringSample(timestamp=0.0, intensity=self._intensity)


def test_adapter_swap() -> None:
    """A custom SensingSource implementation works with calibration functions."""
    fake: SensingSource = _ConstantSensingSource(intensity=0.75, count=3)
    densities: list[float] = []
    while fake.has_data():
        sample = fake.read()
        densities.append(scattering_to_density(sample.intensity))
    assert len(densities) == 3
    assert all(d == pytest.approx(0.75) for d in densities)
    print(f"\nAdapter-swap densities: {densities}")
