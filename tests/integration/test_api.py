"""Integration tests for the FastAPI web layer (Phase 4)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from watchtower.api import create_app
from watchtower.config import Config
from watchtower.storage import ClipMetadata, LocalDiskBackend


def _make_config(tmp_path, api_token: str = "") -> Config:
    return Config(
        cameras=[],
        output_dir=tmp_path / "recordings",
        api_token=api_token,
    )


def _seed_clip(tmp_path, name: str = "cam_20260829_120000Z.mp4") -> Path:
    backend = LocalDiskBackend(tmp_path / "recordings")
    src = tmp_path / name
    src.write_bytes(b"fake-video-bytes")
    meta = ClipMetadata(
        filename=name,
        camera="cam",
        start_utc="2026-08-29T12:00:00",
        motion_score=42.0,
    )
    return backend.save(src, meta)


def test_health(tmp_path):
    client = TestClient(create_app(_make_config(tmp_path)))
    assert client.get("/health").json() == {"status": "ok"}


def test_list_clips_returns_metadata(tmp_path):
    _seed_clip(tmp_path)
    client = TestClient(create_app(_make_config(tmp_path)))
    resp = client.get("/clips")
    assert resp.status_code == 200
    clips = resp.json()
    assert len(clips) == 1
    assert clips[0]["filename"] == "cam_20260829_120000Z.mp4"
    assert clips[0]["camera"] == "cam"
    assert clips[0]["motion_score"] == 42.0


def test_stream_clip_serves_file(tmp_path):
    _seed_clip(tmp_path)
    client = TestClient(create_app(_make_config(tmp_path)))
    resp = client.get("/clips/cam_20260829_120000Z.mp4/stream")
    assert resp.status_code == 200
    assert resp.content == b"fake-video-bytes"


def test_download_clip_attachment(tmp_path):
    _seed_clip(tmp_path)
    client = TestClient(create_app(_make_config(tmp_path)))
    resp = client.get("/clips/cam_20260829_120000Z.mp4/download")
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")


def test_delete_clip(tmp_path):
    _seed_clip(tmp_path)
    client = TestClient(create_app(_make_config(tmp_path)))
    resp = client.delete("/clips/cam_20260829_120000Z.mp4")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": "cam_20260829_120000Z.mp4"}
    assert client.get("/clips").json() == []


def test_unknown_clip_404(tmp_path):
    client = TestClient(create_app(_make_config(tmp_path)))
    assert client.get("/clips/nope.mp4/stream").status_code == 404


def test_path_traversal_rejected(tmp_path):
    _seed_clip(tmp_path)
    client = TestClient(create_app(_make_config(tmp_path)))
    # A clip id that tries to escape the recordings root must be rejected.
    resp = client.get("/clips/..%2F..%2Fsecret.mp4/stream")
    assert resp.status_code == 404


def test_api_token_required_when_set(tmp_path):
    _seed_clip(tmp_path)
    client = TestClient(create_app(_make_config(tmp_path, api_token="sekret")))
    # No token -> 401
    assert client.get("/clips").status_code == 401
    # Wrong token -> 401
    assert client.get("/clips", headers={"Authorization": "Bearer wrong"}).status_code == 401
    # Correct token -> 200
    resp = client.get("/clips", headers={"Authorization": "Bearer sekret"})
    assert resp.status_code == 200


def test_no_token_required_when_unset(tmp_path):
    _seed_clip(tmp_path)
    client = TestClient(create_app(_make_config(tmp_path, api_token="")))
    assert client.get("/clips").status_code == 200


# --- settings -------------------------------------------------------------


def _write_config(tmp_path, **overrides) -> Path:
    data = {
        "retention_days": 30,
        "notifications_enabled": False,
        "cameras": [
            {
                "name": "cam",
                "host": "192.168.1.247",
                "username": "admin",
                "password": "supersecret",
                "rtsp_path": "/live/ch0",
                "sensitivity": 0.02,
            }
        ],
    }
    data.update(overrides)
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_get_settings_never_exposes_password(tmp_path):
    cfg_path = _write_config(tmp_path)
    cfg = Config.from_file(cfg_path)
    client = TestClient(create_app(cfg, config_path=cfg_path))
    resp = client.get("/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cameras"][0]["sensitivity"] == 0.02
    assert "password" not in body["cameras"][0]
    assert "username" not in body["cameras"][0]


def test_update_sensitivity_preserves_password(tmp_path):
    cfg_path = _write_config(tmp_path)
    cfg = Config.from_file(cfg_path)
    client = TestClient(create_app(cfg, config_path=cfg_path))
    resp = client.put(
        "/settings",
        json={"cameras": [{"name": "cam", "host": "192.168.1.247", "sensitivity": 0.08}]},
    )
    assert resp.status_code == 200
    assert resp.json()["cameras"][0]["sensitivity"] == 0.08
    # Password must survive the round-trip in config.json.
    saved = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert saved["cameras"][0]["password"] == "supersecret"


def test_update_retention(tmp_path):
    cfg_path = _write_config(tmp_path)
    cfg = Config.from_file(cfg_path)
    client = TestClient(create_app(cfg, config_path=cfg_path))
    resp = client.put("/settings", json={"retention_days": 7})
    assert resp.status_code == 200
    assert resp.json()["retention_days"] == 7
    assert json.loads(cfg_path.read_text(encoding="utf-8"))["retention_days"] == 7


def test_update_settings_rejected_without_config_path(tmp_path):
    cfg = _make_config(tmp_path)
    client = TestClient(create_app(cfg, config_path=None))
    resp = client.put("/settings", json={"retention_days": 7})
    assert resp.status_code == 400