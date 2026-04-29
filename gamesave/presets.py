from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_PROFILES = ("android-generic", "retroid-pocket-4-pro", "rg476h")


@dataclass(frozen=True)
class PresetPath:
    emulator: str
    system: str
    kind: str
    path: str
    patterns: tuple[str, ...]
    path_role: str
    state_risk: str = "normal"


ANDROID_PRESETS: tuple[PresetPath, ...] = (
    PresetPath("retroarch", "retroarch", "save", "/storage/emulated/0/RetroArch/saves", ("*.srm", "*.sav"), "save"),
    PresetPath("retroarch", "retroarch", "state", "/storage/emulated/0/RetroArch/states", ("*.state*",), "state", "high"),
    PresetPath("duckstation", "ps1", "save", "/storage/emulated/0/DuckStation/memcards", ("*.mcd", "*.mcr"), "save"),
    PresetPath("ppsspp", "psp", "save", "/storage/emulated/0/PSP/SAVEDATA", ("*",), "save"),
    PresetPath("dolphin", "gamecube", "save", "/storage/emulated/0/dolphin-emu/GC", ("*.raw", "*.gci"), "save"),
    PresetPath("dolphin", "wii", "save", "/storage/emulated/0/dolphin-emu/Wii", ("*",), "save"),
    PresetPath("nethersx2", "ps2", "save", "/storage/emulated/0/Android/data/xyz.aethersx2.android/files/memcards", ("*.ps2",), "save"),
    PresetPath("m64plus-fz", "n64", "save", "/storage/emulated/0/Android/data/org.mupen64plusae.v3.fzurita/files/GameData", ("*.sra", "*.eep", "*.fla"), "save"),
)


def list_profiles() -> tuple[str, ...]:
    return SUPPORTED_PROFILES


def list_presets() -> tuple[PresetPath, ...]:
    return ANDROID_PRESETS


def render_config_template(profile: str, *, device_name: str | None = None, sync_dir: str | None = None) -> str:
    if profile not in SUPPORTED_PROFILES:
        raise ValueError(f"unknown profile: {profile}")

    device_name = device_name or profile
    sync_dir = sync_dir or "/storage/emulated/0/RetroSaveSync"
    lines = [
        f'device_name = "{device_name}"',
        f'device_profile = "{profile}"',
        f'sync_dir = "{sync_dir}"',
        "stability_seconds = 15",
        "max_backups_per_key = 5",
        "",
    ]

    for preset in ANDROID_PRESETS:
        lines.extend(
            [
                "[[paths]]",
                f'system = "{preset.system}"',
                f'kind = "{preset.kind}"',
                f'emulator = "{preset.emulator}"',
                f'path_role = "{preset.path_role}"',
                f'state_risk = "{preset.state_risk}"',
                f'path = "{preset.path}"',
                "patterns = [" + ", ".join(f'"{pattern}"' for pattern in preset.patterns) + "]",
                "",
            ]
        )

    lines.extend(
        [
            "# Add manual/custom emulator folders as additional [[paths]] entries.",
            "# Optional ROM audit fields:",
            '# rom_path = "/storage/emulated/0/ROMs/gba"',
            '# rom_patterns = ["*.gba", "*.zip"]',
            "",
        ]
    )
    return "\n".join(lines)


def write_config_template(path: Path, profile: str, *, force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"config already exists: {path}")
    path.write_text(render_config_template(profile), encoding="utf-8")
