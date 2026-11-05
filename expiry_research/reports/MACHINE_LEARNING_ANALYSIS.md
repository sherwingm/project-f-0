# Machine-learning analysis (module `model`, Agent 4)

Scripts: `scripts/model_walkforward.py` (models, baselines, metrics, permutation importance),
`scripts/model_vixbase.py` (VIX-only baseline, added in the resumed run), `scripts/model_tables.py` (tables).
Outputs: `results/model/wf_metrics.csv`, `wf_folds.csv`, `wf_calibration.csv`, `wf_perm_importance.csv`,
`wf_primary.csv`, `wf_vix_baseline.csv`, `tab_wf_*.csv`, `predictions_*.csv`. Method of the folds:
`WALK_FORWARD_VALIDATION.md`.

**Resumed run.** The walk-forward of the first run stopped on a usage limit before writing its metric files; it was
re-run end to end with the same fixed settings (`walkforward_stdout.txt`, 1,496 s). The frozen rule file was not
touched.

## Set-up (fixed before running; nothing tuned on a test fold)
| Model | Settings |
|---|---|
| Logistic L2 (**primary**) / ridge for continuous targets | standardised, C = 0.1 / alpha = 10, median imputation |
| Decision tree | depth 3, min leaf 40 |
| Random forest | 300 trees, depth 5, min leaf 20, sqrt features |
| HistGradientBoosting | depth 3, lr 0.05, 200 iterations, min leaf 30, L2 1.0 (absolute-error loss for regression) |
| Expiry-only twins | logistic and tree trained on expiry-day rows only (`logit_D0`, `tree_D0`) |
| lightgbm | not installed, not used |

Features: 62 at D2 / TCLOSE, 79 at T1515 (stationary price, volatility, futures and option-chain features of the
decision row, close-known outcomes of t where allowed, calendar of the target session). Baselines: training base
rate, always-majority, previous-gap sign, persistence (same outcome of the last session known at the cutoff),
VIX-only logistic; for regression the training median and persistence.

Selection rule, stated before the run: no model is chosen on the test folds; the logistic / ridge is the primary
model; a target is "predictable" only if the primary model's pooled AUC CI low > 0.5 and its Brier is below the
base-rate Brier with one-sided block-bootstrap p < 0.05 (regression: MAE below the median, p < 0.05). The other
models are shown for comparison only.

## 1. Primary model vs baselines
Predictable by the rule (`wf_primary.csv`, `tab_wf_primary_binary.csv`, `tab_wf_primary_reg.csv`):

| Target | NIFTY all / D0 | BANKNIFTY all / D0 |
|---|---|---|
| gap up, ret15/30/60 up, oc up, gap filled (all cutoffs) | no / no | no / no |
| big excursion ≥ 1 % | D2, TCLOSE, T1515 / D2, TCLOSE | D2, TCLOSE, T1515 / D2, TCLOSE |
| |cc| ≥ 1 % | D2, TCLOSE, T1515 / no | D2, TCLOSE / D2, TCLOSE |
| |gap| | no / D2 only (MAE ratio 0.914) | no / no |
| high / low vs prev close | no / no | no / no |

## 2. All models side by side (comparison, not selection)
AUC on all test rows, TCLOSE cutoff (`tab_wf_auc_all_models.csv`):

| UL | Target | logit | tree | forest | boosting | VIX only |
|---|---|---|---|---|---|---|
| NIFTY | gap up | 0.528 | 0.509 | 0.499 | 0.514 | 0.479 |
| NIFTY | oc up | 0.521 | 0.476 | 0.517 | 0.524 | 0.497 |
| NIFTY | gap filled | 0.555 | 0.496 | 0.558 | 0.547 | 0.462 |
| NIFTY | big excursion | 0.741 | 0.637 | 0.734 | 0.691 | 0.766 |
| NIFTY | |cc| ≥ 1 % | 0.644 | 0.610 | 0.697 | 0.628 | 0.724 |
| BANKNIFTY | gap up | 0.522 | 0.514 | 0.516 | 0.504 | 0.502 |
| BANKNIFTY | oc up | 0.504 | 0.517 | 0.480 | 0.491 | 0.484 |
| BANKNIFTY | gap filled | 0.565 | 0.511 | 0.536 | 0.563 | 0.454 |
| BANKNIFTY | big excursion | 0.794 | 0.727 | 0.781 | 0.768 | 0.776 |
| BANKNIFTY | |cc| ≥ 1 % | 0.702 | 0.657 | 0.690 | 0.683 | 0.708 |

- Non-linear models do not find direction either: forest and boosting AUC for gap / oc / first-hour direction lie in
  0.44-0.56 at every cutoff.
- For big moves the single VIX feature is as good as any model. More features add noise, not information.
- Forest Brier skill is near 0 on direction targets (it shrinks to the base rate); logistic and boosting are negative
  (they over-fit noise) (`tab_wf_bss_all_models.csv`).
- Expiry-only models are worse than all-days models evaluated on the same expiry rows (e.g. BANKNIFTY TCLOSE big
  excursion: 0.702 vs 0.727), as expected with 4x fewer training rows.
- Regression (MAE / median forecast, `tab_wf_maeratio_all_models.csv`): forest 0.90-0.93 and boosting 0.92-0.94 for
  |gap| at D2 / TCLOSE; high vs prev close 0.92-0.98; low vs prev close ≈ 1.0. Ridge 0.97-1.12 (it fits the mean of a
  skewed variable).

## 3. Calibration and thresholds
- Big excursion, TCLOSE (`wf_calibration.csv`, 5 quantile bins): NIFTY predicted 0.13 / 0.23 / 0.36 / 0.54 / 0.84,
  observed 0.21 / 0.29 / 0.33 / 0.53 / 0.80 (ECE 0.047); BANKNIFTY ECE 0.048. Usable as probabilities.
- Gap up, TCLOSE: predicted 0.54 → 0.84 across bins but observed 0.62 / 0.72 / 0.66 / 0.66 / 0.73 (NIFTY) — no
  slope: the model's spread is noise.
- Precision when the logistic's probability is above its training-period 67th percentile (`tab_wf_precision.csv`):
  big excursion NIFTY 0.700 vs base 0.431 (383 calls, recall 0.56); BANKNIFTY 0.893 vs 0.645 (456 calls). Gap up:
  NIFTY 0.704 vs 0.678, BANKNIFTY 0.662 vs 0.635 — no lift worth the name.

## 4. Permutation importance (test folds)
For the predictable targets (`tab_wf_perm_top.csv`, logistic, AUC drop): the top features are straddle per √day,
VIX level / VIX 1-year percentile, distance below the 20-day high, 10-day realised vol, 5-10 day momentum, and
`c_days_to_session` (calendar days to the target session: a weekend or holiday in between means a bigger move). The
same volatility family as in `FEATURE_DISCOVERY.md`. Option-positioning features (max pain, call wall, PCR) appear
with small importance (≤ 0.025 AUC) and are not stable across cutoffs.

## 5. Multiple testing
Walk-forward model-vs-base tests (792) and VIX-baseline tests (96) were added to the module's single hypothesis log
`hypotheses.csv` (29,639 tests in all; BH at 10 % over the whole log, column `q_bh_all`). Significant: 103 of 792
walk-forward tests (all on big-move and magnitude targets plus one NIFTY T1515 expiry-day gap-fill forest, n = 78),
4 of 96 VIX-baseline tests (full model AUC > VIX-only AUC: gap filled NIFTY TCLOSE / T1515 and BANKNIFTY TCLOSE, gap
up NIFTY TCLOSE, q 0.08). Those four are rank-only: their Brier skill is negative, and VIX-only AUC is below 0.5
there (VIX is inversely related to gap fill), so beating it is not evidence of a usable model.

## Findings
| id | finding | n | effect | CI / p | label |
|---|---|---|---|---|---|
| ML1 | No model predicts next-session direction (gap, 15/30/60 min, oc) | 1108 / 366 test rows per UL-cutoff | AUC 0.44-0.56 | no CI clear of 0.5 with positive Brier skill | Rejected |
| ML2 | Logistic predicts big excursion, TCLOSE, NIFTY / BANKNIFTY | 1108 | AUC 0.741 / 0.794 | 0.702-0.775 / 0.762-0.826 | Observed (walk-forward, predictable by rule) |
| ML3 | VIX-only logistic equals the full model for big moves | 24 rows | AUC diff -0.17 .. +0.03 | none BH-significant | Observed |
| ML4 | Forest / boosting beat the median for |gap| | 1108 | MAE -6 .. -10 % | p < 0.001 | Observed (not primary) |
| ML5 | Gap fill: AUC > 0.5 but Brier worse than base | 1108 | AUC 0.555 / 0.565 | Brier skill -0.04 / -0.02 | Rejected |
| ML6 | Expiry-only training helps | 235 D0 rows | worse than all-days models | — | Rejected |

## What this does NOT show
- It does not show that any model makes money: no option or futures P&L was computed.
- It does not show that a better-tuned model would fail; hyper-parameters were fixed and not searched (by design, to
  avoid tuning on the test folds).
- Walk-forward stays inside 2018-2024-06; the sealed final period is untouched.
- The minute-era results (T1515 and first-15/30/60 targets) rest on two test years and ~300 training rows.
