"""Render the live HUD overlay onto a camera frame.

Pure drawing: takes a processed :class:`VisionFrame` and a HudState dict and
returns a new BGR image of ``[ camera view | metrics panel ]``.  No capture, no
windowing — vision/runner.py owns the device loop and the imshow window.

Colours follow design.md: a true-black canvas, white display text, and the
cobalt-violet brand accent used sparingly for the primary load gauge.
"""

from __future__ import annotations

import base64
from typing import Any, cast

import cv2
import numpy as np

from .camera import VisionFrame
from .estimate import Frame

# design.md palette, expressed in BGR for OpenCV.
_CANVAS = (0, 0, 0)  # canvas-dark   #000000
_ON_DARK = (255, 255, 255)  # on-dark       #ffffff
_MUTE = (185, 185, 185)  # on-dark-mute  rgba(255,255,255,.72)
_STONE = (158, 150, 141)  # stone         #8d969e
_ELEVATED = (26, 24, 22)  # surface-elevated #16181a
_PRIMARY = (223, 79, 73)  # primary cobalt   #494fdf
_DANGER = (74, 59, 226)  # accent-danger   #e23b4a
_WARNING = (0, 126, 236)  # accent-warning  #ec7e00
_GREEN = (25, 134, 66)  # accent-light-green #428619
_TEAL = (126, 168, 0)  # accent-teal     #00a87e

_PANEL_W = 360
_VIEW_H = 480
_PAD = 24
_FONT = cv2.FONT_HERSHEY_DUPLEX

_KIND_COLOR: dict[str, tuple[int, int, int]] = {
    "VICTIM": _DANGER,
    "ESCAPE_ROUTE": _GREEN,
    "FIRE_POINT": _WARNING,
    "STRUCTURAL": _STONE,
    "TEAMMATE": _TEAL,
}


def _text(
    img: Frame,
    s: str,
    org: tuple[int, int],
    scale: float,
    color: tuple[int, int, int],
    thickness: int = 1,
) -> None:
    cv2.putText(img, s, org, _FONT, scale, color, thickness, cv2.LINE_AA)


def _bar(
    img: Frame,
    x: int,
    y: int,
    w: int,
    h: int,
    frac: float,
    color: tuple[int, int, int],
) -> None:
    cv2.rectangle(img, (x, y), (x + w, y + h), _ELEVATED, -1)
    fill = int(w * float(np.clip(frac, 0.0, 1.0)))
    if fill > 0:
        cv2.rectangle(img, (x, y), (x + fill, y + h), color, -1)


def draw_camera_view(vision: VisionFrame) -> Frame:
    """Scale the camera frame to view height and overlay eye / pupil markers."""
    if vision.image is None:
        return np.zeros((_VIEW_H, _VIEW_H, 3), dtype=np.uint8)

    img = vision.image.copy()
    for eye in vision.eyes:
        ex, ey, ew, eh = eye.bbox
        cv2.rectangle(img, (ex, ey), (ex + ew, ey + eh), _PRIMARY, 2)
        px, py = int(eye.pupil_xy[0]), int(eye.pupil_xy[1])
        cv2.circle(img, (px, py), 3, _ON_DARK, -1)

    h, w = img.shape[:2]
    scale = _VIEW_H / float(h)
    resized: Frame = cast(Frame, cv2.resize(img, (int(w * scale), _VIEW_H)))

    badge = "TRACKING" if vision.detected else "NO FACE"
    badge_color = _GREEN if vision.detected else _DANGER
    _text(resized, badge, (16, 32), 0.6, badge_color, 1)
    return resized


def _draw_gaze_map(
    panel: Frame, x: int, y: int, w: int, h: int, gaze: tuple[float, float],
    screen_size: tuple[int, int],
) -> None:
    cv2.rectangle(panel, (x, y), (x + w, y + h), _ELEVATED, -1)
    cv2.rectangle(panel, (x, y), (x + w, y + h), _STONE, 1)
    sw, sh = screen_size
    gx = x + int(w * float(np.clip(gaze[0] / max(sw - 1, 1), 0.0, 1.0)))
    gy = y + int(h * float(np.clip(gaze[1] / max(sh - 1, 1), 0.0, 1.0)))
    cv2.line(panel, (gx - 8, gy), (gx + 8, gy), _ON_DARK, 1)
    cv2.line(panel, (gx, gy - 8), (gx, gy + 8), _ON_DARK, 1)


def _draw_panel(vision: VisionFrame, hud: dict[str, Any], height: int) -> Frame:
    """Build the black metrics panel from a HudState dict."""
    panel: Frame = np.zeros((height, _PANEL_W, 3), dtype=np.uint8)
    panel[:] = _CANVAS
    x = _PAD
    inner = _PANEL_W - 2 * _PAD

    _text(panel, "PHAROS", (x, 44), 1.1, _ON_DARK, 2)
    _text(panel, "LIVE CAMERA", (x, 68), 0.45, _MUTE, 1)

    cli = float(hud.get("cognitive_load", 0.0))
    cli_color = _DANGER if cli >= 0.7 else _WARNING if cli >= 0.4 else _PRIMARY
    _text(panel, "Cognitive Load", (x, 116), 0.5, _MUTE, 1)
    _text(panel, f"{cli:.2f}", (_PANEL_W - _PAD - 60, 116), 0.6, _ON_DARK, 1)
    _bar(panel, x, 128, inner, 10, cli, cli_color)

    hs = float(hud.get("gaze_entropy_hs", 0.0))
    ht = float(hud.get("gaze_entropy_ht", 0.0))
    _text(panel, "Gaze Entropy Hs", (x, 176), 0.5, _MUTE, 1)
    _text(panel, f"{hs:.2f}", (_PANEL_W - _PAD - 60, 176), 0.55, _ON_DARK, 1)
    _bar(panel, x, 188, inner, 8, hs / 6.0, _ON_DARK)
    _text(panel, "Gaze Entropy Ht", (x, 224), 0.5, _MUTE, 1)
    _text(panel, f"{ht:.2f}", (_PANEL_W - _PAD - 60, 224), 0.55, _ON_DARK, 1)
    _bar(panel, x, 236, inner, 8, ht / 6.0, _ON_DARK)

    smoke = float(hud.get("smoke_density", 0.0)) * 100.0
    vis = float(hud.get("visibility", 0.0))
    _text(panel, "Smoke", (x, 292), 0.45, _STONE, 1)
    _text(panel, f"{smoke:.0f}%", (x, 320), 0.8, _ON_DARK, 1)
    _text(panel, "Visibility", (x + inner // 2, 292), 0.45, _STONE, 1)
    _text(panel, f"{vis:.1f} m", (x + inner // 2, 320), 0.8, _ON_DARK, 1)

    _text(panel, "PRIORITY QUEUE", (x, 364), 0.45, _STONE, 1)
    active_ids = {h["id"] for h in hud.get("active_hazards", [])}
    kinds = {h["id"]: h["kind"] for h in hud.get("active_hazards", [])}
    ranked = hud.get("ranked_scores", [])
    row_y = 388
    for i, entry in enumerate(ranked):
        sc, hid = float(entry[0]), str(entry[1])
        color = _KIND_COLOR.get(kinds.get(hid, ""), _STONE)
        is_active = hid in active_ids
        cv2.circle(panel, (x + 6, row_y - 4), 5, color, -1)
        label_color = _ON_DARK if is_active else _MUTE
        _text(panel, f"{i + 1}  {hid}", (x + 20, row_y), 0.5, label_color, 1)
        _text(panel, f"{sc:.3f}", (_PANEL_W - _PAD - 60, row_y), 0.5, label_color, 1)
        row_y += 30

    _draw_gaze_map(panel, x, row_y + 6, inner, 88, vision.gaze, (800, 600))
    return panel


def render_overlay(vision: VisionFrame, hud: dict[str, Any]) -> Frame:
    """Compose ``[ camera view | metrics panel ]`` into one BGR image."""
    view = draw_camera_view(vision)
    panel = _draw_panel(vision, hud, view.shape[0])
    combined: Frame = np.hstack([view, panel])
    return combined


def encode_jpeg_base64(frame: Frame, quality: int = 70) -> str:
    """Encode a BGR frame as a base64 ``data:`` URL for browser streaming."""
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        return ""
    payload = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{payload}"
