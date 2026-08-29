"""Unit tests for the OpenCV frame-diff motion detector."""
from __future__ import annotations

import numpy as np
import pytest

from watchtower.detector import FrameDiffDetector

pytest.importorskip("cv2")


def _static_frame(size=(240, 320), value=100):
    return np.full((size[0], size[1], 3), value, dtype=np.uint8)


def test_no_motion_on_identical_frames():
    d = FrameDiffDetector(sensitivity=0.02)
    assert d.detect(_static_frame()) is False
    assert d.detect(_static_frame()) is False


def test_motion_on_changed_region():
    d = FrameDiffDetector(sensitivity=0.01)
    d.detect(_static_frame())
    frame = _static_frame()
    # Paint a large changed region in the corner.
    frame[0:80, 0:80] = 255
    assert d.detect(frame) is True


def test_tiny_change_below_sensitivity_is_ignored():
    d = FrameDiffDetector(sensitivity=0.5)  # very high threshold fraction
    d.detect(_static_frame())
    frame = _static_frame()
    frame[0:10, 0:10] = 255  # small region (~0.1% of pixels)
    assert d.detect(frame) is False


def test_reset_forgets_previous_frame():
    d = FrameDiffDetector(sensitivity=0.01)
    d.detect(_static_frame())
    d.reset()
    # After reset, first frame is just a baseline (no motion).
    assert d.detect(_static_frame()) is False
