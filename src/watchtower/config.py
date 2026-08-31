"""Configuration loading and RTSP URL building.

Keeps credentials out of code: everything comes from ``config.json``
(which is git-ignored) and the password is URL-encoded when building URLs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote


@dataclass
class CameraConfig:
    """Connection details for a single camera."""

    name: str
    host: str
    rtsp_port: int = 554
    username: str = "admin"
    password: str = ""
    rtsp_path: str = "/live/ch0"
    # motion recording tuning
    pre_seconds: float = 30.0   # how much to keep BEFORE motion
    post_seconds: float = 5.0   # how long to keep AFTER motion stops
    min_duration: float = 2.0   # ignore blips shorter than this
    sensitivity: float = 0.02   # fraction of pixels that must change
    snapshot_on_motion: bool = True  # save a JPEG thumbnail per motion event
    detector: str = "motion"    # "motion" (frame-diff) or "object" (YOLO)
    detect_categories: list[str] = field(default_factory=lambda: ["person"])  # object classes to record

    @property
    def rtsp_url(self) -> str:
        """Build an RTSP URL with the password percent-encoded.

        A password with special characters (spaces, @, :, etc.) must be
        URL-encoded or the URL is ambiguous.
        """
        user = quote(self.username, safe="")
        pw = quote(self.password, safe="")
        return f"rtsp://{user}:{pw}@{self.host}:{self.rtsp_port}{self.rtsp_path}"


@dataclass
class Config:
    """Top-level application config."""

    cameras: list[CameraConfig]
    output_dir: Path = field(default_factory=lambda: Path("recordings"))
    retention_days: int = 30       # delete clips older than this (0 = never)
    max_storage_gb: float = 20.0   # max recordings size in GB (0 = unlimited)
    check_interval: float = 0.1    # seconds between frames processed
    storage_backend: str = "local" # "local" (future: "google_drive", "firebase", "s3")
    log_level: str = "INFO"        # DEBUG | INFO | WARNING | ERROR
    timezone: str = "UTC"          # display timezone for clip timestamps
    notifications_enabled: bool = False  # future: webhook/email on motion
    web_port: int = 8000           # port for the browser UI / API server
    api_token: str = ""            # optional bearer token for the API ("" = no auth)
    ui_password: str = ""          # password to access the web UI ("" = no login)

    @classmethod
    def from_file(cls, path: Path | str) -> "Config":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))

        # Support both the newer "cameras": [ ... ] list and the legacy
        # singular "camera": { ... } shape from the original config.json.
        if "cameras" in raw:
            items = raw["cameras"]
        elif "camera" in raw:
            items = [raw["camera"]]
        else:
            raise ValueError('config.json must contain a "camera" or "cameras" key')

        cameras = [cls._parse_camera(c) for c in items]
        out = Path(raw.get("output_dir", "recordings"))
        return cls(
            cameras=cameras,
            output_dir=out,
            retention_days=int(raw.get("retention_days", 30)),
            max_storage_gb=float(raw.get("max_storage_gb", 20.0)),
            check_interval=float(raw.get("check_interval", 0.1)),
            storage_backend=raw.get("storage_backend", "local"),
            log_level=raw.get("log_level", "INFO"),
            timezone=raw.get("timezone", "UTC"),
            notifications_enabled=bool(raw.get("notifications_enabled", False)),
            web_port=int(raw.get("web_port", 8000)),
            api_token=raw.get("api_token", ""),
            ui_password=str(raw.get("ui_password", "")),
        )

    @staticmethod
    def _parse_camera(c: dict) -> CameraConfig:
        return CameraConfig(
            name=c.get("name", "camera"),
            host=c["host"],
            rtsp_port=c.get("rtsp_port", 554),
            username=c.get("username", "admin"),
            password=c.get("password", ""),
            rtsp_path=c.get("rtsp_path", "/live/ch0"),
            pre_seconds=float(c.get("pre_seconds", 30.0)),
            post_seconds=float(c.get("post_seconds", 5.0)),
            min_duration=float(c.get("min_duration", 2.0)),
            sensitivity=float(c.get("sensitivity", 0.02)),
            snapshot_on_motion=bool(c.get("snapshot_on_motion", True)),
            detector=c.get("detector", "motion"),
            detect_categories=list(c.get("detect_categories", ["person"])),
        )

    @classmethod
    def from_single(cls, cam: CameraConfig, **kw) -> "Config":
        """Build a config from one camera (used for a single-camera setup)."""
        return cls(cameras=[cam], **kw)
