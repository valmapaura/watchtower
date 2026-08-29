"""Integration tests for the LocalDisk storage backend."""
from __future__ import annotations

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
