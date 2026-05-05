"""Drop jobs that explicitly require a CS/Engineering degree as a hard requirement,
or require hands-on coding ability. The candidate has Commerce + MBA background,
no engineering education or coding skills.

IMPORTANT: This filter is LENIENT on permissive language. JDs that say things like
'Engineering or related degree', 'BE/BTech or equivalent', 'CS preferred',
'engineering background ideally' are KEPT — those roles are open to non-engineering
candidates. Only strict hard requirements trigger the filter."""
import re


# Permissive markers — if any of these words appear within 50 characters AROUND
# a degree/coding mention, the requirement is treated as flexible and NOT filtered.
PERMISSIVE_MARKERS = re.compile(
    r"\b(?:or\s+related|or\s+equivalent|or\s+relevant|or\s+similar|"
    r"preferred|ideally|nice\s+to\s+have|good\s+to\s+have|plus|bonus|"
    r"a\s+plus|advantage|desirable|optional|not\s+mandatory|"
    r"any\s+(?:relevant\s+)?(?:degree|field|background)|"
    r"any\s+discipline|any\s+stream)\b",
    re.IGNORECASE,
)

# Phrases that look like CS/Engineering degree requirements.
DEGREE_PATTERNS = [
    re.compile(r"\b(?:b\.?\s*e\.?|b\.?\s*tech|m\.?\s*tech|b\.?\s*s\.?\s*c|m\.?\s*s)\b\s*(?:degree)?\s*(?:in\s+)?(?:computer\s*science|cs|c\.s\.|software\s*engineering|information\s*technology|it\b|engineering)", re.IGNORECASE),
    re.compile(r"\b(?:bachelor['']?s?|master['']?s?)\s*(?:degree)?\s*(?:in\s+)?(?:computer\s*science|cs\b|software\s*engineering|engineering)", re.IGNORECASE),
    re.compile(r"\b(?:degree|qualification|background|graduate)\s+in\s+(?:computer\s*science|cs\b|software\s*engineering|engineering|information\s*technology)", re.IGNORECASE),
    re.compile(r"\b(?:engineering|cs|computer\s*science)\s+(?:degree|background|graduate|graduates)\s+(?:required|mandatory|must|essential|necessary)", re.IGNORECASE),
]

# Phrases that indicate hands-on coding ability is required for the role itself.
CODING_PATTERNS = [
    re.compile(r"\b(?:hands[\s-]*on|proficient|proficiency|expert(?:ise)?|strong)\s+(?:in|with)\s+(?:coding|programming|java|python|node\.?js|c\+\+|golang|rust|ruby|scala|kotlin)", re.IGNORECASE),
    re.compile(r"\b(?:must|should|required\s+to)\s+(?:be\s+able\s+to\s+)?(?:code|program|write\s+code|develop\s+(?:in|using))\b", re.IGNORECASE),
    re.compile(r"\b(?:write|writing|develop(?:ing)?|build(?:ing)?)\s+(?:production|backend|frontend|api|microservice)s?\s+(?:code|services?|systems?)", re.IGNORECASE),
    re.compile(r"\bsoftware\s+(?:engineer(?:ing)?|developer)\s+(?:role|position|background|experience)\s+(?:required|mandatory|essential)", re.IGNORECASE),
]


def _is_permissive_context(text: str, match_start: int, match_end: int, window: int = 50) -> bool:
    """Check if permissive language appears within `window` chars before/after the match."""
    start = max(0, match_start - window)
    end = min(len(text), match_end + window)
    surrounding = text[start:end]
    return bool(PERMISSIVE_MARKERS.search(surrounding))


def requires_engineering_background(job: dict) -> tuple:
    """Returns (is_disqualified, reason). reason is empty string if not disqualified."""
    text = " ".join([
        job.get("title", "") or "",
        job.get("description", "") or "",
    ])
    if not text.strip():
        return False, ""

    for pattern in DEGREE_PATTERNS:
        for match in pattern.finditer(text):
            if _is_permissive_context(text, match.start(), match.end()):
                continue  # skip — JD allows flexibility
            return True, f"hard CS/Eng degree requirement: '{match.group(0)[:80]}'"

    for pattern in CODING_PATTERNS:
        for match in pattern.finditer(text):
            if _is_permissive_context(text, match.start(), match.end()):
                continue  # skip — coding is just preferred, not required
            return True, f"hands-on coding required: '{match.group(0)[:80]}'"

    return False, ""


def filter_engineering_roles(jobs: list) -> tuple:
    """Returns (kept_jobs, dropped_count). Dropped jobs are silently removed."""
    kept = []
    dropped = 0
    for job in jobs:
        is_disqualified, _reason = requires_engineering_background(job)
        if is_disqualified:
            dropped += 1
        else:
            kept.append(job)
    return kept, dropped
