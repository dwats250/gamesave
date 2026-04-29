from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest

from gamesave.config import Config, SyncPath, load_config
from gamesave.doctor import STALE_LOCK_SECONDS, run_doctor, write_doctor_report
from gamesave.names import audit_names, write_name_audit
from gamesave.presets import list_presets, list_profiles, render_config_template


class PresetDoctorNameTests(unittest.TestCase):
    def test_preset_expansion_for_android_profiles(self) -> None:
        self.assertIn("rg476h", list_profiles())
        self.assertIn("retroid-pocket-4-pro", list_profiles())
        self.assertIn("android-generic", list_profiles())
        emulators = {preset.emulator for preset in list_presets()}
        self.assertTrue({"retroarch", "duckstation", "ppsspp", "dolphin", "nethersx2", "m64plus-fz"} <= emulators)

        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "gamesave.toml"
            config_path.write_text(render_config_template("rg476h"), encoding="utf-8")
            config = load_config(config_path)

            self.assertEqual(config.device_profile, "rg476h")
            self.assertTrue(any(path.emulator == "retroarch" and path.path_role == "state" for path in config.paths))

    def test_doctor_reports_missing_folders_stale_lock_and_state_risk(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            sync_dir = root / "sync"
            sync_dir.mkdir()
            state_dir = root / "states"
            state_dir.mkdir()
            lock = sync_dir / ".gamesave.lock"
            lock.write_text("123", encoding="utf-8")
            old = time.time() - STALE_LOCK_SECONDS - 10
            os.utime(lock, (old, old))
            config = Config(
                device_name="rp4pro",
                sync_dir=sync_dir,
                paths=(
                    SyncPath("retroarch", "save", root / "missing", ("*.srm",), emulator="retroarch"),
                    SyncPath("retroarch", "state", state_dir, ("*.state*",), emulator="retroarch", path_role="state", state_risk="high"),
                ),
                device_profile="retroid-pocket-4-pro",
            )

            report = run_doctor(config)
            path = write_doctor_report(config, report)
            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(report.status, "ERROR")
            self.assertTrue(any("path missing" in error for error in report.errors))
            self.assertTrue(any("stale lock" in warning for warning in report.warnings))
            self.assertTrue(any("high-risk" in warning for warning in report.warnings))
            self.assertEqual(payload["status"], "ERROR")

    def test_name_audit_reports_case_collisions_and_rom_mismatches(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_dir = root / "saves"
            rom_dir = root / "roms"
            sync_dir = root / "sync"
            save_dir.mkdir()
            rom_dir.mkdir()
            sync_dir.mkdir()
            (save_dir / "Game.srm").write_bytes(b"a")
            (save_dir / "game.srm").write_bytes(b"b")
            (save_dir / "NoRom.srm").write_bytes(b"c")
            (rom_dir / "Other.gba").write_bytes(b"rom")
            config = Config(
                device_name="rg476h",
                sync_dir=sync_dir,
                paths=(
                    SyncPath(
                        "gba",
                        "save",
                        save_dir,
                        ("*.srm",),
                        emulator="retroarch",
                        rom_path=rom_dir,
                        rom_patterns=("*.gba",),
                    ),
                ),
                stability_seconds=0,
            )

            audit = audit_names(config)
            path = write_name_audit(config, audit)

            self.assertEqual(len(audit.case_collisions), 1)
            self.assertIn("norom", audit.save_without_rom)
            self.assertIn("other", audit.rom_without_save)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
