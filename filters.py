"""Pre-AI filters: location whitelist, title blacklist, experience cap."""
from config import EXCLUDE_TITLE_KEYWORDS, CITY_PRIORITY, MAX_YEARS_EXPERIENCE
from experience_parser import extract_experience_from_job


def get_city_priority(location: str) -> int | None:
    if not location:
        return None
    lower = location.lower()
    for key, priority in CITY_PRIORITY.items():
        if key in lower:
            return priority
    return None


def filter_by_location(jobs: list) -> list:
    """Keep only jobs in target cities. Stamp city_priority on each."""
    out = []
    for job in jobs:
        priority = get_city_priority(job.get("location", ""))
        if priority is not None:
            out.append({**job, "city_priority": priority})
    return out


def filter_by_title(jobs: list) -> list:
    """Drop senior/lead/etc. titles. Keep only PM / APM / Product Owner roles."""
    out = []
    for job in jobs:
        title = (job.get("title") or "").lower()
        if not title:
            continue
        if any(bad in title for bad in EXCLUDE_TITLE_KEYWORDS):
            continue
        if "product manager" not in title and "product owner" not in title:
            continue
        out.append(job)
    return out


def filter_by_experience(jobs: list, max_years: int = MAX_YEARS_EXPERIENCE) -> list:
    """Drop jobs whose minimum experience requirement clearly exceeds max_years.
    Stamps `min_years_required` on every job (None if unparseable).
    Jobs with no parseable experience are KEPT (let the AI decide)."""
    out = []
    for job in jobs:
        min_years = extract_experience_from_job(job)
        job_with_exp = {**job, "min_years_required": min_years}
        if min_years is None:
            out.append(job_with_exp)  # keep ambiguous jobs
        elif min_years <= max_years:
            out.append(job_with_exp)  # within range
        # else: drop silently (clearly over the limit)
    return out
