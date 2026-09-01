"""Clip writing: turns buffered frames into a playable file.

``ClipWriter`` is the interface. ``OpenCvClipWriter`` is the Phase 1 default,
using OpenCV's VideoWriter (MP4, MPEG-4 codec) which is available everywhere
OpenCV is. Audio is not captured in this phase (a follow-up).

Because writing is behind an interface, tests can use a fake writer and the
recorder logic is fully unit-testable without OpenCV.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timezone


class ClipWriter(ABC):
    @abstractmethod
    def open(self, path: Path, fps: float) -> None:
        """Begin writing a new clip to ``path`` at ``fps``."""

    @abstractmethod
    def write(self, frame) -> None:
        """Append a frame to the current clip."""

    @abstractmethod
    def close(self) -> None:
        """Finalize and close the current clip."""


class OpenCvClipWriter(ClipWriter):
    """Writes frames to an MP4 using OpenCV's VideoWriter.

    Uses the H.264 (AVC) codec so clips play in browsers. Falls back to
    MPEG-4 Part 2 (``mp4v``) if H.264 isn't available on this machine.
    """

    _FOURCC = "avc1"  # H.264 — plays in all browsers

    def __init__(self) -> None:
        try:
            import cv2
        except ImportError:
            raise RuntimeError("OpenCV is required for OpenCvClipWriter")
        self._cv2 = cv2
        self._writer = None
        self._fourcc = self._FOURCC

    def open(self, path: Path, fps: float) -> None:
        self.close()
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        # We don't know the frame size until the first write, so we open lazily.
        self._path = path
        self._fps = fps
        self._size = None

    def write(self, frame) -> None:
        if self._writer is None:
            h, w = frame.shape[:2]
            fourcc = self._cv2.VideoWriter_fourcc(*self._fourcc)
            self._writer = self._cv2.VideoWriter(
                str(self._path),
                fourcc,
                self._fps,
                (w, h),
            )
            # If H.264 isn't available, OpenCV silently fails to open the
            # writer. Detect that and fall back to MPEG-4 Part 2.
            if not self._writer.isOpened():
                self._writer.release()
                self._fourcc = "mp4v"
                self._writer = self._cv2.VideoWriter(
                    str(self._path),
                    self._cv2.VideoWriter_fourcc(*self._fourcc),
                    self._fps,
                    (w, h),
                )
        if self._writer is not None and self._writer.isOpened():
            self._writer.write(frame)

    def close(self) -> None:
        if self._writer is not None:
            self._writer.release()
            self._writer = None


def utc_now_str() -> str:
    """ISO timestamp in UTC, used for clip naming and manifests."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clip_filename(camera: str, start_utc: str) -> str:
    """Human-friendly clip filename: <camera>_<YYYYmmdd_HHMMSS>_<UTC>.mp4"""
    ts = start_utc.replace("-", "").replace(":", "").replace("+00:00", "Z")
    ts = ts.replace("T", "_")
    return f"{camera}_{ts}.mp4"
