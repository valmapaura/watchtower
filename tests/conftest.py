"""Shared fixtures for watchtower tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make src importable
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


class FakeClock:
    def __init__(self, start=0.0):
        self._t = start

    def time(self) -> float:
        return self._t

    def advance(self, dt: float):
        self._t += dt


class FakeDetector:
    """Returns a scripted motion response per call."""

    def __init__(self, sequence=None, scores=None):
        self._seq = list(sequence or [])
        self._scores = list(scores or [])
        self._i = 0
        self.calls = 0

    def detect(self, frame) -> bool:
        return self.motion_score(frame)[0]

    def motion_score(self, frame) -> tuple[bool, float]:
        self.calls += 1
        if self._i < len(self._seq):
            r = self._seq[self._i]
            s = self._scores[self._i] if self._i < len(self._scores) else (100.0 if r else 0.0)
        else:
            r = False
            s = 0.0
        self._i += 1
        return (r, s)

    def reset(self):
        self._i = 0


class FakeWriter:
    def __init__(self):
        self.opened = []
        self.frames = []
        self.closed = 0

    def open(self, path, fps):
        self.opened.append((str(path), fps))

    def write(self, frame):
        self.frames.append(frame)

    def close(self):
        self.closed += 1
