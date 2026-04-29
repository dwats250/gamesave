from __future__ import annotations

from pathlib import Path

from .models import ActionType, FileRecord, PlannedAction
from .scanner import sync_file_path


def plan_sync(
    *,
    local_records: dict[str, FileRecord],
    sync_records: dict[str, FileRecord],
    previous_records: dict[str, dict],
    sync_dir: Path,
) -> list[PlannedAction]:
    actions: list[PlannedAction] = []
    keys = sorted(set(local_records) | set(sync_records))

    for key in keys:
        local = local_records.get(key)
        remote = sync_records.get(key)
        previous = previous_records.get(key)

        if local and not remote:
            actions.append(
                PlannedAction(ActionType.UPLOAD, key, local.path, sync_file_path(sync_dir, key), "missing from sync")
            )
            continue

        if remote and not local:
            actions.append(
                PlannedAction(ActionType.DOWNLOAD, key, remote.path, None, "missing locally")
            )
            continue

        if not local or not remote:
            continue

        if local.sha256 == remote.sha256:
            actions.append(PlannedAction(ActionType.SKIP, key, None, None, "unchanged"))
            continue

        previous_sha = previous.get("sha256") if isinstance(previous, dict) else None
        local_changed = local.sha256 != previous_sha
        remote_changed = remote.sha256 != previous_sha

        if previous_sha is None:
            actions.append(PlannedAction(ActionType.CONFLICT, key, local.path, remote.path, "different files with no baseline"))
        elif local_changed and remote_changed:
            actions.append(PlannedAction(ActionType.CONFLICT, key, local.path, remote.path, "both sides changed"))
        elif local_changed:
            actions.append(PlannedAction(ActionType.UPLOAD, key, local.path, remote.path, "local changed"))
        elif remote_changed:
            actions.append(PlannedAction(ActionType.DOWNLOAD, key, remote.path, local.path, "sync changed"))
        else:
            actions.append(PlannedAction(ActionType.SKIP, key, None, None, "metadata changed only"))

    return actions
