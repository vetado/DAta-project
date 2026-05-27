# Decisions and defences - When Do Powerlifters Peak?

A study reference for the project's analytical choices. For each decision: the choice we made, the alternatives considered, why this one was picked, and a one-sentence answer to give if a grader asks "why did you choose X?"

Read top to bottom before viva. The short answers are deliberately short - they're what you should be able to say without thinking.

---

## Data sources beyond the bulk CSV

The primary data source is the OpenPowerlifting full CSV (the bulk export at openpowerlifting.gitlab.io/opl-csv/). Two supplementary sources are also used, both from Wikipedia, and both for cohort-context only - neither feeds H1 or H2.

**Why supplement at all?** The course rubric requires an API-collection notebook and a scraping notebook. The bulk CSV alone, while sufficient for the analytical work, does not exercise those data-acquisition skills. So we add lightweight enrichment.

**Why Wikipedia, not OpenPowerlifting's own API or a third-party API?**

- OpenPowerlifting's own documentation states explicitly: "no need to scrape our websites: you can download everything here" - the bulk CSV is the canonical source. Their `/api/` path is disallowed by `robots.txt` for automated crawlers. Respecting that guidance, we do not hit OPL programmatically.
- The main third-party option, `api.powerliftingdata.com`, is currently down at the time of the analysis (May 2026 snapshot).
- Wikipedia explicitly permits programmatic access (provided requests are throttled and identify themselves) and publishes both biographical context for notable lifters and absolute-strength reference records that are not in the OPL CSV.

**Notebook 01 - `01_api_collection.py`** uses two Wikipedia APIs together: the MediaWiki Action API (paginated category listings) to walk several "powerlifters" categories, and the REST API (per-page summary JSON) to hydrate each title with description, extract, and source category. Output: ≥200 notable-lifter records cached to `data/raw/wiki_powerlifter_summaries.json` and parsed to `data/processed/wiki_notable_lifters.csv`. Pagination, retry-on-5xx/429 with exponential backoff, polite delay, and a descriptive User-Agent are all in place.

**Notebook 02 - `02_scraping.py`** uses BeautifulSoup to parse wikitables on Wikipedia's "Powerlifting" article. `robots.txt` is fetched programmatically and the User-Agent is checked against it before any HTML request. Raw HTML is cached to `data/raw/wiki_powerlifting.html` after the first fetch so subsequent runs do not re-hit the site.

**What the enrichment is for.** Characterising the "notable lifter" subpopulation that overlaps with our cohort, for the limitations discussion. It does not change the H1 or H2 statistical analysis. The rubric's API + scraping requirements are satisfied entirely by these two notebooks.

---

## Cohort filter (six steps)

### 1. Event filter: keep only `SBD`

- **Choice:** drop every row where `Event != "SBD"`.
- **Alternative:** keep all events; use whichever lift is recorded.
- **Why this:** H1 needs the same lifter to contest all three lifts in the same meet. SBD ("Squat-Bench-Deadlift" - full powerlifting) is the only event format where that happens. Single-lift meets (B, D) draw from a systematically different competitive population (specialists), and mixing them with generalists would bias the comparison.
- **Cost in rows:** ~27.5% of the raw data (1.08M rows).
- **Short answer:** *"We kept only SBD events because H1's cross-lift comparison requires all three lifts from the same competitive meet - single-lift meets mix specialists and generalists."*

### 2. Equipment filter: drop `Straps`

- **Choice:** drop rows where `Equipment == "Straps"`.
- **Alternative:** keep, treat as another category in any descriptive analysis or visualisation.
- **Why this:** Phase A counted 119 Straps rows total (0.003% of data). With that few rows, Straps cannot be meaningfully separated as its own category in any analysis or visualisation. Almost all Straps rows are deadlift-only meets anyway, so the SBD filter takes care of most of them - this filter dropped exactly 1 row after SBD. Keeping it explicit makes the cohort definition transparent.
- **Cost in rows:** practically nothing (~1 row after SBD).
- **Short answer:** *"Straps had only 119 rows in the raw data - far too few to estimate a stable covariate level, and almost all of them weren't SBD events anyway."*

### 3. Place filter: drop `DQ` only

- **Choice:** drop rows where `Place == "DQ"`. Don't explicitly drop `NS` or `G`.
- **Alternatives:** (a) drop all non-numeric placings; (b) keep DQ rows whose lifts are positive.
- **Why this:** DQ means *disqualified after the fact* (often doping violations or rule infractions). The recorded best lifts may be positive (because the lifter physically lifted them) but they don't represent a legitimate competitive performance. NS (no-show) rows have all-NaN lifts because the lifter never attempted anything - they get auto-dropped by filter 5 (the lift-sanity filter). G (guest lifter) rows have real lifts performed at a real meet; the lifter just wasn't officially placed because they were a visiting competitor. We want to keep guest performances.
- **Cost in rows:** 6.8% (192k DQ rows).
- **Short answer:** *"DQ rows are dropped explicitly because their lifts can be positive but invalid; NS rows are dropped automatically by the lift-sanity filter; G rows have valid lifts and we keep them."*

### 4. Age range: `14 ≤ Age ≤ 80` (inclusive)

- **Choice:** keep rows where Age is between 14 and 80.
- **Alternatives:** (a) 18-65 (adult only); (b) no range filter at all.
- **Why this:** 14 is the youngest age most federations allow junior competition (including IPF). 80 is around the top of named senior masters classes. Pandas' `Series.between(...)` evaluates to False for NaN, so the same step that bounds the range also discards every row with missing Age. We treat this as **one semantic decision** ("Age must be a recorded competitive-age value") rather than two, because that's what it actually is.
- **Cost in rows:** 43.6% - by far the biggest single drop. Almost entirely driven by NaN-Age rows, not by out-of-range values.
- **Short answer:** *"The 14-80 band spans the full competitive age range, and `.between` also discards the 37% NaN-Age rows in one step - Age is our dependent variable, we cannot analyse it without it."*

### 5. All three best-lift columns positive

- **Choice:** keep rows where `Best3SquatKg`, `Best3BenchKg`, AND `Best3DeadliftKg` are all > 0.
- **Alternative:** require *any one* to be positive (per-lift analysis).
- **Why this:** This is what makes H1 a within-lifter paired design. Every cohort row contributes a (squat, bench, deadlift) triplet at the same age. The Friedman test compares the three within each lifter - statistically stronger than comparing three unrelated populations. Allowing rows with only one valid lift would give different lifters in each lift's analysis and break the pairing.
- **Cost in rows:** 0.3% - small because the SBD filter already implies most rows have all three.
- **Short answer:** *"Requiring all three best-lift columns positive in every row makes H1 a within-lifter paired comparison - each lifter contributes three peak ages, and Friedman compares them within-subject."*

### 6. `BodyweightKg > 0`

- **Choice:** drop NaN, zero, or negative `BodyweightKg`.
- **Alternative:** none defensible - BW is a denominator.
- **Why this:** Relative strength is lift / BW. NaN, zero, or negative BW produces NaN or infinite relative strength, which would crash downstream code. The defensiveness against zero / negative is precautionary - Phase A confirmed there are none in the current data - but it's cheap and protects against future OPL refreshes that might introduce sentinels.
- **Cost in rows:** 0.3% (44k NaN rows).
- **Short answer:** *"BodyweightKg is the denominator of relative strength - NaN, zero, or negative would give NaN or infinity, so we exclude them. The check on zero and negative is precautionary; the data has none today."*

---

## Outcome variable

### 7. `relative_strength = lift / BodyweightKg`

- **Choice:** simple ratio of best lift to bodyweight.
- **Alternatives:** (a) allometric `lift / BW^0.67`; (b) absolute lift in kg; (c) one of OPL's coefficients (Dots, Wilks, Glossbrenner, Goodlift).
- **Why this:**
  - Easy to explain to a non-specialist ("we divided by bodyweight").
  - The "lift/BW favours lighter lifters" criticism applies more to *between-lifter* strength rankings than to *within-lifter* peak ages. Each lifter's bodyweight is approximately constant across nearby meets, so the bias is small for our purpose.
  - Allometric `BW^0.67` is theoretically better (matches the muscle cross-section vs body-mass scaling law) but harder to defend in simple terms and only marginally more accurate for our question.
  - Absolute kg confounds strength gains with bodyweight gains - a lifter who adds 20 kg of muscle squats more, even if their training never peaks.
  - OPL's coefficients (Dots, Wilks, etc.) score the *total* of all three lifts. Our analysis is per-lift, so we can't use them.
- **Short answer:** *"Simple lift/BW because it's the standard 'relative strength' measure and easy to defend; the known bias toward lighter lifters matters more for between-lifter rankings than for within-lifter peak ages."*

---

## Peak-age estimation

### 8. Per-lifter empirical peak

- **Choice:** for each (lifter, lift), keep the row where their relative strength is maximal; that row's Age is the lifter's peak age for that lift.
- **Alternatives:** (a) population-level quadratic regression - fit `rel_strength ~ Age + Age²` per (Sex × Lift) group, find argmax; (b) both.
- **Why this:**
  - Falls naturally from the dedup decision: "keep one row per lifter at their best meet" gives you the peak age directly with no extra modelling.
  - Gives clean within-lifter triplets that the Friedman test consumes natively.
  - The quadratic regression alternative is more sophisticated but requires defending a polynomial functional form (the quadratic is almost certainly wrong in detail), and disconnects "peak age" from any individual lifter (it's a derived parameter, not an observation).
  - Per-lifter empirical is the standard sports-science approach.
- **Short answer:** *"Per-lifter empirical peak - for each lifter we kept the meet at their best relative strength - because it falls naturally from our dedup and gives clean within-subject triplets for Friedman."*

---

## Sex handling

### 9. Keep `Mx` in the cohort; exclude only from H2

- **Choice:** Mx lifters survive the cohort filter and appear in H1's Friedman analysis. The H2 Mann-Whitney filter excludes them.
- **Alternatives:** (a) drop Mx from the cohort entirely; (b) include Mx as a third sex category in H2.
- **Why this:** H2's hypothesis specifically names *male* and *female*. Mx is too small (74 lifters in the final wide table) to support a sex-level inference on its own. But H1 doesn't depend on sex - including Mx in H1 gives the strongest possible sample. Excluding Mx only at the H2 step is more honest than pretending they weren't in the data at all.
- **Short answer:** *"Mx stays in the cohort because H1 doesn't depend on sex; we exclude them only from H2 because the sample (74 lifters) is too small for sex-level inference."*

---

## Statistical tests

### 10. H1 test: Friedman + pairwise Wilcoxon, Bonferroni-corrected

- **Choice:** Friedman test on the within-lifter triplet for the overall H₀; three pairwise Wilcoxon signed-rank tests as post-hoc; Bonferroni at α/3.
- **Alternatives:** (a) repeated-measures ANOVA + paired t-tests (parametric); (b) Friedman only, no post-hoc.
- **Why this:**
  - Peak-age distributions are right-skewed (long tail of older masters lifters). RM-ANOVA assumes normality and sphericity, both uncomfortable here.
  - Friedman ranks each subject's three values and tests whether the rank distributions differ - the correct non-parametric within-subject analogue of ANOVA.
  - Pairwise Wilcoxon tells us *which* lifts differ from which (the overall Friedman only tells us *something* differs). The H1 prediction was directional ("deadlift latest, bench earliest"), and the post-hoc is what evaluates that.
  - Bonferroni is the conservative one-line default; given three tests, multiply each p by 3.
- **Short answer:** *"Friedman because peak ages are right-skewed and non-parametric is safer than RM-ANOVA, paired Wilcoxon for the pairwise contrasts, Bonferroni because it's the conservative default for three tests."*

### 11. H2 test: Mann-Whitney U per lift, Bonferroni-corrected

- **Choice:** three independent two-sample Mann-Whitney U tests (one per lift) comparing M vs F peak ages. Bonferroni at α/3.
- **Alternatives:** (a) OLS regression `peak_age ~ Sex + Equipment` per lift (covariate-adjusted); (b) Welch's t-test (parametric).
- **Why this:**
  - Matches the non-parametric approach used in H1.
  - No covariate adjustment because that would require defending a linearity assumption *and* a covariate-selection choice. The Equipment-confounding concern is handled in the writeup's caveats instead.
  - The simpler test is more honest about what we know and don't know. Adding regression machinery without a strong prior reason looks like over-engineering.
- **Short answer:** *"Mann-Whitney because it's the non-parametric analogue matching H1, three tests (one per lift), Bonferroni-corrected, no covariate adjustment to keep the test as simple as possible."*

### 12. Multiple-testing correction: Bonferroni

- **Choice:** within each family (H1 post-hocs, H2 per-lift tests), multiply each p by the number of tests in the family (3), cap at 1.
- **Alternatives:** Holm-Bonferroni (sequential step-down); none.
- **Why this:**
  - Bonferroni is the most conservative standard correction and the easiest to motivate in one sentence ("we ran three tests, we adjusted each p by a factor of three").
  - Holm is slightly more powerful but harder to motivate compactly.
  - At our sample size every test was significant by orders of magnitude (p ≪ 10⁻³⁰⁰), so the correction choice is moot in practice - choosing the strictest looks honest.
- **Short answer:** *"Bonferroni because it's conservative and standard; at our N every test was significant at p ≪ 10⁻³⁰⁰ regardless of which correction we used."*

---

## Practical / infrastructure

### 13. Intermediate files: CSV, not parquet

- **Choice:** save `cohort_filtered.csv` and `peaks_wide.csv` in CSV.
- **Alternative:** parquet (faster I/O, smaller files).
- **Why this:** CSV doesn't need `pyarrow` in the dependency list. Keeping `requirements.txt` to the five core analysis libraries (pandas, numpy, matplotlib, scipy, statsmodels) means anyone reproducing the analysis installs exactly five things. Slower I/O for a project this small is a non-issue.
- **Short answer:** *"CSV to keep the dependency list minimal - parquet would need pyarrow, which we didn't want to add for a small project."*

### 14. Plain `.py` scripts, not Jupyter notebooks

- **Choice:** every "notebook" in `notebooks/` is a `.py` script with `# %%` cell-marker comments.
- **Alternative:** Jupyter `.ipynb` notebooks.
- **Why this:**
  - `.ipynb` files are JSON with embedded execution counts and outputs - they diff badly in Git.
  - Plain Python runs from the terminal in one command; no Jupyter, no kernel-selection, no extension setup.
  - The `# %%` markers still let editors like VSCode treat them as cells if you want interactive execution.
- **Short answer:** *"Plain Python scripts because they diff cleanly in Git, don't need Jupyter infrastructure, and run from the terminal in one command."*

---

## Limitations to be honest about

These are the things to mention *unprompted* if a grader asks about weaknesses.

### 15. Single-meet lifters dominate the marginal distributions

After cohort filtering, many lifters have only one meet in the cohort. For those lifters, all three peak ages collapse to the same value (the age at their only meet). They contribute zero within-lifter variance to the Friedman test, so the test still works correctly - but the *marginal* per-lift median peak ages look identical because so many triplets are all-equal. This is why the H2 medians come out to exactly (M = 23.5, F = 26.0) for all three lifts.

A sensitivity analysis restricted to lifters with ≥ 3 cohort meets would address this directly. It's not currently in the pipeline.

### 16. The sex effect could be a sampling artefact

Women's competitive powerlifting expanded mainly in the 2010s-2020s. Women in OPL are on average newer to the sport than men, with shorter competitive careers. "Peak in observed competitive data" is biased toward later ages for lifters who started competing later - because the data simply doesn't include their younger years. The 2.5-year M-F difference is real in the data; we cannot distinguish how much is physiology vs sampling era using OPL alone.

### 17. Age missingness is large (37% in raw, 43.6% effective in cohort chain)

OPL records lifts more reliably than ages. Lifters with unrecorded ages are excluded from our cohort by necessity. If unrecorded-age lifters peak systematically differently from recorded-age lifters, our estimates are biased - and we have no way to test this within OPL.

### 18. Equipment is not adjusted for in H2

If men and women use systematically different equipment distributions, the M-F peak-age difference is partly an Equipment difference. We did not include Equipment as a covariate in the H2 test (we chose simpler Mann-Whitney over OLS regression). The natural follow-up analysis would be per-lift OLS regressions of `peak_age ~ Sex + Equipment`.

---

## Likely grader questions, ranked

1. *"Why did you choose lift/BW over allometric scaling?"* → §7.
2. *"Why drop 43.6% of rows in the age filter? That's huge."* → §4 (significant because Age is the DV; the loss is real but unavoidable).
3. *"H1's effect size is tiny - should you really have rejected H₀?"* → §15 + the writeup's "practical null" framing. With N this large the test detects vanishing effects; we report the median differences as the interpretable effect size.
4. *"The H2 medians are identical across all three lifts - doesn't that look suspicious?"* → §15. Single-meet lifters collapse all three peak ages to the same value, flattening the marginals.
5. *"Did you adjust for Equipment in H2?"* → §18. No, we chose simpler Mann-Whitney. Equipment-confounding is acknowledged as a limitation.
6. *"Why Bonferroni instead of Holm?"* → §12. Conservative is the safer rhetorical position; at our N the correction choice doesn't matter.
7. *"Why exclude Mx from H2 but keep them in the cohort?"* → §9.
8. *"Why didn't you use a mixed-effects model on the un-deduped data?"* → §8. Per-lifter empirical peak was chosen for simplicity and direct interpretability; mixed-effects would be overkill for this rubric.
