"""Live camera streaming for the browser UI.

Browsers cannot play RTSP directly, so we read frames from the camera with
OpenCV and serve them as an **MJPEG stream** (a sequence of JPEG frames in a
multipart HTTP response). Any browser can display this via a plain ``<img>``
tag pointing at the stream URL.

Each camera gets its own ``LiveStream`` that lazily opens the RTSP source on
first request and keeps it open for reuse. Frames are encoded to JPEG and
yielded as multipart chunks.
"""
from __future__ import annotations

import time
from typing import Iterator

from .config import CameraConfig


class LiveStream:
    """Reads frames from one camera and yields MJPEG multipart chunks."""

    def __init__(self, cam: CameraConfig, fps: int = 10, jpeg_quality: int = 70):
        self.cam = cam
        self.fps = fps
        self.jpeg_quality = jpeg_quality
        self._cap = None
        self._cv2 = None

    def _ensure_open(self):
        if self._cap is not None:
            return
        try:
            import cv2
        except ImportError as e:  # pragma: no cover - env-dependent
            raise RuntimeError("OpenCV is required for live streaming") from e
        self._cv2 = cv2
        self._cap = cv2.VideoCapture(self.cam.rtsp_url)

    def frames(self) -> Iterator[bytes]:
        """Yield JPEG-encoded frames as multipart MJPEG chunks."""
        self._ensure_open()
        if self._cap is None:
            return
        frame_interval = 1.0 / max(1, self.fps)
        while True:
            ok, frame = self._cap.read()
            if not ok:
                # Camera rate-limits; pause and retry rather than spin.
                time.sleep(1.0)
                continue
            ok, buf = self._cv2.imencode(
                ".jpg", frame, [self._cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            )
            if ok:
                yield buf.tobytes()
            time.sleep(frame_interval)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None