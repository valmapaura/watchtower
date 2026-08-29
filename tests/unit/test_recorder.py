"""Unit tests for the motion recorder state machine (pure logic, no OpenCV)."""
from __future__ import annotations

from watchtower.recorder import MotionRecorder

from conftest import FakeDetector, FakeWriter


class FakeSource:
    """Yields frames at a fixed fps until exhausted."""

    def __init__(self, n_frames, fps=10.0, start_ts=1000.0):
        self.n = n_frames
        self.fps = fps
        self._ts = start_ts
        self._i = 0

    def next_frame(self):
        if self._i >= self.n:
            return None
        ts = self._ts + self._i / self.fps
        self._i += 1
        return (ts, ("frame", self._i))


def make_recorder(n_frames, motion_seq, pre=2.0, post=1.0, min_dur=0.4, fps=10.0):
    src = FakeSource(n_frames, fps=fps)
    det = FakeDetector(motion_seq)
    w = FakeWriter()
    r = MotionRecorder(src, det, w, camera_name="cam", pre_seconds=pre,
                       post_seconds=post, min_duration=min_dur)
    return r, det, w


def test_no_motion_no_clips():
    r, _, w = make_recorder(50, [False] * 50)
    assert r.run() == 0
    assert w.opened == []


def test_motion_produces_clip_with_prebuffer():
    # 20 idle frames (2s at 10fps), then 10 motion (0.9s event > min 0.4s),
    # then 10 idle for post-roll.
    seq = [False] * 20 + [True] * 10 + [False] * 10
    r, _, w = make_recorder(len(seq), seq, pre=2.0, post=1.0, min_dur=0.4)
    assert r.run() == 1
    # pre(20) + motion(10) + post(10) = 40 frames written
    assert len(w.opened) == 1
    assert len(w.frames) == 40


def test_short_blip_discarded():
    # 5 motion frames (0.5s event) < min_duration 0.8s -> no clip.
    seq = [False] * 10 + [True] * 5 + [False] * 10
    r, _, w = make_recorder(len(seq), seq, pre=1.0, post=0.5, min_dur=0.8)
    assert r.run() == 0
    assert r.clips_saved == 0


def test_two_separate_motion_events_two_clips():
    seq = [False] * 10 + [True] * 10 + [False] * 15 + [True] * 10 + [False] * 10
    r, _, w = make_recorder(len(seq), seq, pre=1.0, post=0.5, min_dur=0.4)
    assert r.run() == 2
    assert len(w.opened) == 2


def test_on_clip_callback_called():
    seq = [False] * 10 + [True] * 10 + [False] * 10
    src = FakeSource(len(seq), fps=10.0)
    det = FakeDetector(seq)
    w = FakeWriter()
    saved = []
    r = MotionRecorder(src, det, w, camera_name="cam", pre_seconds=1.0,
                       post_seconds=0.5, min_duration=0.4,
                       on_clip=lambda p, ts: saved.append((p, ts)))
    r.run()
    assert len(saved) == 1
    path, ts = saved[0]
    assert path.name.startswith("cam_")
    assert ts > 0


def test_post_roll_extends_clip():
    # 10 idle frames, then 5 motion (0.5s), then 15 idle.
    # post=1.0s => 10 post-roll frames.
    seq = [False] * 10 + [True] * 5 + [False] * 15
    r, _, w = make_recorder(len(seq), seq, pre=1.0, post=1.0, min_dur=0.3)
    r.run()
    # pre(10) + motion(5) + post(10) = 25
    assert len(w.frames) == 25


def test_step_returns_false_at_end():
    src = FakeSource(1, fps=10.0)
    det = FakeDetector([False])
    r = MotionRecorder(src, det, FakeWriter())
    assert r.step() is True
    assert r.step() is False
