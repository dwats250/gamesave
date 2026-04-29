from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from .models import FileRecord


MANIFEST_NAME = "manifest.json"


def manifest_path(sync_dir: Path) -> Path:
    return sync_dir / MANIFEST_NAME


def load_manifest(sync_dir: Path) -> dict[str, dict]:
    path = manifest_path(sync_dir)
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    records = raw.get("records", {})
    if not isinstance(records, dict):
        raise ValueError("manifest records must be an object")
    return records


def write_manifest(sync_dir: Path, records: dict[str, FileRecord]) -> None:
    sync_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "records": {
            key: {
                **asdict(record),
                "path": str(record.path),
            }
            for key, record in sorted(records.items())
        },
    }
    target = manifest_path(sync_dir)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(target)
