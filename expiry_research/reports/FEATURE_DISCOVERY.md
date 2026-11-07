# Feature discovery (module `model`, Agent 4)

Design: `reports/lld/model.md` (written before the code). Scripts: `scripts/model_discovery.py` (discovery
only), `scripts/model_validate.py` (frozen candidates, once), `scripts/model_tables.py` (tables). Data: the panels via
`panel_io.load_panel` for NIFTY and BANKNIFTY, target sessions 2018-01 .. 2024-06. Nothing sealed was read.

**Resumed run.** The first run of this module stopped on a usage limit during the walk-forward. Discovery,
freezing and validation had already finished: `candidates_frozen.csv` was written at 07:35:56 and validation at
07:37:16 on 2026-11-05, and the file's SHA-256 is still
`9b9490102276daaedde3519c7e55cbdde55088cacc4085d111c05670fe75aa4d`, the value stored in
`candidates_frozen.sha256` and in every row of `candidates_validation.csv`. The 241 validated ids are exactly the 241
frozen ids (`tests/test_model.py`). Nothing was re-frozen and validation was not re-run.

## How the search worked
- One row per target session s, with features known at one of three cutoffs: `D2` (close two sessions before s),
  `TCLOSE` (close of the session before s, D-1 when s is an expiry), `T1515` (15:15 of D-1; no close-of-day values
  of D-1). Calendar of s is known in advance.
- Targets: gap up, first 15 / 30 / 60 minutes up, open-to-close up, gap filled, big excursion (≥ 1 % from the
  previous close), big close-to-close move (|cc| ≥ 1 %), |gap|, high and low versus the previous close.
- Tests, discovery rows only (s ≤ 2022-12-31): calendar contexts (D0, D0w, D0m, D-1..D-5, D+1, weekday);
  univariate terciles; every pair of the 6 best features (median splits); honest depth-3 trees (fit on the first
  60 %, leaves tested on the last 40 %). Binary: exact binomial vs the base rate of the same rows. Continuous:
  one-sample t vs the same rows' mean.
- BH at FDR 10 % over the whole discovery family: **28,518 tests, 3,336 significant** (`hypotheses_discovery.csv`,
  `discovery_stdout.txt`). Tests are strongly correlated (the same volatility signal appears in many forms), so the
  count of hits overstates the number of independent findings.

## Result 1: expiry day itself is not special for any target (discovery)
Context tests: s = expiry day (D0), weekly expiry, monthly expiry, the day before, the day after, compared with all
days. No D0 / D0w / D0m / D-1 / D+1 test was BH-significant for either index; the only significant calendar effects
were Monday (weekend gap: bigger |gap|, fewer gap fills), Wednesday / Tuesday and D-3. All 13 of those calendar
candidates were **Rejected** in validation (`candidates_validation.csv`, stage `context`).

| UL | Target | D0 n | D0 value | all-days value | p | q |
|---|---|---|---|---|---|---|
| NIFTY | gap up | 216 | 0.671 | 0.691 | 0.56 | 0.94 |
| NIFTY | oc up | 216 | 0.481 | 0.485 | 0.95 | 1.00 |
| NIFTY | big excursion | 216 | 0.468 | 0.459 | 0.84 | 1.00 |
| NIFTY | gap filled | 216 | 0.611 | 0.633 | 0.53 | 0.93 |
| BANKNIFTY | gap up | 261 | 0.659 | 0.644 | 0.65 | 0.98 |
| BANKNIFTY | oc up | 261 | 0.456 | 0.470 | 0.66 | 0.98 |
| BANKNIFTY | big excursion | 261 | 0.667 | 0.678 | 0.69 | 0.99 |
| BANKNIFTY | gap filled | 261 | 0.682 | 0.664 | 0.56 | 0.94 |

Source: `hypotheses_discovery.csv`, stage `context`. Minute targets on D0 have n = 63 (2021-10 onward) and nothing
is significant there either.

## Result 2: magnitude is predictable, direction is not
| UL | Target group | tests | BH-significant |
|---|---|---|---|
| NIFTY | direction (gap up, ret15/30/60 up, oc up, gap filled) | 7,482 | 63 |
| NIFTY | magnitude (big moves, |gap|, high / low vs prev close) | 6,601 | 1,581 |
| BANKNIFTY | direction | 7,498 | 77 |
| BANKNIFTY | magnitude | 6,621 | 1,602 |

Source: `tab_discovery_by_target.csv` (sums of its rows). Magnitude hits are 24 % of magnitude tests; direction
hits are under 1 % of direction tests, which is about what a 10 % FDR lets through by chance in a family this size
when a few strong magnitude effects drive the threshold.

The features behind the magnitude hits are all one idea: **how volatile the market already is**. Most frequent
roots among univariate magnitude hits (`tab_discovery_feature_roots.csv`): near-expiry ATM straddle per square-root
day (`d_opt_near_straddle_daily`), VIX close, the session's range, distance below the 20-day high, ATR(14),
10- and 20-day realised volatility, distance from the 55-day high. These are the same signal: volatility clusters,
so a high-implied-vol close is followed by a bigger next-session move. Option-chain positioning features (PCR, max
pain, call / put walls) appear mostly as second legs of pairs.

## Result 3: the simplest rules that matter (frozen, then validated once)
241 candidates were frozen (at most 3 per UL x cutoff x target x context, BH q < 0.10, n ≥ 30). Validation
2023-01 .. 2024-06, pass rule fixed in advance (same sign, one-sided p < 0.05 vs the validation base rate of the same
rows, effect ≥ half the discovery effect, validation n ≥ 20; n < 20 stays Suggestive).

| Label | Direction targets | Magnitude targets | Total |
|---|---|---|---|
| Passed-validation | 0 | 9 | 9 |
| Rejected | 62 | 117 | 179 |
| Suggestive (validation n < 20) | 11 | 42 | 53 |

Source: `tab_candidate_labels.csv`. Every passed rule is a volatility rule:

| id | UL | cutoff | rule (target) | disc n / effect | val n / effect | val p |
|---|---|---|---|---|---|---|
| M143 | NIFTY | TCLOSE | straddle per √day ≥ 0.767 → big excursion | 410 / +0.254 | 20 / +0.339 | 0.001 |
| M134 | NIFTY | D2 | same, one session earlier → big excursion | 409 / +0.245 | 20 / +0.289 | 0.004 |
| M135 | NIFTY | D2 | straddle/√day > 0.667 & ≥ 1.73 % below 20-day high → big excursion | 407 / +0.240 | 38 / +0.184 | 0.008 |
| M118 | NIFTY | D2 | same rule → big close-to-close move | 407 / +0.173 | 38 / +0.106 | 0.039 |
| M218 | NIFTY | TCLOSE | PCR(OI) > 1.006 & straddle/√day ≤ 0.668 → shallower low (pp of prev close) | 390 / +0.212 | 120 / +0.121 | 0.001 |
| M219 | NIFTY | TCLOSE | 55-day-high distance > -2.36 % & PCR > 1.006 → shallower low | 399 / +0.212 | 108 / +0.111 | 0.006 |
| M220 | NIFTY | TCLOSE | PCR > 1.006 & ATR14 ≤ 1.23 % → shallower low | 369 / +0.217 | 115 / +0.123 | 0.002 |
| M006 | BANKNIFTY | T1515 | straddle change ≤ -0.32 & monthly max-pain distance > -0.017 % (D-2 data) → big cc | 73 / +0.206 | 39 / +0.147 | 0.025 |
| M073 | BANKNIFTY | D2 | expiry day only: 10-day HV ≤ 14.45 → lower high vs prev close | 82 / -0.224 | 56 / -0.156 | 0.018 |

Full numbers with Wilson CIs: `tab_passed.csv`, `candidates_validation.csv`. M134 and M143 have only 20 validation
rows (2023-24 was a low-volatility period, so the high-straddle condition was rare): flag n < 30. M006 is a pair
whose first leg is chosen from 6 candidates on ~300 minute-era rows; its 2021 year and the BANKNIFTY Wednesday
regime (n = 9) have the opposite sign (`robustness_groups.csv`).

Robustness (discovery + validation, `candidates_validation.csv` / `robustness_groups.csv`): all 9 keep their sign
after dropping the best 1 % of outcomes and at both neighbouring thresholds; the NIFTY rules have the same sign in
all 7 years and both weekday regimes. The effect shrinks in the high-VIX tercile for M134 / M135 / M143 (most rows
already sit there): the rule is mostly "VIX is high", not something finer.

Whole-module multiple testing: with walk-forward (792) and VIX-baseline (96) tests added, the module's log
`hypotheses.csv` holds 29,639 tests; BH at 10 % over all of it (`q_bh_all`) keeps 6 of the 9 passed rules (M134,
M135, M143, M218, M219, M220) and drops M006, M073, M118 (q > 0.1). They keep their Passed-validation label under the
pre-registered pass rule, but are the weakest.

## Directional "hits" did not survive
The strongest directional discovery tests were small subsets (n 18-28 on minute-era expiry days, e.g. BANKNIFTY
first-hour up 0.80 vs 0.47 when the 15:15 realised vol was low, n = 20) or tiny shifts on large sets (BANKNIFTY gap
fill 0.59 vs 0.66 when the near expiry is ≥ 6 days away, n = 487). None of the 73 directional frozen candidates
passed: 62 Rejected, 11 too thin in validation (`tab_direction_best_univariate.csv`, `tab_candidate_labels.csv`).

## SENSEX
SENSEX expiry dates exist only from 2024-10 (sealed period). Every SENSEX expiry question is **Untestable** here.

## Findings
| id | finding | n | effect | 95 % CI / p | label |
|---|---|---|---|---|---|
| FD1 | Expiry day (D0, D0w, D0m) differs from other days in no target | 216 / 261 D0 | within ±0.06 | all q ≥ 0.31 | Observed (no effect) |
| FD2 | Monday / D-3 / Tue / Wed calendar effects | 13 rules | — | all failed validation | Rejected |
| FD3 | High straddle per √day at D-1 close → big NIFTY excursion (M143) | 410 / 20 | +0.25 / +0.34 | val p 0.001, n < 30 | Passed-validation |
| FD4 | Same at D-2 (M134), plus 20-day-high pair (M135, M118) | 409-407 / 20-38 | +0.24 / +0.18-0.29 | val p ≤ 0.04 | Passed-validation |
| FD5 | High PCR + calm market → shallower NIFTY next-day low (M218-M220) | 369-399 / 108-120 | +0.21 / +0.11-0.12 pp | val p ≤ 0.006 | Passed-validation |
| FD6 | BANKNIFTY big cc after straddle drop (M006) | 73 / 39 | +0.21 / +0.15 | val p 0.025 | Passed-validation (fragile) |
| FD7 | BANKNIFTY expiry day after calm 10 days: smaller upside (M073) | 82 / 56 | -0.22 / -0.16 pp | val p 0.018 | Passed-validation |
| FD8 | Any direction rule (gap / first 15-60 min / oc / gap fill) | 73 frozen | — | 0 passed | Rejected |
| FD9 | SENSEX expiry questions | — | — | — | Untestable |

## What this does NOT show
- It does not show any way to know the **direction** of the next session, on expiry days or otherwise.
- "Bigger move" rules say nothing about up or down; with bought options only, they could only matter for a
  long-straddle style position, and option prices already contain the same implied volatility the rules use. No
  option P&L was computed (option minute prices exist only in the sealed period).
- Passed-validation is not Validated: the coordinator's single final-period test is still to come.
- The discovery hit count is not a count of independent effects.
