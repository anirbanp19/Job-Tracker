"""Naukri scraping via Playwright. Best-effort: Naukri DOM changes occasionally
and selectors may need updates. Wrapped in try/except so failures don't kill the run."""
from playwright.sync_api import sync_playwright
import time


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _build_url(role: str, location: str, days_old: int) -> str:
    role_slug = role.lower().replace(" ", "-")
    loc_slug = location.lower().replace(" ", "-")
    return (
        f"https://www.naukri.com/{role_slug}-jobs-in-{loc_slug}"
        f"?jobAge={days_old}&experience=4"
    )


def _extract_listings(page) -> list:
    """Try multiple selectors since Naukri's DOM mutates."""
    listings = page.query_selector_all("div.srp-jobtuple-wrapper")
    if not listings:
        listings = page.query_selector_all("article.jobTuple")
    if not listings:
        listings = page.query_selector_all("div.jobTuple")
    return listings


def _safe_text(node, selector: str) -> str:
    try:
        el = node.query_selector(selector)
        return el.inner_text().strip() if el else ""
    except Exception:
        return ""


def _safe_attr(node, selector: str, attr: str) -> str:
    try:
        el = node.query_selector(selector)
        return (el.get_attribute(attr) or "").strip() if el else ""
    except Exception:
        return ""


def _parse_listing(node) -> dict | None:
    title = _safe_text(node, "a.title")
    if not title:
        return None
    return {
        "title": title,
        "company": _safe_text(node, "a.comp-name") or _safe_text(node, "span.comp-name"),
        "location": _safe_text(node, "span.locWdth") or _safe_text(node, "li.location"),
        "experience": _safe_text(node, "span.expwdth") or _safe_text(node, "li.experience"),
        "description": _safe_text(node, "span.job-desc") or _safe_text(node, "div.job-description"),
        "url": _safe_attr(node, "a.title", "href"),
        "source": "naukri",
        "date_posted": _safe_text(node, "span.job-post-day"),
    }


def scrape_naukri(role: str, location: str, days_old: int, max_pages: int = 5) -> list:
    jobs = []
    base_url = _build_url(role, location, days_old)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1280, "height": 900})
            page = context.new_page()

            for page_num in range(1, max_pages + 1):
                url = base_url if page_num == 1 else f"{base_url}&pageNo={page_num}"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    time.sleep(3)
                except Exception as e:
                    print(f"  [Naukri] page {page_num} navigation failed: {e}")
                    break

                listings = _extract_listings(page)
                if not listings:
                    if page_num == 1:
                        print(f"  [Naukri] no listings found for '{role}' in '{location}' (selector miss or blocked)")
                    break

                for node in listings:
                    parsed = _parse_listing(node)
                    if parsed:
                        jobs.append(parsed)

            browser.close()
        except Exception as e:
            print(f"  [Naukri] fatal error for '{role}' in '{location}': {e}")

    return jobs


def scrape_naukri_all(roles: list, locations: list, days_old: int, max_pages: int = 5) -> list:
    out = []
    for role in roles:
        for loc in locations:
            print(f"  [Naukri] {role} | {loc}")
            out.extend(scrape_naukri(role, loc, days_old, max_pages))
    return out
