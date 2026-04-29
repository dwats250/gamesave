from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from .config import Config, SyncPath
from .doctor import run_doctor
from .manifest import load_manifest, write_manifest
from .models import ActionType
from .planner import plan_sync
from .scanner import scan_local, scan_sync_dir, sync_file_path
from .sync import apply_actions


DEFAULT_TEST_ROOT = Path("/storage/emulated/0/GamesaveTest")
DEFAULT_TEST_SYNC = Path("/storage/emulated/0/RetroSaveSyncTest")


@dataclass(frozen=True)
class SelfTestResult:
    ok: bool
    steps: list[str]
    config_path: Path
    local_save: Path
    sync_save: Path


def synthetic_config_text(*, root: Path = DEFAULT_TEST_ROOT, sync_dir: Path = DEFAULT_TEST_SYNC) -> str:
    return f"""
device_name = "android-test"
device_profile = "android-generic"
sync_dir = "{sync_dir}"
stability_seconds = 0
max_backups_per_key = 5

[[paths]]
system = "gba"
kind = "save"
emulator = "retroarch"
path_role = "save"
state_risk = "normal"
path = "{root / "local" / "gba"}"
patterns = ["*.sav"]
""".strip() + "\n"


def write_synthetic_config(config_path: Path, *, root: Path = DEFAULT_TEST_ROOT, sync_dir: Path = DEFAULT_TEST_SYNC, force: bool = False) -> None:
    if config_path.exists() and not force:
        raise FileExistsError(f"config already exists: {config_path}")
    config_path.write_text(synthetic_config_text(root=root, sync_dir=sync_dir), encoding="utf-8")


def run_self_test(config_path: Path, *, root: Path = DEFAULT_TEST_ROOT, sync_dir: Path = DEFAULT_TEST_SYNC, reset: bool = False) -> SelfTestResult:
    if reset:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(sync_dir, ignore_errors=True)

    local_dir = root / "local" / "gba"
    local_dir.mkdir(parents=True, exist_ok=True)
    sync_dir.mkdir(parents=True, exist_ok=True)
    local_save = local_dir / "TestGame.sav"
    local_save.write_bytes(b"test-save-v1")
    write_synthetic_config(config_path, root=root, sync_dir=sync_dir, force=True)

    config = Config(
        device_name="android-test",
        sync_dir=sync_dir,
        paths=(SyncPath("gba", "save", local_dir, ("*.sav",), emulator="retroarch"),),
        stability_seconds=0,
        device_profile="android-generic",
    )

    steps: list[str] = []
    report = run_doctor(config)
    steps.append(f"doctor={report.status}")

    local_records = scan_local(config)
    steps.append(f"scan={len(local_records)}")
    previous_records = load_manifest(config.sync_dir)
    first_actions = plan_sync(
        local_records=local_records,
        sync_records=scan_sync_dir(config.sync_dir),
        previous_records=previous_records,
        sync_dir=config.sync_dir,
    )
    first_action_names = [action.action for action in first_actions]
    steps.append("plan=" + ",".join(action.value for action in first_action_names))
    if ActionType.UPLOAD not in first_action_names:
        return SelfTestResult(False, steps, config_path, local_save, sync_file_path(sync_dir, "gba/save/TestGame.sav"))

    apply_actions(config, first_actions)
    write_manifest(config.sync_dir, scan_sync_dir(config.sync_dir))
    sync_save = sync_file_path(sync_dir, "gba/save/TestGame.sav")
    if not sync_save.exists() or sync_save.read_bytes() != b"test-save-v1":
        steps.append("copy=failed")
        return SelfTestResult(False, steps, config_path, local_save, sync_save)
    steps.append("copy=ok")

    second_actions = plan_sync(
        local_records=scan_local(config),
        sync_records=scan_sync_dir(config.sync_dir),
        previous_records=load_manifest(config.sync_dir),
        sync_dir=config.sync_dir,
    )
    if all(action.action == ActionType.SKIP for action in second_actions):
        steps.append("second_status=skip")
        return SelfTestResult(True, steps, config_path, local_save, sync_save)

    steps.append("second_status=changed")
    return SelfTestResult(False, steps, config_path, local_save, sync_save)


def walkthrough_text() -> str:
    return """
Gamesave handheld walkthrough

Stage 1: verify Python and the CLI
  python3 -m unittest discover -s tests -v
  python3 -m gamesave --help
  python3 -m gamesave presets list

Stage 2: run the isolated synthetic pipeline
  python3 -m gamesave self-test --reset

Stage 3: connect Syncthing-Fork only to the test folder
  Sync this folder between handhelds:
  /storage/emulated/0/RetroSaveSyncTest

Stage 4: prove cross-device movement with test data
  On device A:
    printf "from-device-a" > /storage/emulated/0/GamesaveTest/local/gba/TestGame.sav
    python3 -m gamesave sync --config gamesave-test.toml

  After Syncthing finishes, on device B:
    python3 -m gamesave sync --config gamesave-test.toml
    cat /storage/emulated/0/GamesaveTest/local/gba/TestGame.sav

Stage 5: only then create a real device config
  python3 -m gamesave init-device --profile rg476h --config gamesave.toml
  python3 -m gamesave init-device --profile retroid-pocket-4-pro --config gamesave.toml

Stage 6: real-save safety gate
  python3 -m gamesave doctor --config gamesave.toml
  python3 -m gamesave backup --config gamesave.toml
  python3 -m gamesave sync --config gamesave.toml --dry-run

Run real sync only after the dry run shows expected actions.
""".strip()
