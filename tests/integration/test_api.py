"""Integration tests for the FastAPI web layer (Phase 4)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from watchtower.api import create_app
from watchtower.config import Config
from watchtower.storage import ClipMetadata, LocalDiskBackend


def _make_config(tmp_path, api_token: str = "", ui_password: str = "") -> Config:
    return Config(
        cameras=[],
        output_dir=tmp_path / "recordings",
        api_token=api_token,
        ui_password=ui_password,
    )


def _seed_clip(tmp_path, name: str = "cam_20260829_120000Z.mp4", category: str = "motion") -> Path:
    backend = LocalDiskBackend(tmp_path / "recordings")
    src = tmp_path / name
    src.write_bytes(b"fake-video-bytes")
    meta = ClipMetadata(
        filename=name,
        camera="cam",
        start_utc="2026-08-29T12:00:00",
        motion_score=42.0,
        category=category,
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
    assert clips[0]["category"] == "motion"


def test_list_clips_includes_category(tmp_path):
    _seed_clip(tmp_path, category="person")
    client = TestClient(create_app(_make_config(tmp_path)))
    clips = client.get("/clips").json()
    assert clips[0]["category"] == "person"


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


def test_ui_password_required_when_set(tmp_path):
    _seed_clip(tmp_path)
    client = TestClient(create_app(_make_config(tmp_path, ui_password="sekret")))
    # Not logged in -> 401
    assert client.get("/clips").status_code == 401
    # Wrong password -> 401
    assert client.post("/login", json={"password": "wrong"}).status_code == 401
    # Correct password -> 200 and sets a session cookie
    resp = client.post("/login", json={"password": "sekret"})
    assert resp.status_code == 200
    # With the cookie, the API is accessible.
    assert client.get("/clips").status_code == 200


def test_no_auth_required_when_password_unset(tmp_path):
    _seed_clip(tmp_path)
    client = TestClient(create_app(_make_config(tmp_path, ui_password="")))
    assert client.get("/clips").status_code == 200
    assert client.get("/auth-status").json() == {"authenticated": True}


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


def test_update_max_storage_gb(tmp_path):
    cfg_path = _write_config(tmp_path)
    cfg = Config.from_file(cfg_path)
    client = TestClient(create_app(cfg, config_path=cfg_path))
    resp = client.put("/settings", json={"max_storage_gb": 50})
    assert resp.status_code == 200
    assert resp.json()["max_storage_gb"] == 50
    assert json.loads(cfg_path.read_text(encoding="utf-8"))["max_storage_gb"] == 50


def test_update_settings_rejected_without_config_path(tmp_path):
    cfg = _make_config(tmp_path)
    client = TestClient(create_app(cfg, config_path=None))
    resp = client.put("/settings", json={"retention_days": 7})
    assert resp.status_code == 400


# --- live ----------------------------------------------------------------


def _make_config_with_camera(tmp_path, name="cam") -> Config:
    from watchtower.config import CameraConfig

    return Config(
        cameras=[CameraConfig(name=name, host="192.168.1.247")],
        output_dir=tmp_path / "recordings",
    )


def test_list_live_cameras(tmp_path):
    client = TestClient(create_app(_make_config_with_camera(tmp_path)))
    resp = client.get("/live")
    assert resp.status_code == 200
    cams = resp.json()
    assert len(cams) == 1
    assert cams[0]["name"] == "cam"
    # No credentials exposed.
    assert "password" not in cams[0]
    assert "username" not in cams[0]


def test_live_stream_unknown_camera_404(tmp_path):
    client = TestClient(create_app(_make_config_with_camera(tmp_path)))
    resp = client.get("/live/nope/stream")
    assert resp.status_code == 404


def test_live_stream_returns_mjpeg_media_type(tmp_path):
    class FakeStream:
        def __init__(self, cam):
            self.cam = cam

        def frames(self):
            yield b"\xff\xd8\xff\xe0fakejpeg"
            return

        def close(self):
            pass

    client = TestClient(
        create_app(_make_config_with_camera(tmp_path), live_stream_factory=FakeStream)
    )
    resp = client.get("/live/cam/stream")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("multipart/x-mixed-replace")
    # The body should contain the MJPEG frame boundary + JPEG bytes.
    assert b"--frame" in resp.content
    assert b"fakejpeg" in resp.content


# --- camera setup --------------------------------------------------------


def test_parse_rtsp_link(tmp_path):
    client = TestClient(create_app(_make_config(tmp_path)))
    resp = client.post(
        "/camera/parse",
        json={"url": "rtsp://admin:secret@192.168.1.50:554/live/ch0"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["host"] == "192.168.1.50"
    assert body["username"] == "admin"
    assert body["password"] == "secret"
    assert body["rtsp_port"] == 554
    assert body["rtsp_path"] == "/live/ch0"


def test_parse_rtsp_invalid_link(tmp_path):
    client = TestClient(create_app(_make_config(tmp_path)))
    resp = client.post("/camera/parse", json={"url": "not-a-link"})
    assert resp.status_code == 400


def test_add_camera_persists(tmp_path):
    cfg_path = _write_config(tmp_path)
    cfg = Config.from_file(cfg_path)
    client = TestClient(create_app(cfg, config_path=cfg_path))
    resp = client.post(
        "/camera",
        json={
            "name": "frontdoor",
            "host": "192.168.1.60",
            "username": "admin",
            "password": "pw",
            "rtsp_path": "/live/ch0",
        },
    )
    assert resp.status_code == 200
    saved = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert any(c["name"] == "frontdoor" for c in saved["cameras"])


def test_add_camera_duplicate_name(tmp_path):
    cfg_path = _write_config(tmp_path)
    cfg = Config.from_file(cfg_path)
    client = TestClient(create_app(cfg, config_path=cfg_path))
    resp = client.post(
        "/camera",
        json={"name": "cam", "host": "192.168.1.60", "password": "pw"},
    )
    assert resp.status_code == 400


def test_test_camera_returns_tips_on_failure(tmp_path):
    # No real camera here, so the connection test should fail gracefully
    # and return troubleshooting tips.
    client = TestClient(create_app(_make_config(tmp_path)))
    resp = client.post(
        "/camera/test",
        json={"name": "cam", "host": "192.168.1.99", "password": "pw"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert isinstance(body["tips"], list)
    assert len(body["tips"]) > 0


def test_delete_camera_persists(tmp_path):
    cfg_path = _write_config(tmp_path)
    cfg = Config.from_file(cfg_path)
    client = TestClient(create_app(cfg, config_path=cfg_path))
    resp = client.delete("/camera/cam")
    assert resp.status_code == 200
    saved = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert saved["cameras"] == []


def test_delete_camera_unknown_404(tmp_path):
    cfg_path = _write_config(tmp_path)
    cfg = Config.from_file(cfg_path)
    client = TestClient(create_app(cfg, config_path=cfg_path))
    resp = client.delete("/camera/nope")
    assert resp.status_code == 404


def test_clear_cameras(tmp_path):
    cfg_path = _write_config(tmp_path)
    cfg = Config.from_file(cfg_path)
    client = TestClient(create_app(cfg, config_path=cfg_path))
    resp = client.delete("/cameras")
    assert resp.status_code == 200
    saved = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert saved["cameras"] == []