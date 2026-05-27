# When Do Powerlifters Peak?

A university data project analyzing the OpenPowerlifting dataset to test two hypotheses about the age at which competitive powerlifters reach peak relative strength.

## Hypotheses

- **H1** - Peak age differs across the squat, bench press, and deadlift. *Predicted direction: deadlift latest, bench earliest.*
- **H2** - Within each lift, peak age differs between male and female competitive lifters.

## Headline findings

Cohort of **441,984 unique lifters** drawn from ~1.5M meet-performances after filtering.

- **H1 - practical null.** Peak age is essentially the same across all three lifts (median differences ≤ 0.5 years). The Friedman test technically rejects H₀ but the effect is negligible, and the direction is *opposite* the prediction - deadlift trends earliest, not latest.
- **H2 - supported, substantive effect.** Women's median peak age is **2.5 years later than men's**, identically across all three lifts. This is the meaningful finding. Whether the cause is physiological or sampling-era (women's powerlifting expanded mainly in the 2010s-2020s, so women in OPL are on average newer to the sport) is not resolved here.

Full prose writeup: [`reports/results.md`](reports/results.md).

## Data

- **Source:** [OpenPowerlifting full CSV](https://openpowerlifting.gitlab.io/opl-csv/), public domain.
- Single data source. No scraping.
- The raw OPL bundle (~800 MB) lives in `data/raw/` and is **gitignored**. Download the OPL zip and unzip it into `data/raw/`; the scripts find the CSV via recursive glob, so the bundle's subdirectory layout is preserved.

## How to reproduce

```bash
git clone <repo-url>
cd DAta-project

# venv (macOS forces this via PEP 668; Linux/Windows similar)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Drop the OPL bundle in data/raw/ so you have:
#   data/raw/openpowerlifting-YYYY-MM-DD/openpowerlifting-*.csv

# Run the pipeline in order:
python notebooks/01_api_collection.py  > reports/api_output.txt
python notebooks/02_scraping.py        > reports/scraping_output.txt
python notebooks/03_data_overview.py   > reports/phase_a_output.txt
python notebooks/04_cohort.py          > reports/cohort_output.txt
python notebooks/05_modeling.py        > reports/modeling_output.txt
python notebooks/06_results.py         > reports/results_output.txt
python notebooks/07_final_report.py    > reports/final_report_output.txt
```

Notebook-by-notebook summary:

| # | File | What it does |
|---|---|---|
| 01 | `01_api_collection.py` | Pulls ≥200 Wikipedia powerlifter summaries via paginated MediaWiki Action API + REST API. Saves raw JSON and parsed CSV. |
| 02 | `02_scraping.py` | Scrapes the Wikipedia "Powerlifting" article wikitables with BeautifulSoup. Includes robots.txt check and ethics note. |
| 03 | `03_data_overview.py` | Inspects the raw OPL CSV: shape, schema, missingness, value counts, sanity checks. No filtering. |
| 04 | `04_cohort.py` | Applies the six-step cohort filter. Writes `data/processed/cohort_filtered.csv`. |
| 05 | `05_modeling.py` | Computes relative strength, extracts per-lifter peak ages, writes `data/processed/peaks_wide.csv`. |
| 06 | `06_results.py` | Runs Friedman + Wilcoxon (H1) and Mann-Whitney U (H2). Saves five figures to `reports/figures/`. |
| 07 | `07_final_report.py` | Story-mode walkthrough for the final deliverable. Loads `peaks_wide.csv` only - no recompute. |

Each script writes its full audit trail (row counts at every filter step, descriptive stats, test results) to a `.txt` file in `reports/`. Figures land in `reports/figures/`.

Approximate runtimes on a laptop: `01` 2-3 min (network, ≥200 API calls), `02` ~10 s (cached after first run), `03` ~1 min, `04` ~1-2 min, `05` ~30 s, `06` ~30 s, `07` ~10 s.

## Repo layout

```
.
├── README.md             # this file
├── requirements.txt      # pandas, numpy, matplotlib, scipy, statsmodels, beautifulsoup4, requests
├── data/
│   ├── raw/              # gitignored - drop the OPL bundle here
│   └── processed/        # intermediates written by 04, 05, and the API/scraping notebooks
├── notebooks/            # plain .py scripts with `# %%` cell markers
│   ├── 01_api_collection.py
│   ├── 02_scraping.py
│   ├── 03_data_overview.py
│   ├── 04_cohort.py
│   ├── 05_modeling.py
│   ├── 06_results.py
│   └── 07_final_report.py
├── src/                  # reusable library functions
│   ├── cohort.py         # 6-step cohort filter chain
│   ├── modeling.py       # relative strength + peak extraction + tests
│   └── plotting.py       # five charts (two H1/H2 boxplots + three EDA)
└── reports/
    ├── results.md        # academic writeup
    ├── decisions.md      # decision crib sheet for viva defence
    ├── *_output.txt      # audit trails from each pipeline script
    └── figures/          # five PNG figures
```

## Conventions

- **No Jupyter.** Despite the `notebooks/` directory name, every "notebook" is a plain `.py` script with `# %%` cell-marker comments. Choice made for clean Git diffs and zero install friction.
- **Every code section has a short comment above it** describing what it does and why.
- **Every filter step prints before/after row counts.** The script output IS the audit trail.
- **Intermediates are CSV**, not parquet - keeps the dependency list to five analysis libraries.
- **Modeling never re-cleans from `data/raw/`.** `03_modeling.py` reads from `data/processed/`. Cleaning happens once, in `02_cohort.py`.
- **Allowed libraries:** pandas, numpy, matplotlib, scipy, statsmodels. Anything else gets discussed first.

## Methodology snapshot

| Step | Decision |
|---|---|
| Cohort | `Event == "SBD"`, `Equipment != "Straps"`, `Place != "DQ"`, `14 ≤ Age ≤ 80`, all three best-lift columns > 0, `BodyweightKg > 0` |
| Outcome variable | `relative_strength = lift / BodyweightKg` |
| Peak-age extraction | Per (Name, Sex), per lift, take Age at the meet with max relative strength |
| H1 test | Friedman + pairwise Wilcoxon signed-rank, Bonferroni-corrected |
| H2 test | Mann-Whitney U per lift, Bonferroni-corrected; Mx excluded from H2 only |

Full rationale for every choice (and the alternatives considered + rejected) lives in the Methods section of [`reports/results.md`](reports/results.md) and in the docstrings of [`src/cohort.py`](src/cohort.py) and [`src/modeling.py`](src/modeling.py).

## Data source

OpenPowerlifting is public domain. See [openpowerlifting.org](https://openpowerlifting.org/data) for their data statement.
