"""Cohort filter functions for the OPL peak-age analysis.

Each filter takes a DataFrame and returns a filtered one, printing
before/after row counts via the _filter helper.
"""

import pandas as pd


MIN_AGE = 14
MAX_AGE = 80
EXCLUDED_EQUIPMENT = {"Straps"}
EXCLUDED_PLACE = {"DQ"}
LIFT_COLS = ["Best3SquatKg", "Best3BenchKg", "Best3DeadliftKg"]


def _filter(df: pd.DataFrame, mask: pd.Series, label: str) -> pd.DataFrame:
    """Apply a boolean mask, print before/after counts, return filtered df."""
    before = len(df)
    out = df[mask].copy()
    after = len(out)
    dropped = before - after
    pct = (dropped / before * 100) if before else 0
    print(f"  {label:<40s}  {before:>10,} -> {after:>10,}  "
          f"(-{dropped:>9,}, -{pct:5.1f}%)")
    return out


def filter_sbd_only(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only full-powerlifting meets (Event == 'SBD')."""
    return _filter(df, df["Event"] == "SBD", "1. Event == SBD")


def filter_drop_excluded_equipment(df: pd.DataFrame) -> pd.DataFrame:
    """Drop equipment categories in EXCLUDED_EQUIPMENT."""
    return _filter(
        df,
        ~df["Equipment"].isin(EXCLUDED_EQUIPMENT),
        f"2. Equipment != {sorted(EXCLUDED_EQUIPMENT)}",
    )


def filter_drop_excluded_place(df: pd.DataFrame) -> pd.DataFrame:
    """Drop placings in EXCLUDED_PLACE."""
    return _filter(
        df,
        ~df["Place"].isin(EXCLUDED_PLACE),
        f"3. Place != {sorted(EXCLUDED_PLACE)}",
    )


def filter_age_range(df: pd.DataFrame) -> pd.DataFrame:
    """Keep rows with Age in [MIN_AGE, MAX_AGE]. NaN-Age rows are also dropped."""
    return _filter(
        df,
        df["Age"].between(MIN_AGE, MAX_AGE, inclusive="both"),
        f"4. Age in [{MIN_AGE}, {MAX_AGE}]",
    )


def filter_valid_lifts(df: pd.DataFrame) -> pd.DataFrame:
    """Require all three Best3*Kg columns to be > 0."""
    mask = (df[LIFT_COLS] > 0).all(axis=1)
    return _filter(df, mask, "5. All 3 best-lift cols > 0")


def filter_valid_bodyweight(df: pd.DataFrame) -> pd.DataFrame:
    """Require BodyweightKg to be present and positive."""
    mask = df["BodyweightKg"].notna() & (df["BodyweightKg"] > 0)
    return _filter(df, mask, "6. BodyweightKg > 0")


def apply_cohort_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Run the six cohort filters in order, printing the chain."""
    print("Cohort filter chain:")
    print(f"  {'start':<40s}  {len(df):>10,}")
    df = filter_sbd_only(df)
    df = filter_drop_excluded_equipment(df)
    df = filter_drop_excluded_place(df)
    df = filter_age_range(df)
    df = filter_valid_lifts(df)
    df = filter_valid_bodyweight(df)
    print(f"  {'final':<40s}  {len(df):>10,}")
    return df
