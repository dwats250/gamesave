from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gamesave.backup import backup_actions
from gamesave.config import Config, SyncPath
from gamesave.models import ActionType, PlannedAction
from gamesave.resolution import resolve_conflict
from gamesave.scanner import sync_file_path
from gamesave.sync import apply_actions, conflict_store_path


class BackupResolutionTests(unittest.TestCase):
    def config(self, root: Path) -> Config:
        local = root / "local"
        sync = root / "sync"
        local.mkdir(exist_ok=True)
        sync.mkdir(exist_ok=True)
        return Config(
            device_name="rg476h",
            sync_dir=sync,
            paths=(SyncPath("gba", "save", local, ("*.sav",)),),
            stability_seconds=0,
        )

    def test_backup_snapshot_before_changed_action(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.config(root)
            local = root / "local" / "game.sav"
            sync = root / "sync" / "saves" / "gba" / "save" / "game.sav"
            local.write_bytes(b"local")
            sync.parent.mkdir(parents=True)
            sync.write_bytes(b"sync")
            action = PlannedAction(ActionType.UPLOAD, "gba/save/game.sav", local, sync, "local changed")

            backup = backup_actions(config, [action], timestamp="20260429-120000")

            self.assertIsNotNone(backup)
            self.assertEqual((root / "sync" / "backups" / "20260429-120000" / "local" / "gba" / "save" / "game.sav").read_bytes(), b"local")
            self.assertEqual((root / "sync" / "backups" / "20260429-120000" / "sync" / "gba" / "save" / "game.sav").read_bytes(), b"sync")

    def test_conflict_preserves_sync_copy_and_writes_conflict_store(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.config(root)
            local = root / "local" / "game.sav"
            sync = sync_file_path(root / "sync", "gba/save/game.sav")
            local.write_bytes(b"local")
            sync.parent.mkdir(parents=True)
            sync.write_bytes(b"sync")

            apply_actions(config, [PlannedAction(ActionType.CONFLICT, "gba/save/game.sav", local, sync, "both changed")])

            self.assertEqual(sync.read_bytes(), b"sync")
            conflicts = list((root / "sync" / "conflicts").rglob("*.sav"))
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0].read_bytes(), b"local")

    def test_resolve_can_use_sync_or_file(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self.config(root)
            local = root / "local" / "game.sav"
            sync = sync_file_path(root / "sync", "gba/save/game.sav")
            winner = root / "winner.sav"
            local.write_bytes(b"local")
            sync.parent.mkdir(parents=True)
            sync.write_bytes(b"sync")
            winner.write_bytes(b"winner")

            resolve_conflict(config, "gba/save/game.sav", use="sync")
            self.assertEqual(local.read_bytes(), b"sync")

            resolve_conflict(config, "gba/save/game.sav", use="file", file_path=winner)
            self.assertEqual(local.read_bytes(), b"winner")
            self.assertEqual(sync.read_bytes(), b"winner")

    def test_conflict_store_path_uses_recovery_root(self) -> None:
        path = conflict_store_path(Path("/sync"), "gba/save/game.sav", "rg476h", timestamp="20260429-120000")
        self.assertEqual(path, Path("/sync/conflicts/gba/save/game.conflict.rg476h.20260429-120000.sav"))

    def test_conflict_store_path_does_not_reuse_existing_name(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "sync" / "conflicts" / "gba" / "save" / "game.conflict.rg476h.20260429-120000.sav"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"old")

            path = conflict_store_path(root / "sync", "gba/save/game.sav", "rg476h", timestamp="20260429-120000")

            self.assertEqual(path.name, "game.conflict.rg476h.20260429-120000.1.sav")


if __name__ == "__main__":
    unittest.main()
