"""Unit tests for config loading and RTSP URL building."""
from __future__ import annotations

import json

from watchtower.config import CameraConfig, Config


def test_rtsp_url_password_encoded():
    cam = CameraConfig(name="c", host="10.0.0.5", password="pa ss@word")
    assert cam.rtsp_url == "rtsp://admin:pa%20ss%40word@10.0.0.5:554/live/ch0"


def test_rtsp_url_plain():
    cam = CameraConfig(name="c", host="10.0.0.5", username="u", password="p", rtsp_path="/x")
    assert cam.rtsp_url == "rtsp://u:p@10.0.0.5:554/x"


def test_from_file_list_format(tmp_path):
    data = {
        "output_dir": "clips",
        "retention_days": 7,
        "cameras": [
            {"name": "a", "host": "1.1.1.1", "password": "x", "pre_seconds": 20, "post_seconds": 6}
        ],
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    cfg = Config.from_file(p)
    assert cfg.output_dir.name == "clips"
    assert cfg.retention_days == 7
    assert cfg.cameras[0].name == "a"
    assert cfg.cameras[0].pre_seconds == 20.0
    assert cfg.cameras[0].post_seconds == 6.0


def test_from_file_legacy_singular(tmp_path):
    data = {"camera": {"name": "cam", "host": "2.2.2.2", "password": "y"}}
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    cfg = Config.from_file(p)
    assert len(cfg.cameras) == 1
    assert cfg.cameras[0].host == "2.2.2.2"


def test_from_file_missing_key(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{}", encoding="utf-8")
    import pytest

    with pytest.raises(ValueError):
        Config.from_file(p)


def test_new_top_level_fields_defaults(tmp_path):
    data = {"cameras": [{"name": "a", "host": "1.1.1.1", "password": "x"}]}
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    cfg = Config.from_file(p)
    assert cfg.storage_backend == "local"
    assert cfg.log_level == "INFO"
    assert cfg.timezone == "UTC"
    assert cfg.notifications_enabled is False
    assert cfg.max_storage_gb == 20.0


def test_max_storage_gb_override(tmp_path):
    data = {
        "max_storage_gb": 50,
        "cameras": [{"name": "a", "host": "1.1.1.1", "password": "x"}],
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    cfg = Config.from_file(p)
    assert cfg.max_storage_gb == 50.0


def test_new_top_level_fields_override(tmp_path):
    data = {
        "storage_backend": "google_drive",
        "log_level": "DEBUG",
        "timezone": "Africa/Harare",
        "notifications_enabled": True,
        "cameras": [{"name": "a", "host": "1.1.1.1", "password": "x"}],
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    cfg = Config.from_file(p)
    assert cfg.storage_backend == "google_drive"
    assert cfg.log_level == "DEBUG"
    assert cfg.timezone == "Africa/Harare"
    assert cfg.notifications_enabled is True


def test_snapshot_on_motion_default_true(tmp_path):
    data = {"cameras": [{"name": "a", "host": "1.1.1.1", "password": "x"}]}
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    cfg = Config.from_file(p)
    assert cfg.cameras[0].snapshot_on_motion is True
