"""Atomic personal state and cross-scheduler locking."""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


class StateStore:
    def __init__(self, root: Path):
        self.root = root
        self.directory = root / "automation" / "state"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.directory / "run.lock"

    def path(self, name: str) -> Path:
        return self.directory / name

    def read_json(self, name: str, default: Any) -> Any:
        path = self.path(name)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return default

    def write_json(self, name: str, value: Any) -> None:
        atomic_write_json(self.path(name), value)

    @contextlib.contextmanager
    def lock(self) -> Iterator[None]:
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def can_run_today(self, day: str, force: bool = False) -> bool:
        if force:
            return True
        ledger = self.read_json("run_ledger.json", {})
        return ledger.get("last_success_date") != day

    def mark_success(self, day: str, scheduler: str, summary: dict[str, Any]) -> None:
        self.write_json(
            "run_ledger.json",
            {
                "last_success_date": day,
                "last_success_at": datetime.now().astimezone().isoformat(),
                "last_scheduler": scheduler,
                "last_summary": summary,
                "last_failure": None,
            },
        )

    def mark_failure(self, day: str, scheduler: str, error: str) -> None:
        self.write_json(
            "run_ledger.json",
            {
                **self.read_json("run_ledger.json", {}),
                "last_failure": {
                    "date": day,
                    "at": datetime.now().astimezone().isoformat(),
                    "scheduler": scheduler,
                    "error": error,
                },
            },
        )


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)

