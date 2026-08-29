#!/usr/bin/env python3
"""
watchtower - live RTSP viewer for a generic IP camera.

Features:
  * Live H.264 video with on-screen FPS
  * 's' saves a snapshot PNG to ./snapshots/
  * 'q' / ESC quits
  * Auto-reconnects (the camera rate-limits connections)

Setup:
    pip install opencv-python

Usage:
    python src/cam_viewer.py
    python src/cam_viewer.py --config path/to/config.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import cv2
except ImportError:
    sys.exit("OpenCV is not installed. Run: pip install opencv-python")


def load_camera(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    return cfg["camera"]


def build_rtsp_url(cam: dict) -> str:
    return (
        f"rtsp://{cam['username']}:{cam['password']}@"
        f"{cam['host']}:{cam['rtsp_port']}{cam['rtsp_path']}"
    )


def main() -> None:
    default_config = Path(__file__).resolve().parent.parent / "config.json"
    parser = argparse.ArgumentParser(description="watchtower live RTSP viewer")
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config,
        help="path to config.json (default: ../config.json)",
    )
    args = parser.parse_args()

    if not args.config.exists():
        sys.exit(
            f"config.json not found at {args.config} "
            f"(copy config.example.json to config.json and fill it in)"
        )

    cam = load_camera(args.config)
    url = build_rtsp_url(cam)
    print(f"watchtower connecting to {cam['host']} ...")

    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        sys.exit(
            "Could not open the RTSP stream. Is the camera online? "
            "Is the password correct in config.json?"
        )

    snap_dir = Path("snapshots")
    snap_dir.mkdir(exist_ok=True)

    window = "watchtower - [q] quit  [s] snapshot"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    prev = time.time()
    fps = 0.0
    frame_count = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Stream interrupted (camera rate-limits connections). Retrying...")
            time.sleep(2.0)
            cap = cv2.VideoCapture(url)
            if not cap.isOpened():
                print("Reconnect failed - waiting 10s before next attempt.")
                time.sleep(10.0)
                cap = cv2.VideoCapture(url)
            continue

        frame_count += 1
        now = time.time()
        fps = fps * 0.9 + (1.0 / max(now - prev, 1e-6)) * 0.1
        prev = now

        cv2.putText(
            frame,
            f"{fps:5.1f} fps",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
        cv2.imshow(window, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("s"):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = snap_dir / f"watchtower_{ts}.png"
            cv2.imwrite(str(path), frame)
            print(f"snapshot saved: {path}")

    cap.release()
    cv2.destroyAllWindows()
    print(f"bye - grabbed {frame_count} frames")


if __name__ == "__main__":
    main()
