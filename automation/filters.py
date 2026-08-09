"""Candidate-specific eligibility gates shared by scheduled runs and tests."""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


# These values are deliberately labels rather than an allow-list.  A remote role
# can be useful even when its regional restriction is not one of the candidate's
# preferred markets, but the restriction must be explicit in the notification.
_REGIONAL_RESTRICTIONS: tuple[tuple[str, str], ...] = (
    ("United States", r"(?<![a-z])(?:united states|u\.s\.a?\.?|usa)(?![a-z])"),
    ("United Kingdom", r"(?<![a-z])(?:united kingdom|u\.k\.?|uk|england|scotland|wales|northern ireland)(?![a-z])"),
    ("European Union", r"\b(?:european union|eu)\b"),
    ("EMEA", r"\bemea\b"),
    ("Europe", r"\beurope\b"),
    ("Asia-Pacific", r"\b(?:asia[- ]?pacific|apac)\b"),
    ("ASEAN", r"\basean\b"),
    ("North America", r"\bnorth america\b"),
    ("Latin America", r"\b(?:latin america|latam)\b"),
    ("Canada", r"\bcanada\b"),
    ("Germany", r"\bgermany\b"),
    ("Netherlands", r"\b(?:the )?netherlands\b"),
    ("Japan", r"\bjapan\b"),
    ("Indonesia", r"\bindonesia\b"),
    ("Malaysia", r"\bmalaysia\b"),
    ("Singapore", r"\bsingapore\b"),
    ("Australia", r"\baustralia\b"),
    ("New Zealand", r"\bnew zealand\b"),
    ("India", r"\bindia\b"),
)

_REMOTE_SIGNAL = re.compile(
    r"\b(?:remote|distributed|work from anywhere|work-from-anywhere|anywhere in the world|location independent|global remote|worldwide)\b"
)
_TIMEZONE_SIGNAL = re.compile(
    # A bare time-zone mention can describe a company's customers or offices,
    # so require an eligibility/working-hours cue.  Both word orders occur in
    # real postings: "overlap AEST hours" and "UTC+1 working hours".
    r"(?:\b(?:must|need|requires?|required|expected|eligible|candidate|applicant|you|overlap|within)\b[^.\n;]{0,100}?\b(?:utc|gmt|est|edt|cst|cdt|mst|mdt|pst|pdt|cet|cest|eet|eest|aest|aedt|nzst|nzdt)(?:\s*[+-]?\s*\d{1,2})?\b|\b(?:utc|gmt|est|edt|cst|cdt|mst|mdt|pst|pdt|cet|cest|eet|eest|aest|aedt|nzst|nzdt)(?:\s*[+-]?\s*\d{1,2})?\b[^.\n;]{0,100}?\b(?:time\s*zone|timezone|overlap|working\s+hours?|business\s+hours?)\b)",
    re.IGNORECASE,
)


def _job_text(job: dict[str, Any]) -> str:
    """Combine fields that may legally state a work-location restriction."""
    return " ".join(
        str(job.get(field, ""))
        for field in ("job_location", "location", "work_mode", "description", "title", "employment_type")
    )


def _is_full_remote(job: dict[str, Any]) -> bool:
    mode = normalize(job.get("work_mode"))
    text = normalize(_job_text(job))
    # Hybrid and on-site are never promoted to a full-remote classification even
    # when a stale/over-broad source field says "remote" or their description
    # happens to discuss a remote-work policy.
    if re.search(r"\b(?:hybrid|on[- ]site|in[- ]office)\b", text):
        return False
    if mode in {"remote", "fully remote", "full remote", "100% remote", "true", "yes"}:
        return True
    return bool(_REMOTE_SIGNAL.search(text))


def _restriction_labels(text: str, location: str = "") -> list[str]:
    """Extract disclosed candidate-location limits without mistaking company facts.

    Boards often put a headquarters country or a customer market in the body.
    A bare country reference there is not a work-location restriction, while a
    source's structured location field normally is.  Description evidence is
    therefore accepted only when it appears with an eligibility/location cue.
    """
    labels = [label for label, pattern in _REGIONAL_RESTRICTIONS if re.search(pattern, location, re.IGNORECASE)]
    # Do not use bare "based" or "located" as candidate evidence.  "We are
    # based in Australia" is a company fact, not a work-authorisation limit.
    # Structured board locations above remain authoritative, while prose must
    # connect a country to an applicant-facing eligibility cue.
    location_cue = r"(?:must|only|eligible|eligibility|resid(?:e|ency)|residents?|location|within|authorized|authori[sz]ation|citizen|candidate|applicant|anywhere|work\s+from|hiring\s+in)"
    for label, pattern in _REGIONAL_RESTRICTIONS:
        if label in labels:
            continue
        if re.search(rf"{location_cue}.{{0,100}}{pattern}|{pattern}.{{0,100}}{location_cue}", text, re.IGNORECASE):
            labels.append(label)
    # ``US`` is too common a normal word to search freely in prose.  It is safe
    # in a location field, or when followed by an eligibility qualifier.
    if "United States" not in labels and (
        re.search(r"\b(?:us|u\.s\.?)\b", location, re.IGNORECASE)
        or re.search(r"\b(?:us|u\.s\.?)\s+(?:only|based|residents?|citizens?|candidates?|work authorization)\b", text, re.IGNORECASE)
    ):
        labels.append("United States")
    return labels


def remote_work_taxonomy(job: dict[str, Any]) -> dict[str, str]:
    """Classify full-remote work and expose any geographic restriction.

    ``Worldwide / Unconstrained`` means the source did not state a geographic
    restriction.  It is intentionally not a claim about tax, payroll, or visa
    eligibility, which must still be verified from the full posting.
    """
    if not _is_full_remote(job):
        return {"remote_classification": "", "restriction_details": ""}

    text = normalize(_job_text(job))
    location = " ".join(str(job.get(field, "")) for field in ("job_location", "location"))
    labels = _restriction_labels(text, location)
    timezone = _TIMEZONE_SIGNAL.search(_job_text(job))
    details: list[str] = labels[:3]
    if timezone:
        value = re.sub(r"\s+", " ", timezone.group(0)).strip(" .;:")
        details.append(value[:120])
    if details:
        return {
            "remote_classification": "Full Remote (Regional Constraint)",
            "restriction_details": "; ".join(details),
        }

    # No source-disclosed geographic or time-zone restriction was found.  This
    # remains a disclosure classification, not a guarantee of legal eligibility.
    return {
        "remote_classification": "Full Remote (Worldwide / Unconstrained)",
        "restriction_details": "",
    }


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
        return "PASS", "Indonesia-based roles are accepted in any work model."

    if _is_full_remote(job):
        return "PASS", "Remote work is stated."
    text = normalize(_job_text(job))
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
    taxonomy = remote_work_taxonomy(job)
    return {
        "location": location,
        "location_note": location_note,
        "language_gate": language,
        "language_note": language_note,
        "role_gate": role,
        "role_note": role_note,
        **taxonomy,
        "eligible": "yes" if location == "PASS" and language != "FAIL" and role == "PASS" else "no",
    }
