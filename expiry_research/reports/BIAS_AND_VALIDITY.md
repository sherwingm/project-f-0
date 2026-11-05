# Bias and validity (Agent 5a, module `bias`)

Written 2026-11-05. Design `reports/lld/bias.md` (written before the code). Code `scripts/bias_common.py`,
`bias_discovery.py`, `bias_freeze.py`, `bias_validation.py`, `bias_robustness.py`, end to end `bias_run_all.py`
(re-run gives byte-identical CSVs). Tests `tests/test_bias.py` (4 pass, `results/bias/tests_stdout.txt`).
Every number below is in a CSV of `results/bias/` named next to it.

This module looks for no trading pattern. It gives the other agents and the coordinator: base rates to cross-check,
a false-discovery yardstick, regime and leakage checks, and a checklist. Data: open panels only (`load_panel`,
t <= 2024-06-28); `data/sealed/` and `results/verify/` were not opened. NIFTY and BANKNIFTY are never pooled.
Rows used: 1,232 discovery and 365 validation per index (split-edge rows and blank labels dropped).

## 1. Reference base rates (`ref_discovery.csv`, `ref_validation.csv`)
Targets: gap up / flat / down (|gap| < 0.1 % is flat), oc > 0, cc > 0, |cc| >= 1 %, max excursion from the
previous close >= 1 % ("big_exc"), mean range.

| Target | NIFTY disc | NIFTY val | BANK disc | BANK val |
|---|---|---|---|---|
| gap up | 59.8 % | 55.9 % | 56.3 % | 53.4 % |
| gap flat | 15.9 % | 21.1 % | 13.1 % | 19.7 % |
| gap down | 24.3 % | 23.0 % | 30.5 % | 26.8 % |
| oc > 0 | 48.5 % | 48.2 % | 47.0 % | 45.8 % |
| cc > 0 | 54.1 % | 56.4 % | 53.2 % | 54.8 % |
| abs cc >= 1 % | 26.4 % | 10.7 % | 39.4 % | 21.1 % |
| big_exc | 45.9 % | 21.4 % | 67.8 % | 39.7 % |
| mean range, % | 1.26 | 0.89 | 1.82 | 1.20 |

The index gaps up most days and then drifts down intraday (oc > 0 below 50 %). Any rule must beat these rates for
the same period, not 50 %. Big-move rates halve from discovery to validation (section 4): a volatility rule's
base must always be the period's own rate.

By expiry context of t+1 (discovery, `ctx` rows; validation in the same file):
| t+1 | NIFTY n | NIFTY big_exc | NIFTY gap up | BANK n | BANK big_exc | BANK gap up |
|---|---|---|---|---|---|---|
| D0 (expiry) | 216 | 46.8 % | 59.3 % | 261 | 66.7 % | 55.2 % |
| D-1 | 216 | 44.9 % | 60.2 % | 261 | 66.7 % | 55.6 % |
| D-2 | 212 | 47.2 % | 61.8 % | 256 | 66.0 % | 57.0 % |
| D-3 | 163 | 58.3 % | 59.5 % | 193 | 71.0 % | 60.1 % |
| D+1 | 216 | 51.9 % | 59.3 % | 261 | 69.3 % | 54.8 % |
| base | 1,232 | 45.9 % | 59.8 % | 1,232 | 67.8 % | 56.3 % |

On the daily metrics the expiry day itself is not unusual in discovery. Weekly vs monthly D0, weekday regime x
context, weekday of t+1, weekend gaps and previous gap direction are all in the same CSVs (tags `xkind_ctx`,
`regime_ctx`, `cal_next_dow`, `gap_after`, `o_gap_dir`). Under the Thursday regime, D-3 is a Monday.

P(gap dir t+1 | gap dir t) (`gap_transition_*.csv`): no dependence for NIFTY (chi-square p 0.91 discovery, 0.58
validation). BANKNIFTY discovery p 0.008 (q 0.07): after a flat gap, a down gap is less likely (21.0 % vs 30.5 %,
n 162). It is not seen in validation (p 0.19). Observed only.

## 2. Mining null: the false-discovery yardstick (`mining_*.csv`)
A typical search on discovery: 20 `f_` features, each at its 20th / 80th discovery percentile (40 single conditions),
and each of those AND one of 4 expiry contexts (t+1 is D0 / D-1 / D+1 / in a monthly cycle) = 200 rules x 6 targets.
Rules with n < 30 are skipped (194 tested per index, 1,164 tests). Exact binomial test vs the discovery base.
Null: 200 runs that shuffle whole ISO weeks of the label matrix. A second null swaps only weeks of equal length
(labels keep their weekday slot). Both nulls give the same picture (`mining_null_summary.csv`).

| Per index, 1,164 tests | NIFTY null mean / p95 | NIFTY real | BANK null mean / p95 | BANK real |
|---|---|---|---|---|
| p < 0.05 | 44.8 / 70 | 204 | 44.5 / 66 | 169 |
| BH q < 0.10 | 0.14 / 1 | 148 | 0.13 / 1 | 117 |
| best abs edge, any rule | 24.1 / 29.3 pp | 43.8 pp | 22.6 / 26.8 pp | 38.4 pp |
| direction targets only (776 tests): p < 0.05 | 27.7 / 46 | 31 (emp p 0.33) | 27.7 / 45 | 16 (emp p 0.91) |
| direction only, BH q < 0.10 | 0.05 / 0 | 0 | 0.07 / 0 | 0 |

Direction = gap up, gap down, oc > 0, cc > 0. All the excess "discoveries" are volatility targets (|cc| >= 1 %,
big_exc): volatility clusters, so volatility features predict big days. For direction the real search finds no more
than chance.

BH contamination. When volatility and direction targets share one BH family, true volatility effects lower the
BH bar and direction rules pass by chance. Real: 8 (NIFTY) and 4 (BANKNIFTY) direction rules reach q < 0.10 in the
mixed family. Null that keeps the volatility labels real and shuffles only direction labels: mean 5.8 / 4.4, 95th
percentile 12 / 11 (`dir_only` rows). So "BH-significant" direction rules from a mixed family are exactly what
chance gives. Run BH separately for direction targets, or judge them against this null.

Chance edge by rule size (`mining_null_by_nbin.csv`, week null; edge = rule rate minus base, percentage points):
| Rule n | single test, 95 % | best of the rules in that bin, 95 % (rules per index) |
|---|---|---|
| 30-59 | 13-15 pp | 22-27 pp (about 105) |
| 60-119 | 9-12 pp | 15-21 pp (about 42) |
| 120-249 | 5-7 pp | 9-14 pp (about 42) |
| 250+ | 4-5 pp | 5-6 pp (4) |

Use: a 15-pp edge on 45 rows, found after trying about 100 rules, is the median best result of a pure-noise search.

## 3. Regimes (`regimes_discovery.csv`, `regimes_validation.csv`, `weekday_vs_expiry.csv`)
| Period | NIFTY big_exc | NIFTY gap down | BANK big_exc | n |
|---|---|---|---|---|
| 2018 | 32.4 % | 20.9 % | 50.8 % | 244 |
| 2019 | 34.8 % | 18.4 % | 57.0 % | 244 |
| 2020 | 64.4 % | 25.6 % | 89.6 % | 250 |
| 2021 | 45.7 % | 19.8 % | 70.0 % | 247 |
| 2022 | 51.8 % | 36.4 % | 70.9 % | 247 |
| COVID 2020-02-20..06-30 | 95.3 % | 37.2 % | 96.5 % | 86 |
| validation 2023-24H1 | 21.4 % | 23.0 % | 39.7 % | 365 |

- Volatility rates move by a factor of 2-3 between years (year chi-square p < 1e-9, both indices). Gap down and gap
  flat also differ by year (p <= 0.004); oc > 0 and cc > 0 do not (p 0.14-0.90).
- Atypical periods (BH q < 0.10 in the whole family): COVID and 2020H1 (high volatility, few flat gaps), 2022H1
  (gap down 39 % NIFTY, 43 % BANKNIFTY), 2018-2019H1 (low volatility), and the whole validation period. 87 % of validation rows
  (319 of 365) fall in discovery's low-VIX tercile (VIX <= 15.7). Validation therefore tests mostly a low-volatility
  regime; discovery's high-VIX behaviour is barely sampled there.
- VIX tercile of t: big_exc 25 / 44 / 69 % (NIFTY low / mid / high), 46 / 67 / 90 % (BANKNIFTY). Any big-move
  result must be shown inside VIX terciles.
- Expiry weekday break (BANKNIFTY Thursday to Wednesday, 2023-09 and 2024-03). Comparing t+1 Thursdays across regimes
  (65 % big_exc in B1 vs 40 % in B2+B3, p 0.002) mixes the weekday change with the low-volatility era. Inside
  validation only (same years): expiry days have big_exc 46 % (B1, n 35), 46 % (B2, n 26) and 47 % (B3, n 17);
  Wednesday non-expiry in B1 has 28 % (n 32); Thursday non-expiry in B2 / B3 40 % / 44 % (n 20 / 16). This hints that
  the effect follows the expiry, not the weekday, but every cell is n < 40. Observed only.
- NIFTY has one weekday regime in the open period (Thursday), so expiry and Thursday cannot be separated; the 13
  holiday-shifted expiries are too few (big_exc 38 % vs 42 %, p 0.82).
- Untestable here (sealed period): BANKNIFTY weeklies ending 2024-11-13, the 2025-01 and 2025-09 weekday changes,
  NIFTY Tuesday expiries, and every SENSEX expiry question (calendar only from 2024-10).

## 4. Leakage self-test (`auc_leakage.csv`, `auc_controls.csv`)
Each of 90 numeric `f_` / `f1515_` features per index, discovery rows, AUC for gap up vs down (flats out) and for
oc > 0; big_exc as a calibration target. Flag: |AUC - 0.5| > 0.15.
- Gap direction and oc sign: 0 flags. Largest |AUC - 0.5|: 0.108 (BANKNIFTY `f1515_ret_open_to_1514` for gap, n 269),
  0.055 for oc. Chance spread for a pure-noise feature: 95th percentile 0.032 at n 1,232, 0.066 at n 294.
- Controls work: `y_gap_pct` and `y_oc` give AUC 1.00; a planted leak (next day's `f_mom1`) gives 0.90 (oc) and
  0.79 / 0.74 (gap, NIFTY / BANKNIFTY).
- big_exc: 16 flags per index, all volatility-level features (ATR, HV10/20, VIX, f1515 range / rv / VIX, straddle
  price, futures volume, strike count, distance to the 20 / 55-day high, call-wall distance). Explanation: volatility
  clustering and the leverage effect (far below the recent high = falling market = high volatility). Not leakage:
  each is cut at TCLOSE(t) or 15:14 (panel test a) and the AUC is 0.65-0.77, not near 1.

Independent integrity checks (`integrity.csv`): `f_mom1`, `f_close_pos`, `f_hv10`, `y_gap_pct`, `y_oc`, `y_cc`
recomputed from `px_` columns match exactly; `y_X` equals `o_X` of the next row; `f_vix_close` equals raw
`vix_daily` of the same date on all 1,582 rows and of the day before / after on 0.6 %. One documentation
mismatch: `f_dist_high/low20/55` include day t in the window (`build_panel.py` line 324; 98.8 % exact match), while
the dictionary says the window ends at t-1. This is not look-ahead (t's high / low are known at TCLOSE), but the
feature is always <= 0 (high) / >= 0 (low).

## 5. Checklist
| Risk | Status | Evidence |
|---|---|---|
| Look-ahead in features | No leak found | panel tests a-e (PANEL.md); section 4; `integrity.csv` |
| Look-ahead in tags | 4 rows per index (2023-06-22..27) use the 2023-06-28 expiry before its 06-27 re-dating; BANKNIFTY 2023-08-31 uses 2023-09-06 one evening early (the circular was public since July) | `redated_rows.csv` |
| Label for T1515 decisions | `y_gap` is measured from the 15:29 close; a 15:15 entry earns open(t+1) / price(15:14), not `y_gap` | dictionary; to be handled by the agents that use f1515 |
| Survivorship | None: index series only, no constituent or stock universe; bhavcopy keeps expired contracts | DATA_AUDIT |
| Data snooping | Main risk. Direction search gives chance-level counts; mixed-target BH is contaminated | section 2 |
| Regime dependence | Strong for volatility (x2-3 by year), weak for direction; validation is low-VIX | section 3 |
| Label source (close) | Official close before 2021-10-20, minute close after: a label-definition break inside discovery | below |
| Flat band | 0.1 % band; moving it to 0.05 / 0.15 % changes the discovery flat share from 13-16 % to 6-8 % / 21-25 % | `flat_band_*.csv` |
| Split edges | 1 row per split edge (2022-12-30, 2024-06-28), dropped from every test | `bias_common.load` |
| Muhurat | 3 rows (2018-11-06, 2021-11-03, 2022-10-21) carry the Muhurat move in `y_gap` (NIFTY +0.80 / +1.23 / +1.27 %), all gap-ups; dropping them moves gap-up base by 0.1 pp | panel `cal_special_between` |
| Re-dated expiries | Calendar uses final dates (see tags row) | `redated_rows.csv` |
| Thin minute data | f1515 discovery n about 294; noise AUC spread doubles | `auc_controls.csv` |
| SENSEX | Expiry questions Untestable before the final stage | EXPIRY_CALENDAR_ANALYSIS |

Minute close vs official close (`label_official_vs_minute_*.csv`, `label_rule_flips.csv`). Only 2021-10-20 → 2024-06-28
can be compared here (2024-07 → 2025-09 is sealed).
- Gap direction agrees on 90.1 / 91.1 % of discovery rows and 89.3 / 86.5 % of validation rows (NIFTY / BANKNIFTY);
  almost all disagreements are flat vs up/down, never up vs down except 4 BANKNIFTY rows.
- Base rates barely move: largest change 2.2 pp (BANKNIFTY validation flat 19.8 vs 17.6 %, p 0.45).
- Rule results move a little: of 39-41 mining rules testable in the discovery minute era, 0-2 change nominal
  significance and 4-9 change the sign of a small edge; edge correlation 0.69-0.87. Feature AUC changes up to 0.056
  (`f_close_pos`, which shares the minute close with the label). The gap-transition matrix keeps chi-square p > 0.13.
- Conclusion: gap-direction results that depend on the last minutes of t (close position, last-minute return) should
  be re-checked with `px_close_official`; base rates and most rules are unaffected.

## 6. Frozen controls and their validation (`candidates_frozen.csv`, `candidates_validation.csv`, `robustness*.csv`)
Before any validation number was computed, every discovery expiry-context test with n >= 30 and q < 0.10 in the
discovery family (4,275 tests) was frozen: 14 controls. They are base-rate facts, not trading rules.
- 6 NIFTY "D-6+" controls (lower range / fewer big moves 6+ sessions before expiry): D-6+ exists only in 2018-19, the
  monthly-only, low-volatility period. Inside 2018 the effect shrinks to -1.6 to -3.6 pp. Untestable in validation
  (no D-6+ rows); a year confound.
- 6 NIFTY "D-3" controls (more big moves): D-3 is a Monday. Among weekend gaps alone the effect is +2 pp
  (big_exc 48.8 vs 46.7 %). Validation: 19.5 vs 21.4 %, p 0.70. Rejected; a weekend confound.
- 2 BANKNIFTY monthly-cycle controls (D-3 big_exc, D+1 big_cc; n 47 / 60): validation n 14 / 18, Rejected.
None passed validation.

Hypothesis log `hypotheses.csv`: 5,400 tests (discovery 4,275: mining replica 2,328, reference 1,061, AUC 540,
regime 334, label 12; validation 1,125). BH at FDR 10 % over the whole family: 615 reject, almost all volatility,
regime or AUC-on-volatility tests. Validation reference rows are descriptive only; nothing seen there is a candidate.

## Findings
| id | Finding | n | Effect | CI / null | Label |
|---|---|---|---|---|---|
| B1 | Direction targets: a 200-rule search finds no more nominal hits than chance | 776 tests per index | 31 / 16 hits at p<0.05 | null 95 %: 46 / 45 | Observed |
| B2 | Mixed-target BH lets chance direction rules pass | 776 per index | 8 / 4 at q<0.10 | null mean 5.8 / 4.4, 95 %: 12 / 11 | Observed |
| B3 | Chance best edge by rule size | n 30-59 / 60-119 / 120-249 | 22-27 / 15-21 / 9-14 pp | 95th pct of the null | Observed |
| B4 | Volatility features predict big days (clustering), not leakage | 1,232 | AUC 0.65-0.77 | noise 95 %: 0.53 | Observed |
| B5 | No feature has a leak-like AUC for gap or oc sign | 90 features | max abs dev 0.108 | flag 0.15 | Observed |
| B6 | Validation is a low-volatility regime | 365 | big_exc 21.4 vs 45.9 % (NIFTY) | p < 1e-15 | Observed |
| B7 | Expiry-context effects in discovery were calendar confounds (weekend, 2018) | 14 controls | 0 passed | – | Rejected / Untestable |
| B8 | Official vs minute close changes gap direction on about 10 % of rows, base rates by <= 2.2 pp | 292-363 | 0-2 rule flips of about 40 | – | Observed |
| B9 | BANKNIFTY expiry-day big moves seem to follow the expiry weekday | 17-35 per cell | 46 % vs 28 % | small n | Observed |
| B10 | `f_dist_high/low` windows include t (dictionary says t-1) | 1,579 | – | – | Observed |
| B11 | SENSEX expiry and the 2024-11 / 2025 weekday breaks | – | – | – | Untestable |

## What this does NOT show
- It does not show that no direction pattern exists: only that a broad search of daily `f_` features gives no
  more than chance in discovery. A narrow, pre-registered idea can still be real.
- The null permutes labels by weeks; it keeps serial structure inside a week but not across weeks or regimes.
- Nothing here uses option prices, so it says nothing about whether any volatility effect pays after premium.
- The minute-vs-official comparison covers 2021-10 → 2024-06 only; 2024-07 → 2025-09 stays sealed.
- No result here is Validated; nothing was taken to the final period.
