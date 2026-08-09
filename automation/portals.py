"""Run the installed portal CLIs using their documented interfaces."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any


QUERIES = [
    "Software Engineering Manager",
    "Senior Software Engineer",
    "Principal Engineer",
    "Technical Lead",
    "Team Lead Software Engineering",
]

LINKEDIN_LOCATIONS = [
    ("United States", True),
    ("United Kingdom", True),
    ("Germany", True),
    ("Netherlands", True),
    ("Japan", True),
    ("Malaysia", True),
    ("Singapore", True),
    ("Australia", True),
    ("New Zealand", True),
    ("Remote", True),
]


@dataclass(frozen=True)
class PortalSpec:
    name: str
    command: str


SPECS = {
    "freehire-search": PortalSpec("freehire-search", "freehire-search"),
    "linkedin-search": PortalSpec("linkedin-search", "linkedin-search"),
    "jobindex-search": PortalSpec("jobindex-search", "jobindex-search"),
    "jobnet-search": PortalSpec("jobnet-search", "jobnet-search"),
    "jobbank-search": PortalSpec("jobbank-search", "jobbank-search"),
    "jobdanmark-search": PortalSpec("jobdanmark-search", "jobdanmark-search"),
    "remotive-search": PortalSpec("remotive-search", "global-job-sources"),
    "remoteok-search": PortalSpec("remoteok-search", "global-job-sources"),
    "jobicy-search": PortalSpec("jobicy-search", "global-job-sources"),
    "adzuna-search": PortalSpec("adzuna-search", "global-job-sources"),
    "greenhouse-search": PortalSpec("greenhouse-search", "global-job-sources"),
    "lever-search": PortalSpec("lever-search", "global-job-sources"),
    "ashby-search": PortalSpec("ashby-search", "global-job-sources"),
    "highfive-search": PortalSpec("highfive-search", "global-job-sources"),
    "eztrackr-search": PortalSpec("eztrackr-search", "global-job-sources"),
    "hubstaff-talent-search": PortalSpec("hubstaff-talent-search", "global-job-sources"),
    "remotewoman-search": PortalSpec("remotewoman-search", "global-job-sources"),
    "wellfound-search": PortalSpec("wellfound-search", "global-job-sources"),
    "weworkremotely-search": PortalSpec("weworkremotely-search", "global-job-sources"),
    "workwave-search": PortalSpec("workwave-search", "global-job-sources"),
    "ai-jobs-search": PortalSpec("ai-jobs-search", "global-job-sources"),
    "toptal-search": PortalSpec("toptal-search", "global-job-sources"),
    "flexjobs-search": PortalSpec("flexjobs-search", "global-job-sources"),
    "jsremotely-search": PortalSpec("jsremotely-search", "global-job-sources"),
}

GLOBAL_SOURCE_PORTALS = {
    "remotive-search": "remotive",
    "remoteok-search": "remoteok",
    "jobicy-search": "jobicy",
    "adzuna-search": "adzuna",
    "greenhouse-search": "greenhouse",
    "lever-search": "lever",
    "ashby-search": "ashby",
    "highfive-search": "highfive",
    "eztrackr-search": "eztrackr",
    "hubstaff-talent-search": "hubstaff",
    "remotewoman-search": "remotewoman",
    "wellfound-search": "wellfound",
    "weworkremotely-search": "weworkremotely",
    "workwave-search": "workwave",
    "ai-jobs-search": "aijobs",
    "toptal-search": "toptal",
    "flexjobs-search": "flexjobs",
    "jsremotely-search": "jsremotely",
}


def enabled_portals(root: Path) -> list[str]:
    result: list[str] = []
    skills_root = root / ".agents" / "skills"
    for skill in sorted(skills_root.glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8", errors="replace")
        if re.search(r"^enabled:\s*false\s*$", text, re.MULTILINE):
            continue
        name = skill.parent.name
        if name in SPECS:
            result.append(name)
    return result


def cli_path(root: Path, portal: str) -> Path:
    return root / ".agents" / "skills" / portal / "cli" / "src" / "cli.ts"


def commands_for(portal: str, queries: list[str], since: str) -> list[list[str]]:
    path = f".agents/skills/{portal}/cli/src/cli.ts"
    query = queries[0] if queries else ""
    if portal in GLOBAL_SOURCE_PORTALS:
        command = [
            "bun", "run", ".agents/skills/global-job-sources/cli/src/cli.ts", "search",
            "--source", GLOBAL_SOURCE_PORTALS[portal], "--jobage", "14", "--limit", "100", "--format", "json",
        ]
        for value in queries:
            command.extend(["--query", value])
        return [command]
    if portal == "freehire-search":
        return [["bun", "run", path, "search", "--query", query, "--jobage", "14", "--limit", "20", "--format", "json"]]
    if portal == "linkedin-search":
        commands: list[list[str]] = []
        for location, remote_only in LINKEDIN_LOCATIONS:
            command = [
                "bun", "run", path, "search",
                "--location", location,
                "--query", query,
                "--jobage", "14",
                "--limit", "20",
                "--format", "json",
            ]
            if remote_only:
                command.extend(["--remote", "remote"])
            commands.append(command)
        return commands
    if portal == "jobindex-search":
        return [["bun", "run", path, "search", "--query", query, "--jobage", "14", "--sort", "date", "--limit", "20", "--format", "json"]]
    if portal == "jobnet-search":
        return [["bun", "run", path, "search", "--search-string", query, "--order", "PublicationDate", "--limit", "20", "--format", "json"]]
    if portal == "jobbank-search":
        return [["bun", "run", path, "search", "--key", query, "--since", since, "--limit", "20", "--format", "json"]]
    if portal == "jobdanmark-search":
        return [["bun", "run", path, "search", "--text", query, "--limit", "20", "--format", "json"]]
    return []


def _decode_json(stdout: str) -> Any:
    decoder = json.JSONDecoder()
    for index, char in enumerate(stdout):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(stdout[index:])
            return value
        except json.JSONDecodeError:
            continue
    return None


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("results", "jobs", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                nested = _items(value)
                if nested:
                    return nested
    return []


def _first(item: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if item.get(name) not in (None, ""):
            return item[name]
    return ""


def normalize_job(item: dict[str, Any], portal: str) -> dict[str, Any]:
    location = _first(item, ("location", "locations", "jobLocation", "city", "region"))
    source_urls = item.get("sourceUrls") or item.get("source_urls") or []
    if isinstance(source_urls, str):
        source_urls = [source_urls]
    if not isinstance(source_urls, list):
        source_urls = []
    return {
        "title": _first(item, ("title", "jobTitle", "name", "role")),
        "company": _first(item, ("company", "companyName", "employer", "organization")),
        "url": _first(item, ("url", "link", "jobUrl", "applyUrl", "applicationUrl", "apply_url")),
        "location": location,
        "job_location": location,
        "work_mode": _first(item, ("work_mode", "workMode", "workplaceType", "remote")),
        "description": _first(item, ("description", "body", "content", "snippet", "summary")),
        "posted_date": _first(item, ("posted_date", "postedDate", "publicationDate", "date", "published", "created")),
        "deadline": _first(item, ("deadline", "applicationDeadline", "closingDate", "validThrough")),
        "salary": _first(item, ("salary", "salaryRange", "compensation")),
        "external_id": _first(item, ("external_id", "externalId", "id", "jobId", "jobAdId", "slug")),
        "apply_url": _first(item, ("apply_url", "applyUrl", "applicationUrl")),
        "employment_type": _first(item, ("employment_type", "employmentType", "job_type", "jobType", "contract_type")),
        "seniority": _first(item, ("seniority", "seniorityLevel", "jobLevel")),
        "source": _first(item, ("source", "provider")) or portal,
        "source_urls": source_urls,
        "portal": portal,
    }


def command_work_mode(command: list[str]) -> str:
    try:
        return command[command.index("--remote") + 1]
    except (ValueError, IndexError):
        return ""


def run_portal(root: Path, portal: str, *, timeout: int = 45, since: str | None = None) -> dict[str, Any]:
    since = since or (date.today() - timedelta(days=14)).isoformat()
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    commands_run = 0
    query_groups = [QUERIES] if portal in GLOBAL_SOURCE_PORTALS else [[query] for query in QUERIES]
    skipped = ""
    for queries in query_groups:
        query_label = ", ".join(queries)
        for command in commands_for(portal, queries, since):
            commands_run += 1
            try:
                completed = subprocess.run(
                    command,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                errors.append(f"{query_label}: {exc}")
                continue
            if completed.returncode != 0:
                errors.append(f"{query_label}: {completed.stderr.strip()[-500:] or 'exit ' + str(completed.returncode)}")
                continue
            payload = _decode_json(completed.stdout)
            if isinstance(payload, dict):
                meta = payload.get("meta")
                if isinstance(meta, dict):
                    skipped = str(meta.get("skipped") or skipped)
            for item in _items(payload):
                job = normalize_job(item, portal)
                job["work_mode"] = job.get("work_mode") or command_work_mode(command)
                results.append(job)
    return {"portal": portal, "results": results, "errors": errors, "commands": commands_run, "skipped": skipped}


def enrich_job(root: Path, job: dict[str, Any], *, timeout: int = 45) -> dict[str, Any]:
    if job.get("portal") != "linkedin-search":
        return job
    identifier = str(job.get("external_id") or job.get("url") or "").strip()
    if not identifier:
        return job
    command = [
        "bun",
        "run",
        ".agents/skills/linkedin-search/cli/src/cli.ts",
        "detail",
        identifier,
        "--format",
        "json",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return job
    if completed.returncode != 0:
        return job
    payload = _decode_json(completed.stdout)
    if not isinstance(payload, dict):
        return job
    location = _first(payload, ("location", "jobLocation", "city", "region")) or job.get("job_location") or job.get("location")
    description = _first(payload, ("description", "body", "content")) or job.get("description")
    enriched = {
        **job,
        "title": _first(payload, ("title", "jobTitle", "name", "role")) or job.get("title"),
        "company": _first(payload, ("company", "companyName", "employer", "organization")) or job.get("company"),
        "location": location,
        "job_location": location,
        "description": description,
        "apply_url": _first(payload, ("applyUrl", "applicationUrl")) or job.get("apply_url", ""),
        "company_url": _first(payload, ("companyUrl",)) or job.get("company_url", ""),
        "seniority": _first(payload, ("seniority", "seniorityLevel")) or job.get("seniority", ""),
        "employment_type": _first(payload, ("employmentType",)) or job.get("employment_type", ""),
        "job_function": _first(payload, ("jobFunction",)) or job.get("job_function", ""),
        "industries": _first(payload, ("industries",)) or job.get("industries", ""),
    }
    return enriched


def health_check(root: Path, portal: str, timeout: int = 45) -> dict[str, Any]:
    command = commands_for(portal, ["Software Engineering Manager"], (date.today() - timedelta(days=14)).isoformat())[0]
    if "--limit" in command:
        command[command.index("--limit") + 1] = "3"
    try:
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"portal": portal, "status": "inconclusive", "detail": str(exc)}
    if completed.returncode != 0:
        return {"portal": portal, "status": "broken", "detail": completed.stderr.strip()[-500:]}
    items = _items(_decode_json(completed.stdout))
    if not items:
        return {"portal": portal, "status": "inconclusive", "detail": "zero results"}
    return {"portal": portal, "status": "healthy", "detail": f"{len(items)} results"}
