"""Cohort construction.

Reads the raw OPL CSV and applies the agreed filter chain (defined in
src/cohort.py - see there for per-filter reasoning). Saves the
filtered cohort to data/processed/cohort_filtered.csv. Does not dedup
yet; that happens in 05_modeling.py.

Run from anywhere:
    python notebooks/04_cohort.py

To capture the audit trail:
    python notebooks/04_cohort.py > reports/cohort_output.txt
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.cohort import apply_cohort_filters


def section(n: int, title: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}\n  Block {n}: {title}\n{bar}")


# %% ===== 1. Load the raw OPL CSV ====================================
# Recursive glob under data/raw/ so the script doesn't care which date
# stamp is in the OPL bundle folder name. low_memory=False prevents
# pandas from misreading dtypes on a wide mixed CSV. Loading from raw
# here is correct: this script IS the cleaning stage, so there's no
# upstream intermediate to read.

section(1, "Load raw OPL CSV")
RAW = PROJECT_ROOT / "data" / "raw"
csvs = sorted(RAW.rglob("*.csv"))
assert len(csvs) == 1, (
    f"Expected exactly 1 CSV under {RAW}, found {len(csvs)}: "
    f"{[str(c.relative_to(RAW)) for c in csvs]}"
)
df = pd.read_csv(csvs[0], low_memory=False)
print(f"Loaded {csvs[0].name}")
print(f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")


# %% ===== 2. Apply cohort filters ====================================
# Run the six-step filter chain: Event=SBD, drop Straps equipment,
# drop DQ placings, Age in [14, 80], all three best-lift columns > 0,
# BodyweightKg > 0. Each step prints before/after counts, so the
# script's output is itself the audit trail. Per-filter reasoning lives
# in src/cohort.py docstrings.

section(2, "Apply cohort filters")
cohort = apply_cohort_filters(df)


# %% ===== 3. Post-filter sanity check =================================
# Sanity check: re-tabulate the filtered columns to confirm
# nothing unexpected survived. If a bug let the wrong rows through,
# this is where we'd catch it before the processed CSV gets used
# downstream.

section(3, "Post-filter sanity")
print(f"  Event values:           {sorted(cohort['Event'].unique())}")
print(f"  Equipment values:       {sorted(cohort['Equipment'].unique())}")
print(f"  'DQ' still in Place?    {'DQ' in cohort['Place'].unique()}")
print(f"  Age min / max:          {cohort['Age'].min():.1f} / {cohort['Age'].max():.1f}")
print(f"  BodyweightKg min / max: {cohort['BodyweightKg'].min():.1f} / {cohort['BodyweightKg'].max():.1f}")
print(f"  Sex breakdown:          {dict(cohort['Sex'].value_counts())}")


# %% ===== 4. Save the cohort to data/processed ========================
# CSV (not parquet) keeps the dependency list to five libraries.
# 05_modeling.py reads this file directly, so the modeling stage never
# has to re-clean from the raw data.

section(4, "Save cohort")
OUT = PROJECT_ROOT / "data" / "processed" / "cohort_filtered.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)
cohort.to_csv(OUT, index=False)
print(f"Wrote {OUT.relative_to(PROJECT_ROOT)}: {len(cohort):,} rows")
