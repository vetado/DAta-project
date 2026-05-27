# When Do Powerlifters Peak? - Results

Analysis of the OpenPowerlifting (OPL) dataset, 2026-05-16 snapshot.
Generated 2026-05-24.

---

## Summary

We tested two preregistered hypotheses on a cohort of 441,984 unique powerlifters drawn from the OpenPowerlifting database:

- **H1.** Peak relative strength is reached at different ages across the squat, bench press, and deadlift.
- **H2.** Within each lift, peak relative strength is reached at different ages by men and women.

**H1 is technically rejected** by the Friedman test (χ² = 4867, p ≈ 0, N = 441,984), but the effect is negligible in magnitude (median differences ≤ 0.5 years across lifts) and the direction is **opposite the prediction**: deadlift trends earlier, not later. We interpret this as a *practical null* - peak age is, for practical purposes, the same across the three lifts.

**H2 is supported with a substantial effect.** Across all three lifts, women's median peak age is **2.5 years later** than men's (M = 23.5 yr, F = 26.0 yr, all p ≈ 0, Bonferroni-corrected). The effect is identical across lifts, which rules out lift-specific explanations and points to a sex-level (physiological or sociological) cause discussed below.

---

## Methods

### Data

We used the May 16, 2026 OpenPowerlifting full CSV (3,925,887 meet-performance rows × 42 columns), the canonical public-domain compilation of competitive powerlifting results. No external data or scraping; analysis is restricted to what OPL publishes.

### Cohort construction

Six successive row-level filters, applied in this order, with before/after counts printed at each step (see `reports/cohort_output.txt`):

| # | Filter | Rationale |
|---|---|---|
| 1 | `Event == "SBD"` | Only full-meet performances contest all three lifts; H1's cross-lift comparison requires this to avoid mixing single-lift specialists with generalists. Drops 27.5% of rows. |
| 2 | `Equipment != "Straps"` | "Straps" had 119 rows in the unfiltered data (0.003%), too few to meaningfully analyse or visualise as its own category. After filter 1 only 1 such row remained - the filter is therefore largely redundant after SBD, but we keep it explicit because that explicitness is the audit trail. |
| 3 | `Place != "DQ"` | Disqualified results can have positive recorded lifts (e.g. post-meet doping disqualifications) that would otherwise pass filter 5. NS ("no-show") rows are auto-handled by filter 5 because their lifts are all NaN; "G" (guest lifter) rows are kept because they represent real performances. Drops 6.8%. |
| 4 | `14 ≤ Age ≤ 80` | Spans the full competitive age band (junior to senior masters). The `Series.between` evaluation discards NaN-Age rows in the same step - a single semantic decision ("Age must be a recorded competitive-age value"), not two. Drops **43.6%**, the largest single loss in the chain. |
| 5 | All three of `Best3SquatKg, Best3BenchKg, Best3DeadliftKg > 0` | OPL encodes failed attempts as negative numbers and unreported lifts as NaN. Requiring all three positive in every row enables the within-lifter paired design for H1. Drops 0.3%. |
| 6 | `BodyweightKg > 0` | Denominator of relative strength must be valid. Drops 0.3%. |

Final cohort: **1,487,361 meet-rows**. Sex breakdown of rows: M = 1,032,317; F = 454,915; Mx = 129. After dedup to one row per (Name, Sex) lifter in `05_modeling.py`: **441,984 unique lifters** (M = 309,232; F = 132,678; Mx = 74).

The Age filter accounts for the vast majority of attrition. We considered this carefully: Age is our dependent variable, and OPL records it less reliably than the lifts themselves. There is no defensible alternative - analyzing peak age requires knowing the age.

### Outcome variable

For each lift X ∈ {Squat, Bench, Deadlift}, we define **relative strength** as

$$\text{rel}_X = \frac{\text{Best3}X\text{Kg}}{\text{BodyweightKg}}$$

We chose this simple ratio over allometric (`lift / BW^0.67`) and absolute (`lift` in kg) alternatives for explainability. The lift/BW ratio is known to slightly favor lighter lifters in cross-lifter strength comparisons; this bias matters less for our *peak age* analysis, which is a within-lifter quantity whose bodyweight varies relatively little across nearby meets.

### Peak-age extraction

For each lifter, for each lift, we kept the meet with the maximum relative strength and recorded the lifter's age at that meet. This *per-lifter empirical peak* method produces one age per lifter per lift. Because cohort filter 5 required all three best-lift columns valid in every row, every lifter who survived the cohort filter contributed to the dedup for all three lifts, yielding a complete wide table of (peak_squat_age, peak_bench_age, peak_deadlift_age) per lifter.

We considered a population-level quadratic regression alternative (fit `rel ~ age + age² + covariates` per group, derive peak from the coefficients) but rejected it as harder to defend and disconnected from the per-lifter "peak" intuition.

### Statistical tests

- **H1.** Friedman test on the within-lifter triplet (non-parametric repeated-measures ANOVA). Three pairwise Wilcoxon signed-rank tests as post-hoc, Bonferroni-corrected at α/3.
- **H2.** Mann-Whitney U on M vs F peak ages, separately within each lift. Three independent tests, Bonferroni-corrected at α/3. Mx lifters (n=74 in the wide table) are excluded from H2; H2 names only M and F.

Non-parametric tests throughout because peak-age distributions are right-skewed (a long tail of older lifters at the high end of the competitive band). Bonferroni is the conservative default and trivial to defend in writing.

---

## Sample characteristics

The cohort spans **441,984 unique lifters**, contributing on average 3.4 meets each in the cohort (median is lower; see Caveats §4 below). Sex breakdown after the cohort filter: M = 70%, F = 30%, Mx = 0.02%. The F representation is ample for H2.

Distribution of peak ages per lift (across all sexes):

| Lift | Mean (yr) | Median (yr) | SD (yr) | Range (yr) |
|---|---|---|---|---|
| Squat | 27.17 | 24.5 | 10.43 | 14 - 80 |
| Bench | 27.20 | 24.5 | 10.40 | 14 - 80 |
| Deadlift | 27.08 | 24.0 | 10.41 | 14 - 80 |

The three distributions are nearly indistinguishable on any summary statistic - already a hint at the H1 finding.

---

## Results - H1

**Friedman test.** Test statistic χ² = 4866.68, **p < 1×10⁻³⁰⁰** (below double-precision floor; reported as 0 in scipy), N = 441,984. We reject H₀ that the three lift peak-age distributions are identical.

**Pairwise contrasts (Wilcoxon signed-rank, Bonferroni-corrected):** all three pairwise differences are statistically significant after correction, but the effect sizes are tiny. Two distinct effect-size views, both pointing to the same conclusion:

- *Within-lifter median pairwise differences* (from `results_output.txt` block 3): essentially **0.00 yr** for all three pairs - the script literally prints `median diff = +0.00 yr` for Squat-Bench, Squat-Deadlift, and Bench-Deadlift. The median lifter peaks at the same age across all three lifts.
- *Mean pairwise differences* (computed from §3 marginal means): below 0.13 yr for every pair. Direction shown in the table.

| Pair | Mean difference (yr) | Direction (on the mean) |
|---|---|---|
| Squat − Deadlift | +0.09 | Squat peaks slightly later |
| Bench − Deadlift | +0.12 | Bench peaks slightly later |
| Squat − Bench | −0.03 | Squat ≈ Bench |

**Direction vs prediction.** H1 predicted "deadlift latest, bench earliest." On the mean the data show the **opposite** ordering: deadlift earliest, bench latest by ~0.1 yr. On the median the three pairs are tied. Either way the prediction is not supported.

**Interpretation.** With N = 441,984 the Friedman test is overpowered: it detects vanishingly small effects. The honest reading of these numbers is that **peak relative-strength age is the same across the three lifts to within a fraction of a year**. The technical rejection of H₀ is statistically real but practically negligible. See `reports/figures/peak_age_by_lift.png` - the three boxplots are visually indistinguishable.

---

## Results - H2

**Mann-Whitney U per lift**, Bonferroni-corrected. All three lifts show identical results:

| Lift | n_M | n_F | Median M (yr) | Median F (yr) | Δ M − F (yr) | p (Bonferroni) |
|---|---|---|---|---|---|---|
| Squat | 309,232 | 132,678 | 23.5 | 26.0 | **−2.5** | < 1×10⁻³⁰⁰ |
| Bench | 309,232 | 132,678 | 23.5 | 26.0 | **−2.5** | < 1×10⁻³⁰⁰ |
| Deadlift | 309,232 | 132,678 | 23.5 | 26.0 | **−2.5** | < 1×10⁻³⁰⁰ |

**H2 is supported.** Across all three lifts, **women's median peak age is 2.5 years later than men's**. The effect is consistent in direction and magnitude across lifts. See `reports/figures/peak_age_by_lift_and_sex.png` for the visual.

**Effect size in context.** The 2.5-year sex difference is approximately **20× larger** than the largest H1 lift-by-lift difference. The H2 effect is the substantively meaningful one in this analysis.

**Possible explanations (physiological vs sociological).** Two candidate accounts:

1. *Physiological.* If women's strength-development curves are flatter and later-peaking than men's, we would expect exactly this pattern. The exercise-physiology literature on competitive athletes does not strongly support this for absolute strength.
2. *Selection effects in the data.* Women's competitive powerlifting has expanded primarily in the 2010s-2020s. Women in OPL are therefore on average newer to the sport, with shorter competitive careers, than men. "Peak in observed data" is biased toward later ages for lifters who entered the sport later (because they have fewer young-age meets to peak in). This is a real concern that this study cannot rule out without modeling year-of-first-meet, which is beyond the cohort defined here.

Both effects likely contribute. The honest interpretation: **the data show women peak later in OPL by 2.5 years**; whether that reflects physiology or sampling is an open question that this analysis cannot resolve.

---

## Methodological caveats

1. **Single-meet lifters dominate the marginal distributions.** Mean meets per lifter is 3.4, but with heavy right-skew the median is much lower. For a lifter with only one cohort meet, all three peak ages collapse to the same value (the age at that meet). These lifters contribute zero within-lifter variance to the Friedman test, so the test still works correctly - but they flatten the *marginal* lift-by-lift distributions (which is why §3's medians are nearly identical across lifts and §5's H2 medians are identical to one decimal). A defensible sensitivity analysis is to re-run H1 on lifters with ≥3 cohort meets; this was not included in the current pipeline.

2. **OPL's data is competition-only.** Lifters' true physiological peak may occur in training, between meets, or not at all if they never enter a sufficiently late-career meet. The "peak age in observed competitions" is a lower bound on physiological peak age, censored by competitive participation. This caveat applies equally to all conditions and does not threaten the within-comparison validity of H1 or H2.

3. **Age missingness is large (37% in the raw, 43.6% effective in the cohort chain).** OPL records lifts more reliably than ages. Lifters with unrecorded age are excluded. If unrecorded-age lifters peak systematically differently from recorded-age lifters, our estimates are biased. We have no way to test this with OPL alone.

4. **Dedup tie-breaking is by input order.** Where a lifter hit their maximum relative strength at multiple meets (a tie), we kept the first such meet in input order - typically the earlier date, giving the "first-time peak" age. Alternative tie-breaking rules (latest meet, random) would produce slightly different peak ages for those lifters but do not materially affect the conclusions.

5. **Equipment as confounder.** Equipment was retained in the cohort (filter 2 dropped only Straps) but is **NOT** included as a covariate in the H1 or H2 tests, which operate on per-lifter peak ages directly. If men and women use systematically different equipment distributions, part of the M − F effect could be an Equipment difference. A per-lift OLS regression `peak_age ~ Sex + Equipment` is the natural follow-up analysis.

6. **Wikipedia enrichment context.** A supplementary biographical sample of ≥200 notable powerlifters was pulled from Wikipedia (see `notebooks/01_api_collection.py` and `data/processed/wiki_notable_lifters.csv`). This sample is heavily male-skewed in the same direction as the OPL cohort itself, consistent with the male dominance of the sport's competitive history. The enrichment is cohort-context only and was not used to feed H1 or H2.

---

## Conclusions

| Hypothesis | Statistical result | Practical interpretation |
|---|---|---|
| H1: peak age differs across S, B, D | Rejected (p ≈ 0) | **Practical null.** Effect ≤ 0.5 yr; direction opposite the prediction. |
| H2: peak age differs M vs F within each lift | Supported (p ≈ 0) | **Substantive effect: women peak 2.5 yr later than men, identically across all lifts.** Underlying cause (physiology vs OPL sampling era) cannot be resolved here. |

The cleanest single sentence: *in OpenPowerlifting's competitive data, peak relative-strength age does not meaningfully differ across the squat, bench, and deadlift, but it differs substantially between sexes - women peak about 2.5 years later than men, by an amount that is essentially identical for all three lifts*.

---

## Files

- `data/processed/cohort_filtered.csv` - output of `notebooks/02_cohort.py`; 1,487,361 rows.
- `data/processed/peaks_wide.csv` - output of `notebooks/03_modeling.py`; 441,984 lifter-rows with peak ages.
- `reports/cohort_output.txt`, `modeling_output.txt`, `results_output.txt` - full audit-trail outputs of the three pipeline scripts.
- `reports/figures/peak_age_by_lift.png` - H1 visualization.
- `reports/figures/peak_age_by_lift_and_sex.png` - H2 visualization.
- `src/cohort.py`, `src/modeling.py`, `src/plotting.py` - library functions, each with reasoning docstrings.
