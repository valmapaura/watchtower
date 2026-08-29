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
    """Decides whether a frame contains motion.

    ``detect`` returns a bool for simple callers. ``motion_score`` returns a
    (bool, score) pair where ``score`` is 0-100 intensity, so callers can use
    the "level of movement" (e.g. to categorize or to gate recording quality).
    """

    @abstractmethod
    def detect(self, frame) -> bool:
        """Return True if the given frame shows motion."""
        raise NotImplementedError

    @abstractmethod
    def motion_score(self, frame) -> tuple[bool, float]:
        """Return (has_motion, score) with score in 0..100."""
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

    def _diff_fraction(self, frame) -> float:
        if cv2 is None or np is None:
            raise RuntimeError("OpenCV/numpy are required for FrameDiffDetector")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self._prev is None:
            self._prev = gray
            return 0.0

        delta = cv2.absdiff(gray, self._prev)
        self._prev = gray

        changed = cv2.countNonZero(cv2.threshold(delta, self.threshold, 255, cv2.THRESH_BINARY)[1])
        return changed / float(gray.size)

    def detect(self, frame) -> bool:
        return self.motion_score(frame)[0]

    def motion_score(self, frame) -> tuple[bool, float]:
        """Return (has_motion, score). Score maps the changed-pixel fraction
        to 0-100 via a log-ish scale so small movements are low, big ones high.
        """
        fraction = self._diff_fraction(frame)
        score = min(100.0, fraction / self.sensitivity * 100.0)
        return (fraction > self.sensitivity, round(score, 1))

    def reset(self) -> None:
        self._prev = None
