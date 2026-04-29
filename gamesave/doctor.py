from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import time
from pathlib import Path

from .config import Config


STALE_LOCK_SECONDS = 60 * 30


@dataclass(frozen=True)
class DoctorReport:
    status: str
    warnings: list[str]
    errors: list[str]

    def to_dict(self) -> dict:
        return {"status": self.status, "warnings": self.warnings, "errors": self.errors}


def run_doctor(config: Config, *, now: float | None = None) -> DoctorReport:
    now = time.time() if now is None else now
    warnings: list[str] = []
    errors: list[str] = []

    if not config.sync_dir.exists():
        errors.append(f"sync_dir missing: {config.sync_dir}")
    elif not config.sync_dir.is_dir():
        errors.append(f"sync_dir is not a directory: {config.sync_dir}")

    saves_root = config.sync_dir / "saves"
    if not saves_root.exists():
        warnings.append(f"Syncthing saves folder missing until first sync: {saves_root}")

    lock_path = config.sync_dir / ".gamesave.lock"
    if lock_path.exists():
        age = now - lock_path.stat().st_mtime
        if age >= STALE_LOCK_SECONDS:
            warnings.append(f"stale lock older than {STALE_LOCK_SECONDS}s: {lock_path}")
        else:
            errors.append(f"active sync lock present: {lock_path}")

    for sync_path in config.paths:
        label = f"{sync_path.system}/{sync_path.kind}"
        if not sync_path.path.exists():
            errors.append(f"{label} path missing: {sync_path.path}")
        if sync_path.path_role == "state" or sync_path.state_risk == "high":
            warnings.append(f"{label} is save-state/high-risk; keep emulator/core settings aligned")
        if sync_path.core_name is None and sync_path.emulator == "retroarch" and sync_path.path_role == "state":
            warnings.append(f"{label} RetroArch state path has no core_name metadata")

    status = "ERROR" if errors else "WARN" if warnings else "OK"
    return DoctorReport(status=status, warnings=warnings, errors=errors)


def write_doctor_report(config: Config, report: DoctorReport) -> Path:
    path = config.sync_dir / "reports" / "doctor-latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **report.to_dict(),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path
