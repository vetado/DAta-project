"""Modeling: relative strength and per-lifter peak extraction.

Reads the filtered cohort produced by 04_cohort.py, computes relative
strength per lift (lift / BW), deduplicates to one row per (Name, Sex)
per lift at peak relative strength, and merges into a wide table with
one row per lifter and three peak ages. Saves to
data/processed/peaks_wide.csv.

Run from anywhere:
    python notebooks/05_modeling.py

To capture the audit trail:
    python notebooks/05_modeling.py > reports/modeling_output.txt
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.modeling import (
    add_relative_strength,
    extract_peaks_wide,
    PEAK_AGE_COLS,
    REL_COLS,
)


def section(n: int, title: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}\n  Block {n}: {title}\n{bar}")


# %% ===== 1. Load the cohort =========================================
# Read the filtered cohort produced by 04_cohort.py. The convention
# for this project is that modeling never re-cleans from data/raw - 
# if the processed CSV is missing, run 04_cohort.py first.

section(1, "Load cohort")
COHORT = PROJECT_ROOT / "data" / "processed" / "cohort_filtered.csv"
cohort = pd.read_csv(COHORT, low_memory=False)
print(f"Loaded cohort: {len(cohort):,} rows")


# %% ===== 2. Add relative strength columns ============================
# rel_squat / rel_bench / rel_deadlift = best lift divided by
# bodyweight. This is the outcome variable each lifter's peak is
# defined against. lift/BW was chosen over allometric (lift/BW^0.67)
# and absolute kg for explainability (full rationale in
# src/modeling.py). The cohort filter has already guaranteed BW > 0,
# so the divisions can't produce NaN or infinity.

section(2, "Compute relative strength")
cohort = add_relative_strength(cohort)
print("Relative-strength summary:")
print(cohort[REL_COLS].describe().round(3))


# %% ===== 3. Extract peaks (wide table, one row per lifter) ===========
# For each lift, group by (Name, Sex) and take the row with maximum
# relative strength - that row's Age is the lifter's peak age for
# that lift. Merging the three per-lift tables gives a wide row per
# lifter with three peak ages. Because the cohort required all three
# lifts valid in every row, every lifter appears in all three dedups,
# so the merge is complete.

section(3, "Extract per-lifter peaks (wide table)")
peaks = extract_peaks_wide(cohort)
n_cohort_lifters = cohort.groupby(["Name", "Sex"]).ngroups
print(f"Wide-peak table: {len(peaks):,} lifters (cohort had {n_cohort_lifters:,})")
print("\nPeak-age distribution per lift:")
print(peaks[PEAK_AGE_COLS].describe().round(2))


# %% ===== 4. Save the wide peak table =================================
# Saving here separates computation from analysis: 06_results.py reads
# this file directly, so the tests can be re-run without redoing the
# dedup. Inspecting the saved CSV by hand is also easier than
# re-running the pipeline to check a single number.

section(4, "Save wide peak table")
OUT = PROJECT_ROOT / "data" / "processed" / "peaks_wide.csv"
peaks.to_csv(OUT, index=False)
print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}: {len(peaks):,} rows")
