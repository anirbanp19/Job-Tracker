"""Parse minimum years of experience from free-text job content.
Used as a pre-filter before AI scoring to drop obvious mismatches and save API calls."""
import re


# Patterns ordered most-specific to least-specific. First match wins per source.
_PATTERNS = [
    # "5-8 years", "5 to 8 years", "5–8 yrs", "5 or 8 years"
    re.compile(r"(\d{1,2})\s*(?:[-–]|to|or)\s*(\d{1,2})\s*\+?\s*(?:year|yr)s?", re.IGNORECASE),
    # "minimum 5 years", "minimum of 5 years", "at least 5 years", "must have at least 5 years", "min. 5 years"
    re.compile(r"(?:minimum|at\s*least|min\.?|must\s+have(?:\s+at\s+least)?)\s*(?:of\s*)?(\d{1,2})\s*\+?\s*(?:year|yr)s?", re.IGNORECASE),
    # "5 or more years"
    re.compile(r"(\d{1,2})\s*\+?\s*or\s+more\s+(?:year|yr)s?", re.IGNORECASE),
    # "5+ years", "5 + years", "5+ yrs", "demonstrated 5+ years"
    re.compile(r"(\d{1,2})\s*\+\s*(?:year|yr)s?", re.IGNORECASE),
    # "5 years' experience" (with apostrophe), "5 years experience", "5 years of experience"
    re.compile(r"(\d{1,2})\s*(?:year|yr)s?[''']?\s*(?:of\s*)?experience", re.IGNORECASE),
    # "experience: 5 years", "exp: 5 yrs", "experience of 5 years", "experience required: 5 years"
    re.compile(r"(?:experience|exp)(?:\s+(?:required|of))?\s*[:\-]?\s*(\d{1,2})\s*\+?\s*(?:year|yr)s?", re.IGNORECASE),
    # "with 5 years", "having 5 years"
    re.compile(r"(?:with|having)\s+(\d{1,2})\s*\+?\s*(?:year|yr)s?\s+(?:of\s*)?(?:relevant\s*)?(?:experience|exp)", re.IGNORECASE),
]


def parse_min_years(text: str) -> int | None:
    """Return the minimum years required, or None if not found.
    For ranges like '5-8 years', returns the lower bound (5). For multiple matches in same text, returns the MAXIMUM (most strict requirement) since JDs often state higher floors later in the text."""
    if not text:
        return None

    candidates = []
    for pattern in _PATTERNS:
        for match in pattern.finditer(text):
            try:
                # Range patterns capture two groups; take the first (lower bound)
                value = int(match.group(1))
                if 0 <= value <= 30:  # sanity bounds
                    candidates.append(value)
            except (ValueError, IndexError):
                continue

    if not candidates:
        return None

    # Conservative: take the MAXIMUM stated requirement across all matches.
    # If JD says "3+ years" early and "must have 5+ years in B2B SaaS" later, we want to respect the stricter floor (5), not the lenient one (3). This is safer for the candidate.
    return max(candidates)


def extract_experience_from_job(job: dict) -> int | None:
    """Try structured field first (Naukri), then description text."""
    structured = job.get("experience") or ""
    parsed = parse_min_years(structured)
    if parsed is not None:
        return parsed
    return parse_min_years(job.get("description") or "")
