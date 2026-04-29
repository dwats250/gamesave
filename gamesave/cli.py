from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .backup import backup_actions, create_full_backup
from .config import load_config
from .doctor import run_doctor, write_doctor_report
from .lock import sync_lock
from .manifest import load_manifest, write_manifest
from .models import ActionType, PlannedAction
from .names import audit_names, write_name_audit
from .planner import plan_sync
from .presets import list_presets, list_profiles, write_config_template
from .resolution import resolve_conflict
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
        backup = backup_actions(config, actions)
        if backup is not None:
            print(f"backup {backup}")
        apply_actions(config, actions)
        refreshed = scan_sync_dir(config.sync_dir)
        write_manifest(config.sync_dir, refreshed)

    changed = sum(1 for action in actions if action.action != ActionType.SKIP)
    print(f"applied {changed} action(s)")
    return 0


def cmd_conflicts(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    roots = (config.sync_dir / "conflicts", config.sync_dir / "saves")
    conflicts: list[Path] = []
    for root in roots:
        if root.exists():
            conflicts.extend(path for path in root.rglob("*") if path.is_file() and ".conflict." in path.name)
    conflicts = sorted(conflicts)
    if not conflicts:
        print("no conflicts")
        return 0

    for path in conflicts:
        try:
            print(path.relative_to(config.sync_dir))
        except ValueError:
            print(path)
    print(f"{len(conflicts)} conflict file(s)")
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    root = create_full_backup(config)
    print(f"backup {root}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    report = run_doctor(config)
    print(f"status {report.status}")
    for error in report.errors:
        print(f"ERROR {error}")
    for warning in report.warnings:
        print(f"WARN  {warning}")
    try:
        path = write_doctor_report(config, report)
        print(f"report {path}")
    except OSError as exc:
        print(f"WARN  report not written: {exc}")
    return 1 if report.status == "ERROR" and args.strict else 0


def cmd_presets_list(args: argparse.Namespace) -> int:
    print("profiles")
    for profile in list_profiles():
        print(f"  {profile}")
    print("presets")
    for preset in list_presets():
        print(f"  {preset.emulator:12} {preset.system:10} {preset.kind:5} {preset.path}")
    return 0


def cmd_init_device(args: argparse.Namespace) -> int:
    write_config_template(args.config, args.profile, force=args.force)
    print(f"wrote {args.config}")
    return 0


def cmd_names_audit(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    audit = audit_names(config)
    for collision in audit.case_collisions:
        print("CASE_COLLISION " + " | ".join(collision))
    for name in audit.save_without_rom:
        print(f"SAVE_WITHOUT_ROM {name}")
    for name in audit.rom_without_save:
        print(f"ROM_WITHOUT_SAVE {name}")
    for note in audit.notes:
        print(f"NOTE {note}")
    try:
        path = write_name_audit(config, audit)
        print(f"report {path}")
    except OSError as exc:
        print(f"WARN report not written: {exc}")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    primary, secondary = resolve_conflict(config, args.key, use=args.use, file_path=args.file)
    print(f"resolved {args.key} -> {primary}")
    if secondary is not None:
        print(f"resolved {args.key} -> {secondary}")
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

    backup = subparsers.add_parser("backup", help="create a local save backup snapshot", parents=[config_parent])
    backup.set_defaults(func=cmd_backup)

    doctor = subparsers.add_parser("doctor", help="diagnose sync setup risks", parents=[config_parent])
    doctor.add_argument("--strict", action="store_true", help="exit nonzero when doctor reports errors")
    doctor.set_defaults(func=cmd_doctor)

    init_device = subparsers.add_parser("init-device", help="write an Android device config template", parents=[config_parent])
    init_device.add_argument("--profile", choices=list_profiles(), required=True)
    init_device.add_argument("--force", action="store_true")
    init_device.set_defaults(func=cmd_init_device)

    resolve = subparsers.add_parser("resolve", help="resolve a conflict by selecting a winning file", parents=[config_parent])
    resolve.add_argument("key")
    resolve.add_argument("--use", choices=("local", "sync", "file"), required=True)
    resolve.add_argument("--file", type=Path)
    resolve.set_defaults(func=cmd_resolve)

    presets = subparsers.add_parser("presets", help="inspect device and emulator presets")
    preset_subparsers = presets.add_subparsers(dest="preset_command", required=True)
    presets_list = preset_subparsers.add_parser("list", help="list built-in presets")
    presets_list.set_defaults(func=cmd_presets_list)

    names = subparsers.add_parser("names", help="inspect ROM/save naming issues")
    names_subparsers = names.add_subparsers(dest="names_command", required=True)
    names_audit = names_subparsers.add_parser("audit", help="audit save naming and ROM mismatches", parents=[config_parent])
    names_audit.set_defaults(func=cmd_names_audit)

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
