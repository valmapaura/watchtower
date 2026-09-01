"""watchtower — general RTSP camera motion recorder (CLI entry point).

Usage:
    python -m watchtower.main --config config.json
"""
from __future__ import annotations

import argparse
import signal
from datetime import datetime, timezone
from pathlib import Path

from .config import Config, default_data_dir
from .detector import FrameDiffDetector
from .notifications import NotificationSender
from .recorder import MotionRecorder
from .source import RtspFrameSource
from .storage import ClipMetadata, LocalDiskBackend
from .writer import OpenCvClipWriter


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="watchtower motion recorder")
    p.add_argument("--config", type=Path, default=default_data_dir() / "config.json")
    p.add_argument("--once", action="store_true", help="record a single clip and exit (for testing)")
    return p.parse_args()


def run_single_camera(
    cam,
    output_dir: Path,
    retention_days: int = 30,
    once: bool = False,
    notifications_enabled: bool = False,
    max_storage_gb: float = 20.0,
) -> int:
    """Run the recorder for one camera; returns clips saved."""
    source = RtspFrameSource(cam.rtsp_url)
    detector = _build_detector(cam)
    writer = OpenCvClipWriter()
    backend = LocalDiskBackend(output_dir)
    notifier = NotificationSender(enabled=notifications_enabled)

    recorder = MotionRecorder(
        source=source,
        detector=detector,
        writer=writer,
        camera_name=cam.name,
        pre_seconds=cam.pre_seconds,
        post_seconds=cam.post_seconds,
        min_duration=cam.min_duration,
        on_clip=_save_clip(backend, cam, notifier),
        on_motion=_save_snapshot(cam) if cam.snapshot_on_motion else None,
        category_of=_category_of(detector),
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

    # Enforce retention (age) and the storage size cap.
    removed = backend.cleanup(retention_days, max_storage_gb=max_storage_gb)
    if removed:
        print(f"[watchtower] cleanup: removed {removed} clip(s)")

    return recorder.clips_saved


def _save_clip(backend: LocalDiskBackend, cam, notifier: NotificationSender | None = None):
    def _save(local_path: Path, start_ts: float, motion_score: float, category: str = "motion") -> None:
        start_utc = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat(timespec="seconds")
        metadata = ClipMetadata(
            filename=local_path.name,
            camera=cam.name,
            start_utc=start_utc,
            motion_score=motion_score,
            category=category,
        )
        backend.save(local_path, metadata)
        if notifier is not None:
            notifier.notify(cam.name, local_path.name, score=motion_score)

    return _save


def _build_detector(cam):
    """Build the motion/object detector for a camera based on its config.

    Uses ``FrameDiffDetector`` by default. If the camera config sets
    ``detector: "object"`` (and optionally ``detect_categories``), uses the
    YOLO-based ``ObjectDetector`` instead.
    """
    detector_type = getattr(cam, "detector", "motion")
    if detector_type == "object":
        from .detector_objects import ObjectDetector

        categories = getattr(cam, "detect_categories", None) or ["person"]
        return ObjectDetector(categories=categories)
    return FrameDiffDetector(sensitivity=cam.sensitivity)


def _category_of(detector):
    """Return a callback that reads the current clip category from the detector.

    Object detectors expose ``detected_classes``; frame-diff detectors have no
    classes, so we fall back to "motion".
    """
    def _category() -> str:
        classes = getattr(detector, "detected_classes", None)
        if classes:
            # Pick the most specific class seen (e.g. "person" over "vehicle").
            return sorted(classes)[0]
        return "motion"

    return _category


def _save_snapshot(cam):
    """Return a callback that writes a JPEG thumbnail of a motion frame."""
    import cv2

    def _save(frame, ts: float) -> None:
        if frame is None:
            return
        ts_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_dir = Path("snapshots") / cam.name
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{ts_str}.jpg"
        cv2.imwrite(str(path), frame)

    return _save


def main() -> int:
    args = _parse_args()
    cfg = Config.from_file(args.config)
    for cam in cfg.cameras:
        print(f"[watchtower] watching {cam.name} at {cam.host}")
        n = run_single_camera(
            cam,
            cfg.output_dir,
            retention_days=cfg.retention_days,
            once=args.once,
            notifications_enabled=cfg.notifications_enabled,
            max_storage_gb=cfg.max_storage_gb,
        )
        print(f"[watchtower] {cam.name}: {n} clip(s) recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
