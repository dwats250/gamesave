from __future__ import annotations

from pathlib import Path
import unittest

from gamesave.models import ActionType, FileRecord
from gamesave.planner import plan_sync


def record(key: str, sha: str) -> FileRecord:
    return FileRecord(key=key, path=Path(key), size=1, mtime_ns=1, sha256=sha)


class PlannerTests(unittest.TestCase):
    def test_uploads_when_remote_missing(self) -> None:
        actions = plan_sync(
            local_records={"gba/save/a.sav": record("gba/save/a.sav", "a")},
            sync_records={},
            previous_records={},
            sync_dir=Path("/sync"),
        )
        self.assertEqual(actions[0].action, ActionType.UPLOAD)

    def test_downloads_when_local_missing(self) -> None:
        actions = plan_sync(
            local_records={},
            sync_records={"gba/save/a.sav": record("gba/save/a.sav", "a")},
            previous_records={},
            sync_dir=Path("/sync"),
        )
        self.assertEqual(actions[0].action, ActionType.DOWNLOAD)

    def test_conflicts_when_both_changed_from_baseline(self) -> None:
        actions = plan_sync(
            local_records={"gba/save/a.sav": record("gba/save/a.sav", "local")},
            sync_records={"gba/save/a.sav": record("gba/save/a.sav", "sync")},
            previous_records={"gba/save/a.sav": {"sha256": "base"}},
            sync_dir=Path("/sync"),
        )
        self.assertEqual(actions[0].action, ActionType.CONFLICT)

    def test_uploads_when_only_local_changed(self) -> None:
        actions = plan_sync(
            local_records={"gba/save/a.sav": record("gba/save/a.sav", "local")},
            sync_records={"gba/save/a.sav": record("gba/save/a.sav", "base")},
            previous_records={"gba/save/a.sav": {"sha256": "base"}},
            sync_dir=Path("/sync"),
        )
        self.assertEqual(actions[0].action, ActionType.UPLOAD)


if __name__ == "__main__":
    unittest.main()
