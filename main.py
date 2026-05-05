"""End-to-end orchestrator: scrape -> filter -> dedupe -> score -> Excel."""
import config
from resume_parser import extract_resume_text
from scraper_jobspy import scrape_jobspy_all
from scraper_naukri import scrape_naukri_all
from filters import filter_by_location, filter_by_title, filter_by_experience
from engineering_filter import filter_engineering_roles
from deduper import dedupe_jobs
from matcher import score_all
from excel_writer import write_excel, compute_combined_score
from datetime import date
from job_history import load_history, save_history, split_new_vs_seen, update_history


def main():
    print("=" * 64)
    print("Job Tracker — starting run")
    print("=" * 64)

    # 1) Resume
    print(f"\n[1/6] Reading resume: {config.RESUME_PATH}")
    resume_text = extract_resume_text(config.RESUME_PATH)
    print(f"      Loaded {len(resume_text)} chars")

    # 2) Scrape
    print("\n[2/6] Scraping LinkedIn + Indeed (JobSpy)…")
    jobspy_jobs = scrape_jobspy_all(
        config.ROLE_KEYWORDS,
        config.TARGET_LOCATIONS,
        config.DAYS_OLD,
        config.RESULTS_PER_QUERY,
    )
    print(f"      JobSpy returned {len(jobspy_jobs)} jobs")

    print("\n[3/6] Scraping Naukri (Playwright)…")
    naukri_jobs = scrape_naukri_all(
        config.ROLE_KEYWORDS,
        config.TARGET_LOCATIONS,
        config.DAYS_OLD,
        config.NAUKRI_MAX_PAGES,
    )
    print(f"      Naukri returned {len(naukri_jobs)} jobs")

    all_jobs = jobspy_jobs + naukri_jobs
    print(f"      Total raw: {len(all_jobs)}")

    # 3) Filter
    print("\n[4/6] Filtering…")
    all_jobs = filter_by_title(all_jobs)
    print(f"      After title filter:      {len(all_jobs)}")
    all_jobs = filter_by_location(all_jobs)
    print(f"      After location filter:   {len(all_jobs)}")
    exp_before = len(all_jobs)
    all_jobs = filter_by_experience(all_jobs)
    print(f"      After experience filter: {len(all_jobs)}")
    print(f"      Dropped by exp filter:   {exp_before - len(all_jobs)}")

    all_jobs, dropped_eng = filter_engineering_roles(all_jobs)
    print(f"      After engineering filter: {len(all_jobs)} (dropped {dropped_eng} CS/coding-only roles)")

    # 4) Dedupe
    all_jobs = dedupe_jobs(all_jobs)
    print(f"      After dedup:             {len(all_jobs)}")

    # 4.5) Skip jobs already scored in previous runs
    print("      NOTE: If you want to re-score with the new prompt, delete output/scored_jobs.json")
    history = load_history(config.HISTORY_FILE)
    new_jobs, seen_jobs = split_new_vs_seen(all_jobs, history)
    print(f"      Already scored (skipping): {len(seen_jobs)}")
    print(f"      New jobs to score:         {len(new_jobs)}")

    if not new_jobs and not seen_jobs:
        print("\nNo jobs survived filtering. Nothing to score. Exiting.")
        return

    # 5) Score
    print(f"\n[5/6] Scoring {len(new_jobs)} jobs with Groq…")
    scored_new = score_all(resume_text, new_jobs)

    today = date.today().isoformat()
    for job in scored_new:
        job["date_found"] = today
        job["date_last_seen"] = today

    scored = scored_new + seen_jobs
    history = update_history(history, scored)
    save_history(config.HISTORY_FILE, history)

    # 6) Excel
    print("\n[6/6] Writing Excel…")
    out_path = write_excel(scored, config.STRONG_MATCH_THRESHOLD, config.OUTPUT_DIR)

    strong = sum(1 for j in scored if compute_combined_score(j.get("ats_score", 0), j.get("fit_score", 0)) >= config.STRONG_MATCH_THRESHOLD)
    other = len(scored) - strong
    print("\n" + "=" * 64)
    print(f"✓ Done. Output in master file: {out_path}")
    print(f"  Strong matches (Combined ≥ {config.STRONG_MATCH_THRESHOLD}): {strong}")
    print(f"  Other matches (Combined < {config.STRONG_MATCH_THRESHOLD}): {other}")
    print("=" * 64)


if __name__ == "__main__":
    main()
