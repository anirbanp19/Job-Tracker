"""Persistent record of jobs already scored, so daily runs skip duplicates."""
import json
import os
from datetime import date


def _job_key(job: dict) -> str:
    """Stable identifier across runs: company + title, normalized."""
    company = (job.get("company") or "").strip().lower()
    title = (job.get("title") or "").strip().lower()
    return f"{company}::{title}"


def load_history(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_history(path: str, history: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(history, f, indent=2)


def split_new_vs_seen(jobs: list, history: dict) -> tuple:
    """Return (new_jobs_to_score, already_seen_jobs_with_cached_scores)."""
    new_jobs = []
    seen_jobs = []
    today = date.today().isoformat()

    for job in jobs:
        key = _job_key(job)
        if key in history:
            cached = history[key]
            seen_jobs.append({
                **job,
                "ats_score": cached.get("ats_score", 0),
                "fit_score": cached.get("fit_score", 0),
                "reasoning": cached.get("reasoning", ""),
                "missing_keywords": cached.get("missing_keywords", []),
                "fit_flags": cached.get("fit_flags", []),
                "date_found": cached.get("date_found", today),
                "date_last_seen": today,
            })
        else:
            new_jobs.append(job)
    return new_jobs, seen_jobs


def update_history(history: dict, scored_jobs: list) -> dict:
    """Add newly scored jobs to history. Update last_seen for all."""
    today = date.today().isoformat()
    for job in scored_jobs:
        key = _job_key(job)
        if key not in history:
            history[key] = {
                "company": job.get("company", ""),
                "title": job.get("title", ""),
                "ats_score": job.get("ats_score", 0),
                "fit_score": job.get("fit_score", 0),
                "reasoning": job.get("reasoning", ""),
                "missing_keywords": job.get("missing_keywords", []),
                "fit_flags": job.get("fit_flags", []),
                "date_found": job.get("date_found") or today,
            }
        history[key]["date_last_seen"] = today
    return history
