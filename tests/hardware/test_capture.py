"""Hardware tests against the live camera (excluded by default).

Run explicitly with:  pytest -m hardware
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from watchtower.config import Config

pytestmark = pytest.mark.hardware


def test_capture_short_clip_from_config(tmp_path):
    """Record a few frames from the real camera using config.json."""
    cfg_path = Path(__file__).resolve().parent.parent.parent / "config.json"
    cfg = Config.from_file(cfg_path)
    cam = cfg.cameras[0]

    from watchtower.detector import FrameDiffDetector
    from watchtower.recorder import MotionRecorder
    from watchtower.source import RtspFrameSource
    from watchtower.writer import OpenCvClipWriter

    src = RtspFrameSource(cam.rtsp_url)
    det = FrameDiffDetector()
    writer = OpenCvClipWriter()
    recorder = MotionRecorder(src, det, writer, camera_name=cam.name,
                              pre_seconds=cam.pre_seconds, post_seconds=cam.post_seconds)
    try:
        for _ in range(60):  # ~6 seconds of frames
            if not recorder.step():
                break
    finally:
        src.close()
    assert recorder.clips_saved >= 0  # camera may be quiet; just ensure no crash
