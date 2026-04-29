from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import load_config
from .lock import sync_lock
from .manifest import load_manifest, write_manifest
from .models import ActionType, PlannedAction
from .planner import plan_sync
from .scanner import scan_local, scan_sync_dir
from .sync import apply_actions


def print_actions(actions: list[PlannedAction]) -> None:
    for action in actions:
        print(f"{action.action.value:8} {action.key} ({action.reason})")


def build_plan(config_path: Path) -> tuple[object, list[PlannedAction], dict]:
    config = load_config(config_path)
    local_records = scan_local(config)
    sync_records = scan_sync_dir(config.sync_dir)
    previous_records = load_manifest(config.sync_dir)
    actions = plan_sync(
        local_records=local_records,
        sync_records=sync_records,
        previous_records=previous_records,
        sync_dir=config.sync_dir,
    )
    return config, actions, local_records


def cmd_scan(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    records = scan_local(config)
    for key in sorted(records):
        record = records[key]
        print(f"{key} {record.size} {record.sha256}")
    print(f"{len(records)} local file(s)")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    _, actions, _ = build_plan(args.config)
    print_actions(actions)
    counts = {action_type: 0 for action_type in ActionType}
    for action in actions:
        counts[action.action] += 1
    print(
        "summary "
        + " ".join(f"{action_type.value.lower()}={counts[action_type]}" for action_type in ActionType)
    )
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    config, actions, _ = build_plan(args.config)
    print_actions(actions)

    if args.dry_run:
        print("dry-run: no files copied")
        return 0

    with sync_lock(config.sync_dir):
        apply_actions(config, actions)
        refreshed = scan_sync_dir(config.sync_dir)
        write_manifest(config.sync_dir, refreshed)

    changed = sum(1 for action in actions if action.action != ActionType.SKIP)
    print(f"applied {changed} action(s)")
    return 0


def cmd_conflicts(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    root = config.sync_dir / "saves"
    if not root.exists():
        print("no conflicts")
        return 0

    conflicts = sorted(path for path in root.rglob("*") if path.is_file() and ".conflict." in path.name)
    if not conflicts:
        print("no conflicts")
        return 0

    for path in conflicts:
        print(path.relative_to(root))
    print(f"{len(conflicts)} conflict file(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    config_parent = argparse.ArgumentParser(add_help=False)
    config_parent.add_argument("--config", type=Path, default=argparse.SUPPRESS)

    parser = argparse.ArgumentParser(prog="gamesave")
    parser.add_argument("--config", type=Path, default=Path("gamesave.toml"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="scan local configured save folders", parents=[config_parent])
    scan.set_defaults(func=cmd_scan)

    status = subparsers.add_parser("status", help="show planned sync actions", parents=[config_parent])
    status.set_defaults(func=cmd_status)

    sync = subparsers.add_parser("sync", help="apply planned sync actions", parents=[config_parent])
    sync.add_argument("--dry-run", action="store_true")
    sync.set_defaults(func=cmd_sync)

    conflicts = subparsers.add_parser("conflicts", help="list preserved conflict files", parents=[config_parent])
    conflicts.set_defaults(func=cmd_conflicts)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
