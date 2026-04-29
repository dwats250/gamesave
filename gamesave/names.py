from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .config import Config
from .scanner import scan_local


ROM_SUFFIXES = {".7z", ".bin", ".cue", ".gba", ".gb", ".gbc", ".iso", ".md", ".nes", ".n64", ".sfc", ".smc", ".zip"}


@dataclass(frozen=True)
class NameAudit:
    case_collisions: list[list[str]]
    save_without_rom: list[str]
    rom_without_save: list[str]
    notes: list[str]

    def to_dict(self) -> dict:
        return {
            "case_collisions": self.case_collisions,
            "save_without_rom": self.save_without_rom,
            "rom_without_save": self.rom_without_save,
            "notes": self.notes,
        }


def normalized_stem(path: Path) -> str:
    stem = path.name
    while Path(stem).suffix.lower() in ROM_SUFFIXES:
        stem = Path(stem).stem
    return Path(stem).stem.casefold()


def find_case_collisions(paths: list[Path]) -> list[list[str]]:
    grouped: dict[str, set[str]] = {}
    for path in paths:
        grouped.setdefault(str(path).casefold(), set()).add(str(path))
    return [sorted(values) for values in grouped.values() if len(values) > 1]


def audit_names(config: Config) -> NameAudit:
    records = scan_local(config, now=10**12)
    save_paths = [record.path for record in records.values()]
    collisions = find_case_collisions(save_paths)
    notes: list[str] = []
    save_without_rom: list[str] = []
    rom_without_save: list[str] = []

    for sync_path in config.paths:
        scoped_saves = {
            normalized_stem(record.path)
            for record in records.values()
            if record.key.startswith(f"{sync_path.system}/{sync_path.kind}/")
        }
        if not sync_path.rom_path:
            notes.append(f"{sync_path.system}/{sync_path.kind}: rom_path not configured")
            continue
        if not sync_path.rom_path.exists():
            notes.append(f"{sync_path.system}/{sync_path.kind}: rom_path missing: {sync_path.rom_path}")
            continue
        rom_patterns = sync_path.rom_patterns or ("*",)
        rom_paths: list[Path] = []
        for pattern in rom_patterns:
            rom_paths.extend(path for path in sync_path.rom_path.rglob(pattern) if path.is_file())
        rom_stems = {normalized_stem(path) for path in rom_paths}
        save_without_rom.extend(sorted(stem for stem in scoped_saves - rom_stems))
        rom_without_save.extend(sorted(stem for stem in rom_stems - scoped_saves))

    return NameAudit(
        case_collisions=collisions,
        save_without_rom=sorted(set(save_without_rom)),
        rom_without_save=sorted(set(rom_without_save)),
        notes=notes,
    )


def write_name_audit(config: Config, audit: NameAudit) -> Path:
    path = config.sync_dir / "reports" / "name-audit-latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path
