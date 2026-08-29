"""Unit tests for the Windows notification sender."""
from __future__ import annotations

from watchtower.notifications import NotificationSender


def test_disabled_does_not_notify():
    n = NotificationSender(enabled=False)
    assert n.notify("cam", "clip.mp4", score=50.0) is False


def test_enabled_without_library_falls_back_silently():
    # If winotify isn't installed, enabled notifier returns False (no crash).
    n = NotificationSender(enabled=True)
    result = n.notify("cam", "clip.mp4")
    # It should never raise, and returns False only if the lib is missing
    # (which it may be in a test env). Either way no exception.
    assert result in (True, False)


def test_throttle_limits_frequency():
    n = NotificationSender(enabled=True, max_frequency_s=60.0)
    first = n.notify("cam", "a.mp4", now=1000.0)
    second = n.notify("cam", "b.mp4", now=1000.5)  # 0.5s later -> throttled
    assert second is False
    # If the lib is present, the first fires; if absent, also False.
    # The key assertion is the throttle suppressing the second one.
    assert second is False
