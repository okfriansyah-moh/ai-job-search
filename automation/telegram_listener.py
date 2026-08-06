"""Run the always-on local Telegram polling listener."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.state import StateStore  # noqa: E402
from automation.telegram import listen  # noqa: E402
from automation.config import load_local_env  # noqa: E402


if __name__ == "__main__":
    load_local_env(ROOT)
    listen(ROOT, StateStore(ROOT))
