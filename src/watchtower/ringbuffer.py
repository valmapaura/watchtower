"""A time-based circular buffer used for the motion pre-buffer.

The recorder keeps appending frames. When motion is detected, it flushes
everything currently held (up to ``pre_seconds`` of video) and keeps writing
for ``post_seconds`` after motion stops.
"""
from __future__ import annotations

from collections import deque
from typing import Generic, TypeVar

T = TypeVar("T")


class RingBuffer(Generic[T]):
    """Bounded FIFO that keeps the most recent ``capacity`` items."""

    def __init__(self, capacity: int):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self._buf: deque[T] = deque(maxlen=capacity)

    def append(self, item: T) -> None:
        self._buf.append(item)

    def __len__(self) -> int:
        return len(self._buf)

    def drain(self) -> list[T]:
        """Return and remove all buffered items (oldest first)."""
        items = list(self._buf)
        self._buf.clear()
        return items

    def peek(self) -> list[T]:
        """Return buffered items without removing them (oldest first)."""
        return list(self._buf)

    def clear(self) -> None:
        self._buf.clear()
