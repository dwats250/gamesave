from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


DEFAULT_STABILITY_SECONDS = 10


@dataclass(frozen=True)
class SyncPath:
    system: str
    kind: str
    path: Path
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class Config:
    device_name: str
    sync_dir: Path
    paths: tuple[SyncPath, ...]
    stability_seconds: int = DEFAULT_STABILITY_SECONDS


def load_config(path: Path) -> Config:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))

    try:
        device_name = str(raw["device_name"]).strip()
        sync_dir = Path(raw["sync_dir"]).expanduser()
    except KeyError as exc:
        raise ValueError(f"missing required config key: {exc.args[0]}") from exc

    if not device_name:
        raise ValueError("device_name cannot be empty")

    entries = raw.get("paths", [])
    if not isinstance(entries, list) or not entries:
        raise ValueError("config must include at least one [[paths]] entry")

    sync_paths: list[SyncPath] = []
    for index, entry in enumerate(entries, start=1):
        try:
            system = str(entry["system"]).strip()
            kind = str(entry["kind"]).strip()
            local_path = Path(entry["path"]).expanduser()
            patterns_raw = entry["patterns"]
        except KeyError as exc:
            raise ValueError(f"paths entry {index} missing key: {exc.args[0]}") from exc

        if not system or not kind:
            raise ValueError(f"paths entry {index} has empty system or kind")
        if not isinstance(patterns_raw, list) or not patterns_raw:
            raise ValueError(f"paths entry {index} must include non-empty patterns list")

        patterns = tuple(str(pattern) for pattern in patterns_raw)
        sync_paths.append(SyncPath(system=system, kind=kind, path=local_path, patterns=patterns))

    stability_seconds = int(raw.get("stability_seconds", DEFAULT_STABILITY_SECONDS))
    if stability_seconds < 0:
        raise ValueError("stability_seconds cannot be negative")

    return Config(
        device_name=device_name,
        sync_dir=sync_dir,
        paths=tuple(sync_paths),
        stability_seconds=stability_seconds,
    )
