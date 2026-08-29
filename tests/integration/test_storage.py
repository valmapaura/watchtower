"""Integration tests for the LocalDisk storage backend."""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from watchtower.storage import ClipMetadata, LocalDiskBackend


def test_save_creates_file_and_manifest(tmp_path):
    clip = tmp_path / "source.mp4"
    clip.write_bytes(b"fake-video-bytes")
    backend = LocalDiskBackend(tmp_path / "recordings")
    meta = ClipMetadata(filename="source.mp4", camera="cam", start_utc="2026-08-29T12:00:00")
    dest = backend.save(clip, meta)

    assert dest.exists()
    assert clip.exists()  # source untouched
    manifest = dest.with_suffix(dest.suffix + ".manifest.json")
    assert manifest.exists()
    assert "camera" in manifest.read_text()


def test_save_organizes_by_camera_and_date(tmp_path):
    clip = tmp_path / "source.mp4"
    clip.write_bytes(b"x")
    backend = LocalDiskBackend(tmp_path / "recordings")
    backend.save(clip, ClipMetadata("source.mp4", "cam", "2026-08-29T12:00:00"))
    expected = tmp_path / "recordings" / "cam" / "2026-08-29" / "source.mp4"
    assert expected.exists()


def test_list_finds_clips(tmp_path):
    backend = LocalDiskBackend(tmp_path / "recordings")
    for i in range(2):
        clip = tmp_path / f"clip{i}.mp4"
        clip.write_bytes(b"x")
        backend.save(clip, ClipMetadata(f"clip{i}.mp4", "cam", "2026-08-29T12:00:00"))
    clips = backend.list()
    assert len(clips) == 2
    assert all(p.suffix == ".mp4" for p in clips)


def test_delete_removes_clip_and_manifest(tmp_path):
    clip = tmp_path / "source.mp4"
    clip.write_bytes(b"x")
    backend = LocalDiskBackend(tmp_path / "recordings")
    dest = backend.save(clip, ClipMetadata("source.mp4", "cam", "2026-08-29T12:00:00"))
    manifest = dest.with_suffix(dest.suffix + ".manifest.json")
    backend.delete(dest)
    assert not dest.exists()
    assert not manifest.exists()


def _save_with_mtime(backend, name, age_days, camera="cam"):
    """Save a clip and backdate its file mtime by `age_days` days."""
    clip = Path(tempfile.mkdtemp()) / name
    clip.write_bytes(b"x")
    dest = backend.save(clip, ClipMetadata(name, camera, "2026-08-29T12:00:00"))
    old = time.time() - age_days * 86400
    os.utime(dest, (old, old))
    return dest


def test_cleanup_removes_old_clips_keeps_new(tmp_path):
    backend = LocalDiskBackend(tmp_path / "recordings")
    _save_with_mtime(backend, "old.mp4", age_days=40)
    _save_with_mtime(backend, "new.mp4", age_days=1)
    removed = backend.cleanup(retention_days=30, now=time.time())
    assert removed == 1
    assert not (tmp_path / "recordings" / "cam" / "2026-08-29" / "old.mp4").exists()
    assert (tmp_path / "recordings" / "cam" / "2026-08-29" / "new.mp4").exists()


def test_cleanup_respects_retention_days_off(tmp_path):
    backend = LocalDiskBackend(tmp_path / "recordings")
    _save_with_mtime(backend, "old.mp4", age_days=40)
    # retention_days=0 means "never delete"
    removed = backend.cleanup(retention_days=0)
    assert removed == 0
    assert len(backend.list()) == 1
