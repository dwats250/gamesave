from __future__ import annotations

from pathlib import Path, PurePosixPath
import time

from .config import Config, SyncPath
from .hashutil import file_sha256
from .models import FileRecord


def make_key(sync_path: SyncPath, file_path: Path) -> str:
    relative = file_path.relative_to(sync_path.path)
    return str(PurePosixPath(sync_path.system, sync_path.kind, *relative.parts))


def scan_local(config: Config, *, now: float | None = None) -> dict[str, FileRecord]:
    now = time.time() if now is None else now
    records: dict[str, FileRecord] = {}

    for sync_path in config.paths:
        if not sync_path.path.exists():
            continue

        for pattern in sync_path.patterns:
            for path in sync_path.path.rglob(pattern):
                if not path.is_file():
                    continue

                stat = path.stat()
                age_seconds = now - stat.st_mtime
                if age_seconds < config.stability_seconds:
                    continue

                key = make_key(sync_path, path)
                records[key] = FileRecord(
                    key=key,
                    path=path,
                    size=stat.st_size,
                    mtime_ns=stat.st_mtime_ns,
                    sha256=file_sha256(path),
                    device=config.device_name,
                )

    return records


def sync_file_path(sync_dir: Path, key: str) -> Path:
    return sync_dir / "saves" / Path(*PurePosixPath(key).parts)


def scan_sync_dir(sync_dir: Path) -> dict[str, FileRecord]:
    root = sync_dir / "saves"
    records: dict[str, FileRecord] = {}
    if not root.exists():
        return records

    for path in root.rglob("*"):
        if not path.is_file() or ".conflict." in path.name:
            continue

        stat = path.stat()
        key = str(PurePosixPath(*path.relative_to(root).parts))
        records[key] = FileRecord(
            key=key,
            path=path,
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            sha256=file_sha256(path),
        )

    return records
