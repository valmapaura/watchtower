"""FastAPI web layer for the watchtower browser UI (Phase 4).

Serves the clip library over HTTP so a browser client can list, stream,
download, and delete recordings. This is a thin read/write layer over the
``StorageBackend`` — it does not run the recorder itself.

Security model (matches the project's "private by default" principle):
  * The server binds to localhost by default. To expose it on the LAN, set
    ``host`` explicitly when running (e.g. ``--host 0.0.0.0``).
  * If ``api_token`` is set in config.json, every request must carry it as a
    bearer token. When it is empty, the API is open (fine for localhost-only).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Config
from .storage import LocalDiskBackend

_bearer = HTTPBearer(auto_error=False)


def _require_token(
    config: Config,
    credentials: HTTPAuthorizationCredentials | None,
) -> None:
    """Raise 401 unless the request carries the configured bearer token."""
    if not config.api_token:
        return
    if credentials is None or credentials.credentials != config.api_token:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


def create_app(config: Config) -> FastAPI:
    """Build the FastAPI app bound to the given config."""
    backend = LocalDiskBackend(config.output_dir)

    app = FastAPI(title="watchtower", version="0.1.0")

    def auth(
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> None:
        _require_token(config, credentials)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

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
    uvicorn.run(create_app(cfg), host=args.host, port=port)


if __name__ == "__main__":
    main()