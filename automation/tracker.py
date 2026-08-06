"""CSV compatibility layer for application tracking."""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Any

from .filters import job_key, normalize
from .state import atomic_write_text


CURRENT_HEADER = ["company", "role", "url", "status", "fit", "cv_file", "cover_letter_file", "date_applied", "notes"]


def load_tracker(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return CURRENT_HEADER.copy(), []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or CURRENT_HEADER), list(reader)


def tracker_job_key(row: dict[str, Any]) -> str:
    return job_key({"url": row.get("url"), "company": row.get("company"), "title": row.get("role")})


def find_row(rows: list[dict[str, str]], job: dict[str, Any]) -> dict[str, str] | None:
    target = job_key(job)
    company_role = f"{normalize(job.get('company'))}::{normalize(job.get('title') or job.get('role'))}"
    for row in rows:
        if tracker_job_key(row) == target:
            return row
        if f"{normalize(row.get('company'))}::{normalize(row.get('role'))}" == company_role:
            return row
    return None


def tracked_keys(rows: list[dict[str, str]]) -> set[str]:
    return {tracker_job_key(row) for row in rows}


def _set_if_present(row: dict[str, str], fields: list[str], aliases: tuple[str, ...], value: str) -> None:
    for field in aliases:
        if field in fields:
            row[field] = value
            return


def _append_note(row: dict[str, str], fields: list[str], note: str) -> None:
    for field in ("notes", "note"):
        if field in fields:
            existing = (row.get(field) or "").strip()
            row[field] = f"{existing}; {note}" if existing else note
            return


def write_tracker(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    output: list[str] = []
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write_text(path, buffer.getvalue())


def upsert_status(
    path: Path,
    job: dict[str, Any],
    status: str,
    note: str,
    *,
    fit: str = "",
    channel: str = "telegram",
    applied_date: str | None = None,
) -> dict[str, str]:
    fields, rows = load_tracker(path)
    row = find_row(rows, job)
    if row is None:
        row = {field: "" for field in fields}
        _set_if_present(row, fields, ("company",), str(job.get("company", "")))
        _set_if_present(row, fields, ("role", "title"), str(job.get("title", "")))
        _set_if_present(row, fields, ("url", "source"), str(job.get("url", "")))
        rows.append(row)
    _set_if_present(row, fields, ("status",), status)
    _set_if_present(row, fields, ("fit", "fit_rating"), fit)
    if applied_date or status == "applied":
        _set_if_present(row, fields, ("date_applied", "date"), applied_date or date.today().isoformat())
    _set_if_present(row, fields, ("channel",), channel)
    _append_note(row, fields, f"{date.today().isoformat()} {channel}: {note}")
    write_tracker(path, fields, rows)
    return row


def pipeline_summary(path: Path) -> dict[str, int]:
    _, rows = load_tracker(path)
    summary: dict[str, int] = {}
    for row in rows:
        status = (row.get("status") or "unknown").strip().lower() or "unknown"
        summary[status] = summary.get(status, 0) + 1
    return summary


def archive_outcome(root: Path, job: dict[str, Any], status: str, note: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "_", f"{job.get('company', '')}_{job.get('title', '')}".lower()).strip("_")[:120]
    folder = root / "documents" / "applications" / slug
    folder.mkdir(parents=True, exist_ok=True)
    outcome = folder / "outcome.md"
    if outcome.exists():
        text = outcome.read_text(encoding="utf-8")
        text += f"\n{date.today().isoformat()} (via Telegram): {note}\n"
    else:
        text = (
            f"# Outcome: {job.get('company', '')} — {job.get('title', '')}\n\n"
            f"**Status:** {status}\n\n"
            f"**Source:** {job.get('url', '')}\n\n"
            "## Interview stages reached\n"
            "- [ ] Phone screen\n- [ ] Technical interview\n- [ ] Case interview\n- [ ] Final round\n- [ ] Offer received\n\n"
            "## Notes\n"
            f"{date.today().isoformat()} (via Telegram): {note}\n"
        )
    outcome.write_text(text, encoding="utf-8")
    return outcome


def record_stage(root: Path, job: dict[str, Any], stage: str) -> Path:
    labels = {
        "phone": "Phone screen",
        "phone screen": "Phone screen",
        "technical": "Technical interview",
        "technical interview": "Technical interview",
        "case": "Case interview",
        "case interview": "Case interview",
        "final": "Final round",
        "final round": "Final round",
        "offer": "Offer received",
        "offer received": "Offer received",
    }
    label = labels.get(normalize(stage), stage.strip().title())
    outcome = archive_outcome(root, job, "interview", f"Interview stage reached: {label}.")
    text = outcome.read_text(encoding="utf-8")
    marker = f"- [ ] {label}"
    checked = f"- [x] {label} ({date.today().isoformat()})"
    if marker in text:
        text = text.replace(marker, checked, 1)
    elif f"- [x] {label}" not in text:
        text += f"\n- [x] {label} ({date.today().isoformat()})\n"
    outcome.write_text(text, encoding="utf-8")
    return outcome
