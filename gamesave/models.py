from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ActionType(str, Enum):
    UPLOAD = "UPLOAD"
    DOWNLOAD = "DOWNLOAD"
    CONFLICT = "CONFLICT"
    SKIP = "SKIP"


@dataclass(frozen=True)
class FileRecord:
    key: str
    path: Path
    size: int
    mtime_ns: int
    sha256: str
    device: str | None = None
    emulator: str = "custom"
    path_role: str = "save"
    state_risk: str = "normal"
    core_name: str | None = None


@dataclass(frozen=True)
class PlannedAction:
    action: ActionType
    key: str
    source: Path | None
    target: Path | None
    reason: str
