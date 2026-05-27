"""Charts for the peak-age analysis."""

import matplotlib.pyplot as plt


LIFTS = ("Squat", "Bench", "Deadlift")

# Okabe-Ito colorblind-safe palette. Same hex codes shared across charts.
OKABE_ITO = {"M": "#0072B2", "F": "#D55E00", "Mx": "#009E73"}
SOURCE_NOTE = "Source: OpenPowerlifting, 2026-05-16 snapshot"


def peak_age_boxplot(wide):
    """Boxplot of peak age by lift (all sexes pooled). Returns the Figure."""
    fig, ax = plt.subplots(figsize=(7, 5))
    data = [wide[f"peak_{lift.lower()}_age"].values for lift in LIFTS]
    ax.boxplot(data, tick_labels=list(LIFTS), showfliers=False)
    ax.set_ylabel("Peak age (years)")
    ax.set_title("Peak age by lift\n(per-lifter empirical peak, all sexes)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def peak_age_by_sex_boxplot(wide):
    """Boxplot of peak age by lift x sex (M and F only). Returns the Figure."""
    mf = wide[wide["Sex"].isin(["M", "F"])]
    fig, ax = plt.subplots(figsize=(9, 5))
    positions, labels = [], []
    pos = 1
    for lift in LIFTS:
        col = f"peak_{lift.lower()}_age"
        m = mf.loc[mf["Sex"] == "M", col].values
        f = mf.loc[mf["Sex"] == "F", col].values
        ax.boxplot(
            [m, f],
            positions=[pos, pos + 1],
            widths=0.7,
            showfliers=False,
        )
        labels.extend([f"{lift}\nM", f"{lift}\nF"])
        positions.extend([pos, pos + 1])
        pos += 3
    ax.set_xticks(positions)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Peak age (years)")
    ax.set_title("Peak age by lift and sex\n(per-lifter empirical peak, Mx excluded)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def age_distribution_histogram(cohort):
    """Stacked histogram of cohort Age by Sex. Returns the Figure.

    Cohort is the meet-level DataFrame (one row per meet-performance).
    The chart shows what survived the cohort filter; together with the
    legend counts, it makes the post-filter sex/age structure visible.
    """
    fig, ax = plt.subplots(figsize=(9, 5))
    bins = list(range(14, 82))  # 14 to 80 inclusive, 1-year bins
    series_by_sex = []
    labels = []
    colors = []
    for sex in ["M", "F", "Mx"]:
        ages = cohort.loc[cohort["Sex"] == sex, "Age"]
        series_by_sex.append(ages)
        labels.append(f"{sex} (n={len(ages):,})")
        colors.append(OKABE_ITO[sex])
    ax.hist(series_by_sex, bins=bins, stacked=True, label=labels, color=colors)
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Number of meet-performances")
    ax.set_title("Age distribution of the cohort, by sex")
    ax.legend(title="Sex")
    ax.grid(axis="y", alpha=0.3)
    fig.text(0.5, 0.005, SOURCE_NOTE, ha="center", fontsize=8, color="gray")
    fig.tight_layout()
    return fig


def sex_breakdown_bar(peaks):
    """Bar chart of M/F/Mx counts in the peak table. Returns the Figure.

    Input is peaks_wide (one row per unique lifter), which matches H2's
    per-lifter unit of analysis.
    """
    fig, ax = plt.subplots(figsize=(7, 5))
    counts = peaks["Sex"].value_counts().reindex(["M", "F", "Mx"]).fillna(0).astype(int)
    colors = [OKABE_ITO[s] for s in counts.index]
    bars = ax.bar(counts.index, counts.values, color=colors)
    for bar, n in zip(bars, counts.values):
        ax.annotate(
            f"{n:,}",
            xy=(bar.get_x() + bar.get_width() / 2, n),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_xlabel("Sex")
    ax.set_ylabel("Unique lifters")
    ax.set_title("Cohort breakdown by sex (after dedup to peaks)")
    ax.grid(axis="y", alpha=0.3)
    fig.text(0.5, 0.005, SOURCE_NOTE, ha="center", fontsize=8, color="gray")
    fig.tight_layout()
    return fig


def meets_per_lifter_distribution(cohort):
    """Log-y histogram of meets per lifter in the cohort. Returns the Figure.

    Motivates the 'single-meet lifters dominate the marginals' caveat:
    a lifter who appears in only one cohort meet has all three peak ages
    collapsed to the same value (their one meet's age), contributing
    zero within-lifter variance to the Friedman test.
    """
    fig, ax = plt.subplots(figsize=(9, 5))
    meets_per = cohort.groupby(["Name", "Sex"]).size()
    median = meets_per.median()
    pct_single = (meets_per == 1).mean() * 100
    bins = list(range(1, 51))  # 1-meet-wide bins from 1 to 50; long tail (>50) is rare
    ax.hist(meets_per, bins=bins, color="#56B4E9")  # Okabe-Ito sky-blue
    ax.set_yscale("log")
    ax.axvline(
        median,
        color="black",
        linestyle="--",
        linewidth=1,
        alpha=0.7,
        label=f"median = {median:.0f}    |    {pct_single:.0f}% of lifters have only 1 meet",
    )
    ax.set_xlabel("Meets per lifter")
    ax.set_ylabel("Number of lifters (log scale)")
    ax.set_title("Distribution of meets per lifter in the cohort")
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3, which="both")
    fig.text(0.5, 0.005, SOURCE_NOTE, ha="center", fontsize=8, color="gray")
    fig.tight_layout()
    return fig
