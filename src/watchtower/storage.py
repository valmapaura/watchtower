"""Storage abstraction: a swappable backend for where footage lives.

Phase 1 ships ``LocalDiskBackend``. The interface is designed so future
backends (Google Drive, Firebase, S3, NAS) implement the same contract and
can be plugged in without touching the recorder.
"""
from __future__ import annotations

import json
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ClipMetadata:
    """Metadata written alongside each clip as ``manifest.json``."""

    filename: str
    camera: str
    start_utc: str
    duration_s: float = 0.0
    motion_score: float = 0.0
    recorded_by: str = "watchtower-motion-recorder"
    source_url: str = ""
    category: str = "motion"  # "motion" (frame-diff) or an object class (person, car, ...)

class StorageBackend(ABC):
    @abstractmethod
    def save(self, local_path: Path, metadata: ClipMetadata) -> Path:
        """Persist a clip + its manifest; return the stored path."""

    @abstractmethod
    def list(self) -> list[Path]:
        """Return stored clip paths (oldest first)."""

    @abstractmethod
    def get(self, path: Path) -> Path:
        """Return a path that can be opened/read for the given clip."""

    @abstractmethod
    def delete(self, path: Path) -> None:
        """Remove a stored clip and its manifest."""

    def cleanup(self, retention_days: int, now: float | None = None) -> int:
        """Delete clips older than ``retention_days``. Returns count removed.

        Subclasses may override; the default walks ``list()`` and uses each
        clip's mtime as its age.
        """
        if retention_days <= 0:
            return 0
        now = now if now is not None else time.time()
        cutoff = now - retention_days * 86400
        removed = 0
        for clip in self.list():
            try:
                if clip.stat().st_mtime < cutoff:
                    self.delete(clip)
                    removed += 1
            except FileNotFoundError:
                continue
        return removed


class LocalDiskBackend(StorageBackend):
    """Stores clips under ``root/<camera>/<date>/`` on local disk."""

    def __init__(self, root: Path | str):
        self.root = Path(root)

    def save(self, local_path: Path, metadata: ClipMetadata) -> Path:
        date_dir = self.root / metadata.camera / metadata.start_utc[:10]
        # Categorised clips live under <camera>/<date>/<category>/ so the UI
        # can filter by what triggered them. Plain motion stays at the root.
        if metadata.category and metadata.category != "motion":
            date_dir = date_dir / metadata.category
        date_dir.mkdir(parents=True, exist_ok=True)
        dest = date_dir / metadata.filename
        shutil.copyfile(local_path, dest)

        manifest = date_dir / f"{metadata.filename}.manifest.json"
        manifest.write_text(json.dumps(asdict(metadata), indent=2), encoding="utf-8")
        return dest

    def list(self) -> list[Path]:
        return sorted(self.root.rglob("*.mp4"))

    def get(self, path: Path) -> Path:
        return path

    def manifest_path(self, clip: Path) -> Path:
        """Return the manifest path that sits alongside a clip."""
        return clip.with_suffix(clip.suffix + ".manifest.json")

    def list_metadata(self) -> list[ClipMetadata]:
        """Return ``ClipMetadata`` for every stored clip (oldest first).

        Clips whose manifest is missing or unreadable are skipped so a
        partially-written clip never breaks the listing.
        """
        result: list[ClipMetadata] = []
        for clip in self.list():
            manifest = self.manifest_path(clip)
            if not manifest.exists():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                result.append(ClipMetadata(**data))
            except (json.JSONDecodeError, TypeError):
                continue
        return result

    def total_size(self) -> int:
        """Return the total size of all stored clips in bytes."""
        return sum(p.stat().st_size for p in self.list())

    def cleanup(
        self,
        retention_days: int,
        now: float | None = None,
        max_storage_gb: float = 0.0,
    ) -> int:
        """Delete clips by age and/or total size. Returns count removed.

        Two independent rules, whichever triggers first:
          * ``retention_days`` — delete clips older than this (0 = keep all).
          * ``max_storage_gb`` — delete the oldest clips until the total size
            of ``recordings/`` is under the cap (0 = unlimited).
        """
        removed = 0
        clips = self.list()

        # Rule 1: age-based retention.
        if retention_days > 0:
            now = now if now is not None else time.time()
            cutoff = now - retention_days * 86400
            for clip in clips:
                try:
                    if clip.stat().st_mtime < cutoff:
                        self.delete(clip)
                        removed += 1
                except FileNotFoundError:
                    continue

        # Rule 2: size cap — delete oldest first until under the limit.
        if max_storage_gb > 0:
            cap_bytes = max_storage_gb * (1024**3)
            # Re-list so we don't touch clips already removed by retention.
            for clip in self.list():
                if self.total_size() <= cap_bytes:
                    break
                try:
                    self.delete(clip)
                    removed += 1
                except FileNotFoundError:
                    continue

        return removed

    def delete(self, path: Path) -> None:
        manifest = self.manifest_path(path)
        path.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
