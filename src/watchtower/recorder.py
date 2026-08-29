"""The motion recorder: captures frames, detects motion, and saves clips.

Design goals (see docs/PROJECT.md):
  * Modular — the detector and writer are interfaces, so they can be swapped.
  * Testable — the recorder depends only on a frame source, detector, writer,
    and a clock. Tests inject synthetic frames, a fake detector/writer, and a
    fake clock. No camera or OpenCV needed for unit tests.

Pipeline for each camera:
  source ──► detector (motion?) ──► pre-buffer ──► writer
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from .writer import clip_filename


class FrameSource(Protocol):
    """Yields (timestamp, frame) pairs; returns None when the stream ends."""

    def next_frame(self) -> tuple[float, object] | None: ...


class Clock(Protocol):
    def time(self) -> float: ...


class RealClock:
    def time(self) -> float:
        import time

        return time.time()


@dataclass
class Session:
    """State for the clip currently being written (or about to be)."""

    first_ts: float
    frames: list[tuple[float, object]]
    motion_start_ts: float
    last_motion_ts: float
    peak_score: float = 0.0


class MotionRecorder:
    """Drives one camera through detect → buffer → write.

    * Every frame is added to a time-based pre-buffer (up to ``pre_seconds``).
    * When motion starts while idle, the pre-buffer is flushed to the writer
      and new frames keep being written.
    * When motion stops, writing continues for ``post_seconds``, then the clip
      is finalized. Clips shorter than ``min_duration`` are discarded.
    """

    def __init__(
        self,
        source: FrameSource,
        detector,
        writer,
        camera_name: str = "cam",
        pre_seconds: float = 30.0,
        post_seconds: float = 5.0,
        min_duration: float = 2.0,
        clock: Clock | None = None,
        on_clip: Callable[[Path, float, float], None] | None = None,
        on_motion: Callable[[object, float], None] | None = None,
    ):
        self.source = source
        self.detector = detector
        self.writer = writer
        self.camera_name = camera_name
        self.pre_seconds = float(pre_seconds)
        self.post_seconds = float(post_seconds)
        self.min_duration = float(min_duration)
        self.clock = clock or RealClock()
        self.on_clip = on_clip
        self.on_motion = on_motion

        self._pre: list[tuple[float, object]] = []
        self._session: Session | None = None
        self._fps = 10.0
        self._last_ts: float | None = None
        self.clips_saved = 0

    # -- public API -------------------------------------------------------

    def run(self) -> int:
        """Process frames until the source ends. Returns clips saved."""
        while self.step():
            pass
        return self.clips_saved

    def step(self) -> bool:
        """Process exactly one frame; returns False when the source ends."""
        frame = self.source.next_frame()
        if frame is None:
            self._finalize(force=True)
            return False
        ts, img = frame
        self._process(ts, img)
        return True

    # -- internals --------------------------------------------------------

    def _process(self, ts: float, img: object) -> None:
        # Keep a rough FPS estimate so we can size the pre-buffer by time.
        if self._last_ts is not None and ts > self._last_ts:
            self._fps = self._fps * 0.9 + (1.0 / (ts - self._last_ts)) * 0.1
        self._last_ts = ts

        motion, score = self.detector.motion_score(img)
        self._pre.append((ts, img))
        # Trim the pre-buffer down to pre_seconds of frames.
        cutoff = ts - self.pre_seconds
        while self._pre and self._pre[0][0] < cutoff:
            self._pre.pop(0)

        if self._session is None:
            if motion and self._pre:
                self._start_clip(ts)
                self._session.peak_score = max(self._session.peak_score, score)
                if self.on_motion:
                    self.on_motion(img, ts)
        else:
            self._session.frames.append((ts, img))
            # Write the new frame live to the writer as well.
            self.writer.write(img)
            if motion:
                self._session.last_motion_ts = ts
                self._session.peak_score = max(self._session.peak_score, score)
            elif (ts - self._session.last_motion_ts) >= self.post_seconds:
                self._finalize()

    def _start_clip(self, ts: float) -> None:
        first_ts = self._pre[0][0]
        frames = list(self._pre)
        self._pre.clear()
        self._session = Session(
            first_ts=first_ts,
            frames=frames,
            motion_start_ts=ts,
            last_motion_ts=ts,
        )
        self.writer.open(self._clip_path(first_ts), self._fps)
        for _, img in frames:
            self.writer.write(img)

    def _clip_path(self, first_ts: float) -> Path:
        start = datetime.fromtimestamp(first_ts, tz=timezone.utc).isoformat(timespec="seconds")
        return Path(clip_filename(self.camera_name, start))

    def _finalize(self, force: bool = False) -> None:
        if self._session is None:
            return
        # min_duration applies to the motion event itself, so short noise
        # blips get discarded even though the pre/post buffer adds length.
        event_dur = self._session.last_motion_ts - self._session.motion_start_ts
        self.writer.close()
        if force or event_dur >= self.min_duration:
            self.clips_saved += 1
            if self.on_clip:
                self.on_clip(
                    self._clip_path(self._session.first_ts),
                    self._session.first_ts,
                    self._session.peak_score,
                )
        self._session = None
