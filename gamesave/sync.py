from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path, PurePosixPath
import shutil

from .config import Config, SyncPath
from .models import ActionType, PlannedAction
from .scanner import sync_file_path


def atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    shutil.copy2(source, tmp)
    os.replace(tmp, target)


def local_path_for_key(config: Config, key: str) -> Path | None:
    parts = PurePosixPath(key).parts
    if len(parts) < 3:
        return None
    system, kind, *relative = parts
    for sync_path in config.paths:
        if sync_path.system == system and sync_path.kind == kind:
            return sync_path.path.joinpath(*relative)
    return None


def conflict_path(target: Path, device_name: str, *, timestamp: str | None = None) -> Path:
    timestamp = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    return target.with_name(f"{target.stem}.conflict.{device_name}.{timestamp}{target.suffix}")


def apply_actions(config: Config, actions: list[PlannedAction]) -> None:
    for action in actions:
        if action.action == ActionType.SKIP:
            continue

        if action.action == ActionType.DOWNLOAD:
            if action.source is None:
                raise ValueError(f"download missing source for {action.key}")
            target = action.target or local_path_for_key(config, action.key)
            if target is None:
                continue
            atomic_copy(action.source, target)
            continue

        if action.action == ActionType.UPLOAD:
            if action.source is None:
                raise ValueError(f"upload missing source for {action.key}")
            target = action.target or sync_file_path(config.sync_dir, action.key)
            atomic_copy(action.source, target)
            continue

        if action.action == ActionType.CONFLICT:
            if action.source is None:
                raise ValueError(f"conflict missing source for {action.key}")
            target = sync_file_path(config.sync_dir, action.key)
            atomic_copy(action.source, conflict_path(target, config.device_name))
