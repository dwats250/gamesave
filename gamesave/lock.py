from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path


@contextmanager
def sync_lock(sync_dir: Path):
    sync_dir.mkdir(parents=True, exist_ok=True)
    lock_path = sync_dir / ".gamesave.lock"
    fd: int | None = None
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("ascii"))
        yield
    except FileExistsError as exc:
        raise RuntimeError(f"sync lock already exists: {lock_path}") from exc
    finally:
        if fd is not None:
            os.close(fd)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass
