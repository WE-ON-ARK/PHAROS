"""Pure image-processing estimators for the camera input path.

These functions turn a single webcam frame (numpy BGR or grayscale array) into
the same three quantities the synthetic simulator produces — a gaze fixation
point, a pupil diameter, and a smoke-scattering proxy — so the real camera can
drive the unchanged PharosPipeline through the existing source adapters.

Everything here is deterministic and frame-pure: no capture device, no global
state.  The thin capture/loop layer lives in vision/camera.py and vision/runner.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import cv2
import numpy as np
import numpy.typing as npt

Frame = npt.NDArray[np.uint8]

# Pupil threshold as a fraction up the ROI's dark→light dynamic range.
_PUPIL_DARK_FRACTION: float = 0.35
# Reject blobs covering more than this share of the ROI as non-pupil.
_PUPIL_MAX_AREA_FRACTION: float = 0.6
# Human palpebral-fissure width (mm); used as a distance-invariant px→mm scale.
_EYE_WIDTH_MM: float = 24.0
# Min filter kernel for the dark-channel haze estimate.
_DARK_CHANNEL_KERNEL: int = 7


@dataclass(frozen=True)
class PupilBlob:
    """Pupil detection result within an eye ROI, in ROI-local pixel coordinates.

    center_xy    — (x, y) centroid of the dark pupil blob, ROI-local pixels
    diameter_px  — equivalent-circle diameter of the blob, pixels
    """

    center_xy: tuple[float, float]
    diameter_px: float


@dataclass(frozen=True)
class EyeReading:
    """A single detected eye with its pupil, in full-frame pixel coordinates.

    bbox        — (x, y, w, h) eye region in the full frame
    pupil_xy    — (x, y) pupil centroid in full-frame pixels
    diameter_px — pupil diameter in pixels
    """

    bbox: tuple[int, int, int, int]
    pupil_xy: tuple[float, float]
    diameter_px: float


@dataclass(frozen=True)
class GazeMapping:
    """Maps normalised in-eye pupil offset to a screen fixation point.

    gain   — amplifies small iris excursions so they span the screen
    mirror — webcam frames are mirrored; flip x so left-look maps to screen-left
    """

    gain: float = 1.6
    mirror: bool = True


def to_grayscale(frame: Frame) -> Frame:
    """Return a single-channel uint8 image; pass through if already grayscale."""
    if frame.ndim == 2:
        return frame
    return cast(Frame, cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))


def detect_pupil(eye_gray: Frame) -> PupilBlob | None:
    """Locate the pupil as the largest dark blob in a grayscale eye ROI.

    Returns None when the ROI is empty or no dark region forms a usable contour.
    """
    if eye_gray.size == 0:
        return None

    blur = cv2.GaussianBlur(eye_gray, (5, 5), 0)
    lo, hi = float(blur.min()), float(blur.max())
    if hi <= lo:
        return None
    # Threshold relative to the ROI's own range so it adapts to lighting and
    # never collapses onto the background value (a fixed percentile would).
    threshold = lo + _PUPIL_DARK_FRACTION * (hi - lo)
    _, binary = cv2.threshold(blur, threshold, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    area = float(cv2.contourArea(largest))
    if area <= 0.0 or area > _PUPIL_MAX_AREA_FRACTION * float(eye_gray.size):
        return None

    moments = cv2.moments(largest)
    if moments["m00"] == 0.0:
        return None

    cx = float(moments["m10"] / moments["m00"])
    cy = float(moments["m01"] / moments["m00"])
    diameter = 2.0 * float(np.sqrt(area / np.pi))
    return PupilBlob(center_xy=(cx, cy), diameter_px=diameter)


def detect_eyes(
    gray: Frame,
    face_cascade: cv2.CascadeClassifier,
    eye_cascade: cv2.CascadeClassifier,
) -> list[EyeReading]:
    """Detect faces, then eyes within each face, then the pupil within each eye.

    Restricting eye search to the upper half of each face suppresses the common
    nostril / mouth false positives the Haar eye cascade produces.
    """
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
    readings: list[EyeReading] = []

    for fx, fy, fw, fh in faces:
        upper = gray[fy : fy + fh // 2, fx : fx + fw]
        eyes = eye_cascade.detectMultiScale(upper, scaleFactor=1.1, minNeighbors=6)
        for ex, ey, ew, eh in eyes:
            abs_x, abs_y = fx + int(ex), fy + int(ey)
            eye_roi = gray[abs_y : abs_y + eh, abs_x : abs_x + ew]
            blob = detect_pupil(eye_roi)
            if blob is None:
                continue
            readings.append(
                EyeReading(
                    bbox=(abs_x, abs_y, int(ew), int(eh)),
                    pupil_xy=(abs_x + blob.center_xy[0], abs_y + blob.center_xy[1]),
                    diameter_px=blob.diameter_px,
                )
            )
    return readings


def pupil_diameter_mm(diameter_px: float, eye_width_px: float) -> float:
    """Convert pupil diameter from pixels to millimetres.

    Scales by the eye ROI width so the estimate is invariant to how close the
    operator's face sits to the camera — only the pupil-to-eye ratio matters.
    """
    if eye_width_px <= 0.0:
        return 0.0
    px_per_mm = eye_width_px / _EYE_WIDTH_MM
    return diameter_px / px_per_mm


def gaze_point(
    eyes: list[EyeReading],
    screen_size: tuple[int, int],
    mapping: GazeMapping | None = None,
) -> tuple[float, float] | None:
    """Map averaged in-eye pupil offset to a screen-pixel fixation point.

    Returns None when no eyes are supplied.  The mapping is intentionally
    uncalibrated: a per-eye offset of 0 maps to screen centre, and `gain`
    controls how far a normalised excursion of ±1 reaches toward the edges.
    """
    if not eyes:
        return None

    m = mapping if mapping is not None else GazeMapping()
    width, height = screen_size

    nxs: list[float] = []
    nys: list[float] = []
    for eye in eyes:
        ex, ey, ew, eh = eye.bbox
        if ew <= 0 or eh <= 0:
            continue
        nxs.append((eye.pupil_xy[0] - (ex + ew / 2.0)) / (ew / 2.0))
        nys.append((eye.pupil_xy[1] - (ey + eh / 2.0)) / (eh / 2.0))
    if not nxs:
        return None

    nx = float(np.clip(np.mean(nxs) * m.gain, -1.0, 1.0))
    ny = float(np.clip(np.mean(nys) * m.gain, -1.0, 1.0))
    if m.mirror:
        nx = -nx

    sx = (0.5 + 0.5 * nx) * (width - 1)
    sy = (0.5 + 0.5 * ny) * (height - 1)
    return float(sx), float(sy)


def estimate_haze(frame: Frame) -> float:
    """Estimate a smoke-scattering proxy in [0, 1] via the dark-channel prior.

    Smoke lifts the per-pixel minimum-channel floor (airlight scattering), so a
    bright dark-channel signals haze.  This stands in for the Tyndall sensor's
    scattering intensity when only a scene camera is available.
    """
    if frame.size == 0:
        return 0.0

    min_channel = frame if frame.ndim == 2 else frame.min(axis=2)

    kernel = np.ones((_DARK_CHANNEL_KERNEL, _DARK_CHANNEL_KERNEL), dtype=np.uint8)
    dark_channel = cv2.erode(min_channel, kernel)
    return float(np.clip(dark_channel.mean() / 255.0, 0.0, 1.0))
