"""Data overview: inspect the raw OpenPowerlifting CSV before any filtering.

The full OPL dump is huge and messy; before deciding on cohort filters
we need to know what's actually in it - column types, missingness,
value distributions, obvious data-quality issues. This script loads
the raw CSV and prints a series of summaries. Nothing is modified or
saved.

Run from anywhere:
    python notebooks/03_data_overview.py

Paths resolve via __file__ so the working directory doesn't matter.
Output goes to stdout; redirect to a file if you want a record.
"""

import pandas as pd
import numpy as np
from pathlib import Path


def section(n: int, title: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}\n  Block {n}: {title}\n{bar}")


# %% ===== 1. Imports ==================================================
# pandas for DataFrame work, numpy for vectorised arithmetic, pathlib
# for clean filesystem paths. No matplotlib - there are no plots in
# this script. A ModuleNotFoundError here means the venv wasn't set up;
# install requirements.txt first.

section(1, "Imports")
print("pandas:", pd.__version__)
print("numpy: ", np.__version__)


# %% ===== 2. Locate and load the OPL CSV =============================
# OPL ships as a bundle directory (CSV plus LICENSE.txt and README.txt)
# whose folder name carries a date stamp. We glob recursively under
# data/raw/ so the script keeps working across OPL refreshes without
# hard-coded filenames. The assertion catches the two failure modes
# (no CSV, two CSVs sitting around) and reports them clearly.
# low_memory=False forces pandas to scan the whole file before guessing
# dtypes, which matters on a wide mixed CSV.

section(2, "Locate and load the OPL CSV")
SCRIPT_DIR = Path(__file__).resolve().parent
RAW = SCRIPT_DIR.parent / "data" / "raw"
csvs = sorted(RAW.rglob("*.csv"))
assert len(csvs) == 1, (
    f"Expected exactly 1 CSV under {RAW}, found {len(csvs)}: "
    f"{[str(c.relative_to(RAW)) for c in csvs]}"
)
PATH = csvs[0]
df = pd.read_csv(PATH, low_memory=False)
print(f"Loaded {PATH.relative_to(RAW)}")
print(f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")


# %% ===== 3. Schema check =============================================
# Confirm the columns we'll need exist and have sensible dtypes:
# Best3SquatKg/BenchKg/DeadliftKg (the lifts), Age, Sex, BodyweightKg,
# Equipment, Event, Place, Name. Age and BodyweightKg should be numeric
# - if either comes in as object/string that points to mixed values
# (e.g. "23-24" ranges, sentinel strings) that need handling.

section(3, "Schema check - columns and dtypes")
print("Columns:", df.columns.tolist())
print("\nDtypes:")
print(df.dtypes)


# %% ===== 4. Missingness ==============================================
# Fraction of NaN per column, top-20. The cohort filter will drop rows
# where Age, BodyweightKg, or any best-lift column is NaN; this shows
# how much volume that costs. If Age is missing in more than ~30% of
# rows the drop is significant (not cosmetic) and needs flagging in
# the writeup.

section(4, "Missingness - top 20 most-missing columns (fraction NaN)")
missingness = df.isna().mean().sort_values(ascending=False)
print(missingness.head(20).round(4))


# %% ===== 5. Value counts - Event =====================================
# OPL records several event formats: SBD (full powerlifting), B
# (bench-only), D, BD, etc. We plan to keep only SBD because it's the
# only event where all three lifts are contested in the same meet,
# which the cross-lift comparison (H1) needs.

section(5, "Value counts - Event")
print(df['Event'].value_counts(dropna=False))


# %% ===== 6. Value counts - Sex =======================================
# H2 compares male and female peak ages, so both groups need enough
# lifters for the test. Under ~5% F would mean caveating every H2
# result. Mx (non-binary) is also a category in OPL - small but real,
# decide separately how to handle.

section(6, "Value counts - Sex")
print(df['Sex'].value_counts(dropna=False))


# %% ===== 7. Value counts - Equipment =================================
# Plan is to keep all equipment categories and treat Equipment as a
# covariate. That's only defensible if all categories are well
# populated. Typical OPL categories: Raw, Wraps, Single-ply, Multi-ply,
# Unlimited, Straps. Equipment lets lifters lift more weight, so it
# has a real effect on relative strength and shouldn't be ignored.

section(7, "Value counts - Equipment")
print(df['Equipment'].value_counts(dropna=False))


# %% ===== 8. Value counts - Place (top 20) ============================
# Top 20 because the long tail of numeric placings would drown out the
# non-numeric codes we care about. We plan to drop DQ; other codes in
# OPL (NS = no-show, DD = doping DQ, G = guest lifter) each mean
# different things and need explicit handling.

section(8, "Value counts - Place (top 20)")
print(df['Place'].value_counts(dropna=False).head(20))


# %% ===== 9. Lift sanity ==============================================
# OPL encodes failed attempts as negative numbers - a Best3SquatKg of
# -150 means the lifter's best attempt was 150 kg but failed. Zero
# usually means the lift wasn't attempted at the event (bench-only
# meets leave squat at 0). NaN means not recorded. Splitting all four
# cases out here justifies the cohort filter: without it, "best squat"
# averages would silently include negatives.

section(9, "Lift sanity - <0 / ==0 / NaN / >0 per best-lift column")
for col in ['Best3SquatKg', 'Best3BenchKg', 'Best3DeadliftKg']:
    s = df[col]
    n_neg = (s < 0).sum()
    n_zero = (s == 0).sum()
    n_nan = s.isna().sum()
    n_pos = (s > 0).sum()
    total = len(s)
    print(f"\n{col}:")
    print(f"  <  0 (failed attempts):  {n_neg:>10,}  ({n_neg/total:.1%})")
    print(f"  == 0 (did not attempt):  {n_zero:>10,}  ({n_zero/total:.1%})")
    print(f"  NaN  (not recorded):     {n_nan:>10,}  ({n_nan/total:.1%})")
    print(f"  >  0 (valid best):       {n_pos:>10,}  ({n_pos/total:.1%})")


# %% ===== 10. Age =====================================================
# Age is the dependent variable, so we need its distribution. Tentative
# range filter is 14-80 (junior to senior masters band), chosen
# somewhat arbitrarily - the empirical distribution either confirms
# the bounds as cosmetic or reveals real edge cases. OPL also uses
# fractional ages (e.g. 24.5 when only birth year is known). Sentinel
# values like 0 or 999 would be a red flag.

section(10, "Age - descriptive stats + out-of-range counts")
print(df['Age'].describe())
print()
print(f"Age <  14:   {(df['Age'] <  14).sum():,}")
print(f"Age >  80:   {(df['Age'] >  80).sum():,}")
print(f"Age == NaN:  {df['Age'].isna().sum():,}")


# %% ===== 11. BodyweightKg ============================================
# BW is the denominator of relative strength, so zeros and negatives
# must be excluded. Range should run from ~40 kg (youth lightweight)
# to 150+ kg (superheavyweight); a max in the 300s would be a unit
# error (lb mislabelled as kg).

section(11, "BodyweightKg - descriptive stats + sanity")
print(df['BodyweightKg'].describe())
print()
print(f"BodyweightKg == 0:  {(df['BodyweightKg'] == 0).sum():,}")
print(f"BodyweightKg <  0:  {(df['BodyweightKg'] <  0).sum():,}")
print(f"BodyweightKg NaN:   {df['BodyweightKg'].isna().sum():,}")


# %% ===== 12. Unique lifters ==========================================
# Rows are meet performances, not lifters - many lifters compete
# repeatedly. After dedup to one row per (Name, Sex) per lift, the
# number of unique lifters bounds the independent analytical units.
# If either sex has only a few thousand unique lifters, H2 test power
# is limited.

section(12, "Unique lifters")
n_unique_total = df['Name'].nunique()
n_unique_by_sex = df.groupby('Sex')['Name'].nunique()
print(f"Unique lifters (total):  {n_unique_total:,}")
print(f"Total rows (meet-perfs): {len(df):,}")
print(f"Rows per lifter (mean):  {len(df) / n_unique_total:.1f}")
print()
print("Unique lifters by Sex:")
print(n_unique_by_sex)


# %% ===== 13. Notes ===================================================
# Fill in observations from the blocks above. For each block, note what
# you saw, whether it was a concern, and what (if anything) it changes
# for the cohort decisions in 04_cohort.py.
#
#   Block 1 (imports):
#
#   Block 2 (load):
#
#   Block 3 (schema):
#
#   Block 4 (missingness):
#
#   Block 5 (Event):
#
#   Block 6 (Sex):
#
#   Block 7 (Equipment):
#
#   Block 8 (Place):
#
#   Block 9 (lift sanity):
#
#   Block 10 (Age):
#
#   Block 11 (BodyweightKg):
#
#   Block 12 (unique lifters):

