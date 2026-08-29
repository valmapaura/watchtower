"""Unit tests for the ring buffer."""
from __future__ import annotations

import pytest

from watchtower.ringbuffer import RingBuffer


def test_append_and_peek_oldest_first():
    rb = RingBuffer(3)
    rb.append("a")
    rb.append("b")
    assert rb.peek() == ["a", "b"]


def test_capacity_evicts_oldest():
    rb = RingBuffer(2)
    rb.append("a")
    rb.append("b")
    rb.append("c")
    assert rb.peek() == ["b", "c"]


def test_drain_returns_all_and_clears():
    rb = RingBuffer(5)
    rb.append(1)
    rb.append(2)
    assert rb.drain() == [1, 2]
    assert len(rb) == 0
    assert rb.drain() == []


def test_invalid_capacity():
    with pytest.raises(ValueError):
        RingBuffer(0)


def test_len():
    rb = RingBuffer(10)
    assert len(rb) == 0
    rb.append("x")
    assert len(rb) == 1
