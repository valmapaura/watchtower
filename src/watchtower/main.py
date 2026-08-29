"""watchtower — general RTSP camera motion recorder (CLI entry point).

Usage:
    python -m watchtower.main --config config.json
"""
from __future__ import annotations

import argparse
import signal
from pathlib import Path

from .config import Config
from .detector import FrameDiffDetector
from .recorder import MotionRecorder
from .source import RtspFrameSource
from .storage import ClipMetadata, LocalDiskBackend
from .writer import OpenCvClipWriter


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="watchtower motion recorder")
    p.add_argument("--config", type=Path, default=Path("config.json"))
    p.add_argument("--once", action="store_true", help="record a single clip and exit (for testing)")
    return p.parse_args()


def run_single_camera(cam, output_dir: Path, once: bool = False) -> int:
    """Run the recorder for one camera; returns clips saved."""
    source = RtspFrameSource(cam.rtsp_url)
    detector = FrameDiffDetector(sensitivity=cam.sensitivity)
    writer = OpenCvClipWriter()
    backend = LocalDiskBackend(output_dir)

    recorder = MotionRecorder(
        source=source,
        detector=detector,
        writer=writer,
        camera_name=cam.name,
        pre_seconds=cam.pre_seconds,
        post_seconds=cam.post_seconds,
        min_duration=cam.min_duration,
        on_clip=_save_clip(backend, cam),
    )

    # Stop cleanly on Ctrl-C.
    stop = {"flag": False}

    def _handler(sig, frame):  # pragma: no cover - Ctrl-C only
        stop["flag"] = True

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)

    try:
        if once:
            # Capture a fixed number of frames so the recorder runs then exits.
            for _ in range(60):
                if not recorder.step() or stop["flag"]:
                    break
        else:
            while not stop["flag"]:
                if not recorder.step():
                    break
    finally:
        source.close()

    return recorder.clips_saved


def _save_clip(backend: LocalDiskBackend, cam):
    def _save(local_path: Path, start_ts: float) -> None:
        from datetime import datetime, timezone

        start_utc = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat(timespec="seconds")
        metadata = ClipMetadata(
            filename=local_path.name,
            camera=cam.name,
            start_utc=start_utc,
        )
        backend.save(local_path, metadata)

    return _save


def main() -> int:
    args = _parse_args()
    cfg = Config.from_file(args.config)
    for cam in cfg.cameras:
        print(f"[watchtower] watching {cam.name} at {cam.host}")
        n = run_single_camera(cam, cfg.output_dir, once=args.once)
        print(f"[watchtower] {cam.name}: {n} clip(s) recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
