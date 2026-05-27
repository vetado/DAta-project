"""API collection: Wikipedia summaries of notable powerlifters.

This notebook supplements the OpenPowerlifting bulk-CSV cohort with biographical
context from Wikipedia. We use TWO Wikipedia APIs together:

  1. MediaWiki Action API  (w/api.php) - paginated category listings
  2. Wikipedia REST API    (api/rest_v1/...) - per-page summary JSON

Workflow:
  a. Walk several "powerlifter" categories on Wikipedia, paginating via
     `cmcontinue` tokens until exhausted or until we hit a cap.
  b. Deduplicate the resulting list of page titles.
  c. For each title, fetch the REST API summary (description, extract,
     birth year if surfaced, thumbnail, etc.).
  d. Save raw JSON dumps in data/raw/ and a parsed DataFrame in
     data/processed/.

Why Wikipedia and not OPL?
  OpenPowerlifting's official documentation explicitly says "no need to
  scrape our websites: you can download everything here" - i.e. the
  bulk CSV we already use is the canonical source. Their /api/ path is
  also disallowed by robots.txt for automated crawlers. So we use
  Wikipedia, which welcomes programmatic access and provides
  biographical context the OPL CSV does not.

This data does NOT feed H1 or H2 - it is cohort-context enrichment used
to characterise the "notable lifter" subpopulation in the limitations
discussion.

Run from anywhere:
    python notebooks/01_api_collection.py

To capture the audit trail:
    python notebooks/01_api_collection.py > reports/api_output.txt
"""

import json
import sys
import time
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import requests


# ----- constants -----
ACTION_API = "https://en.wikipedia.org/w/api.php"
REST_API   = "https://en.wikipedia.org/api/rest_v1/page/summary"

# Categories to walk. We pick a handful so the sample isn't dominated by
# any single country/sex bucket. If you want more, add more category names.
CATEGORIES = [
    "American powerlifters",
    "British powerlifters",
    "Russian powerlifters",
    "Female powerlifters",
    "Ukrainian powerlifters",
]

LIFTER_CAP = 200       # hard cap on summaries fetched (rubric ≥200)
POLITE_DELAY = 0.5     # seconds between REST API requests (Wikipedia is generous, but be polite)
HEADERS = {
    # Wikipedia's API policy requires a descriptive User-Agent that identifies
    # the project and a contact email. Don't ship the default requests UA.
    "User-Agent": (
        "WhenDoPowerliftersPeak/1.0 "
        "(university data-projects course; contact: dmolon@albertschool.com)"
    ),
}


def section(n: int, title: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}\n  Block {n}: {title}\n{bar}")


# %% ===== 1. Imports & paths ==========================================
# requests for HTTP, pandas for the final DataFrame, pathlib for paths.
# Wikipedia APIs are public and unauthenticated, so no .env / API-key
# handling is needed here. If we were hitting a paid API we'd load the
# key from .env using python-dotenv - left out because Wikipedia doesn't
# need it.

section(1, "Imports & paths")
print(f"requests: {requests.__version__}")
print(f"pandas:   {pd.__version__}")
RAW_DIR  = PROJECT_ROOT / "data" / "raw"
PROC_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)
print(f"Raw dir:       {RAW_DIR.relative_to(PROJECT_ROOT)}")
print(f"Processed dir: {PROC_DIR.relative_to(PROJECT_ROOT)}")


# %% ===== 2. Helper: robust GET with retries =========================
# Wikipedia rarely fails, but we wrap requests in retry logic anyway:
# transient 5xx errors and 429 (rate-limited) should back off and retry,
# not crash the run. Three retries with exponential backoff is the
# standard pattern.

section(2, "Helper: robust GET with retries")

def get_json(url: str, params: dict | None = None, max_retries: int = 3) -> dict:
    """GET a JSON endpoint with retry on 429/5xx. Raises on permanent failure."""
    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        except requests.RequestException as e:
            if attempt == max_retries:
                raise
            print(f"    network error ({e}); retrying in {backoff:.1f}s")
            time.sleep(backoff)
            backoff *= 2
            continue

        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
            print(f"    HTTP {r.status_code}; retrying in {backoff:.1f}s")
            time.sleep(backoff)
            backoff *= 2
            continue
        # 4xx other than 429, or final retry → fail
        r.raise_for_status()
    raise RuntimeError("unreachable")

print("Helper ready.")


# %% ===== 3. Step A - walk categories with pagination ================
# Wikipedia's Action API returns up to 500 category members per call.
# When more exist, the response includes a `continue.cmcontinue` token
# that you pass back on the next call to get the next page. Keep going
# until the token is absent (category exhausted) or we hit the cap.
#
# This is the rubric's "pagination handled" demonstration - we loop
# over pages until exhausted, with a sensible safety cap.

section(3, "Step A - walk categories with pagination")

def fetch_category_members(category: str, hard_cap: int = 1000) -> list[dict]:
    """Return all page members of a Wikipedia category, paginated."""
    titles: list[dict] = []
    params = {
        "action": "query",
        "list":   "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": 500,
        "cmtype":  "page",     # skip subcategories and files
        "format":  "json",
    }
    page_n = 0
    while True:
        page_n += 1
        data = get_json(ACTION_API, params)
        batch = data.get("query", {}).get("categorymembers", [])
        titles.extend({"title": m["title"], "pageid": m["pageid"], "category": category}
                      for m in batch)
        print(f"  [{category}] page {page_n}: +{len(batch)} → total {len(titles)}")

        # Wikipedia pagination token. If absent → done with this category.
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont or len(titles) >= hard_cap:
            break
        params["cmcontinue"] = cont
        time.sleep(POLITE_DELAY)
    return titles


all_members: list[dict] = []
for cat in CATEGORIES:
    all_members.extend(fetch_category_members(cat))

# Dedup by title - a lifter may appear in multiple categories (e.g. both
# "American powerlifters" and "Female powerlifters"). Keep first occurrence.
seen, deduped = set(), []
for m in all_members:
    if m["title"] not in seen:
        seen.add(m["title"])
        deduped.append(m)

print(f"\nTotal raw members across categories: {len(all_members):,}")
print(f"After dedup by title:                {len(deduped):,}")

# Cap to LIFTER_CAP for the summary-fetch step.
sample = deduped[:LIFTER_CAP]
print(f"Sampling {len(sample):,} for summary fetch (rubric minimum: 200).")


# %% ===== 4. Step B - fetch REST summary per lifter ==================
# Wikipedia's REST API returns one JSON object per page with extract,
# description, thumbnail, etc. One request per lifter, with the polite
# delay between calls. We catch 404s individually because some category
# members can be redirects or recently-deleted pages - we don't want
# one missing record to abort the whole batch.

section(4, "Step B - fetch REST summary per lifter")

summaries: list[dict] = []
errors: list[dict] = []

for i, member in enumerate(sample, start=1):
    title = member["title"]
    # Wikipedia REST URLs use underscores for spaces.
    url = f"{REST_API}/{title.replace(' ', '_')}"
    try:
        s = get_json(url)
        summaries.append({**s, "source_category": member["category"]})
    except requests.HTTPError as e:
        errors.append({"title": title, "status": e.response.status_code, "msg": str(e)})

    if i % 25 == 0 or i == len(sample):
        print(f"  fetched {i:>3}/{len(sample)}  (errors so far: {len(errors)})")
    time.sleep(POLITE_DELAY)

print(f"\nSummaries collected: {len(summaries):,}")
print(f"Errors:              {len(errors):,}")


# %% ===== 5. Save raw JSON dump (the checkpoint) =====================
# Rubric requirement: "At least one saved raw file in data/raw/ ... so
# the API isn't re-hit every run." Saving the raw responses lets the
# parsing step iterate without re-fetching.

section(5, "Save raw JSON dump")
RAW_FILE = RAW_DIR / "wiki_powerlifter_summaries.json"
with RAW_FILE.open("w", encoding="utf-8") as f:
    json.dump({"summaries": summaries, "errors": errors}, f, ensure_ascii=False, indent=2)
print(f"Wrote {RAW_FILE.relative_to(PROJECT_ROOT)} ({RAW_FILE.stat().st_size / 1024:.1f} KB)")


# %% ===== 6. Parse into DataFrame =====================================
# Build a flat DataFrame with the fields most useful for cohort-context
# enrichment: title (the canonical name, used as the JOIN KEY to the
# OPL cohort), description, extract (short bio), and source_category.
# Missing keys default to None so the DataFrame stays rectangular.

section(6, "Parse into DataFrame")
rows = []
for s in summaries:
    rows.append({
        "title":           s.get("title"),
        "description":     s.get("description"),
        "extract":         (s.get("extract") or "")[:400],   # truncate long bios
        "lang":            s.get("lang"),
        "page_url":        s.get("content_urls", {}).get("desktop", {}).get("page"),
        "source_category": s.get("source_category"),
    })
df = pd.DataFrame(rows)
print(f"DataFrame shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
print("\nHead:")
print(df.head().to_string())
print("\nInfo:")
df.info()


# %% ===== 7. Save processed CSV =======================================
# This CSV is the artefact other notebooks can JOIN with our main cohort
# (on `title` ≈ OPL `Name`). Conservative on size, just the fields we'll
# actually use downstream.

section(7, "Save processed CSV")
OUT = PROC_DIR / "wiki_notable_lifters.csv"
df.to_csv(OUT, index=False)
print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}: {len(df):,} rows")


# %% ===== 8. Markdown summary (rubric: short summary at top) =========
# This block prints a short summary so the script's stdout is itself a
# complete record of what happened. Mirror the same information at the
# very top of the docstring when the assignment requires the summary to
# be a markdown cell.

section(8, "Run summary")
print(f"Categories walked:     {len(CATEGORIES)}")
print(f"Raw category members:  {len(all_members):,}")
print(f"After dedup:           {len(deduped):,}")
print(f"Summaries fetched:     {len(summaries):,}")
print(f"Errors:                {len(errors):,}")
print(f"Saved raw to:          {RAW_FILE.relative_to(PROJECT_ROOT)}")
print(f"Saved processed to:    {OUT.relative_to(PROJECT_ROOT)}")
