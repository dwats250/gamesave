from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gamesave.config import Config, SyncPath
from gamesave.scanner import scan_local, scan_sync_dir
from gamesave.sync import atomic_copy, conflict_path


class ScannerSyncTests(unittest.TestCase):
    def test_scan_local_uses_system_kind_key(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_dir = root / "local"
            save_dir.mkdir()
            save = save_dir / "Pokemon.sav"
            save.write_bytes(b"save")
            config = Config(
                device_name="pc",
                sync_dir=root / "sync",
                paths=(SyncPath("gba", "save", save_dir, ("*.sav",)),),
                stability_seconds=0,
            )

            records = scan_local(config)

            self.assertIn("gba/save/Pokemon.sav", records)

    def test_atomic_copy_creates_target_parent(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.sav"
            target = root / "nested" / "target.sav"
            source.write_bytes(b"abc")

            atomic_copy(source, target)

            self.assertEqual(target.read_bytes(), b"abc")

    def test_scan_sync_ignores_conflict_files(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            sync_save = root / "saves" / "gba" / "save"
            sync_save.mkdir(parents=True)
            (sync_save / "a.sav").write_bytes(b"a")
            (sync_save / "a.conflict.pc.20260428-120000.sav").write_bytes(b"b")

            records = scan_sync_dir(root)

            self.assertEqual(sorted(records), ["gba/save/a.sav"])

    def test_conflict_path_preserves_suffix(self) -> None:
        result = conflict_path(Path("/sync/saves/gba/save/a.sav"), "deck", timestamp="20260428-120000")
        self.assertEqual(result.name, "a.conflict.deck.20260428-120000.sav")


if __name__ == "__main__":
    unittest.main()
