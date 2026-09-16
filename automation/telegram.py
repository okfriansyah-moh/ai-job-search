"""Small standard-library Telegram Bot API client and message renderer."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .dedupe import NotificationDeduper, notification_fingerprint
from .state import StateStore
from .tracker import archive_outcome, pipeline_summary, record_stage, upsert_status


MAX_MESSAGE = 4096
CARD_BUDGET = 3500
REQUEST_TIMEOUT_SECONDS = 10
LONG_POLL_SECONDS = 25
LONG_POLL_TIMEOUT_SECONDS = LONG_POLL_SECONDS + REQUEST_TIMEOUT_SECONDS + 5
MAX_RESPONSE_BYTES = 1024 * 1024
RETRY_AFTER_PATTERNS = (
    re.compile(r"retry after\s+(\d+)", flags=re.IGNORECASE),
    re.compile(r'"retry_after"\s*:\s*(\d+)'),
)


class TelegramDeliveryError(RuntimeError):
    """A Telegram failure with an explicit retry-safety classification."""

    def __init__(self, message: str, *, retryable: bool):
        super().__init__(message)
        self.retryable = retryable


def _retry_after_seconds(error: TelegramDeliveryError) -> int | None:
    for pattern in RETRY_AFTER_PATTERNS:
        match = pattern.search(str(error))
        if not match:
            continue
        try:
            seconds = int(match.group(1))
        except (TypeError, ValueError):
            continue
        if seconds > 0:
            return seconds
    return None


def short_id(job: dict[str, Any]) -> str:
    return hashlib.sha256(str(job.get("key") or job.get("url") or job.get("title")).encode()).hexdigest()[:10]


def work_category(job: dict[str, Any]) -> str:
    explicit = str(job.get("work_mode") or "").strip().lower()
    if explicit in {"remote", "hybrid", "onsite", "on-site"}:
        return "On-site" if explicit in {"onsite", "on-site"} else explicit.title()
    text = " ".join(str(job.get(field, "")) for field in ("job_location", "description")).lower()
    if "remote" in text or "work from anywhere" in text or "distributed" in text:
        return "Remote"
    if "hybrid" in text:
        return "Hybrid"
    if "on-site" in text or "onsite" in text or "in-office" in text:
        return "On-site"
    return "Not stated"


def remote_taxonomy(job: dict[str, Any]) -> tuple[str, str]:
    """Return display-safe remote classification details without changing card actions.

    The eligibility pipeline is the authority for these fields.  Keeping a small
    fallback here lets older cards remain readable while state migrates forward.
    """
    classification = str(job.get("remote_classification") or "").strip()
    restriction = str(job.get("restriction_details") or "").strip()
    if not classification and work_category(job) == "Remote":
        classification = "Full Remote (Unclassified)"
    return classification, restriction


def card_value(job: dict[str, Any], field: str, fallback: str = "Not stated") -> str:
    value = str(job.get(field) or "").strip()
    return html.escape(value or fallback)


def render_card(job: dict[str, Any]) -> str:
    title = html.escape(str(job.get("title") or "Untitled role"))
    company = html.escape(str(job.get("company") or "Unknown company"))
    company_url = html.escape(str(job.get("company_url") or ""), quote=True)
    score = html.escape(str(job.get("rank_score", job.get("score", "unranked"))))
    verdict = html.escape(str(job.get("rank_verdict", job.get("verdict", "New match"))))
    job_location = card_value(job, "job_location")
    work_mode = html.escape(work_category(job))
    portal = html.escape(str(job.get("portal") or "unknown portal"))
    deadline = card_value(job, "deadline")
    posted_date = card_value(job, "posted_date")
    seniority = card_value(job, "seniority")
    employment_type = card_value(job, "employment_type")
    salary = card_value(job, "salary", "Not disclosed")
    url = html.escape(str(job.get("url") or ""), quote=True)
    remote_classification, restriction_details = remote_taxonomy(job)
    strengths = job.get("strengths") or []
    gaps = job.get("gaps") or []
    company_line = f'<a href="{company_url}">{company}</a>' if company_url.startswith(("http://", "https://")) else company
    lines = [
        f"<b>{title}</b> · {company_line}",
        f"<b>Fit:</b> {score} · {verdict}",
        f"<b>Job location:</b> {job_location}",
        f"<b>Work category:</b> {work_mode}",
        f"<b>Level:</b> {seniority} · <b>Employment:</b> {employment_type}",
        f"<b>Compensation:</b> {salary}",
        f"<b>Posted:</b> {posted_date} · <b>Deadline:</b> {deadline}",
        f"<b>Source:</b> {portal}",
    ]
    if remote_classification:
        lines.insert(4, f"<b>Remote taxonomy:</b> {html.escape(remote_classification)}")
    if restriction_details:
        insertion = 5 if remote_classification else 4
        lines.insert(insertion, f"<b>📍 Restriction:</b> {html.escape(restriction_details)}")
    if strengths:
        lines.append("<b>Why it matches</b>\n" + "\n".join(f"• {html.escape(str(item))}" for item in strengths[:2]))
    if gaps:
        lines.append("<b>Check</b>\n" + "\n".join(f"• {html.escape(str(item))}" for item in gaps[:1]))
    if url:
        lines.append(f'<a href="{url}">Open posting</a>')
    return "\n".join(lines)


def split_cards(cards: list[str], limit: int = CARD_BUDGET) -> list[str]:
    batches: list[str] = []
    current = ""
    for card in cards:
        candidate = f"{current}\n\n{card}" if current else card
        if current and len(candidate) > limit:
            batches.append(current)
            current = card
        else:
            current = candidate
    if current:
        batches.append(current)
    return batches


def keyboard(job: dict[str, Any]) -> dict[str, Any]:
    job_id = short_id(job)
    url = str(job.get("url") or "")
    open_button = {"text": "🔗 Open posting", "url": url} if url.startswith(("http://", "https://")) else {"text": "🔗 Open posting", "callback_data": f"noop:{job_id}"}
    return {
        "inline_keyboard": [
            [open_button],
            [
                {"text": "✅ Applied", "callback_data": f"apply:{job_id}"},
                {"text": "⭐ Interested", "callback_data": f"interest:{job_id}"},
                {"text": "⏭ Skip", "callback_data": f"skip:{job_id}"},
            ],
            [{"text": "📋 Update status", "callback_data": f"status:{job_id}"}],
        ]
    }


class TelegramClient:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = str(chat_id)
        self.base = f"https://api.telegram.org/bot{token}/"

    @classmethod
    def from_env(cls) -> "TelegramClient":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = (os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_ALLOWED_CHAT_ID") or "").strip()
        if not token or not chat_id:
            raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (or TELEGRAM_ALLOWED_CHAT_ID) are required")
        return cls(token, chat_id)

    @classmethod
    def from_token_env(cls) -> "TelegramClient":
        """Create a client for setup/discovery before a chat ID is known."""
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
        return cls(token, "")

    def call(self, method: str, payload: dict[str, Any], timeout: int = REQUEST_TIMEOUT_SECONDS) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.base + method,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read(MAX_RESPONSE_BYTES).decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read(MAX_RESPONSE_BYTES).decode(errors="replace")[-500:]
            # An HTTP response proves that Telegram rejected the request.  It
            # is safe to retain this card in the retryable outbox (including
            # 429 rate limits).  A transport failure below is deliberately
            # *not* retried automatically because Telegram may have accepted
            # the message before the connection was interrupted.
            raise TelegramDeliveryError(f"Telegram HTTP {exc.code}: {self._mask(detail)}", retryable=True) from exc
        except Exception as exc:
            raise TelegramDeliveryError(f"Telegram request failed: {self._mask(str(exc))}", retryable=False) from exc
        if not body.get("ok"):
            raise TelegramDeliveryError(
                f"Telegram API error: {self._mask(json.dumps(body, ensure_ascii=False))}", retryable=True
            )
        return body.get("result", {})

    def _mask(self, value: str) -> str:
        return value.replace(self.token, "[REDACTED_BOT_TOKEN]")

    def send(self, text: str, reply_markup: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.call("sendMessage", payload)

    def answer(self, callback_id: str, text: str = "") -> None:
        self.call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text[:200]})

    def updates(self, offset: int | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": LONG_POLL_SECONDS, "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            payload["offset"] = offset
        return self.call("getUpdates", payload, timeout=LONG_POLL_TIMEOUT_SECONDS)


def send_digest(root: Path, jobs: list[dict[str, Any]], state: StateStore, dry_run: bool = False) -> dict[str, Any]:
    if dry_run:
        print(f"Telegram preview: {len(jobs)} job card(s)")
        for index, job in enumerate(jobs, 1):
            print(f"\n--- Telegram job {index}/{len(jobs)} ---\n{render_card(job)}")
        return {"jobs": len(jobs), "batches": len(jobs), "sent": False}
    pending_outbox = state.read_json("telegram_outbox.json", [])
    deduper = NotificationDeduper(state)
    if not jobs and not pending_outbox:
        unresolved = deduper.unresolved_count()
        return {"jobs": 0, "batches": 0, "sent": unresolved == 0, "failed": unresolved, "uncertain": unresolved}
    mapping = state.read_json("telegram_jobs.json", {})
    for job in jobs:
        job_id = short_id(job)
        mapping[job_id] = job
    state.write_json("telegram_jobs.json", mapping)
    # The JSON outbox remains human-readable and survives configuration/rate
    # limit failures.  The SQLite ledger below is the actual idempotency gate;
    # never infer delivery state from the outbox alone.
    candidates: list[dict[str, Any]] = []
    for item in pending_outbox:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        candidates.append({
            **item,
            "fingerprint": str(item.get("fingerprint") or hashlib.sha256(
                f"legacy-outbox:{item.get('text')}:{json.dumps(item.get('reply_markup'), sort_keys=True)}".encode()
            ).hexdigest()),
            "job": item.get("job") if isinstance(item.get("job"), dict) else None,
        })
    if jobs:
        # A stable, per-set summary prevents a force-run from repeating the
        # heading while preserving the existing Telegram card presentation.
        job_fingerprints = sorted({notification_fingerprint(job) for job in jobs})
        candidates.append({
            "created": time.time(),
            "text": f"<b>Daily job matches</b>\n{len(jobs)} new ranked job(s).",
            "reply_markup": None,
            "fingerprint": hashlib.sha256(f"digest:{'|'.join(job_fingerprints)}".encode()).hexdigest(),
            "job": {"external_id": f"digest:{'|'.join(job_fingerprints)}", "source": "telegram-digest"},
            "kind": "digest",
        })
    seen_fingerprints: set[str] = set()
    for job in jobs:
        fingerprint = notification_fingerprint(job)
        if fingerprint in seen_fingerprints:
            continue
        candidates.append({
            "created": time.time(),
            "text": render_card(job),
            "reply_markup": keyboard(job),
            "fingerprint": fingerprint,
            "job": job,
            "kind": "job",
        })
        seen_fingerprints.add(fingerprint)

    # Do not send duplicate payloads queued by a previous process.  A record
    # in the ledger still decides the final outcome, making this an efficiency
    # measure rather than a correctness dependency.
    unique_candidates: list[dict[str, Any]] = []
    queued_fingerprints: set[str] = set()
    for item in candidates:
        fingerprint = str(item["fingerprint"])
        if fingerprint not in queued_fingerprints:
            unique_candidates.append(item)
            queued_fingerprints.add(fingerprint)

    sent = 0
    retry_outbox: list[dict[str, Any]] = []
    uncertain = 0
    try:
        client = TelegramClient.from_env()
    except Exception as exc:
        for item in unique_candidates:
            retry_outbox.append({**item, "error": str(exc)})
        state.write_json("telegram_outbox.json", retry_outbox)
        return {"jobs": len(jobs), "batches": len(unique_candidates), "sent": False, "failed": len(retry_outbox), "error": str(exc)}
    for item in unique_candidates:
        job = item.get("job") or {"external_id": f"outbox:{item['fingerprint']}", "source": "telegram-outbox"}
        claim = deduper.claim(job, payload={"text": item["text"], "reply_markup": item.get("reply_markup")})
        if not claim.claimed:
            # A sent, in-flight, or uncertain record is intentionally not
            # requeued.  Repeating it would break the zero-duplicate promise.
            continue
        retried_after_limit = False
        while True:
            try:
                result = client.send(item["text"], item.get("reply_markup"))
                deduper.mark_sent(claim.fingerprint, result)
                sent += 1
                time.sleep(0.5)
                break
            except TelegramDeliveryError as exc:
                retry_after = _retry_after_seconds(exc)
                if exc.retryable and retry_after is not None and not retried_after_limit:
                    # Honor Telegram's explicit backoff once, then fall back
                    # to the standard outbox retry path if it still fails.
                    time.sleep(retry_after + 1)
                    retried_after_limit = True
                    continue
                deduper.mark_failed(claim.fingerprint, exc, retryable=exc.retryable)
                if exc.retryable:
                    retry_outbox.append({**item, "error": str(exc)})
                else:
                    uncertain += 1
                break
            except Exception as exc:
                # Unknown client errors are treated just like an interrupted
                # network request: fail closed and leave an auditable record.
                deduper.mark_failed(claim.fingerprint, exc, retryable=False)
                uncertain += 1
                break
    state.write_json("telegram_outbox.json", retry_outbox)
    # Retain visibility of older ambiguous deliveries.  Silently treating a
    # later run as healthy would erase the only signal that a card might have
    # reached Telegram after its connection was interrupted.
    unresolved = deduper.unresolved_count()
    failed = len(retry_outbox) + unresolved
    return {
        "jobs": len(jobs),
        "batches": len(unique_candidates),
        "sent": failed == 0,
        "failed": failed,
        "uncertain": unresolved,
        "deduplicated": len(unique_candidates) - sent - len(retry_outbox) - uncertain,
    }


def process_update(root: Path, state: StateStore, update: dict[str, Any]) -> None:
    client = TelegramClient.from_env()
    allowed = client.chat_id
    message = update.get("message") or {}
    callback = update.get("callback_query")
    chat_id = str((message.get("chat") or {}).get("id") or ((callback or {}).get("message") or {}).get("chat", {}).get("id", ""))
    if chat_id != allowed:
        if callback:
            client.answer(callback.get("id", ""), "This bot is private.")
        return
    mapping = state.read_json("telegram_jobs.json", {})
    tracker = root / "job_search_tracker.csv"
    if callback:
        data = str(callback.get("data", ""))
        parts = data.split(":")
        action = parts[0]
        job_id = parts[1] if len(parts) > 1 else ""
        job = mapping.get(job_id)
        client.answer(callback.get("id", ""))
        if not job:
            client.send("That job card has expired. Use /new for the latest list.")
            return
        if action == "noop":
            client.send(f"<a href=\"{html.escape(str(job.get('url', '')), quote=True)}\">Open {html.escape(str(job.get('title', 'posting')))}</a>")
        elif action == "interest":
            interests = state.read_json("interests.json", {})
            interests[job_id] = {"job": job, "updated": time.time()}
            state.write_json("interests.json", interests)
            client.send("⭐ Saved to your interested list.")
        elif action == "skip":
            skipped = state.read_json("skipped.json", {})
            skipped[job_id] = {"job": job, "updated": time.time()}
            state.write_json("skipped.json", skipped)
            client.send("⏭ Skipped. It will not be surfaced again by the bot.")
        elif action == "apply":
            pending = state.read_json("pending.json", {})
            pending[chat_id] = {"action": "apply", "job_id": job_id}
            state.write_json("pending.json", pending)
            client.send("Confirm application tracking? This records the job as applied but never submits it.", {"inline_keyboard": [[{"text": "Confirm applied", "callback_data": f"confirm_apply:{job_id}"}, {"text": "Cancel", "callback_data": f"cancel:{job_id}"}]]})
        elif action == "confirm_apply":
            upsert_status(tracker, job, "applied", "marked applied from the Telegram confirmation", fit=str(job.get("rank_score", "")))
            archive_outcome(root, job, "applied", "Marked applied from Telegram; submission was completed by the candidate.")
            client.send("✅ Recorded as applied. The bot did not submit anything externally.")
        elif action == "status":
            buttons = [[{"text": status.title(), "callback_data": f"setstatus:{job_id}:{status}"}] for status in ("interview", "offer", "hired", "rejected", "withdrawn")]
            buttons.append([{"text": "📞 Update interview stage", "callback_data": f"stage:{job_id}"}])
            client.send("Choose the new application status:", {"inline_keyboard": buttons})
        elif action == "stage":
            stages = ("phone", "technical", "case", "final", "offer")
            client.send("Choose the stage reached:", {"inline_keyboard": [[{"text": stage.title(), "callback_data": f"setstage:{job_id}:{stage}"}] for stage in stages]})
        elif action == "setstage":
            stage = parts[2] if len(parts) > 2 else "phone"
            record_stage(root, job, stage)
            upsert_status(tracker, job, "interview", f"interview stage recorded: {stage}", fit=str(job.get("rank_score", "")))
            client.send(f"✅ Interview stage recorded: <b>{html.escape(stage.title())}</b>.")
        elif action == "cancel":
            pending = state.read_json("pending.json", {})
            pending.pop(chat_id, None)
            state.write_json("pending.json", pending)
            client.send("↩ Cancelled.")
        elif action == "setstatus":
            status = parts[2] if len(parts) == 3 else "interview"
            upsert_status(tracker, job, status, f"status changed to {status} from Telegram", fit=str(job.get("rank_score", "")))
            archive_outcome(root, job, status, f"Status changed to {status} from Telegram.")
            client.send(f"✅ Status updated to <b>{html.escape(status)}</b>.")
        return
    text = str((message.get("text") or "")).strip()
    if text == "/pipeline":
        summary = pipeline_summary(tracker)
        body = "\n".join(f"<b>{html.escape(key)}</b>: {value}" for key, value in sorted(summary.items())) or "No tracked applications yet."
        client.send(body)
    elif text == "/new" or text == "/today":
        jobs = list(mapping.values())[-10:]
        if not jobs:
            client.send("No job cards are available yet. Run the daily search first.")
        else:
            for job in jobs:
                client.send(render_card(job), keyboard(job))
    elif text.startswith("/job "):
        job = mapping.get(text.split(maxsplit=1)[1])
        client.send(render_card(job) if job else "Unknown job ID.", keyboard(job) if job else None)
    elif text.startswith("/note "):
        parts = text.split(maxsplit=2)
        job = mapping.get(parts[1]) if len(parts) > 1 else None
        if job and len(parts) > 2:
            upsert_status(tracker, job, "interested", parts[2], fit=str(job.get("rank_score", "")))
            archive_outcome(root, job, "interested", parts[2])
            client.send("📝 Note saved.")
        else:
            client.send("Usage: /note <job-id> <your note>")
    elif text.startswith("/stage "):
        parts = text.split(maxsplit=2)
        job = mapping.get(parts[1]) if len(parts) > 1 else None
        if job and len(parts) > 2:
            record_stage(root, job, parts[2])
            upsert_status(tracker, job, "interview", f"interview stage recorded: {parts[2]}", fit=str(job.get("rank_score", "")))
            client.send("✅ Interview stage recorded.")
        else:
            client.send("Usage: /stage <job-id> <phone|technical|case|final|offer>")
    elif text == "/help":
        client.send("<b>Job Search Bot</b>\n/today or /new — latest cards\n/pipeline — application statuses\n/job &lt;id&gt; — show one job\n/note &lt;id&gt; &lt;text&gt; — save a note\n/stage &lt;id&gt; &lt;stage&gt; — record interview stage\nApplications are never submitted automatically.")


def listen(root: Path, state: StateStore) -> None:
    client = TelegramClient.from_env()
    telegram_state = state.read_json("telegram_state.json", {"offset": None})
    offset = telegram_state.get("offset")
    while True:
        try:
            updates = client.updates(offset)
        except Exception as exc:
            print(f"Telegram listener temporarily unavailable: {exc}", file=sys.stderr)
            time.sleep(5)
            continue
        for update in updates:
            offset = int(update.get("update_id", 0)) + 1
            telegram_state["offset"] = offset
            process_update(root, state, update)
            state.write_json("telegram_state.json", telegram_state)
