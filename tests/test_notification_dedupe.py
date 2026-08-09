"""Regression tests for durable, fail-closed Telegram idempotency."""

from __future__ import annotations

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

from automation.dedupe import NotificationDeduper, STATUS_FAILED, STATUS_SENT, STATUS_UNCERTAIN
from automation.state import StateStore
from automation.telegram import send_digest


class NotificationDeduplicationTest(unittest.TestCase):
    def test_ledger_joins_url_and_role_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = NotificationDeduper(StateStore(Path(directory)))
            first = {
                "company": "Example",
                "title": "Principal Engineer",
                "job_location": "Remote",
                "url": "https://first.test/jobs/9?utm_source=x",
            }
            syndicated = {
                "company": "Example",
                "title": "Principal Engineer",
                "job_location": "Remote",
                "url": "https://syndicated.test/roles/99",
            }
            claim = ledger.claim(first)
            self.assertTrue(claim.claimed)
            ledger.mark_sent(claim.fingerprint, {"message_id": 123})
            duplicate = ledger.claim(syndicated)
            self.assertFalse(duplicate.claimed)
            self.assertEqual(duplicate.status, STATUS_SENT)
            self.assertEqual(len(ledger.records()), 1)

    def test_ledger_only_allows_one_concurrent_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            state = StateStore(Path(directory))
            job = {
                "company": "Example",
                "title": "Engineering Manager",
                "job_location": "Remote",
                "url": "https://example.test/role",
            }
            with ThreadPoolExecutor(max_workers=4) as executor:
                claims = list(executor.map(lambda _: NotificationDeduper(state).claim(job), range(4)))
            self.assertEqual(sum(claim.claimed for claim in claims), 1)

    def test_ledger_retries_only_known_non_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = NotificationDeduper(StateStore(Path(directory)))
            safe = ledger.claim({"external_id": "safe", "source": "test"})
            ledger.mark_failed(safe.fingerprint, "HTTP 429", retryable=True)
            self.assertEqual(ledger.status(safe.fingerprint), STATUS_FAILED)
            self.assertTrue(ledger.claim({"external_id": "safe", "source": "test"}).claimed)
            uncertain = ledger.claim({"external_id": "uncertain", "source": "test"})
            ledger.mark_failed(uncertain.fingerprint, "timeout", retryable=False)
            self.assertEqual(ledger.status(uncertain.fingerprint), STATUS_UNCERTAIN)
            self.assertFalse(ledger.claim({"external_id": "uncertain", "source": "test"}).claimed)

    def test_send_digest_never_repeats_a_delivered_job_card(self):
        with tempfile.TemporaryDirectory() as directory:
            state = StateStore(Path(directory))
            job = {
                "company": "Example",
                "title": "Principal Engineer",
                "job_location": "Remote",
                "url": "https://example.test/jobs/1",
                "rank_score": 90,
            }
            client = MagicMock()
            client.send.return_value = {"message_id": 1}
            with patch("automation.telegram.TelegramClient.from_env", return_value=client), patch("automation.telegram.time.sleep"):
                first = send_digest(Path(directory), [job], state)
                second = send_digest(Path(directory), [job], state)
            self.assertEqual(first["failed"], 0)
            self.assertEqual(second["failed"], 0)
            # Summary + card from the first call, and nothing from the second.
            self.assertEqual(client.send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
