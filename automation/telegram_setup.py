"""Discover the Telegram chat ID that should receive job notifications."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.config import load_local_env  # noqa: E402
from automation.telegram import TelegramClient  # noqa: E402


def chats_from_updates(updates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    chats: dict[str, dict[str, Any]] = {}
    for update in updates:
        message = update.get("message") or update.get("edited_message") or {}
        if not message:
            message = (update.get("callback_query") or {}).get("message") or {}
        chat = message.get("chat") or {}
        if chat.get("id") is not None:
            chats[str(chat["id"])] = chat
    return chats


def write_chat_id(chat_id: str, path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    output: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith("TELEGRAM_CHAT_ID=") or line.startswith("TELEGRAM_ALLOWED_CHAT_ID="):
            if not replaced:
                output.append(f"TELEGRAM_CHAT_ID={chat_id}")
                replaced = True
            continue
        output.append(line)
    if not replaced:
        if output and output[-1] != "":
            output.append("")
        output.append(f"TELEGRAM_CHAT_ID={chat_id}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(output) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write a single discovered chat ID to automation/.env")
    parser.add_argument("--json", action="store_true", help="print discovered chats as JSON")
    args = parser.parse_args()
    load_local_env(ROOT)
    try:
        updates = TelegramClient.from_token_env().updates()
    except Exception as exc:
        print(f"Telegram setup failed: {exc}", file=sys.stderr)
        return 1
    chats = chats_from_updates(updates)
    if args.json:
        print(json.dumps(chats, indent=2, ensure_ascii=False))
    elif not chats:
        print("No chat found. Open your bot in Telegram, send /start, then run this command again.")
    else:
        for chat_id, chat in chats.items():
            label = chat.get("title") or " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")])) or chat.get("username") or "Unnamed chat"
            print(f"{label}: {chat_id} ({chat.get('type', 'unknown')})")
    if args.write:
        if len(chats) != 1:
            print("--write requires exactly one discovered chat.", file=sys.stderr)
            return 2
        path = ROOT / "automation" / ".env"
        write_chat_id(next(iter(chats)), path)
        print(f"Saved TELEGRAM_CHAT_ID to {path}")
    return 0 if chats else 1


if __name__ == "__main__":
    raise SystemExit(main())
