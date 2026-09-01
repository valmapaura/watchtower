"""OpenCV-backed frame source that reads from an RTSP camera."""

from __future__ import annotations

import time


class RtspFrameSource:
    """Reads frames from an RTSP URL via OpenCV.

    Implements the recorder's ``FrameSource`` protocol. Auto-reconnects on
    stream interruption (the camera rate-limits connections).
    """

    def __init__(self, rtsp_url: str, reconnect_sec: float = 2.0):
        try:
            import cv2
        except ImportError:
            raise RuntimeError("OpenCV is required for RtspFrameSource")
        self._cv2 = cv2
        self._url = rtsp_url
        self._reconnect_sec = reconnect_sec
        self._cap = self._cv2.VideoCapture(self._url)

    @property
    def fps(self) -> float:
        """Return the camera's reported frame rate (falls back to 25.0)."""
        if self._cap is None:
            return 25.0
        try:
            fps = self._cap.get(self._cv2.CAP_PROP_FPS)
            if fps and fps > 0 and fps < 120:
                return float(fps)
        except Exception:
            pass
        return 25.0

    def next_frame(self) -> tuple[float, object] | None:
        ok, frame = self._cap.read()
        if not ok:
            # Transient read failure — reconnect and signal the caller to
            # retry (return None), but do NOT treat this as "stream ended".
            time.sleep(self._reconnect_sec)
            self._cap.release()
            self._cap = self._cv2.VideoCapture(self._url)
            return None
        return (time.time(), frame)

    def close(self) -> None:
        self._cap.release()
