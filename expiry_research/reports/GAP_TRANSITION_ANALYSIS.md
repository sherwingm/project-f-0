# Gap and reversal patterns around expiry (module `gaps`, Agent 1)

Written 2026-11-05. Design: `reports/lld/gaps.md` (written before the code). Code: `scripts/gaps_common.py`,
`gaps_specs.py` (the hypothesis family), `gaps_eval.py`, `gaps_discovery.py`, `gaps_freeze.py`, `gaps_validate.py`,
`gaps_robust.py`, `gaps_behaviour.py`. Tests: `tests/test_gaps.py` (10 pass, `results/gaps/tests_stdout.txt`).
Every number below is in a CSV under `results/gaps/` named next to it. Run logs: `results/gaps/*_stdout.txt`.

## 1. Short answer
- **Nothing in this module survived validation.** 239 tests on discovery (2018-2022), 4 were BH-significant
  (FDR 10 %), all 4 were frozen and all 4 failed validation (2023 → Jun 2024). No candidate goes to the final test.
- A gap up is **not** followed by a gap down more often than usual (NIFTY 24.7 % vs 24.3 % base), and the reverse
  is also absent. Gaps are mostly up in both indices (NIFTY 60 %, BANKNIFTY 56 %), whatever happened the day before.
- Large opening gaps (≥ 0.5 %, ≥ 1 %) neither continue nor reverse more than ordinary gaps; the close-to-open
  direction is a coin flip (45-51 %). Gap fill falls with size (NIFTY ~77 % for 0.1-0.3 % gaps, 26 % for ≥ 1 %).
- Reversal of the previous gap does **not** rise as expiry approaches (trend p = 0.52 NIFTY, 0.78 BANKNIFTY).
- Expiry-day strong gaps (≥ 0.3 / 0.5 %) behave like strong gaps on other days (continuation, fill and signed
  close-to-open all within ±3 points / ±0.12 %). The minute data hint at an early fade on expiry day (first 15
  minutes) but n = 44-46 and it is not BH-significant.
- Weak, consistent-sign hints that are only **Observed**: large gaps the day **before** expiry (D-1) fade more in
  both indices; gap fill is higher when VIX is high; a close near the day's high is followed by a gap up a bit more
  often. None is BH-significant; none is a tested rule.

## 2. Data and rows
| Item | NIFTY | BANKNIFTY |
|---|---|---|
| Discovery rows (t+1 from 2018-01-02 to 2022-12-30) | 1,229 | 1,229 |
| Validation rows (t+1 2023-01-03 → 2024-06-28) | 365 | 365 |
| Discovery rows with minute data for t+1 (from 2021-10-20) | 293 | 293 |
| Discovery expiry days (D0) / with minute data | 216 / 63 | 261 / 63 |
| Discovery monthly D0 with minute data | 15 | 15 |

`results/gaps/minute_coverage.csv`. Rows are full sessions from `panel_io.load_panel`; dropped: the 2 split-edge rows
and the 3 rows whose gap spans a Muhurat session. A row is session t with its label session t+1.

- Gap = open(t+1) / close(t) − 1. Flat if |gap| < 0.1 %. From 2021-10-20 the close is the 15:29 minute close; before,
  the official close (PANEL.md: the two disagree on the up / flat / down label on ~11 % of days, so matrices mix two
  close definitions across 2021-10).
- Context of t+1 from the calendar: D0 = expiry day, D-k = k sessions before the next expiry, D+1 = first session after
  an expiry. In a normal 5-day weekly week **D+1 and D-4 are the same session** (Friday when expiry is Thursday).
  D-5 exists only in NIFTY 2018 (monthly expiries only) and is reported as k = 5.
- Weekday regimes in the open data: NIFTY monthly-only (2018 → 2019-02-08) then Thursday weekly; BANKNIFTY Thursday
  (→ 2023-08), Wednesday weekly + Thursday monthly (2023-09 → 2024-02), Wednesday (2024-03 →). In discovery every
  weekly expiry is a Thursday, so **D0 / D-1 / D+1 are also Thursday / Wednesday / Friday**, and "ordinary" days are
  Monday and Tuesday (Monday gaps include the weekend). The only non-expiry Thursdays in discovery are NIFTY 2018.
- SENSEX: its expiry calendar starts 2024-10-04 (sealed period), so every SENSEX expiry question is **Untestable** here.

Decision times: rules using only gaps of t and the calendar are T1515(t) (gap of t is known at 09:15 of t);
rules using the close position or close of t are TCLOSE(t) and cannot trade the next gap itself; rules using the
opening gap of t+1 are OPEN(t+1) and are scored from the 09:15 bar close (minute data) or, for the long history,
from the open itself (daily `y_oc`, optimistic by one minute).

## 3. Transition matrices, gap of t → gap of t+1 (discovery, `transitions.csv`)
Row = gap of t, cell = share of next gaps; n = rows.

| NIFTY | next up | next flat | next down | n |
|---|---|---|---|---|
| up | 59.2 % | 16.1 % | 24.7 % | 733 |
| flat | 62.8 % | 14.3 % | 23.0 % | 196 |
| down | 58.9 % | 16.7 % | 24.4 % | 299 |
| all (base) | 59.7 % | 15.9 % | 24.3 % | 1,228 |

| BANKNIFTY | next up | next flat | next down | n |
|---|---|---|---|---|
| up | 53.7 % | 13.6 % | 32.7 % | 691 |
| flat | 60.2 % | 18.6 % | 21.1 % | 161 |
| down | 59.0 % | 10.1 % | 30.9 % | 376 |
| all (base) | 56.2 % | 13.2 % | 30.6 % | 1,228 |

Independence test: NIFTY χ² p = 0.91; BANKNIFTY p = 0.0075, Cramér's V 0.075, BH q = 0.22 (not significant). The
BANKNIFTY departure is small: after a flat gap the next gap is flat more often.

Tests vs the base rate (`hypotheses.csv`, group T):
| Rule (T1515) | NIFTY rate vs base | p | BANKNIFTY rate vs base | p |
|---|---|---|---|---|
| gap up → next gap down | 24.7 vs 24.3 % (733) | 0.83 | 32.7 vs 30.6 % (691) | 0.23 |
| gap down → next gap up | 58.9 vs 59.7 % (299) | 0.77 | 59.0 vs 56.2 % (376) | 0.28 |
| gap ≥ +0.5 % → next down | 27.1 vs 24.3 % (258) | 0.31 | 36.6 vs 30.6 % (295) | 0.027 |
| gap ≤ −0.5 % → next up | 61.8 vs 59.7 % (131) | 0.66 | 61.6 vs 56.2 % (177) | 0.17 |
| gap ≥ +1 % → next down | 32.8 vs 24.3 % (58) | 0.17 | 34.3 vs 30.6 % (102) | 0.45 |
| gap ≤ −1 % → next up | 65.0 vs 59.7 % (60) | 0.43 | 66.7 vs 56.2 % (87) | 0.052 |

Large gaps reverse slightly more often at the next open (all signs point that way) but no test is BH-significant
(smallest q = 0.34).

By expiry context (`transitions.csv`, slices "t+1 = D0 / D-1 / D+1 / D0 monthly"): the matrices look like the overall
one; e.g. NIFTY gap up → next down is 27.7 % when t+1 is D0 (n 130), 26.3 % on D-1 (133), 28.3 % on D+1 (127).
Monthly-expiry slices have 5-33 rows per cell (thin).

## 4. Does reversal rise as expiry approaches? (`reversal_by_context.csv`, group X)
Reversal = next gap opposite to today's gap (both non-flat).

| t+1 | NIFTY rate (n) | BANKNIFTY rate (n) |
|---|---|---|
| D-4 (= D+1 in a normal week) | 48.4 % (126) | 50.7 % (140) |
| D-3 | 37.5 % (152) | 44.8 % (201) |
| D-2 | 40.9 % (149) | 49.3 % (203) |
| D-1 | 41.9 % (148) | 49.7 % (199) |
| D0 | 41.1 % (158) | 45.8 % (192) |
| D+1 | 46.6 % (161) | 49.0 % (194) |
| base (all) | 41.3 % (864) | 47.9 % (935) |

Trend test over D-4 → D0: p = 0.52 (NIFTY), 0.78 (BANKNIFTY). No context differs from base (all p ≥ 0.12).
For large gaps (|gap of t| ≥ 0.5 %) reversal is 51.7 % into D0 vs 44.4 % overall for NIFTY (n 58) and 57.1 % vs 50.8 %
for BANKNIFTY (n 77); the D0/D-1 vs rest test gives p = 0.74 and 0.13. **Answer: no.**

## 5. Large gaps on the day itself: continue or reverse? (`gap_buckets.csv`, group L)
Continuation = close-to-open of t+1 has the gap's sign. Signed oc = oc × gap sign (+ = continues).

| | NIFTY | BANKNIFTY |
|---|---|---|
| continuation, all non-flat gaps (base) | 49.3 % | 47.0 % |
| continuation, \|gap\| ≥ 0.5 % | 49.5 % (386), p 0.96 | 45.7 % (470), p 0.58 |
| continuation, \|gap\| ≥ 1 % | 47.4 % (116), p 0.71 | 44.7 % (188), p 0.56 |
| mean signed oc, \|gap\| ≥ 1 % vs 0.1-0.5 % gaps | −0.17 vs −0.02 %, p 0.39 | −0.24 vs −0.01 %, p 0.18 |
| mean signed 09:16→close, \|gap\| ≥ 0.5 % (minute) | −0.01 % (115) vs −0.07 %, p 0.62 | −0.07 % (130) vs −0.11 %, p 0.76 |

Gap fill (the session trades back to the previous close), discovery, `fill_conditions.csv`:
| \|gap\| | NIFTY fill (n) | BANKNIFTY fill (n) |
|---|---|---|
| 0.1-0.3 % | 76.9 % (364) | 82.3 % (339) |
| 0.3-0.5 % | 63.3 % (283) | 67.1 % (258) |
| 0.5-1.0 % | 41.5 % (270) | 52.1 % (282) |
| ≥ 1.0 % | 25.9 % (116) | 35.1 % (188) |
Fill by size is mechanical and was not tested. **Answer: large gaps neither continue nor reverse in a usable way.**

## 6. Streaks of same-direction gaps (`streaks.csv`, group S)
| Rule | NIFTY rate vs base (n), p | BANKNIFTY rate vs base (n), p |
|---|---|---|
| ≥ 2 gaps up → next gap up (T1515) | 57.6 vs 59.7 % (436), 0.38 | 54.4 vs 56.2 % (373), 0.50 |
| ≥ 3 gaps up → next gap up | 55.0 vs 59.7 % (251), 0.14 | 52.2 vs 56.2 % (203), 0.26 |
| ≥ 2 gaps down → next gap down | 31.5 vs 24.3 % (73), 0.17 | 31.9 vs 30.6 % (116), 0.76 |
| ≥ 2 gaps up → next oc > 0 (TCLOSE) | 53.4 vs 48.5 % (436), 0.039 | 50.4 vs 47.0 % (373), 0.20 |
| ≥ 2 gaps down → next oc < 0 | 63.0 vs 51.5 % (73), 0.060 | 57.8 vs 53.0 % (116), 0.31 |
≥ 3 down-gap streaks have 23 (NIFTY) and 37 (BANKNIFTY) rows. Nothing is BH-significant (smallest q 0.41).

## 7. Close position in the day's range → next gap (`close_pos.csv`, group C)
| Rule | NIFTY | BANKNIFTY |
|---|---|---|
| close in top 20 % → next gap up (TCLOSE) | 64.4 vs 59.7 % (354), p 0.074 | 62.4 vs 56.2 % (311), p 0.030 |
| close in bottom 20 % → next gap down | 29.5 vs 24.3 % (288), p 0.046 | 30.7 vs 30.6 % (267), p 0.95 |
| 15:14 price in top 20 % → gap up (T1515, minute, 2021-10 →) | 63.3 vs 53.1 % (98), p 0.054 | 62.5 vs 54.1 % (80), p 0.15 |
| t+1 is D0 and close in top 20 % → gap up | 71.2 vs 59.7 % (66), p 0.060 | 66.2 vs 56.2 % (68), p 0.11 |
The sign is consistent (a strong close leans to a gap up) but no test passes BH (q ≥ 0.36). The TCLOSE version cannot
trade the gap; only the T1515 twin could, and it has 80-98 rows.

## 8. Strong opening gap on expiry day (OPEN(t+1), group E)
Same-size gaps on D0 vs all other days (two-group tests).
| \|gap\| on D0 | NIFTY D0 vs other | BANKNIFTY D0 vs other |
|---|---|---|
| ≥ 0.3 %: continuation | 51.2 vs 48.9 % (125 / 544), p 0.64 | 48.1 vs 46.1 % (158 / 570), p 0.66 |
| ≥ 0.3 %: fill | 48.0 vs 48.0 %, p 1.00 | 55.7 vs 52.3 %, p 0.45 |
| ≥ 0.5 %: continuation | 50.0 vs 49.4 % (78 / 308), p 0.92 | 47.6 vs 45.2 % (103 / 367), p 0.67 |
| ≥ 0.5 %: signed oc | −0.02 vs −0.14 %, p 0.40 | −0.05 vs −0.17 %, p 0.48 |
| ≥ 0.3 %, minute, entry 09:15 bar close: signed ret15 | −0.08 vs +0.04 % (46 / 142), p 0.006 | −0.07 vs +0.03 % (44 / 158), p 0.08 |
| signed ret30 / ret60 | −0.05 / −0.09 % vs +0.01 / +0.03 %, p 0.29 / 0.10 | −0.05 / −0.07 % vs −0.01 / 0.00 %, p 0.60 / 0.49 |
| signed 09:16 → close | −0.17 vs +0.02 %, p 0.24 | −0.22 vs −0.06 %, p 0.48 |
| fill after 09:16 | 56.5 vs 41.5 %, p 0.076 | 52.3 vs 48.1 %, p 0.62 |
The early fade on expiry day points the same way in both indices (first 15 minutes go against the gap) but rests on
44-46 expiry days from 2021-10 to 2022-12; NIFTY's q is 0.22. **Observed only.**

The day **before** expiry (D-1) shows a larger, consistent fade of strong gaps, also not BH-significant:
| \|gap\| on D-1 | NIFTY | BANKNIFTY |
|---|---|---|
| ≥ 0.3 %: fill, D-1 vs other | 57.7 vs 46.1 % (111 / 558), p 0.026 | 59.7 vs 51.3 % (149 / 579), p 0.066 |
| ≥ 0.3 %: signed oc | −0.29 vs −0.03 %, p 0.046 | −0.32 vs −0.04 %, p 0.066 |
| ≥ 0.5 %: fill | 46.2 vs 34.9 % (65 / 321), p 0.086 | 58.0 vs 42.4 % (88 / 382), p 0.008 |
| ≥ 0.5 %: signed oc | −0.43 vs −0.05 %, p 0.058 | −0.56 vs −0.05 %, p 0.024 |
D-1 is Wednesday in all discovery data, so this may be a Wednesday effect; smallest q 0.22. **Observed only.**
On D+1 strong gaps behave like other days (BANKNIFTY ≥ 0.3 % continuation 53.6 vs 44.9 %, p 0.064).

## 9. When does a gap fill? (OPEN(t+1), group F, `fill_conditions.csv`)
| Condition (within the size bucket) | NIFTY | BANKNIFTY |
|---|---|---|
| 0.1-0.5 %: gap up vs gap down | 74.3 vs 61.3 % (479 / 168), p 0.0014, **q 0.09** | 77.9 vs 71.4 %, p 0.079 |
| 0.1-0.5 %: VIX top vs bottom tercile | 78.0 vs 66.9 %, p 0.015 | 83.3 vs 71.3 %, p 0.009 |
| ≥ 0.5 %: VIX top vs bottom tercile | 41.6 vs 31.5 %, p 0.17 | 51.6 vs 37.0 %, p 0.023 |
| ≥ 0.5 %: gap up vs down | 39.6 vs 31.3 %, p 0.11 | 49.5 vs 38.4 %, p 0.020 |
| ≥ 0.5 %: t+1 D0/D-1 vs k ≥ 2 | 41.3 vs 34.2 %, p 0.16 | 50.8 vs 41.6 %, p 0.049 |
| ≥ 0.5 %: gap with the 5-day trend vs against | 32.9 vs 41.8 %, p 0.072 | 41.8 vs 49.3 %, p 0.10 |
| 0.1-0.5 %: t+1 D+1 vs other | 72.6 vs 70.6 %, p 0.68 | 73.4 vs 76.3 %, p 0.50 |
VIX tercile cut points (discovery): 15.70 and 19.81. Up gaps fill more than down gaps, high VIX fills more, and a gap
against the recent trend fills more; only NIFTY's up-vs-down test passed BH, and it failed validation (section 11).

## 10. First session after expiry (group P)
| Rule (TCLOSE of the expiry day) | NIFTY | BANKNIFTY |
|---|---|---|
| next gap against the expiry-day close-to-close move, vs other days | 49.7 vs 43.4 % (181 / 852), p 0.12 | 48.4 vs 46.1 %, p 0.53 |
| next oc against the expiry-day move | 52.1 vs 48.9 %, p 0.40 | 50.6 vs 48.1 %, p 0.49 |
| expiry-day \|cc\| ≥ 1 % → next oc reverses | 59.0 vs 48.5 % (61 / 264), p 0.14 | 55.4 vs 45.7 % (101 / 383), p 0.081 |
| D+1 gap up | 59.1 vs 59.7 %, p 0.84 | 54.4 vs 56.2 %, p 0.57 |
A big expiry-day move is partly reversed the next day slightly more often than a big move on another day, in both
indices, but not significantly.

## 11. Frozen candidates, validation and robustness
Freeze rule (fixed in the LLD): BH q < 0.10 on the whole 239-test family, n ≥ 30 in each group, non-label decision time.
`candidates_frozen.csv` was written (with the sha256 of the spec / data / evaluation code) before any validation number;
`gaps_validate.py` refuses to run if that code changed. Pass rule: same sign, one-sided p < 0.05, effect ≥ half.

| id | Rule | Discovery effect (n) | Validation effect (n), p (one-sided) | Label |
|---|---|---|---|---|
| N_Fa_dir | NIFTY 0.1-0.5 % gaps: up fill more than down | +13.0 pts (479 / 168) | +2.2 pts (171 / 67), 0.37 | Rejected |
| N_BD0_low_min | NIFTY expiry day: low made later than on ordinary days (minute) | +73 min (62 / 106) | +21 min (78 / 131), 0.15 | Rejected |
| N_BDp1_low_min | NIFTY D+1: low made later (minute) | +74 min (62 / 106) | +4 min (78 / 131), 0.41 | Rejected |
| B_BDm1_abs_gap | BANKNIFTY D-1 gap smaller than ordinary days | −0.17 % (260 / 449) | −0.01 % (78 / 131), 0.38 | Rejected |

Robustness on discovery + validation (`robustness.csv`): all four keep their sign on the pooled data and after dropping
the best 1 %, but each depends on the discovery years. N_Fa_dir is negative in 2021 and 2024 (both thin). The two
minute candidates are driven by 2022 (+89 and +78 min) and flip sign in 2024. B_BDm1_abs_gap is −0.15 % in the
Thursday regime and −0.07 % / −0.005 % in the two Wednesday regimes (n 17 and 26): it is a "Wednesday has no weekend
gap" effect that disappeared when BANKNIFTY's D-1 moved to Tuesday. Per-row files: `predictions/<id>_<split>.csv`.

## 12. How thin the minute data are
Minute-based targets (returns from the 09:15 bar close, time of high / low, realised vol) exist only for t+1 ≥
2021-10-20: 293 discovery rows per index, 63 expiry days (46 / 44 with a gap ≥ 0.3 %, 27 with ≥ 0.5 %), 15 monthly
expiry days. Validation adds 365 rows and 78 expiry days. With 44-63 expiry days a difference of 0.1 % in 15-minute
return has a standard error of about 0.04 %, so only large effects can be seen; the 15-row monthly cells are
anecdotes (flagged thin, n < 30).

## 13. Findings
| id | Finding | n | Effect | 95 % CI of the condition group | Label |
|---|---|---|---|---|---|
| N_T1 / B_T1 | Gap up → next gap down, vs base | 733 / 691 | +0.4 / +2.1 pts | 21.7-27.9 % / 29.3-36.3 % | Observed (null) |
| N_Xtrend / B_Xtrend | Reversal rises toward expiry | 733 / 935 | slope −0.8 / −0.3 pts per session | – | Observed (null) |
| N_L2 / B_L2 | \|gap\| ≥ 1 %: close-open continues | 116 / 188 | −1.9 / −2.4 pts | 38.6-56.4 % / 37.8-51.8 % | Observed (null) |
| N_ED0_05_cont / B_ED0_05_cont | Expiry-day gap ≥ 0.5 % continues vs other days | 78 / 103 | +0.6 / +2.3 pts | 39.2-60.8 % / 38.2-57.1 % | Observed (null) |
| N_ED0m_se_ret15 | Expiry-day gap ≥ 0.3 %: first 15 min fade (minute) | 46 | −0.12 % vs other days | mean −0.15 to −0.01 % | Observed (q 0.22) |
| N_EDm1_05_soc / B_EDm1_05_soc | D-1 gap ≥ 0.5 % fades during the day | 65 / 88 | −0.39 / −0.52 % vs other days | mean −0.81 to −0.06 % / −0.98 to −0.15 % | Observed (q 0.41 / 0.33) |
| B_Fa_vix | High VIX: 0.1-0.5 % gaps fill more | 132 | +12.1 pts | 76.1-88.7 % | Observed (q 0.22) |
| N_C3 | 15:14 price in top 20 % → gap up (T1515) | 98 | +10.2 pts | 53.4-72.1 % | Observed (q 0.41) |
| N_Fa_dir | Small up gaps fill more than down gaps | 479 | +13.0 pts | 70.2-78.0 % | Rejected (validation) |
| N_BD0_low_min | Expiry-day low later in the session | 62 | +73 min | 168-238 min | Rejected (validation) |
| N_BDp1_low_min | D+1 low later in the session | 62 | +74 min | 170-239 min | Rejected (validation) |
| B_BDm1_abs_gap | BANKNIFTY D-1 gap smaller | 260 | −0.17 % | 0.43-0.57 % | Rejected (validation) |
| SENSEX | Any SENSEX expiry pattern | 0 | – | – | Untestable (calendar starts 2024-10) |

Family: 239 tests (NIFTY 121, BANKNIFTY 118), BH at FDR 10 %, 4 significant, 10 thin. Full log with labels:
`results/gaps/hypotheses.csv`.

## What this does NOT show
- It does not show that gaps are unpredictable in general: only the rules listed in `gaps_specs.py` were tested, on
  index prices, with daily and (from 2021-10) minute data.
- It says nothing about option prices. No option was priced (option minutes exist only from 2024-08, sealed), so
  there is no evidence here for or against any option-buying trade; theta, IV crush and spreads are not modelled.
- The expiry contexts are tied to weekdays in discovery (Thursday expiries); an expiry effect and a weekday effect
  cannot be fully separated before 2023-09.
- "Observed" hints (D-1 fade, expiry-day early fade, high-VIX fill, strong-close → gap up) are not tested rules;
  re-testing any of them now would be a new candidate that has not passed validation.
- SENSEX and the BANKNIFTY monthly-only era (after 2024-11) are not covered.
