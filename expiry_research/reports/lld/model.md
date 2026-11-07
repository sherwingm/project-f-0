# LLD: next-session prediction, feature discovery and machine learning (module `model`)

Written 2026-11-05, before any code of this module. Agent 4 of the research stage; independent of the other agents
and of S1 / S2 / S3. Code: `scripts/model_common.py`, `scripts/model_discovery.py`, `scripts/model_validate.py`,
`scripts/model_walkforward.py`, `scripts/model_finalize.py`; tests `tests/test_model.py`; outputs `results/model/`.
Reports: `NEXT_SESSION_PREDICTION.md`, `FEATURE_DISCOVERY.md`, `MACHINE_LEARNING_ANALYSIS.md`,
`WALK_FORWARD_VALIDATION.md`.

## Inputs
Only `panel_io.load_panel(ul)` for NIFTY and BANKNIFTY (t <= 2024-06-28). Nothing from `data/sealed/`,
`results/verify/`, other agents' folders, S1/S2/S3. No raw store reads (the panel already holds every needed value).
SENSEX: its open panel has no expiry tags (first stored SENSEX expiry 2024-10-04, sealed period), so every SENSEX
expiry question is **Untestable** here; SENSEX is not modelled.

## Frames: one row per target session s (= t+1), built per (underlying, cutoff)
Row t of the panel describes session t; its `y_` columns describe s = t+1.
| Cutoff | Decision time | Features used |
|---|---|---|
| `TCLOSE` | close of t (= D-1 when s is the expiry) | `f_` of t; close-known `o_` of t; calendar of s |
| `D2` | close of t-1 (two sessions before s) | `f_` and `o_` of t-1 (prefix `l1_`); calendar of s |
| `T1515` | 15:15 of t | `f1515_` of t; open-known `o_` of t (`o_gap_pct`, `o_ret15/30/60`); `f_` and `o_` of t-1 (prefix `l1_`); calendar of s |

- Never used at T1515: `o_cc, o_oc, o_range_pct, o_max_exc, o_last_hour, o_rv, o_high_min, o_low_min, o_gap_filled,
  o_high_vs_prevclose, o_low_vs_prevclose, o_big_move_*` of t, and any `f_` of t (needs the close / bhavcopy of t).
- `y_` columns are labels only; no `y_` column is ever a feature (test).
- Calendar of s = the `cal_next_*` columns of row t (published in advance; for D2 this assumes the expiry was listed by
  t-1 — weeklies are listed weeks ahead, so this changes nothing in practice).
- Derived same-row features (from columns of the same decision row only): `d_absgap = |o_gap_pct|`,
  `d_absmom1 = |f_mom1|`, `d_opt_near_netoichg = (pe_oi_chg - ce_oi_chg) / (ce_oi + pe_oi)`,
  `d_opt_near_straddle_daily = straddle_pct / sqrt(max(dte, 1))`, `d_opt_near_atmvol_ratio = atm_pe_vol / atm_ce_vol`.
- Level features that drift with the index (raw OI, strikes, prices) are excluded; ratios and % distances are kept.
- Rows dropped: s missing, or `cal_special_between` (a Muhurat session inside the gap).
- Split by the date of s: discovery s <= 2022-12-31, validation 2023-01-01 .. 2024-06-30. So no label crosses a split.
- Minute-dependent items (`T1515` features, `y_ret15/30/60`) exist only from 2021-10-20 (discovery ≈ 300 rows).

## Targets (labels of s)
| Target | Type | Definition |
|---|---|---|
| `gap_up` | binary | `y_gap_pct > 0` (rows with gap exactly 0 dropped) |
| `ret15_up`, `ret30_up`, `ret60_up` | binary | `y_ret15/30/60 > 0` (minute days) |
| `oc_up` | binary | `y_oc > 0` (intraday trend) |
| `gap_filled` | binary | `y_gap_filled` (fill vs continuation) |
| `big_exc` | binary | `y_max_exc >= 1 %` |
| `big_cc` | binary | `|y_cc| >= 1 %` |
| `gap_abs` | continuous | `|y_gap_pct|` (gap magnitude) |
| `high_pc`, `low_pc` | continuous | `y_high_vs_prevclose`, `y_low_vs_prevclose` |

## Expiry context of s (tags)
`all`; `D0` (s is an expiry), `D0w` (weekly), `D0m` (monthly); `Dm1..Dm5` (s is 1..5 sessions before its next
expiry); `Dp1` (first session after an expiry, s not itself an expiry); `nonexp`; weekday of s (Mon..Fri).
Weekday regime of s: NIFTY `2018 monthly-only` / `Thu weekly` (from 2019-02-14); BANKNIFTY `Thu` (to 2023-09-01),
`Wed weekly + Thu monthly` (2023-09-04 .. 2024-02-29), `Wed` (2024-03-01 ..). In NIFTY's open period every expiry
is a Thursday (or the session before a holiday), so "s is an expiry" and "s is a Thursday" are nearly the same set.

## Stage 1: discovery (`model_discovery.py`, discovery rows only)
1. Context profile: for each target and context, rate (or mean) of the context vs the all-days rate of discovery.
2. Univariate: thresholds = discovery terciles (q33, q67) of the feature on all-days rows of that frame; rules
   `x <= q33` and `x >= q67` (booleans: `== 1`, `== 0`); contexts `all`, `D0`, `D0m`.
3. Pairs: per (UL, cutoff, target, context in {all, D0}) the 6 features with the smallest univariate p; every pair,
   median splits, 4 quadrants.
4. Honest trees: depth <= 3, `min_samples_leaf = max(20, 8 % of fit rows)`, fitted on the first 60 % of the discovery
   rows (by date), each leaf tested on the last 40 % (binary targets; contexts `all`, `D0`). The leaf statistics and p
   come from the held-out 40 %.
- Test: binary = exact binomial vs the base rate of the same rows (context rows with the feature present);
  continuous = one-sample t-test of the condition mean vs the base mean. Effect = rate - base (or mean - base).
- Every test goes into `results/model/hypotheses.csv`. BH (FDR 10 %) over all discovery-stage tests = the
  discovery family (size stated). n < 30 flagged.
- Freeze (`candidates_frozen.csv`, written before any validation statistic exists): discovery tests with BH q < 0.10
  and n >= 30; per (UL, cutoff, target, context) at most 3, ranked by p (ties: simpler rule first). The file holds the
  exact rule (JSON thresholds), decision time, target, direction, discovery n / rate / base / effect / p / q.

## Stage 2: validation (`model_validate.py`, once, frozen candidates only)
- Same rule, same thresholds, validation rows of the same context. Pass rule (fixed now): same sign as discovery,
  one-sided p < 0.05 vs the validation base rate of the same rows (binomial; continuous: one-sample t), effect >= half
  the discovery effect, and validation n >= 20 (n < 20 → stays Suggestive, "not testable in validation").
- The script refuses to run if `candidates_frozen.csv` is missing and records its SHA-256 in the output.
- Robustness on discovery + validation (reported, not used to pass): drop the best 1 % of the condition's outcomes
  (favourable side of the continuous source of the target; `gap_filled` has none); effect per year; per weekday
  regime; per VIX tercile (discovery terciles of the VIX close known at the decision time); neighbouring thresholds
  (each threshold moved to its discovery quantile ± 0.05).
- Labels: Passed-validation / Rejected / Suggestive (validation n < 20). Nothing is called Validated.

## Stage 3: walk-forward ML (`model_walkforward.py`, discovery + validation)
- Folds by calendar year of s, expanding window: train on all years before Y, test Y, for Y = 2020, 2021, 2022, 2023,
  2024 (Jan-Jun). Minute targets and the T1515 cutoff start 2021-10-20: test years 2023 and 2024 only.
  Purge: the last training session before each test year is dropped. No shuffling anywhere.
- Fold features: drop columns with > 30 % missing or constant in the training fold; median imputation fitted on the
  training fold (HGB uses NaN natively).
- Models, fixed hyper-parameters (no tuning on any test fold):
  logistic L2 (standardized, C = 0.1); decision tree (depth 3, min leaf 40); random forest (300 trees, depth 5,
  min leaf 20, sqrt features); HistGradientBoosting (depth 3, lr 0.05, 200 iterations, min leaf 30, L2 1.0).
  Regression twins: ridge (alpha 10), tree, forest, HGB (absolute-error loss). lightgbm is not installed: not used.
- Training sets: `all` days (all four models) and `D0` only (logistic + tree; small n).
- Baselines: base rate (training-fold rate as the probability), always-majority (training majority), previous-gap
  sign (sign of the last known gap: t at TCLOSE / T1515, t-1 at D2), persistence (the same outcome of the last fully
  known session: e.g. `o_oc` of t at TCLOSE, of t-1 at D2 / T1515; `o_ret15` and `o_gap_pct` of t at T1515);
  regression: training median (naive) and persistence.
- Metrics, pooled over test folds and per fold, on all test rows and on expiry rows (D0, D0w, D0m): accuracy vs
  majority, balanced accuracy, AUC with a moving-block bootstrap 95 % CI (block 5, 1000 reps), Brier vs base-rate
  Brier (skill score and one-sided bootstrap p), log-loss, calibration (5 quantile bins, ECE), precision / recall at
  0.5 and at the training-fold 67th percentile of fitted probabilities. Regression: MAE vs naive and persistence
  (ratio, bootstrap p).
- Selection rule, stated before running: no model is chosen on the test folds. The **primary model is the logistic
  regression** (ridge for regression targets). A target counts as "predictable beyond baseline" at a cutoff only if
  the primary model's pooled AUC CI lower bound > 0.5 **and** its Brier is below the base-rate Brier with one-sided
  bootstrap p < 0.05 (regression: MAE below naive, p < 0.05). The other models are reported for comparison.
- Permutation importance on the test folds (logistic and HGB, all-days training, 5 repeats, AUC / MAE drop),
  averaged over folds weighted by fold size.
- Per-session prediction files `results/model/predictions_<UL>_<target>_<cutoff>.csv` (every test-fold row, with
  expiry tags, fold, truth, baselines and each model's prediction); expiry rows are flagged (`is_expiry`, `kind`).
- Walk-forward tests (one p per UL x cutoff x target x model x training set x eval subset) are logged in
  `hypotheses.csv` (stage `walkforward`); `model_finalize.py` adds BH over the whole log (`q_bh_all`).

## Tests (`tests/test_model.py`)
No `y_` or forbidden `o_` column in any feature set; T1515 features contain no `f_` of t; D2 features equal row t-1;
target equals the next row's outcome; folds are chronological, disjoint and purged; the frozen file exists and its
hash matches the one recorded by validation; no frame row has a target date >= 2024-07-01.

## Addendum (resumed run, 2026-11-05, written before the added code was run)
The first run stopped on a usage limit inside the walk-forward. Discovery, freeze and validation were complete and
are not re-run; `candidates_frozen.csv` keeps SHA-256 `9b9490…aa4d`. Added:
- `model_vixbase.py`: VIX-only logistic baseline (VIX known at the cutoff), same folds / purge / rows as the
  walk-forward; AUC difference vs the primary model with block-bootstrap one-sided p. Its tests join the hypothesis
  log as stage `wf_vixbase`. It does not change the pre-stated "predictable" rule; it is reported next to it.
- `model_tables.py`: report tables only (no new tests), incl. per-regime AUC of the primary model.
- Three more checks in `tests/test_model.py` (pass rule applied as fixed; primary model fixed; BH over the log).
