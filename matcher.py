"""Resume vs JD scoring using Google Gemini (free tier)."""
import os
import json
import time
from groq import Groq
from config import GROQ_MODEL


PROMPT_TEMPLATE = """You are an expert technical recruiter and ATS analyst. Your job is to evaluate a candidate's resume against a Product Manager job description and return two distinct scores plus a list of missing keywords.

CANDIDATE RESUME:
{resume}

JOB DETAILS:
Title: {title}
Company: {company}
Location: {location}
Minimum Years Required (extracted from JD text): {min_years_required}
Raw Experience Field: {experience}
Description:
{description}

CRITICAL HARD RULES — apply these BEFORE scoring:
1. The candidate has 4 years of experience.
2. If "Minimum Years Required" above is a number greater than 4, BOTH scores MUST be below 30.
3. If the title contains any of: Senior, Sr., Lead, Principal, Director, VP, Head of, Group Product Manager, GPM, Staff, or Chief — BOTH scores MUST be below 30.
4. If the description text contains "5+ years", "6+ years", "7+ years", "minimum 5 years", "at least 5 years", or any similar phrase requiring more than 4 years, BOTH scores MUST be below 30.

If hard rules pass, evaluate two independent dimensions:

═══════════════════════════════════════════════════════
DIMENSION 1 — ATS SCORE (0-100): Will this resume pass automated screening?
═══════════════════════════════════════════════════════

Score based on (weighted):
- Keyword match (50%): How many concrete skills, tools, technologies, methodologies, and qualifications from the JD appear verbatim or as close synonyms in the resume? Count specific terms like "Jira", "SQL", "Agile", "RAG", "B2B SaaS", "stakeholder management", "prompt engineering", "Power BI", etc. Higher overlap = higher score.
- Title/seniority alignment (30%): Does the candidate's most recent title (Associate Product Manager) align with the target title? Same level or one step up = full marks. Two steps up = partial. Senior+ = fail.
- Hard requirements (20%): Years of experience match, location match (Bengaluru/Kolkata/Hyderabad/Pune), education match (MBA helps for PM roles), and any explicit must-haves listed in the JD.

ATS systems are mechanical — they reward keyword density and exact title matches. Be strict. A resume with strong relevant content but missing 5+ JD-specific keywords should score 50-65, not 80+.

ATS Score Range Anchors (use these as calibration):
- 90-100: Resume contains 80%+ of JD's named tools, methodologies, and skills verbatim. Title matches exactly (APM → APM, PM → PM). All knockout criteria pass (years, location, degree).
- 75-89: Most key terms present with minor gaps. Title is one level adjacent (APM applying to PM). All knockouts pass.
- 60-74: Some relevant terms present but 3-5 critical JD keywords are missing. Title alignment is workable. Likely passes lenient ATS, fails strict ones.
- 45-59: Significant keyword gaps (5-10 missing). Title is two levels off OR domain mismatch makes keywords irrelevant. Borderline — most ATS systems will filter out.
- 30-44: Few JD keywords found, weak title/seniority match. ATS will almost certainly reject.
- Below 30: Hard rule violation (senior role, 5+ years required) OR near-zero keyword overlap.

IMPORTANT: A score of 70+ should mean "I genuinely expect this resume to pass automated screening." If you're not confident, score lower. Inflated scores waste the candidate's application effort.

═══════════════════════════════════════════════════════
DIMENSION 2 — JOB FIT SCORE (0-100): Is this candidate genuinely a good fit?
═══════════════════════════════════════════════════════

This is your judgment as a recruiter, beyond keywords. Score based on:
- Domain alignment: Candidate strengths are B2B/B2C SaaS, GenAI/RAG, travel tech, enterprise products, FMCG enterprise tools. How aligned is the JD's domain?
- Depth of relevant experience: Has the candidate done similar work, even if titles/keywords differ? E.g., "Tender Management for renewable energy" demonstrates enterprise workflow design even if "renewable energy" isn't in the JD.
- Trajectory fit: Is this a logical next role for someone moving from APM with GenAI experience?
- Skills overlap beyond keywords: Functional capabilities like "0-to-1 product development", "RAG architecture decisions", "cross-functional leadership across engineering/design/data".

Be honest. A role can have a high ATS score but low fit (great keyword match, wrong domain) or vice versa (right domain, missing keywords).

Fit Score Range Anchors (use these as calibration):
- 90-100: Strong domain match (B2B SaaS, GenAI, travel tech, enterprise products). Clear trajectory fit. Candidate has done substantially similar work before. Logical next role.
- 75-89: Relevant domain with minor adjacency. Most required capabilities are demonstrated in the resume. Plausible and exciting next role.
- 60-74: Tangential domain match. Transferable skills but candidate hasn't done this exact work. Plausible stretch.
- 45-59: Weak domain alignment. Would need significant pivot or re-skilling. Possible but not ideal.
- 30-44: Domain mismatch (e.g., pure hardware PM, deep-tech research, fintech with no SaaS overlap). Skills won't translate cleanly.
- Below 30: Hard rule violation OR completely incompatible domain (e.g., medical device PM requiring clinical background).

═══════════════════════════════════════════════════════
MISSING KEYWORDS
═══════════════════════════════════════════════════════

List 5-10 specific, actionable keywords or phrases from the JD that are NOT present in the resume but COULD be added if the candidate has actually done that work. Prioritize:
- Specific tools/technologies named in the JD (e.g., "Mixpanel", "A/B testing", "Snowflake")
- Methodologies and frameworks (e.g., "OKRs", "Jobs-to-be-Done", "RICE prioritization")
- Domain terms (e.g., "marketplace dynamics", "two-sided platforms", "PLG")
- Specific outcomes mentioned (e.g., "NPS improvement", "MAU growth", "reducing TAT")

Do NOT list generic words ("teamwork", "communication"), keywords already present in the resume, or words the candidate clearly hasn't done (don't suggest "managed Series-B fundraising" if no investor experience exists).

PRIORITIZE the missing_keywords list. Put the keywords most likely to trigger ATS rejection FIRST. Tools and methodologies named multiple times in the JD are highest priority. Domain-specific jargon is medium priority. Generic best-practices terms are lowest priority. The candidate should be able to act on the first 3-5 items in the list and meaningfully improve ATS pass rate.

Return ONLY valid JSON in this EXACT format:
{{
  "ats_score": <integer 0-100>,
  "fit_score": <integer 0-100>,
  "reasoning": "<one or two sentences explaining the scores, including the years requirement if it triggered a hard rule, and the most important keyword gap>",
  "missing_keywords": ["<keyword1>", "<keyword2>", "<keyword3>"],
  "fit_flags": ["<flag1>", "<flag2>"]
}}

Valid fit_flags: experience_overshoot, senior_role, domain_match, skills_match, domain_mismatch, skills_gap, strong_genai_fit, strong_saas_fit, ats_keyword_rich, ats_keyword_poor
"""


def _build_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    return Groq(api_key=api_key)


def score_job(client, resume_text: str, job: dict) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        resume=resume_text,
        title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        experience=job.get("experience", "") or "Not specified",
        min_years_required=job.get("min_years_required") if job.get("min_years_required") is not None else "Not stated in JD",
        description=(job.get("description") or "")[:2500],  # cap input tokens
    )

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                reasoning_effort="low",
            )
            result = json.loads(response.choices[0].message.content)
            return {
                "ats_score": int(result.get("ats_score", 0)),
                "fit_score": int(result.get("fit_score", 0)),
                "reasoning": result.get("reasoning", ""),
                "missing_keywords": result.get("missing_keywords", []),
                "fit_flags": result.get("fit_flags", []),
            }
        except Exception as e:
            print(f"    scoring attempt {attempt + 1} failed: {e}")
            if "429" in str(e).lower() or "rate_limit" in str(e).lower():
                time.sleep(60)
            else:
                time.sleep(2 ** attempt)

    return {"ats_score": 0, "fit_score": 0, "reasoning": "scoring failed after 3 attempts", "missing_keywords": [], "fit_flags": []}


def score_all(resume_text: str, jobs: list) -> list:
    client = _build_client()
    scored = []
    total = len(jobs)
    for i, job in enumerate(jobs, start=1):
        title_preview = (job.get("title") or "")[:60]
        print(f"  [{i}/{total}] {title_preview}")
        result = score_job(client, resume_text, job)
        scored.append({**job, **result})
        # Groq free tier: ~6000 TPM means ~3 requests/min max for prompts of our size
        time.sleep(22)
    return scored
