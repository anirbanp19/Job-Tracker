"""LinkedIn + Indeed scraping via JobSpy's guest endpoints (no login)."""
from jobspy import scrape_jobs
import pandas as pd
import time


def _scrape_one(role: str, location: str, hours_old: int, results_wanted: int) -> pd.DataFrame:
    try:
        return scrape_jobs(
            site_name=["linkedin", "indeed"],
            search_term=role,
            location=location,
            hours_old=hours_old,
            results_wanted=results_wanted,
            country_indeed="India",
            linkedin_fetch_description=True,
        )
    except Exception as e:
        print(f"  [JobSpy] failed for '{role}' in '{location}': {e}")
        return pd.DataFrame()


def scrape_jobspy_all(roles: list, locations: list, days_old: int, results_per_query: int = 50) -> list:
    """Returns a normalized list of dicts."""
    hours = days_old * 24
    frames = []
    for role in roles:
        for location in locations:
            print(f"  [JobSpy] {role} | {location}")
            df = _scrape_one(role, location, hours, results_per_query)
            if not df.empty:
                frames.append(df)
            time.sleep(2)  # be polite, avoid rate limits

    if not frames:
        return []

    combined = pd.concat(frames, ignore_index=True)
    return _to_records(combined)


def _to_records(df: pd.DataFrame) -> list:
    records = []
    for _, row in df.iterrows():
        records.append({
            "title": str(row.get("title", "") or ""),
            "company": str(row.get("company", "") or ""),
            "location": str(row.get("location", "") or ""),
            "experience": "",  # JobSpy doesn't expose a structured experience field
            "description": str(row.get("description", "") or ""),
            "url": str(row.get("job_url", "") or ""),
            "source": str(row.get("site", "") or ""),
            "date_posted": str(row.get("date_posted", "") or ""),
        })
    return records
