"""Candidate-specific eligibility gates shared by scheduled runs and tests."""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", " ", text).strip().lower()


def canonical_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    kept = [(key, item) for key, item in parse_qsl(parsed.query, keep_blank_values=True) if not key.lower().startswith(("utm_", "trk", "ref", "source"))]
    return normalize(urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), urlencode(kept), "")))


def job_key(job: dict[str, Any]) -> str:
    company = normalize(job.get("company"))
    title = normalize(job.get("title"))
    location = normalize(job.get("job_location") or job.get("location"))
    if company and title:
        return f"{company}::{title}::{location}"
    external_id = normalize(job.get("external_id"))
    source = normalize(job.get("source") or job.get("portal"))
    if source and external_id:
        return f"{source}::{external_id}"
    return canonical_url(job.get("apply_url") or job.get("url"))


def is_india_job(job: dict[str, Any]) -> bool:
    text = normalize(
        " ".join(
            str(job.get(field, ""))
            for field in ("company", "job_location", "location", "description", "url")
        )
    )
    return bool(re.search(r"\b(india|indian|gurugram|gurgaon|bengaluru|bangalore|mumbai|delhi|hyderabad|pune|chennai|noida)\b", text))


def is_indonesia_job(job: dict[str, Any]) -> bool:
    text = normalize(" ".join(str(job.get(field, "")) for field in ("job_location", "location", "url")))
    return bool(re.search(r"\b(indonesia|jakarta|bandung|surabaya|yogyakarta|bali|bekasi|tangerang)\b", text))


def is_target_role(job: dict[str, Any]) -> bool:
    title = normalize(job.get("title"))
    patterns = (
        r"\b(?:senior|sr\.?)(?:\s+(?:software|backend|platform|systems?|infrastructure|application))?\s+engineer\b",
        r"\bsoftware engineering manager\b",
        r"\bengineering manager\b",
        r"\bprincipal(?:\s+(?:software|backend|platform|systems?|infrastructure))?\s+engineer\b",
        r"\b(?:technical|tech|team) lead\b",
    )
    return any(re.search(pattern, title) for pattern in patterns) and "full stack" not in title and "fullstack" not in title


def location_gate(job: dict[str, Any]) -> tuple[str, str]:
    if is_india_job(job):
        return "FAIL", "India-based role, employer, or work location is excluded by the candidate profile."
    if is_indonesia_job(job):
        return "FAIL", "Indonesia-based roles are excluded from the daily international-remote search."

    text = normalize(" ".join(str(job.get(field, "")) for field in ("job_location", "location", "work_mode", "description")))
    if re.search(r"\b(remote|distributed|work from anywhere|anywhere in the world|global remote)\b", text):
        return "PASS", "Remote work is stated."
    if re.search(r"\b(relocation|relocate)\b", text) and re.search(r"\b(sponsor|sponsored|support|package|assistance)\b", text):
        return "PASS", "Employer-supported relocation is stated."
    return "FAIL", "Outside-Indonesia role lacks explicit remote work or supported relocation."


KNOWN_UNDECLARED_LANGUAGES = {
    "german", "japanese", "korean", "mandarin", "chinese", "dutch", "french",
    "spanish", "portuguese", "italian", "danish", "swedish", "norwegian", "arabic",
}


def language_gate(job: dict[str, Any]) -> tuple[str, str]:
    text = normalize(job.get("description"))
    for language in sorted(KNOWN_UNDECLARED_LANGUAGES):
        if re.search(rf"\b{re.escape(language)}\b", text) and re.search(
            rf"\b(required|must|fluent|native|professional|speaker|language)\b.{{0,80}}\b{re.escape(language)}\b|\b{re.escape(language)}\b.{{0,80}}\b(required|must|fluent|native|professional|speaker)\b",
            text,
        ):
            return "FAIL", f"The posting appears to require {language}, which is not declared in the candidate profile."
    if re.search(r"\b(native|fluent|near-native)\s+english\b", text):
        return "FLAG", "The posting asks for a higher English level than the declared professional working proficiency."
    return "PASS", "No undeclared required language detected."


def eligibility(job: dict[str, Any]) -> dict[str, str]:
    location, location_note = location_gate(job)
    language, language_note = language_gate(job)
    role = "PASS" if is_target_role(job) else "FAIL"
    role_note = "Matches the configured senior or leadership role target." if role == "PASS" else "Title is outside the configured senior or leadership role target."
    return {
        "location": location,
        "location_note": location_note,
        "language_gate": language,
        "language_note": language_note,
        "role_gate": role,
        "role_note": role_note,
        "eligible": "yes" if location == "PASS" and language != "FAIL" and role == "PASS" else "no",
    }
