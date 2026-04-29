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
    emulator: str = "custom"
    path_role: str = "save"
    state_risk: str = "normal"
    core_name: str | None = None
    rom_path: Path | None = None
    rom_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class Config:
    device_name: str
    sync_dir: Path
    paths: tuple[SyncPath, ...]
    stability_seconds: int = DEFAULT_STABILITY_SECONDS
    device_profile: str = "custom"
    max_backups_per_key: int = 5


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
        rom_patterns_raw = entry.get("rom_patterns", [])
        if not isinstance(rom_patterns_raw, list):
            raise ValueError(f"paths entry {index} rom_patterns must be a list")
        rom_path_raw = entry.get("rom_path")
        sync_paths.append(
            SyncPath(
                system=system,
                kind=kind,
                path=local_path,
                patterns=patterns,
                emulator=str(entry.get("emulator", "custom")).strip() or "custom",
                path_role=str(entry.get("path_role", kind)).strip() or kind,
                state_risk=str(entry.get("state_risk", "high" if kind == "state" else "normal")).strip(),
                core_name=str(entry["core_name"]).strip() if entry.get("core_name") else None,
                rom_path=Path(rom_path_raw).expanduser() if rom_path_raw else None,
                rom_patterns=tuple(str(pattern) for pattern in rom_patterns_raw),
            )
        )

    stability_seconds = int(raw.get("stability_seconds", DEFAULT_STABILITY_SECONDS))
    if stability_seconds < 0:
        raise ValueError("stability_seconds cannot be negative")
    max_backups_per_key = int(raw.get("max_backups_per_key", 5))
    if max_backups_per_key < 1:
        raise ValueError("max_backups_per_key must be at least 1")

    return Config(
        device_name=device_name,
        sync_dir=sync_dir,
        paths=tuple(sync_paths),
        stability_seconds=stability_seconds,
        device_profile=str(raw.get("device_profile", "custom")).strip() or "custom",
        max_backups_per_key=max_backups_per_key,
    )
