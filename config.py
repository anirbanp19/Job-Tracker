"""All tunable settings live here. Edit and re-run."""

# Roles to search (used as keywords across all portals)
ROLE_KEYWORDS = ["Product Manager", "Associate Product Manager"]

# Title-level exclusions (case-insensitive substring match on job title)
EXCLUDE_TITLE_KEYWORDS = [
    "senior", "sr.", "sr ", "lead", "principal", "director", "vp ",
    "head of", "group product manager", "gpm", "chief", "staff",
]

# Cities to search and rank by (priority 1 = highest)
# Bengaluru and Bangalore both map to priority 1.
TARGET_LOCATIONS = ["Bengaluru", "Kolkata", "Hyderabad", "Pune"]

CITY_PRIORITY = {
    "bengaluru": 1,
    "bangalore": 1,
    "kolkata": 2,
    "calcutta": 2,
    "hyderabad": 3,
    "hyd": 3,
    "pune": 4,
}

# Experience: keep jobs whose minimum requirement is <= this value (years)
MAX_YEARS_EXPERIENCE = 4

# Recency window
DAYS_OLD = 3

# Score >= this lands in "Strong Matches" sheet, < this goes to "Other Matches"
STRONG_MATCH_THRESHOLD = 60

# JobSpy / Naukri scrape volume per role+location
RESULTS_PER_QUERY = 50
NAUKRI_MAX_PAGES = 5

# Paths
RESUME_PATH = "resume/resume.pdf"
OUTPUT_DIR = "output"

# Groq model for matching (free tier: 30 RPM, ~6000 TPM, 1000 RPD; reasoning model)
GROQ_MODEL = "openai/gpt-oss-120b"

HISTORY_FILE = "output/scored_jobs.json"
