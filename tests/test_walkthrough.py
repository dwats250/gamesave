from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gamesave.cli import main
from gamesave.config import load_config
from gamesave.walkthrough import run_self_test, synthetic_config_text, walkthrough_text


class WalkthroughTests(unittest.TestCase):
    def test_synthetic_config_is_loadable(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "gamesave-test.toml"
            config_path.write_text(
                synthetic_config_text(root=root / "test", sync_dir=root / "sync"),
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertEqual(config.device_name, "android-test")
            self.assertEqual(config.paths[0].system, "gba")

    def test_self_test_runs_end_to_end(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_self_test(
                root / "gamesave-test.toml",
                root=root / "GamesaveTest",
                sync_dir=root / "RetroSaveSyncTest",
                reset=True,
            )

            self.assertTrue(result.ok)
            self.assertEqual(result.local_save.read_bytes(), b"test-save-v1")
            self.assertEqual(result.sync_save.read_bytes(), b"test-save-v1")

    def test_cli_walkthrough_prints_stages(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["walkthrough"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Stage 2", output.getvalue())
        self.assertIn("self-test", output.getvalue())

    def test_cli_self_test_accepts_safe_paths(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = StringIO()

            with redirect_stdout(output):
                exit_code = main(
                    [
                        "self-test",
                        "--config",
                        str(root / "gamesave-test.toml"),
                        "--root",
                        str(root / "GamesaveTest"),
                        "--sync-dir",
                        str(root / "RetroSaveSyncTest"),
                        "--reset",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("result PASS", output.getvalue())

    def test_walkthrough_text_mentions_real_save_gate(self) -> None:
        self.assertIn("real-save safety gate", walkthrough_text())


if __name__ == "__main__":
    unittest.main()
