"""Windows local (toast) notifications on motion.

Uses ``winotify`` to raise a native Windows toast notification when a clip is
recorded. Falls back silently if the library isn't available (e.g. on a
non-Windows machine or in tests).

Enabled via config:  "notifications_enabled": true
"""
from __future__ import annotations

from pathlib import Path


class NotificationSender:
    """Sends a Windows toast when a motion clip is saved.

    ``enabled`` gates it. ``max_frequency_s`` throttles how often a toast can
    appear to avoid spamming during continuous motion.
    """

    def __init__(self, enabled: bool, max_frequency_s: float = 60.0):
        self.enabled = bool(enabled)
        self.max_frequency_s = float(max_frequency_s)
        self._last_sent: float | None = None
        self._toaster = None
        if self.enabled:
            try:
                from winotify import Notification  # type: ignore

                self._toaster = Notification
            except ImportError:
                self._toaster = None

    def notify(self, camera: str, clip_name: str, score: float | None = None, now: float | None = None) -> bool:
        """Send a toast; returns True if one was actually shown."""
        if not self.enabled or self._toaster is None:
            return False

        import time

        now = now if now is not None else time.time()
        if self._last_sent is not None and (now - self._last_sent) < self.max_frequency_s:
            return False
        self._last_sent = now

        title = f"Watchtower — Motion detected"
        body = f"{camera} recorded a clip"
        if score is not None:
            body += f" (motion {score:.0f}/100)"
        body += f"\n{clip_name}"

        toast = self._toaster(app_id="Watchtower", title=title, msg=body)
        toast.show()
        return True

    def _available(self) -> bool:
        return self._toaster is not None
