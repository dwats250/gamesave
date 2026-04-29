from __future__ import annotations

from datetime import datetime
from pathlib import Path, PurePosixPath
import shutil

from .config import Config
from .models import ActionType, PlannedAction
from .sync import local_path_for_key


def backup_root(config: Config, *, timestamp: str | None = None) -> Path:
    timestamp = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    return config.sync_dir / "backups" / timestamp


def backup_path(root: Path, side: str, key: str) -> Path:
    return root / side / Path(*PurePosixPath(key).parts)


def copy_if_present(source: Path | None, target: Path) -> bool:
    if source is None or not source.exists() or not source.is_file():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def backup_actions(config: Config, actions: list[PlannedAction], *, timestamp: str | None = None) -> Path | None:
    changed = [action for action in actions if action.action != ActionType.SKIP]
    if not changed:
        return None

    root = backup_root(config, timestamp=timestamp)
    copied = 0
    for action in changed:
        local = local_path_for_key(config, action.key)
        sync = config.sync_dir / "saves" / Path(*PurePosixPath(action.key).parts)
        copied += int(copy_if_present(local, backup_path(root, "local", action.key)))
        copied += int(copy_if_present(sync, backup_path(root, "sync", action.key)))

    if copied:
        prune_backups(config)
        return root
    return None


def create_full_backup(config: Config, *, timestamp: str | None = None) -> Path:
    root = backup_root(config, timestamp=timestamp)
    copied = 0
    for sync_path in config.paths:
        if not sync_path.path.exists():
            continue
        for pattern in sync_path.patterns:
            for source in sync_path.path.rglob(pattern):
                if not source.is_file():
                    continue
                relative = source.relative_to(sync_path.path)
                target = root / "local" / sync_path.system / sync_path.kind / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                copied += 1
    if not copied:
        root.mkdir(parents=True, exist_ok=True)
    prune_backups(config)
    return root


def prune_backups(config: Config) -> None:
    root = config.sync_dir / "backups"
    if not root.exists():
        return
    snapshots = sorted(path for path in root.iterdir() if path.is_dir())
    overflow = len(snapshots) - config.max_backups_per_key
    for snapshot in snapshots[: max(0, overflow)]:
        shutil.rmtree(snapshot)
