# Next-session prediction (module `model`, Agent 4, central experiment C)

Question: from what is known at **D-2** (close two sessions before), **TCLOSE(D-1)** (close of the day before) or
**T1515(D-1)** (15:15 of the day before), can we predict the next session, especially when that session is an expiry
day? Design `reports/lld/model.md`; numbers from `results/model/` (scripts `model_*.py`). Companion reports:
`FEATURE_DISCOVERY.md` (rules), `MACHINE_LEARNING_ANALYSIS.md` (models), `WALK_FORWARD_VALIDATION.md` (method).

**Resumed run.** The first run stopped on a usage limit during the walk-forward. Discovery, freezing and validation
were complete; `candidates_frozen.csv` was not touched (SHA-256 `9b9490…aa4d` unchanged, matched by validation and by
`tests/test_model.py`), validation was not re-run. The walk-forward was re-run end to end, and two pieces were added
after the resume: a VIX-only baseline (`model_vixbase.py`) and the table script (`model_tables.py`).

Data: NIFTY and BANKNIFTY panels, target sessions 2018-01 .. 2024-06 (discovery ≤ 2022-12, validation 2023-01 ..
2024-06). Minute targets (first 15 / 30 / 60 min) and the T1515 cutoff start 2021-10. NIFTY and BANKNIFTY are never
pooled. SENSEX: **Untestable** (its expiry calendar starts 2024-10, in the sealed period).

## Short answer
| Target | Expiry day (D0) | Every day | Verdict |
|---|---|---|---|
| Gap direction | no | no | not predictable at any cutoff |
| First 15 / 30 / 60 min direction | no | no | not predictable |
| Open-to-close direction | no | no | not predictable |
| Gap filled vs continued | no | weak rank signal, not usable | not predictable (Brier worse than base) |
| Big move (excursion ≥ 1 %, |cc| ≥ 1 %) | yes | yes | predictable, but VIX alone does as well |
| Gap size, high / low vs prev close | partly | partly | forest / boosting beat the median by 5-10 % MAE; primary ridge does not |

"Predictable" uses the rule fixed before the run: primary model (logistic, L2) pooled walk-forward AUC CI lower bound
> 0.5 **and** Brier below the base-rate Brier with one-sided bootstrap p < 0.05 (`wf_primary.csv`).

## 1. Is the expiry day different?
Discovery (2018-2022): the expiry day is not different from other days for any target, either index (all q ≥ 0.31;
`FEATURE_DISCOVERY.md` §1). Validation, described only (not a test, `context_profile.csv`):

| UL | Target | D0 2023-24 (n 78) | non-expiry 2023-24 (n 288) |
|---|---|---|---|
| NIFTY | gap up | 0.615 | 0.691 |
| NIFTY | oc up | 0.462 | 0.490 |
| NIFTY | big excursion | 0.269 | 0.198 |
| BANKNIFTY | gap up | 0.564 | 0.653 |
| BANKNIFTY | oc up | 0.359 | 0.486 |
| BANKNIFTY | big excursion | 0.462 | 0.378 |

These validation gaps (fewer gap-ups and more big excursions on expiry days, BANKNIFTY open-to-close more often
down) were not seen in discovery, so they are **Observed** only. BANKNIFTY's 2023-24 expiries mix the Thursday,
Wednesday-weekly and Wednesday regimes.

## 2. Direction: nothing beats the baselines
Primary model, pooled walk-forward test folds (`tab_wf_primary_binary.csv`):

| UL | Cutoff | Target | rows | AUC (95 % CI) | Brier skill | acc / majority |
|---|---|---|---|---|---|---|
| NIFTY | TCLOSE | gap up | 1108 | 0.528 (0.498-0.559) | -0.034 | 0.669 / 0.678 |
| NIFTY | TCLOSE | gap up, D0 only | 235 | 0.482 (0.407-0.558) | -0.042 | 0.643 / 0.638 |
| NIFTY | TCLOSE | oc up | 1108 | 0.521 (0.486-0.553) | -0.071 | 0.518 / 0.502 |
| NIFTY | T1515 | first 15 min up | 366 | 0.495 (0.428-0.548) | -0.102 | 0.508 / 0.582 |
| BANKNIFTY | TCLOSE | gap up | 1108 | 0.522 (0.489-0.557) | -0.054 | 0.633 / 0.635 |
| BANKNIFTY | TCLOSE | oc up, D0 only | 235 | 0.554 (0.494-0.628) | -0.053 | 0.553 / 0.566 |
| BANKNIFTY | D2 | first 15 min up | 366 | 0.557 (0.499-0.613) | +0.019 | 0.593 / 0.407 |

No directional target at any cutoff, on all days or on expiry days, meets the rule (all 36 direction x cutoff x UL
rows and their 36 D0 twins: `predictable = False`). Brier skill is negative almost everywhere: the model's probabilities
are worse than simply using the training-period up-rate. Previous-gap-sign and persistence baselines are no better
(accuracy 0.41-0.58, `tab_wf_accuracy_vs_baselines.csv`). The always-up gap call is the hardest baseline to beat (gap
up on 64-68 % of sessions) and no model beats it.

The 73 directional rules frozen from discovery also failed: 62 Rejected, 11 too thin in validation, 0 passed
(`candidates_validation.csv`).

## 3. Gap fill: a faint rank signal, not a usable one
Logistic AUC 0.555 (0.522-0.591) NIFTY and 0.565 (0.532-0.601) BANKNIFTY at TCLOSE, but Brier skill -0.04 / -0.02
(worse than the base rate). It ranks a little better than chance and is badly calibrated; not predictable by the
rule. No frozen gap-fill rule passed validation.

## 4. Big moves: predictable, but it is the VIX
| UL | Cutoff | Target | rows | AUC (95 % CI) | Brier skill (p) | VIX-only AUC |
|---|---|---|---|---|---|---|
| NIFTY | TCLOSE | excursion ≥ 1 % | 1108 | 0.741 (0.702-0.775) | +0.226 (<0.001) | 0.766 |
| NIFTY | TCLOSE | same, D0 only | 235 | 0.714 (0.640-0.784) | +0.192 (<0.001) | 0.755 |
| NIFTY | D2 | excursion ≥ 1 % | 1108 | 0.682 (0.637-0.725) | +0.146 (<0.001) | 0.760 |
| NIFTY | TCLOSE | |cc| ≥ 1 % | 1108 | 0.644 (0.598-0.689) | +0.075 (0.007) | 0.724 |
| BANKNIFTY | TCLOSE | excursion ≥ 1 % | 1108 | 0.794 (0.762-0.826) | +0.278 (<0.001) | 0.776 |
| BANKNIFTY | TCLOSE | same, D0 only | 235 | 0.727 (0.662-0.797) | +0.171 (0.003) | 0.744 |
| BANKNIFTY | D2 | |cc| ≥ 1 %, D0 only | 235 | 0.677 (0.609-0.745) | +0.143 (<0.001) | 0.721 |

Sources: `tab_wf_primary_binary.csv`, `wf_vix_baseline.csv`. The pre-stated rule says yes for big excursion at all
three cutoffs for both indices on all days, and for D0 at D2 / TCLOSE. But a one-feature logistic on the VIX known at
the cutoff is within 0.03 AUC of the full model, or better, in all 24 big-move rows (2 UL x 3 cutoffs x 2 targets x
all / D0), and the full model is never significantly better after BH (best: BANKNIFTY TCLOSE excursion +0.018,
p 0.031, q > 0.1). The information is "volatility is high", which the option prices already show.

## 5. Magnitudes (gap size, high / low vs previous close)
Primary ridge: MAE not below the median forecast except NIFTY D2 |gap| on expiry days (MAE ratio 0.914, p 0.013,
n 235). Ridge fits the mean of a skewed variable, so it loses to the median on MAE. Random forest and gradient
boosting (absolute-error loss) do beat the median: |gap| MAE ratio 0.90-0.94 at D2 / TCLOSE, both indices
(`tab_wf_maeratio_all_models.csv`). They were not the pre-stated primary model, so this is **Observed**, and it is
again a volatility-level effect (ridge forecast vs outcome Spearman 0.29-0.35). At T1515, trained only on
2021-10 .. 2022 (a high-vol period), ridge over-forecasts 2023-24 (MAE ratio up to 1.5); boosting holds 0.86-0.99.

## 6. Per-expiry prediction files
`results/model/predictions_<UL>_<target>_<cutoff>.csv`, 66 files (2 UL x 11 targets x 3 cutoffs): one row per
test-fold session with `target_date`, `is_expiry`, `kind` (weekly / monthly), `s_to_exp`, `regime`, `fold`, truth
`y`, each model's probability / forecast, the expiry-only models (`logit_D0`, `tree_D0`), base rate, majority,
previous-gap and persistence baselines. Expiry rows are selected with `is_expiry == True`.

## Findings
| id | finding | n | effect | CI / p | label |
|---|---|---|---|---|---|
| NS1 | Next-session gap direction, any cutoff, all days or D0 | 1108 / 235 per UL-cutoff | AUC 0.47-0.55 | all CIs include 0.5 or Brier worse than base | Rejected (not predictable) |
| NS2 | First 15/30/60-min direction | 366 / 78 | AUC 0.44-0.56 | none passes | Rejected |
| NS3 | Open-to-close direction | 1108 / 235 | AUC 0.49-0.55 | none passes | Rejected |
| NS4 | Gap fill vs continuation | 1108 | AUC 0.555 / 0.565 | CI > 0.5 but Brier skill < 0 | Rejected (rank-only, Observed) |
| NS5 | Big excursion ≥ 1 % next session, TCLOSE, NIFTY / BANKNIFTY | 1108 | AUC 0.741 / 0.794 | lo 0.702 / 0.762, Brier p < 0.001 | Observed in walk-forward (predictable by rule) |
| NS6 | Same on expiry days only | 235 | AUC 0.714 / 0.727 | lo 0.640 / 0.662 | Observed in walk-forward |
| NS7 | Full model adds nothing over VIX level for big moves | 1108 / 235 | AUC diff -0.17 .. +0.03 | 0 of 24 big-move rows BH-significant | Observed |
| NS8 | Frozen rule M143: NIFTY straddle/√day ≥ 0.767 at D-1 close → big excursion | 410 / 20 | +0.25 / +0.34 | val p 0.001 (n < 30) | Passed-validation |
| NS9 | Expiry day differs from other days (discovery) | 216 / 261 | ≤ ±0.06 | all q ≥ 0.31 | Rejected |
| NS10 | 2023-24 expiry days: fewer gap-ups, more big excursions | 78 | -0.08 / +0.07..0.08 | not tested | Observed |
| NS11 | SENSEX expiry questions | — | — | — | Untestable |

## What this does NOT show
- No model or rule tells the direction of the next session (gap, first hour, open-to-close), on expiry days or any
  day. This is the main result.
- "Big move predicted" is not a trade: it says nothing about direction, and the option premium already prices the
  same VIX. Whether a bought straddle on high-VIX days pays after its price was not tested (option minute prices are
  only in the sealed period).
- Walk-forward results are inside discovery + validation; the final sealed period has not been opened. Nothing here
  is Validated.
- The minute-era tests (T1515, first 15/30/60 min) have only 2 test years (366 rows, 78 expiries).
