"""``python -m pharos.vision`` — run the live webcam HUD."""

from __future__ import annotations

import argparse

from .runner import run_live


def main() -> None:
    """Parse CLI arguments and launch the live camera loop."""
    parser = argparse.ArgumentParser(description="PHAROS live camera HUD")
    parser.add_argument("--camera", type=int, default=0, help="camera device index")
    parser.add_argument(
        "--gain", type=float, default=1.6, help="gaze mapping gain (iris→screen)"
    )
    args = parser.parse_args()
    run_live(camera_index=args.camera, gaze_gain=args.gain)


if __name__ == "__main__":
    main()
