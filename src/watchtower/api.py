"""FastAPI web layer for the watchtower browser UI (Phase 4).

Serves the clip library over HTTP so a browser client can list, stream,
download, and delete recordings. This is a thin read/write layer over the
``StorageBackend`` — it does not run the recorder itself.

Security model (matches the project's "private by default" principle):
  * The server binds to localhost by default. To expose it on the LAN, set
    ``host`` explicitly when running (e.g. ``--host 0.0.0.0``).
  * If ``ui_password`` is set in config.json, the web UI requires a login
    (session cookie). When it is empty, the API is open (fine for
    localhost-only).
"""
from __future__ import annotations

import hmac
import json
import os
import secrets
import shutil
import threading
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from .config import Config, parse_rtsp_url
from .live import LiveStream
from .notifications import NotificationSender
from .storage import ClipMetadata, LocalDiskBackend

COOKIE_NAME = "wt_session"

# When the launcher (scripts/dev.js) sees the backend exit with this code, it
# respawns the process. Used by the "Restart server" button in Settings.
RESTART_EXIT_CODE = 42

# Server start time, used to report uptime in /status.
_START_TIME = time.time()


class RecorderManager:
    """Runs the motion recorder for all cameras in a background thread.

    The web app is the always-on process (started by the launcher or the
    installable app), so it owns the recorder loop. This lets notifications
    fire automatically when motion is detected, without a separate process.
    """

    def __init__(self, config: Config):
        self._config = config
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._notifier = NotificationSender(enabled=config.notifications_enabled)

    def start(self) -> None:
        """Start the recorder thread if it isn't already running."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        stop = self._stop  # capture this generation's stop event
        self._thread = threading.Thread(
            target=self._run, args=(stop,), name="watchtower-recorder", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the recorder thread to stop."""
        self._stop.set()

    def restart(self) -> None:
        """Restart the recorder (e.g. after settings change).

        The recorder thread may be blocked reading from a camera, so we can't
        wait for it to exit. We signal it to stop and start a fresh thread with
        a NEW stop event, so the old thread can't be re-armed by the new one.
        """
        self._stop.set()
        # Swap in a fresh stop event so the new thread has its own signal.
        self._stop = threading.Event()
        self._thread = None
        self.start()

    def set_notifications(self, enabled: bool) -> None:
        """Update whether notifications fire, without a full restart."""
        self._notifier.enabled = bool(enabled)

    def send_test_notification(self) -> bool:
        """Send a test toast; returns True if one was shown."""
        return self._notifier.notify("Watchtower", "Test notification", score=100)

    def _run(self, stop: threading.Event) -> None:
        from .detector import FrameDiffDetector
        from .recorder import MotionRecorder
        from .source import RtspFrameSource
        from .writer import OpenCvClipWriter

        backend = LocalDiskBackend(self._config.output_dir)

        for cam in self._config.cameras:
            if stop.is_set():
                break
            try:
                source = RtspFrameSource(cam.rtsp_url)
                detector = self._build_detector(cam)
                writer = OpenCvClipWriter()
                recorder = MotionRecorder(
                    source=source,
                    detector=detector,
                    writer=writer,
                    camera_name=cam.name,
                    pre_seconds=cam.pre_seconds,
                    post_seconds=cam.post_seconds,
                    min_duration=cam.min_duration,
                    on_clip=self._save_clip(backend, cam),
                    category_of=self._category_of(detector),
                )
                while not stop.is_set():
                    if not recorder.step():
                        break
                source.close()
            except Exception:
                # A camera failing shouldn't kill the whole loop; log and move on.
                import traceback

                traceback.print_exc()
                continue

        # Enforce retention + storage cap once at the end.
        backend.cleanup(
            self._config.retention_days, max_storage_gb=self._config.max_storage_gb
        )

    def _save_clip(self, backend: LocalDiskBackend, cam):
        from datetime import datetime, timezone

        def _save(local_path: Path, start_ts: float, motion_score: float, category: str = "motion") -> None:
            start_utc = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat(timespec="seconds")
            metadata = ClipMetadata(
                filename=local_path.name,
                camera=cam.name,
                start_utc=start_utc,
                motion_score=motion_score,
                category=category,
            )
            backend.save(local_path, metadata)
            self._notifier.notify(cam.name, local_path.name, score=motion_score)

        return _save

    @staticmethod
    def _build_detector(cam):
        from .detector import FrameDiffDetector

        detector_type = getattr(cam, "detector", "motion")
        if detector_type == "object":
            from .detector_objects import ObjectDetector

            categories = getattr(cam, "detect_categories", None) or ["person"]
            return ObjectDetector(categories=categories)
        return FrameDiffDetector(sensitivity=cam.sensitivity)

    @staticmethod
    def _category_of(detector):
        def _category() -> str:
            classes = getattr(detector, "detected_classes", None)
            if classes:
                return sorted(classes)[0]
            return "motion"

        return _category


def _auto_start_status() -> dict:
    """Return whether Watchtower is set to start automatically at login."""
    import subprocess

    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", "WatchtowerRecorder"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        enabled = result.returncode == 0
    except Exception:
        enabled = False
    return {"enabled": enabled}


def _set_auto_start(enabled: bool, config_path: Path | None = None) -> dict:
    """Install or remove the Windows scheduled task that starts Watchtower."""
    import subprocess
    import sys

    if config_path is None:
        from .config import default_data_dir

        config_path = default_data_dir() / "config.json"

    if enabled:
        # Run the web app (which owns the recorder) at logon/startup.
        # We wrap the command so the working directory is the config folder,
        # otherwise relative paths (recordings/, config.json) resolve wrong.
        if getattr(sys, "frozen", False):
            # Packaged exe — just run it with the config path.
            exe = sys.executable
            args = f'cmd /c "cd /d "{config_path.parent}" && "{exe}" --config "{config_path}""'
        else:
            python = sys.executable
            args = (
                f'cmd /c "cd /d "{config_path.parent}" && "{python}" -m watchtower.api '
                f'--config "{config_path}""'
            )
        cmd = [
            "schtasks",
            "/Create",
            "/TN",
            "WatchtowerRecorder",
            "/TR",
            args,
            "/SC",
            "ONLOGON",
            "/RL",
            "LIMITED",
            "/F",
        ]
    else:
        cmd = ["schtasks", "/Delete", "/TN", "WatchtowerRecorder", "/F"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return {
                "ok": False,
                "message": result.stderr.strip() or "Couldn't update auto-start",
            }
    except Exception as e:
        return {"ok": False, "message": str(e)}

    return {"ok": True, "enabled": enabled}


def _ultralytics_installed() -> bool:
    """Return whether the YOLO object-detection package is available."""
    try:
        import ultralytics  # noqa: F401

        return True
    except ImportError:
        return False


def _install_ultralytics() -> dict:
    """Install ultralytics (and torch) via pip. Returns a status dict.

    This is a large download (~2GB with torch), so it runs in a background
    thread and the UI polls for progress.
    """
    import subprocess
    import sys

    if _ultralytics_installed():
        return {"ok": True, "installed": True, "message": "Already installed"}

    def _run():
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "ultralytics"],
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True, "installed": False, "message": "Installing…"}


class LoginRequest(BaseModel):
    password: str


class CredentialsChecker:
    """Authenticates UI logins against the configured password.

    The UI password is stored in the (git-ignored) config.json, alongside the
    camera credentials. It is compared in constant time to avoid side-channel
    timing leaks.
    """

    def __init__(self, config: Config):
        self._enabled = bool(config.ui_password)
        self._stored = config.ui_password

    @property
    def enabled(self) -> bool:
        return self._enabled

    def verify(self, password: str) -> bool:
        if not self._enabled:
            return True
        return hmac.compare_digest(password, self._stored)


class SessionStore:
    """Store of valid login session tokens.

    Tokens are persisted to a small file so they survive a server restart
    (e.g. the "Restart server" button in Settings) without logging the user
    out. Tokens are random 32-byte secrets, so storing them on disk carries
    the same trust level as the UI password in config.json.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._tokens: set[str] = set()
        if path is not None and path.exists():
            try:
                self._tokens = set(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, TypeError):
                self._tokens = set()

    def _persist(self) -> None:
        if self._path is not None:
            self._path.write_text(
                json.dumps(sorted(self._tokens)), encoding="utf-8"
            )

    def create(self) -> str:
        token = secrets.token_urlsafe(32)
        self._tokens.add(token)
        self._persist()
        return token

    def valid(self, token: str | None) -> bool:
        return token is not None and token in self._tokens

    def revoke(self, token: str) -> None:
        self._tokens.discard(token)
        self._persist()


class CameraSettings(BaseModel):
    """Editable camera settings. Passwords are intentionally NOT included."""

    name: str
    host: str
    rtsp_port: int = 554
    rtsp_path: str = "/live/ch0"
    pre_seconds: float = 30.0
    post_seconds: float = 5.0
    min_duration: float = 2.0
    sensitivity: float = 0.02
    snapshot_on_motion: bool = True
    detector: str = "motion"
    detect_categories: list[str] = ["person"]


class SettingsUpdate(BaseModel):
    """Fields the UI is allowed to change."""

    cameras: list[CameraSettings] | None = None
    retention_days: int | None = None
    max_storage_gb: float | None = None
    notifications_enabled: bool | None = None


class AutoStartRequest(BaseModel):
    """Toggle for running Watchtower automatically at login."""

    enabled: bool


class ChangePasswordRequest(BaseModel):
    """Request to change the UI login password."""

    current_password: str = ""
    new_password: str


class ParseRtspRequest(BaseModel):
    url: str


class AddCameraRequest(BaseModel):
    """A camera to add. Passwords are stored in config.json (git-ignored)."""

    name: str
    host: str
    rtsp_port: int = 554
    username: str = "admin"
    password: str = ""
    rtsp_path: str = "/live/ch0"


def create_app(
    config: Config,
    config_path: Path | None = None,
    live_stream_factory=None,
) -> FastAPI:
    """Build the FastAPI app bound to the given config.

    ``config_path`` is the config.json file to persist settings changes to.
    If omitted, settings writes are rejected (read-only mode).

    ``live_stream_factory`` is an optional callable ``(CameraConfig) -> LiveStream``
    used to build the live stream for a camera. Tests inject a fake here so they
    don't need a real RTSP camera.
    """
    backend = LocalDiskBackend(config.output_dir)
    if live_stream_factory is None:
        live_stream_factory = LiveStream

    # Run the motion recorder in the background so notifications fire
    # automatically while the web app is running.
    recorder = RecorderManager(config)

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        recorder.start()
        yield
        recorder.stop()

    app = FastAPI(title="watchtower", version="0.1.0", lifespan=lifespan)

    # CORS with credentials support so the browser UI can send/receive cookies.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    creds = CredentialsChecker(config)
    # Persist sessions next to config.json so a restart doesn't log the user out.
    session_path = (
        config_path.with_name(".wt_sessions.json") if config_path is not None else None
    )
    sessions = SessionStore(session_path)

    @app.post("/login")
    def login(req: LoginRequest, response: Response):
        """Authenticate and set a session cookie."""
        if not creds.verify(req.password):
            return JSONResponse(status_code=401, content={"detail": "Invalid password"})
        token = sessions.create()
        response.set_cookie(
            COOKIE_NAME,
            token,
            httponly=True,
            samesite="lax",
            max_age=30 * 86400,  # 30 days
        )
        return {"ok": True}

    @app.post("/logout")
    def logout(request: Request, response: Response):
        sessions.revoke(request.cookies.get(COOKIE_NAME, ""))
        response.delete_cookie(COOKIE_NAME)

    @app.get("/auth-status")
    def auth_status(request: Request) -> dict:
        """Return whether a valid session exists (for the UI to check on load)."""
        if not creds.enabled:
            return {"authenticated": True}
        return {"authenticated": sessions.valid(request.cookies.get(COOKIE_NAME))}

    def auth(request: Request) -> None:
        """Require a valid session unless auth is disabled."""
        if not creds.enabled:
            return
        if not sessions.valid(request.cookies.get(COOKIE_NAME)):
            raise HTTPException(status_code=401, detail="Not authenticated")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/status", dependencies=[Depends(auth)])
    def status() -> dict:
        """Return server health info for the Settings "Server" panel."""
        return {
            "status": "ok",
            "version": app.version,
            "uptime_s": int(time.time() - _START_TIME),
            "web_port": config.web_port,
            "output_dir": str(config.output_dir),
            "camera_count": len(config.cameras),
        }

    @app.get("/storage", dependencies=[Depends(auth)])
    def storage() -> dict:
        """Return disk usage for the Settings "Storage" panel.

        Reports total recordings size, the configured cap, and a per-camera
        breakdown so the UI can show who is using the most space.
        """
        clips = backend.list()
        total = sum(p.stat().st_size for p in clips)
        cap_bytes = config.max_storage_gb * (1024**3) if config.max_storage_gb > 0 else 0

        # Attribute each clip to a camera. Prefer the manifest's camera field
        # (accurate even for clips stored at the recordings root); fall back to
        # the first path segment. Clips with no manifest and no camera folder
        # are grouped under "Uncategorised".
        per_camera: dict[str, int] = {}
        for p in clips:
            cam = "unknown"
            manifest = backend.manifest_path(p)
            if manifest.exists():
                try:
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    cam = data.get("camera") or cam
                except (json.JSONDecodeError, TypeError):
                    pass
            if cam == "unknown":
                parts = p.relative_to(backend.root).parts
                cam = parts[0] if parts else "unknown"
                if cam.endswith(".mp4"):
                    cam = "Uncategorised"
            per_camera[cam] = per_camera.get(cam, 0) + p.stat().st_size

        return {
            "total_bytes": total,
            "max_storage_gb": config.max_storage_gb,
            "cap_bytes": cap_bytes,
            "clip_count": len(clips),
            "per_camera": [
                {"camera": name, "bytes": size}
                for name, size in sorted(per_camera.items(), key=lambda kv: -kv[1])
            ],
        }

    @app.post("/restart", dependencies=[Depends(auth)])
    def restart() -> dict:
        """Ask the launcher to restart the backend.

        The API process exits with a special code; scripts/dev.js watches for
        that code and respawns it. If the backend wasn't started by the
        launcher, this just shuts it down.
        """
        # Give the response a moment to flush before we exit.
        threading.Timer(0.5, lambda: os._exit(RESTART_EXIT_CODE)).start()
        return {"ok": True, "message": "Restarting…"}

    @app.post("/notifications/test", dependencies=[Depends(auth)])
    def test_notification() -> dict:
        """Send a test Windows toast so the user can confirm notifications work."""
        sent = recorder.send_test_notification()
        if not sent:
            return {
                "ok": False,
                "message": "Notifications aren't available. Make sure they're enabled and you're on Windows.",
            }
        return {"ok": True, "message": "Test notification sent ✓"}

    @app.get("/detection/status", dependencies=[Depends(auth)])
    def detection_status() -> dict:
        """Return whether the AI object-detection package is installed."""
        return {"installed": _ultralytics_installed()}

    @app.post("/detection/install", dependencies=[Depends(auth)])
    def detection_install() -> dict:
        """Install the AI object-detection package (ultralytics + torch)."""
        return _install_ultralytics()

    @app.get("/live", dependencies=[Depends(auth)])
    def list_live_cameras() -> list[dict]:
        """Return cameras available for live viewing (no credentials)."""
        return [
            {"name": c.name, "host": c.host, "rtsp_path": c.rtsp_path}
            for c in config.cameras
        ]

    @app.get("/live/{camera_name}/stream", dependencies=[Depends(auth)])
    def live_stream(camera_name: str) -> StreamingResponse:
        """Serve a camera's live feed as an MJPEG stream (browser-playable)."""
        cam = next((c for c in config.cameras if c.name == camera_name), None)
        if cam is None:
            raise HTTPException(status_code=404, detail="Camera not found")
        stream = live_stream_factory(cam)
        return StreamingResponse(
            _mjpeg_generator(stream),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get("/clips", dependencies=[Depends(auth)])
    def list_clips() -> list[dict]:
        """Return metadata for every stored clip (oldest first)."""
        return [m.__dict__ for m in backend.list_metadata()]

    @app.get("/clips/{clip_id}/stream", dependencies=[Depends(auth)])
    def stream_clip(clip_id: str) -> FileResponse:
        """Serve a clip's MP4 with HTTP range support (enables seeking)."""
        path = _resolve_clip(backend, clip_id)
        return FileResponse(path, media_type="video/mp4")

    @app.get("/clips/{clip_id}/download", dependencies=[Depends(auth)])
    def download_clip(clip_id: str) -> FileResponse:
        """Download a clip as an attachment."""
        path = _resolve_clip(backend, clip_id)
        return FileResponse(path, media_type="video/mp4", filename=path.name)

    @app.delete("/clips/{clip_id}", dependencies=[Depends(auth)])
    def delete_clip(clip_id: str) -> dict:
        """Delete a clip and its manifest."""
        path = _resolve_clip(backend, clip_id)
        backend.delete(path)
        return {"deleted": clip_id}

    @app.get("/settings", dependencies=[Depends(auth)])
    def get_settings() -> dict:
        """Return editable settings. Passwords are never exposed."""
        return {
            "retention_days": config.retention_days,
            "max_storage_gb": config.max_storage_gb,
            "notifications_enabled": config.notifications_enabled,
            "auto_start": _auto_start_status()["enabled"],
            "cameras": [
                {
                    "name": c.name,
                    "host": c.host,
                    "rtsp_port": c.rtsp_port,
                    "rtsp_path": c.rtsp_path,
                    "pre_seconds": c.pre_seconds,
                    "post_seconds": c.post_seconds,
                    "min_duration": c.min_duration,
                    "sensitivity": c.sensitivity,
                    "snapshot_on_motion": c.snapshot_on_motion,
                    "detector": c.detector,
                    "detect_categories": c.detect_categories,
                }
                for c in config.cameras
            ],
        }

    @app.put("/settings", dependencies=[Depends(auth)])
    def update_settings(update: SettingsUpdate) -> dict:
        """Persist editable settings to config.json (passwords untouched)."""
        if config_path is None:
            raise HTTPException(status_code=400, detail="Settings persistence is disabled")

        raw = json.loads(config_path.read_text(encoding="utf-8"))

        if update.retention_days is not None:
            raw["retention_days"] = update.retention_days
            config.retention_days = update.retention_days
        if update.max_storage_gb is not None:
            raw["max_storage_gb"] = update.max_storage_gb
            config.max_storage_gb = update.max_storage_gb
        if update.notifications_enabled is not None:
            raw["notifications_enabled"] = update.notifications_enabled
            config.notifications_enabled = update.notifications_enabled

        if update.cameras is not None:
            # Merge by name so we never clobber passwords that live in config.json.
            by_name = {c.name: c for c in config.cameras}
            new_cameras = []
            for cam in update.cameras:
                existing = by_name.get(cam.name)
                entry = {
                    "name": cam.name,
                    "host": cam.host,
                    "rtsp_port": cam.rtsp_port,
                    "rtsp_path": cam.rtsp_path,
                    "pre_seconds": cam.pre_seconds,
                    "post_seconds": cam.post_seconds,
                    "min_duration": cam.min_duration,
                    "sensitivity": cam.sensitivity,
                    "snapshot_on_motion": cam.snapshot_on_motion,
                    "detector": cam.detector,
                    "detect_categories": cam.detect_categories,
                }
                if existing is not None:
                    # Preserve the stored password and username.
                    entry["username"] = existing.username
                    entry["password"] = existing.password
                new_cameras.append(entry)
            raw["cameras"] = new_cameras
            config.cameras = [
                Config._parse_camera(c) for c in new_cameras
            ]

        config_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

        # Apply the notifications toggle immediately (no full restart needed).
        recorder.set_notifications(config.notifications_enabled)

        # Settings changed — restart the recorder so it picks up new cameras
        # and detection settings.
        recorder.restart()
        return get_settings()

    @app.put("/settings/password", dependencies=[Depends(auth)])
    def change_password(req: ChangePasswordRequest) -> dict:
        """Change the UI login password (persisted to config.json)."""
        if config_path is None:
            raise HTTPException(status_code=400, detail="Settings persistence is disabled")

        # If a password is currently set, require the current one to change it.
        if creds.enabled and not creds.verify(req.current_password):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

        if len(req.new_password) < 4:
            raise HTTPException(status_code=400, detail="Password must be at least 4 characters")

        raw = json.loads(config_path.read_text(encoding="utf-8"))
        raw["ui_password"] = req.new_password
        config_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

        # Update the live checker so the new password takes effect immediately.
        config.ui_password = req.new_password
        creds._stored = req.new_password
        creds._enabled = bool(req.new_password)

        return {"ok": True}

    @app.put("/settings/auto-start", dependencies=[Depends(auth)])
    def set_auto_start(req: AutoStartRequest) -> dict:
        """Enable/disable running Watchtower automatically at login."""
        if config_path is None:
            raise HTTPException(status_code=400, detail="Settings persistence is disabled")

        result = _set_auto_start(req.enabled, config_path)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "Failed"))

        # Persist the preference so the UI reflects it on next load.
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        raw["auto_start"] = req.enabled
        config_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        config.auto_start = req.enabled
        return {"ok": True, "enabled": req.enabled}

    @app.post("/camera/parse", dependencies=[Depends(auth)])
    def parse_camera(req: ParseRtspRequest) -> dict:
        """Parse a pasted RTSP link into camera fields."""
        try:
            return parse_rtsp_url(req.url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/camera/test", dependencies=[Depends(auth)])
    def test_camera(req: AddCameraRequest) -> dict:
        """Try to connect to a camera and report whether it works.

        Returns a friendly ``message`` and ``tips`` list on failure so the UI
        can guide a non-technical user through troubleshooting.
        """
        cam = Config._parse_camera(req.model_dump())
        ok, message, tips = _test_rtsp_connection(cam)
        return {"ok": ok, "message": message, "tips": tips}

    @app.post("/camera", dependencies=[Depends(auth)])
    def add_camera(req: AddCameraRequest) -> dict:
        """Add a camera to config.json (persisted)."""
        if config_path is None:
            raise HTTPException(status_code=400, detail="Settings persistence is disabled")

        raw = json.loads(config_path.read_text(encoding="utf-8"))
        cameras = raw.setdefault("cameras", [])

        # Avoid duplicate names.
        if any(c.get("name") == req.name for c in cameras):
            raise HTTPException(status_code=400, detail="A camera with that name already exists")

        cameras.append(req.model_dump())
        config_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        config.cameras = [Config._parse_camera(c) for c in cameras]
        recorder.restart()
        return {"ok": True, "name": req.name}

    @app.delete("/camera/{camera_name}", dependencies=[Depends(auth)])
    def delete_camera(camera_name: str) -> dict:
        """Remove a camera from config.json (persisted)."""
        if config_path is None:
            raise HTTPException(status_code=400, detail="Settings persistence is disabled")

        raw = json.loads(config_path.read_text(encoding="utf-8"))
        cameras = raw.get("cameras", [])
        remaining = [c for c in cameras if c.get("name") != camera_name]
        if len(remaining) == len(cameras):
            raise HTTPException(status_code=404, detail="Camera not found")

        raw["cameras"] = remaining
        config_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        config.cameras = [Config._parse_camera(c) for c in remaining]
        recorder.restart()
        return {"deleted": camera_name}

    @app.delete("/cameras", dependencies=[Depends(auth)])
    def clear_cameras() -> dict:
        """Remove all cameras from config.json (persisted)."""
        if config_path is None:
            raise HTTPException(status_code=400, detail="Settings persistence is disabled")

        raw = json.loads(config_path.read_text(encoding="utf-8"))
        raw["cameras"] = []
        config_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        config.cameras = []
        recorder.restart()
        return {"deleted": len(config.cameras)}

    return app


def _resolve_clip(backend: LocalDiskBackend, clip_id: str) -> Path:
    """Resolve a clip id to a real path, guarding against path traversal."""
    # clip_id is the clip's filename (e.g. "cam_20260829_120000Z.mp4").
    # Reject anything that isn't a bare filename so callers can't escape the
    # recordings root via "../".
    name = Path(clip_id).name
    if name != clip_id or not name.endswith(".mp4"):
        raise HTTPException(status_code=404, detail="Clip not found")

    # Find the clip by filename across the tree (filenames are unique because
    # they embed a timestamp).
    for path in backend.list():
        if path.name == name:
            return path
    raise HTTPException(status_code=404, detail="Clip not found")


def _test_rtsp_connection(cam, timeout: float = 5.0) -> tuple[bool, str, list[str]]:
    """Try to open the camera's RTSP stream, with a timeout.

    Returns (ok, message, tips). On failure, ``tips`` holds plain-language
    troubleshooting steps for a non-technical user. The connection attempt runs
    in a thread so it can't hang the request if the camera is unreachable.
    """
    import threading

    result: dict = {}

    def _attempt():
        try:
            import cv2
        except ImportError:  # pragma: no cover - env-dependent
            result["error"] = "Video support isn't installed."
            return
        cap = cv2.VideoCapture(cam.rtsp_url)
        try:
            ok, _ = cap.read()
            result["ok"] = ok
        finally:
            cap.release()

    t = threading.Thread(target=_attempt, daemon=True)
    t.start()
    t.join(timeout)

    if "error" in result:
        return (False, result["error"], ["Install OpenCV and try again."])
    if "ok" not in result:
        # Timed out — the camera is unreachable.
        return (
            False,
            "Couldn't connect to the camera.",
            [
                "Make sure your computer and camera are on the same network (Wi-Fi).",
                "Check that the camera is powered on and connected.",
                "Double-check the username and password in the link.",
                "If it still fails, restart the camera and try again.",
            ],
        )
    if result["ok"]:
        return (True, "Connected! Your camera is working.", [])
    return (
        False,
        "Couldn't connect to the camera.",
        [
            "Make sure your computer and camera are on the same network (Wi-Fi).",
            "Check that the camera is powered on and connected.",
            "Double-check the username and password in the link.",
            "If it still fails, restart the camera and try again.",
        ],
    )


def _mjpeg_generator(stream: LiveStream):
    """Yield MJPEG multipart chunks from a live camera stream."""
    try:
        for frame in stream.frames():
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
    finally:
        stream.close()


def main() -> None:
    """Run the API server from the CLI: python -m watchtower.api --config config.json"""
    import argparse

    import uvicorn

    from .config import default_data_dir

    p = argparse.ArgumentParser(description="watchtower web API")
    p.add_argument(
        "--config",
        type=Path,
        default=default_data_dir() / "config.json",
        help="config.json path (default: %APPDATA%/Watchtower/config.json)",
    )
    p.add_argument("--host", default="127.0.0.1", help="bind address (default: localhost)")
    p.add_argument("--port", type=int, default=None, help="override config web_port")
    args = p.parse_args()

    # First run: create a default config so the app "just works" without the
    # user having to find or copy a config file.
    if not args.config.exists():
        args.config.parent.mkdir(parents=True, exist_ok=True)
        args.config.write_text(
            json.dumps(
                {
                    "output_dir": "recordings",
                    "retention_days": 30,
                    "max_storage_gb": 20,
                    "notifications_enabled": False,
                    "web_port": 8000,
                    "ui_password": "",
                    "cameras": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    cfg = Config.from_file(args.config)
    port = args.port or cfg.web_port
    uvicorn.run(create_app(cfg, config_path=args.config), host=args.host, port=port)


if __name__ == "__main__":
    main()