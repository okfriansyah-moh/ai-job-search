"""Offline tests for the scheduler-neutral job-search automation."""

from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from automation.filters import canonical_url, eligibility, job_key
from automation.portals import normalize_job
from automation.run_daily import merge_jobs
from automation.ranking import deterministic_rank
from automation.state import StateStore
from automation.telegram import LONG_POLL_TIMEOUT_SECONDS, TelegramClient, render_card, short_id, split_cards
from automation.telegram_setup import chats_from_updates
from automation.tracker import CURRENT_HEADER, load_tracker, pipeline_summary, record_stage, upsert_status


class AutomationTest(unittest.TestCase):
    def test_location_and_india_gates(self):
        remote = {"company": "Example", "title": "Software Engineering Manager", "location": "Remote", "description": "Remote worldwide"}
        self.assertEqual(eligibility(remote)["eligible"], "yes")
        self.assertEqual(eligibility({**remote, "location": "Gurugram, India"})["eligible"], "no")
        self.assertEqual(eligibility({**remote, "location": "London, UK", "description": "Hybrid role"})["eligible"], "no")
        self.assertEqual(eligibility({**remote, "location": "Jakarta, Indonesia"})["eligible"], "no")
        self.assertEqual(eligibility({**remote, "title": "Software Engineer"})["eligible"], "no")

    def test_language_gate(self):
        job = {"company": "Example", "title": "Lead", "location": "Remote", "description": "German language required"}
        result = eligibility(job)
        self.assertEqual(result["language_gate"], "FAIL")
        self.assertEqual(result["eligible"], "no")

    def test_deterministic_rank_has_contract(self):
        result = deterministic_rank({"company": "Fintech", "title": "Engineering Manager", "location": "Remote", "description": "Remote payments platform using Go and Java"})
        self.assertIn(result["verdict"], {"Strong Fit", "Good Fit", "Moderate Fit", "Weak Fit", "Poor Fit"})
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertTrue(result["strengths"])

    def test_tracker_preserves_current_schema_and_is_idempotent_keyed_by_url(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tracker.csv"
            path.write_text(",".join(CURRENT_HEADER) + "\n", encoding="utf-8")
            job = {"company": "Example", "title": "Software Engineering Manager", "url": "https://example.test/job/1"}
            upsert_status(path, job, "applied", "first application", fit="88")
            upsert_status(path, job, "interview", "screen scheduled", fit="88")
            fields, rows = load_tracker(path)
            self.assertEqual(fields, CURRENT_HEADER)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "interview")
            self.assertIn("first application", rows[0]["notes"])
            self.assertEqual(pipeline_summary(path), {"interview": 1})

    def test_telegram_batches_and_escaping(self):
        jobs = [{"key": str(index), "title": "Role & <test>", "company": "Company", "url": "https://example.test", "job_location": "New York, United States", "work_mode": "remote", "employment_type": "Full-time", "strengths": ["Good match"], "gaps": ["Check details"]} for index in range(20)]
        batches = split_cards([render_card(job) for job in jobs])
        self.assertTrue(all(len(batch) <= 3500 for batch in batches))
        self.assertIn("&amp;", batches[0])
        self.assertIn("Job location:", batches[0])
        self.assertIn("Work category:</b> Remote", batches[0])
        self.assertEqual(len(short_id(jobs[0])), 10)

    def test_state_ledger_allows_only_one_successful_daily_run(self):
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore(Path(directory))
            with store.lock():
                self.assertTrue(store.can_run_today("2026-08-05"))
                store.mark_success("2026-08-05", "codex", {"new": 1})
            with store.lock():
                self.assertFalse(store.can_run_today("2026-08-05"))
                self.assertTrue(store.can_run_today("2026-08-06"))

    def test_job_key_deduplicates_sources_by_company_title_location(self):
        first = {"url": "https://first.test/1?utm_source=email", "company": "A", "title": "B", "job_location": "Remote"}
        second = {"url": "https://second.test/2", "company": "A", "title": "B", "job_location": "Remote"}
        self.assertEqual(job_key(first), job_key(second))
        self.assertEqual(canonical_url(first["url"]), "https://first.test/1")

    def test_normalize_global_source_fields_and_merge_provenance(self):
        raw = normalize_job({"title": "Senior Software Engineer", "company": "Example", "url": "https://example.test/job", "workMode": "remote", "externalId": "1", "source": "remotive", "sourceUrls": ["https://remotive.test/job"], "employmentType": "full_time"}, "remotive-search")
        self.assertEqual(raw["work_mode"], "remote")
        self.assertEqual(raw["external_id"], "1")
        seen, new = merge_jobs({}, [raw], set(), "2026-08-06")
        duplicate = {**raw, "source": "remoteok", "url": "https://remoteok.test/job", "source_urls": ["https://remoteok.test/job"]}
        seen, repeated = merge_jobs(seen, [duplicate], set(), "2026-08-06")
        self.assertEqual(len(new), 1)
        self.assertEqual(repeated, [])
        stored = next(iter(seen.values()))
        self.assertEqual(stored["sources"], ["remoteok", "remotive"])

    def test_merge_jobs_accepts_legacy_url_key(self):
        raw = {"title": "Senior Software Engineer", "company": "Example", "url": "https://example.test/job", "job_location": "Remote", "work_mode": "remote", "source": "remotive"}
        legacy = {"https://example.test/job": {**raw, "key": "https://example.test/job", "status": "ranked"}}
        seen, new = merge_jobs(legacy, [raw], set(), "2026-08-06")
        self.assertEqual(new, [])
        self.assertEqual(len(seen), 1)

    def test_interview_stage_is_recorded_in_application_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcome = record_stage(root, {"company": "Example", "title": "Engineer", "url": "https://example.test/1"}, "technical")
            text = outcome.read_text(encoding="utf-8")
            self.assertIn("- [x] Technical interview", text)

    def test_telegram_client_uses_json_and_bounded_timeout(self):
        response = MagicMock()
        response.read.return_value = b'{"ok": true, "result": {"message_id": 1}}'
        response.__enter__.return_value = response
        with patch("automation.telegram.urllib.request.urlopen", return_value=response) as urlopen:
            result = TelegramClient("secret-token", "123").send("Hello")
        self.assertEqual(result["message_id"], 1)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(json.loads(request.data.decode("utf-8"))["chat_id"], "123")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 10)
        self.assertEqual(response.read.call_args.args[0], 1024 * 1024)

    def test_telegram_updates_allow_long_poll_to_finish(self):
        response = MagicMock()
        response.read.return_value = b'{"ok": true, "result": []}'
        response.__enter__.return_value = response
        with patch("automation.telegram.urllib.request.urlopen", return_value=response) as urlopen:
            self.assertEqual(TelegramClient("secret-token", "123").updates(), [])
        self.assertEqual(urlopen.call_args.kwargs["timeout"], LONG_POLL_TIMEOUT_SECONDS)

    def test_telegram_chat_id_alias_and_update_discovery(self):
        updates = [{"update_id": 1, "message": {"chat": {"id": 42, "type": "private", "first_name": "Mekari"}}}]
        self.assertEqual(chats_from_updates(updates)["42"]["first_name"], "Mekari")


if __name__ == "__main__":
    unittest.main()
