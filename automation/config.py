"""Local, ignored configuration loading for scheduled environments."""

from __future__ import annotations

import os
from pathlib import Path


def load_local_env(root: Path) -> None:
    """Load simple KEY=value pairs without overwriting scheduler-provided env."""
    candidates = [root / "automation" / ".env", root / ".env"]
    for path in candidates:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            if key and key not in os.environ:
                os.environ[key] = value

