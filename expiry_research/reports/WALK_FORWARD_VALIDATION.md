# Walk-forward validation (module `model`, Agent 4)

Scope: chronological walk-forward **inside discovery + validation only** (target sessions 2018-01 .. 2024-06). The
coordinator adds the final-period section later; nothing here touches `data/sealed/` or `results/verify/`.
Scripts: `scripts/model_walkforward.py`, `scripts/model_vixbase.py`; checks in `tests/test_model.py` (10 tests pass).

**Resumed run.** The first run's walk-forward was cut off by a usage limit (it had reached BANKNIFTY T1515
first-hour). It was re-run from the start with identical fixed settings; `walkforward_stdout.txt` ends with
`done 1496s`. The VIX-only baseline was added after the resume and before its result was seen.

## Design
| Item | Choice |
|---|---|
| Folds | expanding window by calendar year of the target session: train on all years < Y, test on Y |
| Test years | 2020, 2021, 2022, 2023, 2024 (Jan-Jun); minute targets and T1515: 2023, 2024 only (minute data from 2021-10) |
| Purge | the last training session before each test year is dropped (its label is the first test session's neighbour) |
| Shuffling | none, anywhere |
| Preprocessing | fitted on the training fold only: column filter (> 30 % missing or constant), median imputation, scaling |
| Hyper-parameters | fixed in the LLD, not searched |
| Primary model | logistic L2 / ridge, chosen before running |
| Uncertainty | moving-block bootstrap of the pooled test rows (block 5 sessions, 1,000 reps) |

Training rows per fold (NIFTY TCLOSE gap up): 486 (test 2020), 736, 982, 1,228, 1,473 (test 2024). T1515: 291
(test 2023), 536 (test 2024). Checks (`tests/test_model.py`): every test row's year equals its fold; `n_train` equals
the count of earlier rows minus one (purge); no target date ≥ 2024-07-01; no `y_` column or close-dependent `o_` column
in any feature set; T1515 features contain nothing from the close of D-1; D2 features equal the previous row.

## Stability across folds (primary model)
AUC per test year, TCLOSE (`tab_wf_fold_primary.csv`):

| UL | Target | 2020 | 2021 | 2022 | 2023 | 2024 H1 |
|---|---|---|---|---|---|---|
| NIFTY | big excursion | 0.750 | 0.757 | 0.721 | 0.662 | 0.654 |
| NIFTY | |cc| ≥ 1 % | 0.681 | 0.602 | 0.656 | 0.624 | 0.628 |
| NIFTY | gap up | 0.454 | 0.546 | 0.559 | 0.600 | 0.490 |
| NIFTY | oc up | 0.446 | 0.557 | 0.535 | 0.599 | 0.554 |
| BANKNIFTY | big excursion | 0.862 | 0.712 | 0.771 | 0.598 | 0.580 |
| BANKNIFTY | |cc| ≥ 1 % | 0.705 | 0.598 | 0.655 | 0.573 | 0.566 |
| BANKNIFTY | gap up | 0.400 | 0.562 | 0.545 | 0.530 | 0.528 |
| BANKNIFTY | oc up | 0.478 | 0.584 | 0.493 | 0.544 | 0.490 |

- Big-move AUC is above 0.5 in every year for both indices, but falls in 2023-24 (the validation years): with VIX
  low and range-bound, there is less volatility variation to rank.
- Direction AUC swings around 0.5 from year to year (0.40-0.60), the signature of noise. A single good year (NIFTY
  gap up 2023, 0.600) is not followed by a good next year (2024: 0.490).
- Regression (MAE / median, primary ridge, D2 and TCLOSE) gets worse over time: |gap| 0.84-0.93 in 2020, 1.21-1.40 in 2024. The
  2023-24 gaps were smaller than any earlier training period.

## Walk-forward of the frozen rules
The frozen rules were tested once on validation (2023-01 .. 2024-06) with the pass rule fixed in advance; that is
the module's out-of-sample step for rules. 9 of 241 passed (`candidates_validation.csv`; listed in
`FEATURE_DISCOVERY.md`). Their effect per calendar year on discovery + validation (`robustness_groups.csv`): the six
NIFTY rules have the same sign in all 7 years and both weekday regimes; M073 (BANKNIFTY expiry days) in 6 of 6 years
with n ≥ 10; M006 (BANKNIFTY T1515) has a negative 2021 and a negative Wednesday-regime cell (n = 9).

Of the 9, six also stay significant when BH is applied over the module's whole 29,639-test log
(M134, M135, M143, M218, M219, M220; `hypotheses.csv`, stage `validation`, `q_bh_all`); M006, M073 and M118 do not.

## Per weekday regime
NIFTY's discovery + validation rows are one weekly regime (Thursday) plus 2018 monthly-only; BANKNIFTY's validation
contains the Thursday, Wednesday-weekly + Thursday-monthly (2023-09 .. 2024-02) and Wednesday (2024-03 ..) regimes.
BANKNIFTY logistic AUC by regime, TCLOSE, pooled test rows (`tab_wf_regime_auc.csv`):

| Target | Thu, non-exp (716) | Thu, expiry (192) | Wed-weekly+Thu-monthly, non-exp / exp (96 / 26) | Wed, non-exp / exp (61 / 17) |
|---|---|---|---|---|
| big excursion | 0.825 | 0.733 | 0.644 / 0.429 | 0.542 / 0.611 |
| gap up | 0.520 | 0.476 | 0.505 / 0.643 | 0.477 / 0.600 |

The big-move signal is strong in the long Thursday regime and weak in the short Wednesday regimes (which are also the
calm 2023-24 period, so regime and volatility level cannot be separated). The Wednesday expiry cells have n = 17-26:
too small to read (flag n < 30). Direction stays near 0.5 in the large cells.
BANKNIFTY weeklies end 2024-11-13 (sealed period); SENSEX expiries (from 2024-10) are **Untestable** here.

## What the coordinator receives
- `candidates_frozen.csv` (241 rules, SHA-256 `9b9490102276daaedde3519c7e55cbdde55088cacc4085d111c05670fe75aa4d`)
  and `candidates_validation.csv` (labels). Only the 9 Passed-validation rules are eligible for the single final test.
- The fixed walk-forward models (settings above) can be re-fitted on all data ≤ 2024-06 and scored once on the final
  period; the pre-stated rule (primary logistic, AUC CI low > 0.5 and Brier p < 0.05) and the VIX-only comparison
  should be kept unchanged.

## Findings
| id | finding | n | effect | CI / p | label |
|---|---|---|---|---|---|
| WF1 | Big-move AUC > 0.5 in every fold, both indices | 5 folds x 2 UL | 0.57-0.86 | per-fold, falling in 2023-24 | Observed |
| WF2 | Direction AUC per fold oscillates around 0.5 | 5 folds x 2 UL | 0.40-0.60 | — | Rejected (noise) |
| WF3 | |gap| ridge forecast worsens out of sample over time | 1108 | MAE ratio 0.84-0.93 → 1.21-1.40 | — | Observed |
| WF4 | 6 of 9 passed rules survive whole-log BH | 20-120 val rows | — | q < 0.1 | Passed-validation |
| WF5 | BANKNIFTY Wednesday-regime expiry cells | 17-26 | AUC 0.43-0.64 | n < 30 | Untestable (too small) |

## What this does NOT show
- It is not a test on the final period; nothing is Validated.
- It does not show trading profit; only forecast quality.
- With two test years, the minute-era results (T1515, first 15/30/60 min) are weak either way.

## Final out-of-sample (opened once, 2026-11-05)
Coordinator step, module `final`. Design `reports/lld/final.md` (written before the seal was opened). Code
`scripts/final_test.py` (gate) and `scripts/final_extras.py` (Observed extras, reads only the flags files).
Outputs in `results/final/`. Plan followed as written in `FINAL_TEST_PLAN.md`; no threshold, window or rule changed.

Final period: target sessions 2024-07-01 → 2026-10-29 (about 574 usable rows per index). The sealed panels were
read only by `final_test.py` via `load_sealed_final(ul, coordinator=True)`.

### Same code path (checked before any final number)
- Features rebuilt with each module's own functions (pricepath `build_features`; optionchain `build` and
  `context_frame`; model `build_frame` + `rows_for`). Only the period cut-offs in their source were lifted;
  nothing else in their code changed.
- 85 of 85 checks pass (`code_path_checks.csv`): every rule feature and target equals the module's own value on
  all 366 validation rows (zero differences). The final-test code also reproduces every candidate's validation
  n, k and base from its module's validation CSV exactly. (The first run stopped here once: the 2024-06-28 edge
  label is blank in the open file by design; that row was then left out of the label check.)

### Result per candidate (`final_results.csv`)
Rate = share of flagged sessions with the target (M218 / M220: mean low of t+1 vs previous close, %).
Gate: same sign, one-sided p < 0.05, effect ≥ half the discovery effect, then BH 10 % over the 13.

| Id | UL | n flag | Rate | Base | Effect | Disc. effect | p | BH q | Label |
|---|---|---|---|---|---|---|---|---|---|
| PPC032 | NIFTY | 117 | 46.2 % | 31.0 % | +15.1 pp | +25.5 | 0.0004 | 0.0005 | Validated (size) |
| PPC062 | NIFTY | 76 | 21.1 % | 31.0 % | −9.96 pp | −12.4 | 0.037 | 0.040 | Validated (size) |
| PPC092 | BANK | 76 | 69.7 % | 39.7 % | +30.0 pp | +18.4 | <1e-4 | <1e-4 | Validated (size) |
| PPC098 | BANK | 72 | 77.8 % | 39.7 % | +38.1 pp | +16.7 | <1e-4 | <1e-4 | Validated (size) |
| PPC129 | BANK | 117 | 47.0 % | 39.7 % | +7.3 pp | +9.2 | 0.066 | 0.066 | Rejected (p) |
| OC08 | BANK | 302 | 36.8 % | 24.9 % | +11.8 pp | +24.0 | <1e-4 | <1e-4 | Rejected (< half) |
| OC13 | NIFTY | 280 | 44.6 % | 33.6 % | +11.0 pp | +20.3 | 0.0001 | 0.0002 | Validated (size) |
| OC17 | NIFTY | 281 | 48.0 % | 33.6 % | +14.4 pp | +19.3 | <1e-4 | <1e-4 | Validated (size) |
| OC21 | NIFTY | 280 | 41.4 % | 30.8 % | +10.6 pp | +17.6 | 0.0001 | 0.0002 | Validated (size) |
| OC118 | BANK | 123 | 32.5 % | 24.3 % | +8.2 pp | +8.6 | 0.024 | 0.028 | Validated (size) |
| M143 | NIFTY | 71 | 66.2 % | 30.7 % | +35.5 pp | +25.4 | <1e-4 | <1e-4 | Validated (size) |
| M218 | NIFTY | 138 | −0.32 % | −0.48 % | +0.16 | +0.21 | 0.0001 | 0.0001 | Validated (size) |
| M220 | NIFTY | 126 | −0.33 % | −0.48 % | +0.15 | +0.22 | 0.0003 | 0.0004 | Validated (size) |

11 of 13 are **Validated (size)**; PPC129 (p 0.066) and OC08 (effect 11.8 pp, below half of 24.0) are **Rejected**.
OC13 and OC21 flag the same sessions (same rule, two targets); OC13 / OC17 and M143 / PPC032 overlap heavily, so
the 11 are not 11 independent findings. For NIFTY they are one idea: wide or costly option chains and recent
falls come before bigger moves; calm, high-PCR days come before shallower lows.

### Reported, not gating
| Id | From t+1 open: effect, p | Beyond VIX: residual diff, p |
|---|---|---|
| PPC032 | +10.9 pp, 0.004 | +0.11, 0.008 |
| PPC062 | −8.4 pp, 0.044 | −0.07, 0.078 (n.s.) |
| PPC092 | +20.2 pp, 0.0002 | +0.24, <1e-4 |
| PPC098 | +21.8 pp, 0.0001 | +0.26, <1e-4 |
| PPC129 | +2.6 pp, 0.30 | +0.05, 0.13 (n.s.) |
| OC08 | +11.8 pp, <1e-4 (same as label) | +0.11, 0.0004 |
| OC13 | +11.0 pp (same as label) | +0.10, 0.003 |
| OC17 | +14.4 pp (same as label) | +0.16, <1e-4 |
| OC21 | +6.6 pp, 0.005 | +0.11, 0.001 |
| OC118 | +8.2 pp (same as label) | +0.005, 0.46 (n.s.) |
| M143 | +22.2 pp, <1e-4 | +0.17, 0.001 |
| M218 | +0.08, 0.004 (low vs open) | +0.14, 0.005 |
| M220 | +0.09, 0.004 (low vs open) | +0.12, 0.016 |

- From the open: big-move targets measured from the t+1 open (what a TCLOSE signal can trade). Every Validated rule
  keeps the sign and p < 0.05, with smaller effects than the gap-inclusive label (part of the move is the gap).
  Range targets have no gap in them, so they are the same.
- Beyond VIX: a VIX-only logistic (OLS for low_pc) fitted on discovery + validation; residual = outcome − VIX
  forecast; flagged minus unflagged mean residual, Welch one-sided. 9 of the 11 Validated add to VIX at p < 0.05;
  PPC062 and OC118 do not (they restate VIX in this period).
- Observed extras (`extras_summary.csv`, `extras_groups.csv`): circular-shift p (keeps flag clustering) < 0.01 for
  all Validated except PPC062 (0.054) and OC118 (0.013). Flags fall in 18-28 different months. Same sign in all or all but one half-year
  (cells with ≥ 5 flags); inside final-period VIX terciles 2-3 of 3 except OC118 (1 of 3). M143 fires almost only
  in high VIX (66 of 71 flags).

### Observed cross-checks (no test of any candidate)
(a) Expiry-day direction (`observed_expiry_direction.csv`; t+1 is an expiry day; gap up uses the 0.1 % flat band).

| UL | Gap up, disc. D0 | Gap up, final D0 | Final all | oc > 0, disc. D0 | oc > 0, final D0 |
|---|---|---|---|---|---|
| NIFTY | 59.3 % (216) | 41.0 % (122) | 42.9 % | 48.1 % | 39.3 % |
| BANKNIFTY | 55.2 % (261) | 27.3 % (44) | 39.8 % | 45.6 % | 45.5 % |
| SENSEX | no calendar | 46.2 % (106) | 44.3 % | no calendar | 43.4 % |

- Gap-up rates fell in every session type in the final period (NIFTY 59.8 → 42.9 % on all sessions, p < 1e-4),
  into both flat and down gaps. Inside the final period the expiry day is not different from other days for gap up
  (p 0.61 / 0.08 / 0.47) or oc sign (p 0.055 / 0.70 / 0.62). So no expiry-day direction base rate carries over;
  this agrees with no direction candidate reaching the final test. Discovery D0 figures equal `ref_discovery.csv`.
- BANKNIFTY D0 has n 44 (weeklies ended 2024-11-13). NIFTY expiries moved to Tuesday in the final period.

(b) Gap transition P(gap dir t+1 | gap dir t) (`observed_gap_transition_final.csv`): no dependence in the final
period (chi-square p 0.28 NIFTY, 0.83 BANKNIFTY, 0.59 SENSEX). The BANKNIFTY discovery effect (p 0.008) is gone.

### Not done in this step
The NIFTY straddle tradeability test of the plan was run afterwards as its own step: see `TRADEABILITY_ANALYSIS.md`
(no Validated rule is tradeable as a bought straddle).

### Caveats from the independent final review (`results/review_final/`, added 2026-11-05)
- OC13 and OC21 are the same rule (wall_near >= 1.83441) with two targets; their flags are identical. They are one
  confirmation, not two. BH over 12 tests without OC21 gives the same labels.
- Inside final-period VIX quintiles (`vix_stratified.csv`, permutation within quintile): PPC062 -0.060, p 0.14;
  OC118 +0.004, p 0.48 (restates VIX); OC13 p 0.034 (weaker than the logistic check). M143: 59 of 71 flags in the
  top VIX quintile, 51 % of flags in 3 months, none in 2025 H2; its effect falls from +35.5 pp raw to +26 pp within
  quintiles. The labels stand under the pre-registered gate; these are the caveats.

### Findings
| id | Finding | n | Effect | p / q | Label |
|---|---|---|---|---|---|
| FN1 | 11 of 13 size rules hold out of sample | 71-302 flags | see table | BH q ≤ 0.04 | Validated (size) |
| FN2 | PPC129, OC08 fail the gate | 117 / 302 | +7.3 / +11.8 pp | p 0.066 / effect < half | Rejected |
| FN3 | PPC062 and OC118 add nothing beyond VIX | 76 / 123 | resid +-0.07 / +0.005 | 0.08 / 0.46 | Observed |
| FN4 | Expiry-day gap / oc rates do not differ from other days; gap-up base fell | 44-122 D0 | – | – | Observed |
| FN5 | No gap-direction persistence in the final period | 576 | – | chi2 p 0.28-0.83 | Observed |

### What this does NOT show
- No profit: no option was priced here.
- One period, 2024-07 → 2026-10, with a weekday change for NIFTY and the end of BANKNIFTY weeklies.
- The binomial gate treats sessions as independent; flags cluster. The circular-shift p is the check for that.
