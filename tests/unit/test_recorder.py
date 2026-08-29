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


def test_on_motion_callback_fires_once_per_event():
    # Two separate motion events -> on_motion called twice.
    seq = [False] * 10 + [True] * 5 + [False] * 15 + [True] * 5 + [False] * 10
    src = FakeSource(len(seq), fps=10.0)
    det = FakeDetector(seq)
    w = FakeWriter()
    motion_frames = []
    r = MotionRecorder(src, det, w, camera_name="cam", pre_seconds=1.0,
                       post_seconds=0.5, min_duration=0.4,
                       on_motion=lambda img, ts: motion_frames.append((img, ts)))
    r.run()
    assert len(motion_frames) == 2
    # Each callback receives the first motion frame and its timestamp.
    assert all(isinstance(ts, float) for _, ts in motion_frames)


def test_no_motion_callback_when_never_moves():
    seq = [False] * 20
    src = FakeSource(len(seq), fps=10.0)
    det = FakeDetector(seq)
    motion_frames = []
    r = MotionRecorder(src, det, FakeWriter(), on_motion=lambda img, ts: motion_frames.append(ts))
    r.run()
    assert motion_frames == []


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
                       on_clip=lambda p, ts, score, cat: saved.append((p, ts, score)))
    r.run()
    assert len(saved) == 1
    path, ts, score = saved[0]
    assert path.name.startswith("cam_")
    assert ts > 0
    assert 0 <= score <= 100


def test_peak_motion_score_reported():
    # scores for the 10 motion frames: last is the highest
    seq = [False] * 10 + [True] * 10 + [False] * 10
    scores = [0.0] * 10 + [20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 95.0, 42.0] + [0.0] * 10
    src = FakeSource(len(seq), fps=10.0)
    det = FakeDetector(seq, scores)
    saved = []
    r = MotionRecorder(src, det, FakeWriter(), camera_name="cam", pre_seconds=1.0,
                       post_seconds=0.5, min_duration=0.4,
                       on_clip=lambda p, ts, score, cat: saved.append(score))
    r.run()
    # peak of the motion scores is 95.0
    assert saved == [95.0]


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


def test_category_of_callback_tags_clip():
    seq = [False] * 10 + [True] * 10 + [False] * 10
    src = FakeSource(len(seq), fps=10.0)
    det = FakeDetector(seq)
    saved = []
    r = MotionRecorder(src, det, FakeWriter(), camera_name="cam", pre_seconds=1.0,
                       post_seconds=0.5, min_duration=0.4,
                       category_of=lambda: "person",
                       on_clip=lambda p, ts, score, cat: saved.append(cat))
    r.run()
    assert saved == ["person"]


def test_category_defaults_to_motion():
    seq = [False] * 10 + [True] * 10 + [False] * 10
    src = FakeSource(len(seq), fps=10.0)
    det = FakeDetector(seq)
    saved = []
    r = MotionRecorder(src, det, FakeWriter(), camera_name="cam", pre_seconds=1.0,
                       post_seconds=0.5, min_duration=0.4,
                       on_clip=lambda p, ts, score, cat: saved.append(cat))
    r.run()
    assert saved == ["motion"]
