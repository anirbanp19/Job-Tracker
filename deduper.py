"""Collapse duplicate listings across portals using normalized (company, title)."""
import re


def _normalize(s: str) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9 ]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def dedupe_jobs(jobs: list) -> list:
    grouped = {}
    for job in jobs:
        key = (_normalize(job.get("company", "")), _normalize(job.get("title", "")))
        if not key[0] or not key[1]:
            continue
        if key not in grouped:
            grouped[key] = {
                **job,
                "all_sources": [(job.get("source", ""), job.get("url", ""))],
            }
        else:
            existing = grouped[key]
            existing["all_sources"].append((job.get("source", ""), job.get("url", "")))
            # Keep longest description (more context for AI scoring)
            new_desc = job.get("description", "") or ""
            old_desc = existing.get("description", "") or ""
            if len(new_desc) > len(old_desc):
                existing["description"] = new_desc
            # Prefer non-empty experience field
            if not existing.get("experience") and job.get("experience"):
                existing["experience"] = job["experience"]
    return list(grouped.values())
