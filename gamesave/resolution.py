from __future__ import annotations

from pathlib import Path

from .config import Config
from .scanner import sync_file_path
from .sync import atomic_copy, local_path_for_key


def resolve_conflict(config: Config, key: str, *, use: str, file_path: Path | None = None) -> tuple[Path, Path | None]:
    sync_target = sync_file_path(config.sync_dir, key)
    local_target = local_path_for_key(config, key)

    if use == "local":
        if local_target is None or not local_target.exists():
            raise FileNotFoundError(f"local file not found for {key}")
        atomic_copy(local_target, sync_target)
        return sync_target, None

    if use == "sync":
        if local_target is None:
            raise ValueError(f"no configured local path for {key}")
        if not sync_target.exists():
            raise FileNotFoundError(f"sync file not found for {key}")
        atomic_copy(sync_target, local_target)
        return local_target, None

    if use == "file":
        if file_path is None:
            raise ValueError("--file is required when --use file")
        if not file_path.exists():
            raise FileNotFoundError(f"resolution file not found: {file_path}")
        atomic_copy(file_path, sync_target)
        if local_target is not None:
            atomic_copy(file_path, local_target)
        return sync_target, local_target

    raise ValueError("--use must be local, sync, or file")
