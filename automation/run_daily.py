"""Scheduled daily job-search runner.

The command is intentionally provider-neutral: Codex, Cursor, Claude Code,
Copilot, cron, and launchd all invoke this same entrypoint.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.filters import canonical_url, eligibility, job_key, normalize  # noqa: E402
from automation.config import load_local_env  # noqa: E402
from automation.portals import enabled_portals, enrich_job, health_check, run_portal  # noqa: E402
from automation.ranking import rank_job, ranked_job_sort_key  # noqa: E402
from automation.state import StateStore, atomic_write_json  # noqa: E402
from automation.telegram import send_digest  # noqa: E402
from automation.tracker import load_tracker, tracked_keys  # noqa: E402


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the personalized daily job search")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing state or sending Telegram")
    parser.add_argument("--force", action="store_true", help="Run even if this date already succeeded")
    parser.add_argument("--health", action="store_true", help="Probe each enabled portal and exit")
    parser.add_argument("--scheduler", choices=("codex", "cursor", "claude", "copilot", "cron", "launchd", "manual"), default="manual")
    return parser.parse_args()


def merge_jobs(existing: dict[str, Any], incoming: list[dict[str, Any]], tracker_keys: set[str], day: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    new_jobs: list[dict[str, Any]] = []
    for raw in incoming:
        if not raw.get("title") or not raw.get("company") or not raw.get("url"):
            continue
        key = job_key(raw)
        existing_key = key if key in existing else canonical_url(raw.get("apply_url") or raw.get("url"))
        if existing_key not in existing:
            existing_key = next((stored_key for stored_key, stored in existing.items() if isinstance(stored, dict) and job_key(stored) == key), "")
        if existing_key in existing:
            prior = existing[existing_key]
            sources = {str(item) for item in prior.get("sources", []) if item}
            sources.update(str(item) for item in raw.get("sources", []) if item)
            sources.add(str(prior.get("source") or prior.get("portal") or ""))
            sources.add(str(raw.get("source") or raw.get("portal") or ""))
            prior["sources"] = sorted(item for item in sources if item)
            urls = {str(item) for item in prior.get("source_urls", []) if item}
            urls.update(str(item) for item in raw.get("source_urls", []) if item)
            urls.update(str(item) for item in (prior.get("url"), raw.get("url")) if item)
            prior["source_urls"] = sorted(urls)
            continue
        tracker_identity = f"{normalize(raw.get('company'))}::{normalize(raw.get('title'))}::"
        if key in tracker_keys or tracker_identity in tracker_keys:
            continue
        job = {
            **raw,
            "key": key,
            "first_seen": day,
            "status": "new",
            "sources": sorted({str(raw.get("source") or raw.get("portal") or "")} - {""}),
            "source_urls": sorted(({str(item) for item in raw.get("source_urls", []) if item} | {str(raw.get("url") or "")}) - {""}),
        }
        if not job.get("job_location"):
            job["job_location"] = raw.get("location", "")
        gate = eligibility(job)
        job.update(gate)
        if gate["eligible"] != "yes":
            job["status"] = "skipped"
            job["fit"] = "low"
        existing[key] = job
        if job["status"] == "new":
            new_jobs.append(job)
    return existing, new_jobs


def run(args: argparse.Namespace) -> int:
    load_local_env(ROOT)
    day = datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
    state = StateStore(ROOT)
    if args.health:
        portals = enabled_portals(ROOT)
        for portal in portals:
            print(json.dumps(health_check(ROOT, portal), ensure_ascii=False))
        return 0
    with state.lock():
        if not state.can_run_today(day, args.force):
            print(f"Daily run already completed for {day}; no-op.")
            return 0
        try:
            fields, tracker_rows = load_tracker(ROOT / "job_search_tracker.csv")
            tracker_keys = tracked_keys(tracker_rows)
            state_path = ROOT / "job_scraper" / "seen_jobs.json"
            try:
                seen_data = json.loads(state_path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                seen_data = {"seen": {}}
            seen = seen_data.setdefault("seen", {})
            portal_reports = []
            fetched: list[dict[str, Any]] = []
            for portal in enabled_portals(ROOT):
                report = run_portal(ROOT, portal, since=(date.today() - timedelta(days=14)).isoformat())
                portal_reports.append(report)
                fetched.extend(report["results"])
            seen, new_jobs = merge_jobs(seen, fetched, tracker_keys, day)
            providers = [item.strip() for item in __import__("os").environ.get("AUTOMATION_AGENT_CHAIN", "claude,codex,copilot").split(",") if item.strip()]
            ranked: list[dict[str, Any]] = []
            for job in new_jobs:
                job = enrich_job(ROOT, job)
                gate = eligibility(job)
                job.update(gate)
                ranking = rank_job(ROOT, job, providers)
                job.update({
                    "rank_score": ranking["score"],
                    "rank_verdict": ranking["verdict"],
                    "rank_date": day,
                    "location": ranking.get("location", job.get("location")),
                    "language_gate": ranking.get("language_gate", job.get("language_gate")),
                    "language_note": ranking.get("language_note", job.get("language_note")),
                    "strengths": ranking.get("strengths", []),
                    "gaps": ranking.get("gaps", []),
                    "rank_provider": ranking.get("provider"),
                })
                job["status"] = "ranked"
                seen[job["key"]] = job
                ranked.append(job)
            ranked.sort(key=ranked_job_sort_key)
            if not args.dry_run:
                atomic_write_json(state_path, {"seen": seen})
            if args.dry_run:
                print(f"Fetched {len(fetched)} jobs; {len(new_jobs)} new eligible jobs from {len(portal_reports)} portals.")
            telegram = send_digest(ROOT, ranked, state, dry_run=args.dry_run)
            summary = {
                "fetched": len(fetched),
                "new": len(new_jobs),
                "ranked": len(ranked),
                "portals": {
                    report["portal"]: {"results": len(report["results"]), "errors": report["errors"], "skipped": report.get("skipped", "")}
                    for report in portal_reports
                },
                "telegram": telegram,
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            if not args.dry_run and telegram.get("failed", 0):
                raise RuntimeError(f"Telegram delivery failed for {telegram['failed']} batch(es); retained in outbox for retry")
            if not args.dry_run:
                state.mark_success(day, args.scheduler, summary)
            return 0
        except Exception as exc:
            if not args.dry_run:
                state.mark_failure(day, args.scheduler, str(exc))
            print(f"daily job-search failed: {exc}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(run(arguments()))
