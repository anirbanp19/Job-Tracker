# Job Tracker — PM/APM auto-scan

Scrapes LinkedIn, Indeed, and Naukri weekly for Product Manager and Associate Product Manager roles in Bengaluru / Kolkata / Hyderabad / Pune, scores each one against your resume using Groq + GPT-OSS 120B (open-weight reasoning model from OpenAI), and produces an Excel file with one-click apply hyperlinks.

## What you get

An Excel file with two sheets:

- **Strong Matches** — ATS Score ≥ 60. Apply to these.
- **Other Matches** — ATS Score < 60. Useful for spotting roles you'd qualify for with small resume tweaks.

Each row: Company, Role, Location, Experience required, Min Years Required, ATS Score, Fit Score, AI reasoning, Missing Keywords, Source(s) found on, Apply Link (hyperlink), City Priority, Date Posted, Date Found, Date Last Seen. 
Sorted by city priority (Bengaluru → Pune), then ATS score descending, then Fit score descending.

### The Scoring System
Each job gets two distinct scores to help you prioritize:
- **ATS Score (0-100):** Measures mechanical overlap (verbatim keyword matches, exact title matches). Will this resume pass an automated HR screen?
- **Fit Score (0-100):** AI recruiter's judgement of your actual capability to do the job based on domain alignment and functional overlap, even if the keywords differ.
- **Missing Keywords:** 5-10 actionable keywords from the JD that you can inject into your resume to bypass ATS filters, provided you actually have the experience.

## Caveats — read these first

1. **Scraping is technically against LinkedIn's, Indeed's, and Naukri's ToS.** This tool uses guest endpoints (no login) which is the safest path, but never link this to your real LinkedIn account.
2. **GitHub-hosted runner IPs sometimes get rate-limited or blocked** by LinkedIn / Naukri because they're shared. If runs come back empty, you have two options: re-run manually a few hours later, or run locally (instructions below).
3. **Naukri's HTML changes occasionally** — when it does, `scraper_naukri.py` will silently return zero jobs. The other two sources will still work. Fix is to update the CSS selectors in `_extract_listings` and `_parse_listing`.
4. **Groq free tier limits**: 30 RPM, ~6000 TPM. The script paces itself heavily (sleeping 22s between requests) so large lists of new jobs will take a while.
5. **`groq` SDK is used for API requests** directly to the Groq inference engine.

---

## Setup — local first (recommended for first run)

### 1. Clone and install

```bash
git clone <your-repo-url> job-tracker
cd job-tracker

python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Add your resume

Drop your PDF into `resume/resume.pdf`. Exact filename matters.

### 3. Get a free Groq API key

Go to <https://console.groq.com/keys>, sign in, click "Create API key". Copy it.

### 4. Set the env var and run

```bash
# Linux / macOS
export GROQ_API_KEY="your-key-here"
python main.py

# Windows PowerShell
$env:GROQ_API_KEY = "your-key-here"
python main.py
```

You'll see progress in the terminal. When it finishes, open `output/jobs_master.xlsx`.

---

## Cloud setup — GitHub Actions for daily runs

### 1. Create a private GitHub repo

Create a private repo and push this code to it. **Use private** — the resume will be in there.

### 2. Add the Groq API key as a secret

Repo → Settings → Secrets and variables → Actions → "New repository secret":
- Name: `GROQ_API_KEY`
- Value: your API key

### 3. (Optional) Keep resume out of the repo

If you'd rather not commit the PDF:

```bash
# Generate a base64 string of your PDF
base64 -w0 resume/resume.pdf > resume.b64    # Linux
base64 -i resume/resume.pdf -o resume.b64    # macOS
```

Add the contents of `resume.b64` as a secret named `RESUME_PDF_BASE64`. Then add `resume/resume.pdf` to `.gitignore` and remove it from the repo. The workflow will reconstruct it at runtime.

### 4. That's it

The workflow runs every day at 09:30 IST. You can also trigger it manually from the Actions tab → "Daily Job Scan" → "Run workflow".

The Excel lands as both a workflow artifact (downloadable from the Actions run page) and as a committed file in `output/jobs_master.xlsx`.

---

## Customizing filters

Open `config.py` and edit:

| Setting | What it does |
|---|---|
| `ROLE_KEYWORDS` | Search terms used on each portal |
| `EXCLUDE_TITLE_KEYWORDS` | Substrings that disqualify a title |
| `TARGET_LOCATIONS` | Cities to search |
| `CITY_PRIORITY` | Lower number ranks higher in the output sort |
| `MAX_YEARS_EXPERIENCE` | Drop listings whose minimum requirement exceeds this |
| `DAYS_OLD` | Recency window |
| `STRONG_MATCH_THRESHOLD` | ATS Score cutoff between sheet 1 and sheet 2 |
| `RESULTS_PER_QUERY` | How many jobs to pull per role+city combo |

---

## Troubleshooting

**"GROQ_API_KEY not set"** — env var missing. See setup step 4.

**"JobSpy returned 0 jobs"** on every query — your IP is being rate-limited. Wait a few hours and retry, or switch to running locally on your home network.

**"Naukri returned 0 jobs"** but JobSpy works fine — Naukri's selectors changed. Open the Naukri search URL in a browser, inspect a job card, and update the selectors in `scraper_naukri.py`.

**Groq errors with 429** — free-tier quota hit. The script pauses for 60s but if it fails repeatedly, wait and retry.

**Excel hyperlinks not clickable in the cell** — click once to select, then click again on "Apply" text. Excel sometimes requires the second click.

---

## Job history (for daily runs)

- Each scored job is cached in `output/scored_jobs.json` with its scores, reasoning, missing keywords, and the date it was found.
- Daily runs will scrape the last 3 days of postings, then skip over any job that is already saved in your history. This means only brand new jobs hit the API, saving rate limits and time.
- The output file `output/jobs_master.xlsx` overwrites itself on every run and contains the FULL history of all jobs ever scored, not just the jobs from today's run.
- **Updating your resume:** If you update your resume, delete the `output/scored_jobs.json` file. This forces the tracker to perform a full re-score of all jobs on the next run.
- **Manual vs. Automated runs:** If you plan to run the script manually on your Mac while the GitHub Action also runs daily in the cloud, be sure to run `git pull` before your local run to fetch the latest `scored_jobs.json` history. After your local run finishes, run `git push` so the cloud gets your newly cached jobs.

---

## Project layout

```
job-tracker/
├── .github/workflows/job-scan.yml   # daily cron on GitHub Actions
├── main.py                          # orchestrator
├── config.py                        # all tunables
├── resume_parser.py                 # PDF -> text
├── scraper_jobspy.py                # LinkedIn + Indeed
├── scraper_naukri.py                # Naukri (Playwright)
├── filters.py                       # title / location / experience
├── experience_parser.py             # regex parsers for minimum years
├── deduper.py                       # collapse cross-portal duplicates
├── matcher.py                       # Groq ATS/Fit scoring
├── job_history.py                   # manages dedupe cache across runs
├── excel_writer.py                  # two-sheet Excel output
├── resume/resume.pdf                # YOUR resume goes here
├── output/                          # generated xlsx + json cache land here
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Swap to a different LLM (optional)

If you'd prefer Groq with Llama 3.3 (also free tier, fully open-weights model):

1. Keep the `groq` installation
2. Replace the `GROQ_MODEL` setting in `config.py` with `"llama-3.3-70b-versatile"`
3. Remove `reasoning_effort` param from `matcher.py` (Llama 3.3 is not a reasoning model)

The prompt template is identical.
