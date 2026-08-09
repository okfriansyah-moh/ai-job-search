"""Durable, fail-closed notification idempotency for Telegram deliveries.

Telegram's Bot API does not accept an idempotency key.  A client-side ledger is
therefore the only way to make a retry safe.  This module records a delivery
*before* the request is made and deliberately treats an interrupted request as
uncertain, rather than retrying it and risking a duplicate card.

SQLite is the durable source of truth.  It uses ``BEGIN IMMEDIATE`` so two
processes sharing the workspace cannot claim the same role concurrently.  The
schema stores every useful identity for a job, so syndicated listings are also
collapsed when their URLs differ.  The small API is backend-neutral: a Redis
mirror can be enabled later without changing callers, while a missing/unhealthy
Redis service never weakens the local SQLite guarantee.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .filters import canonical_url, normalize
from .state import StateStore


SCHEMA_VERSION = 1
STATUS_PENDING = "pending"
STATUS_SENT = "sent"
STATUS_FAILED = "failed"
STATUS_UNCERTAIN = "uncertain"
BLOCKING_STATUSES = frozenset({STATUS_PENDING, STATUS_SENT, STATUS_UNCERTAIN})


@dataclass(frozen=True)
class Claim:
    """The result of atomically reserving a notification."""

    fingerprint: str
    claimed: bool
    status: str


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def job_identities(job: dict[str, Any]) -> tuple[str, ...]:
    """Return stable, ordered aliases used to identify one job notification.

    URLs are normalized first, followed by source-scoped platform IDs and a
    human fallback.  Keeping all aliases avoids false negatives when one board
    republishes another board's posting under a different URL.
    """
    identities: list[str] = []
    for value in (job.get("apply_url"), job.get("url")):
        value = canonical_url(value)
        if value:
            identities.append(f"url:{value}")

    source = normalize(job.get("source") or job.get("portal"))
    external_id = normalize(job.get("external_id") or job.get("job_id") or job.get("id"))
    if external_id:
        # Some aggregators expose globally unique IDs and no reliable source.
        identities.append(f"job:{source}:{external_id}" if source else f"job:{external_id}")

    company = normalize(job.get("company"))
    title = normalize(job.get("title"))
    location = normalize(job.get("job_location") or job.get("location"))
    if company and title:
        identities.append(f"role:{company}:{title}:{location}")

    # A malformed job should never turn all such cards into one notification.
    # The fallback is only used when no trustworthy identity is available.
    if not identities:
        payload = json.dumps(job, sort_keys=True, ensure_ascii=False, default=str)
        identities.append(f"payload:{_digest(payload)}")
    return tuple(dict.fromkeys(identities))


def notification_fingerprint(job: dict[str, Any]) -> str:
    """Return the public-safe fingerprint for a job card (never the raw URL)."""
    return _digest(job_identities(job)[0])


class NotificationDeduper:
    """SQLite-backed, transactional notification ledger.

    ``AUTOMATION_REDIS_URL`` is intentionally optional.  The environment value
    is reserved for deployments that add Redis as a cache/replica; SQLite stays
    authoritative so a Redis outage cannot result in duplicate sends.  This is
    a safer fallback than silently switching idempotency stores at runtime.
    """

    def __init__(self, state: StateStore):
        self.path = state.path("notification_ledger.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.redis_url = os.environ.get("AUTOMATION_REDIS_URL", "").strip()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=15000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        # Schema creation itself is a write.  It is retried so several worker
        # processes can cold-start against an empty state directory safely.
        for attempt in range(6):
            connection = self._connect()
            try:
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA synchronous=FULL")
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS notification_deliveries (
                        fingerprint TEXT PRIMARY KEY,
                        status TEXT NOT NULL CHECK (status IN ('pending', 'sent', 'failed', 'uncertain')),
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        sent_at REAL,
                        message_id TEXT,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        last_error TEXT,
                        payload_json TEXT NOT NULL DEFAULT '{}'
                    );
                    CREATE TABLE IF NOT EXISTS notification_identities (
                        identity_hash TEXT PRIMARY KEY,
                        fingerprint TEXT NOT NULL REFERENCES notification_deliveries(fingerprint) ON DELETE CASCADE,
                        identity_kind TEXT NOT NULL,
                        created_at REAL NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS notification_deliveries_status_idx
                        ON notification_deliveries(status, updated_at);
                    PRAGMA user_version = 1;
                    """
                )
                return
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower() or attempt == 5:
                    raise
                time.sleep(0.05 * (attempt + 1))
            finally:
                connection.close()

    @staticmethod
    def _identity_hash(identity: str) -> str:
        return _digest(identity)

    def claim(self, job: dict[str, Any], *, payload: dict[str, Any] | None = None) -> Claim:
        """Reserve a card if and only if no matching card can have been sent.

        ``pending`` also blocks subsequent workers forever.  A crashed process
        might have sent a request after reserving it; auto-expiring that claim
        would violate the zero-duplicate contract.  Operators may explicitly
        call :meth:`mark_failed` only when they know Telegram did not accept
        the request.
        """
        identities = job_identities(job)
        proposed = notification_fingerprint(job)
        identity_hashes = [self._identity_hash(value) for value in identities]
        now = time.time()
        safe_payload = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False, default=str)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            placeholders = ",".join("?" for _ in identity_hashes)
            matches = connection.execute(
                f"""
                SELECT d.fingerprint, d.status
                FROM notification_identities AS i
                JOIN notification_deliveries AS d ON d.fingerprint = i.fingerprint
                WHERE i.identity_hash IN ({placeholders})
                ORDER BY d.updated_at DESC
                """,
                identity_hashes,
            ).fetchall()
            blocking = next((row for row in matches if row["status"] in BLOCKING_STATUSES), None)
            if blocking:
                connection.execute("COMMIT")
                return Claim(str(blocking["fingerprint"]), False, str(blocking["status"]))

            # A prior explicit failure is safe to retry under its original
            # fingerprint; otherwise establish the proposed stable identity.
            fingerprint = str(matches[0]["fingerprint"]) if matches else proposed
            connection.execute(
                """
                INSERT INTO notification_deliveries
                    (fingerprint, status, created_at, updated_at, attempts, payload_json)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    attempts=notification_deliveries.attempts + 1,
                    last_error=NULL,
                    payload_json=excluded.payload_json
                """,
                (fingerprint, STATUS_PENDING, now, now, safe_payload),
            )
            for identity in identities:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO notification_identities
                        (identity_hash, fingerprint, identity_kind, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (self._identity_hash(identity), fingerprint, identity.partition(":")[0], now),
                )
            connection.execute("COMMIT")
            return Claim(fingerprint, True, STATUS_PENDING)
        except Exception:
            with contextlib.suppress(sqlite3.Error):
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def mark_sent(self, fingerprint: str, result: dict[str, Any] | None = None) -> None:
        message_id = str((result or {}).get("message_id") or "") or None
        now = time.time()
        connection = self._connect()
        try:
            connection.execute(
                """UPDATE notification_deliveries
                   SET status=?, sent_at=?, updated_at=?, message_id=?, last_error=NULL
                   WHERE fingerprint=?""",
                (STATUS_SENT, now, now, message_id, fingerprint),
            )
        finally:
            connection.close()

    def mark_failed(self, fingerprint: str, error: Exception | str, *, retryable: bool) -> None:
        """Record a known failure or an ambiguous delivery without resending it."""
        status = STATUS_FAILED if retryable else STATUS_UNCERTAIN
        detail = str(error)[-1000:]
        connection = self._connect()
        try:
            connection.execute(
                "UPDATE notification_deliveries SET status=?, updated_at=?, last_error=? WHERE fingerprint=?",
                (status, time.time(), detail, fingerprint),
            )
        finally:
            connection.close()

    def status(self, fingerprint: str) -> str | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT status FROM notification_deliveries WHERE fingerprint=?", (fingerprint,)
            ).fetchone()
        finally:
            connection.close()
        return str(row["status"]) if row else None

    def records(self) -> list[dict[str, Any]]:
        """Small diagnostic hook used by tests and operational troubleshooting."""
        connection = self._connect()
        try:
            return [dict(row) for row in connection.execute("SELECT * FROM notification_deliveries ORDER BY created_at")]
        finally:
            connection.close()

    def unresolved_count(self) -> int:
        """Return ambiguous deliveries that require an operator decision."""
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM notification_deliveries WHERE status IN (?, ?)",
                (STATUS_PENDING, STATUS_UNCERTAIN),
            ).fetchone()
            return int(row["count"])
        finally:
            connection.close()
