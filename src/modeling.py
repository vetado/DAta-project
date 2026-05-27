"""Modeling helpers: relative strength, per-lifter peak extraction,
and the statistical tests for H1 (Friedman + Wilcoxon) and H2 (Mann-Whitney U).
"""

import pandas as pd
import numpy as np
from scipy import stats


LIFTS = ["Squat", "Bench", "Deadlift"]
LIFT_COLS = [f"Best3{lift}Kg" for lift in LIFTS]
REL_COLS = [f"rel_{lift.lower()}" for lift in LIFTS]
PEAK_AGE_COLS = [f"peak_{lift.lower()}_age" for lift in LIFTS]


def add_relative_strength(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with rel_squat, rel_bench, rel_deadlift = lift / BW."""
    out = df.copy()
    for lift, col, rel in zip(LIFTS, LIFT_COLS, REL_COLS):
        out[rel] = out[col] / out["BodyweightKg"]
    return out


def extract_peaks_wide(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (Name, Sex) with peak age, equipment, and rel-strength per lift.

    For each lift, keep the row where rel_<lift> is maximal per (Name, Sex),
    then merge the three per-lift tables.
    """
    pieces = []
    for lift, rel in zip(LIFTS, REL_COLS):
        idx = df.groupby(["Name", "Sex"])[rel].idxmax()
        piece = df.loc[idx, ["Name", "Sex", "Age", "Equipment", rel]].rename(
            columns={
                "Age": f"peak_{lift.lower()}_age",
                "Equipment": f"eq_{lift.lower()}_peak",
                rel: f"peak_{lift.lower()}_relstr",
            }
        )
        pieces.append(piece)
    wide = (
        pieces[0]
        .merge(pieces[1], on=["Name", "Sex"])
        .merge(pieces[2], on=["Name", "Sex"])
    )
    return wide


def h1_friedman(wide: pd.DataFrame) -> dict:
    """Friedman test on within-lifter peak-age triplets. Returns {stat, p, n}."""
    ages = [wide[col].values for col in PEAK_AGE_COLS]
    res = stats.friedmanchisquare(*ages)
    return {"stat": float(res.statistic), "p": float(res.pvalue), "n": len(wide)}


def h1_pairwise_wilcoxon(wide: pd.DataFrame, alpha: float = 0.05) -> list:
    """Pairwise Wilcoxon signed-rank tests (S-B, S-D, B-D), Bonferroni-corrected.

    Returns one dict per pair with pair, median_diff_years, stat, p_raw,
    p_bonferroni, significant_after_bonf.
    """
    pairs = [("Squat", "Bench"), ("Squat", "Deadlift"), ("Bench", "Deadlift")]
    n_tests = len(pairs)
    results = []
    for a, b in pairs:
        ca, cb = f"peak_{a.lower()}_age", f"peak_{b.lower()}_age"
        diff = wide[ca] - wide[cb]
        res = stats.wilcoxon(wide[ca], wide[cb])
        p_bonf = min(float(res.pvalue) * n_tests, 1.0)
        results.append({
            "pair": f"{a} - {b}",
            "median_diff_years": float(diff.median()),
            "stat": float(res.statistic),
            "p_raw": float(res.pvalue),
            "p_bonferroni": p_bonf,
            "significant_after_bonf": p_bonf < alpha,
        })
    return results


def h2_mann_whitney(wide: pd.DataFrame, alpha: float = 0.05) -> list:
    """Mann-Whitney U on M vs F peak age per lift (Mx excluded), Bonferroni-corrected.

    Returns one dict per lift with lift, n_M, n_F, median_M, median_F,
    median_diff_M_minus_F, stat, p_raw, p_bonferroni, significant_after_bonf.
    """
    mf = wide[wide["Sex"].isin(["M", "F"])]
    n_tests = len(LIFTS)
    results = []
    for lift in LIFTS:
        col = f"peak_{lift.lower()}_age"
        m_ages = mf.loc[mf["Sex"] == "M", col].values
        f_ages = mf.loc[mf["Sex"] == "F", col].values
        res = stats.mannwhitneyu(m_ages, f_ages, alternative="two-sided")
        p_bonf = min(float(res.pvalue) * n_tests, 1.0)
        results.append({
            "lift": lift,
            "n_M": int(len(m_ages)),
            "n_F": int(len(f_ages)),
            "median_M": float(np.median(m_ages)),
            "median_F": float(np.median(f_ages)),
            "median_diff_M_minus_F": float(np.median(m_ages) - np.median(f_ages)),
            "stat": float(res.statistic),
            "p_raw": float(res.pvalue),
            "p_bonferroni": p_bonf,
            "significant_after_bonf": p_bonf < alpha,
        })
    return results
