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
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from .config import Config
from .live import LiveStream
from .storage import LocalDiskBackend

COOKIE_NAME = "wt_session"


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
    """In-memory store of valid login session tokens."""

    def __init__(self) -> None:
        self._tokens: set[str] = set()

    def create(self) -> str:
        token = secrets.token_urlsafe(32)
        self._tokens.add(token)
        return token

    def valid(self, token: str | None) -> bool:
        return token is not None and token in self._tokens

    def revoke(self, token: str) -> None:
        self._tokens.discard(token)


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

    app = FastAPI(title="watchtower", version="0.1.0")

    # CORS with credentials support so the browser UI can send/receive cookies.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    creds = CredentialsChecker(config)
    sessions = SessionStore()

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
        return get_settings()

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

    p = argparse.ArgumentParser(description="watchtower web API")
    p.add_argument("--config", type=Path, default=Path("config.json"))
    p.add_argument("--host", default="127.0.0.1", help="bind address (default: localhost)")
    p.add_argument("--port", type=int, default=None, help="override config web_port")
    args = p.parse_args()

    cfg = Config.from_file(args.config)
    port = args.port or cfg.web_port
    uvicorn.run(create_app(cfg, config_path=args.config), host=args.host, port=port)


if __name__ == "__main__":
    main()