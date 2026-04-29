from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gamesave.cli import main


class CliTests(unittest.TestCase):
    def test_sync_dry_run_accepts_config_after_command(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / "local"
            local.mkdir()
            (local / "game.sav").write_bytes(b"save")
            config = root / "gamesave.toml"
            config.write_text(
                f"""
device_name = "pc"
sync_dir = "{root / "sync"}"
stability_seconds = 0

[[paths]]
system = "gba"
kind = "save"
path = "{local}"
patterns = ["*.sav"]
""".strip(),
                encoding="utf-8",
            )

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["sync", "--config", str(config), "--dry-run"])

            self.assertEqual(exit_code, 0)
            self.assertIn("UPLOAD   gba/save/game.sav", output.getvalue())

    def test_conflicts_lists_conflict_files(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            sync_save = root / "sync" / "saves" / "gba" / "save"
            sync_save.mkdir(parents=True)
            (sync_save / "game.conflict.pc.20260428-120000.sav").write_bytes(b"save")
            local = root / "local"
            local.mkdir()
            config = root / "gamesave.toml"
            config.write_text(
                f"""
device_name = "pc"
sync_dir = "{root / "sync"}"

[[paths]]
system = "gba"
kind = "save"
path = "{local}"
patterns = ["*.sav"]
""".strip(),
                encoding="utf-8",
            )

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["conflicts", "--config", str(config)])

            self.assertEqual(exit_code, 0)
            self.assertIn("gba/save/game.conflict.pc.20260428-120000.sav", output.getvalue())


if __name__ == "__main__":
    unittest.main()
