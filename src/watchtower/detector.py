"""Motion detection with a swappable interface.

``MotionDetector`` is the interface. ``FrameDiffDetector`` is a simple,
proven implementation using OpenCV frame differencing. Because the detector
is behind an interface, a future ML detector can be dropped in without
touching the recorder.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover - only needed when running OpenCV detector
    cv2 = None
    np = None


class MotionDetector(ABC):
    """Decides whether a frame contains motion."""

    @abstractmethod
    def detect(self, frame) -> bool:
        """Return True if the given frame shows motion."""
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Forget internal state (e.g. after a camera reconnect)."""
        raise NotImplementedError


class FrameDiffDetector(MotionDetector):
    """Detects motion by comparing each frame to the previous one.

    ``sensitivity`` is the fraction of pixels whose absolute change exceeds
    ``threshold`` before we consider it motion. Higher = less sensitive.
    """

    def __init__(self, sensitivity: float = 0.02, threshold: int = 25):
        self.sensitivity = float(sensitivity)
        self.threshold = int(threshold)
        self._prev: object | None = None

    def detect(self, frame) -> bool:
        if cv2 is None or np is None:
            raise RuntimeError("OpenCV/numpy are required for FrameDiffDetector")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self._prev is None:
            self._prev = gray
            return False

        delta = cv2.absdiff(gray, self._prev)
        self._prev = gray

        changed = cv2.countNonZero(cv2.threshold(delta, self.threshold, 255, cv2.THRESH_BINARY)[1])
        fraction = changed / float(gray.size)
        return fraction > self.sensitivity

    def reset(self) -> None:
        self._prev = None
