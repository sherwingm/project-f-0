# Pre-expiry price patterns, previous-day candles (module `pricepath`, Agent 2)

Written 2026-11-05. Design: `reports/lld/pricepath.md` (written before the code). Code: `scripts/pricepath_common.py`,
`pricepath_discovery.py`, `pricepath_validate.py`, `pricepath_extras.py`. Tests: `tests/test_pricepath.py`
(7 pass, `results/pricepath/tests_stdout.txt`). Every number below is in a CSV under `results/pricepath/`.

Data: open panels only (`panel_io.load_panel`), NIFTY and BANKNIFTY, discovery 2018-01 → 2022-12, validation
2023-01 → 2024-06. No raw data, no sealed data, no S1/S2/S3 material. Rows whose label crosses a split or a Muhurat
session are dropped. **SENSEX: Untestable.** Its expiry calendar starts 2024-10 (sealed period), so the open panel
has no SENSEX expiry tags.

## How the work was done
1. Discovery only: an event study (Part A), the listed pre-expiry hypotheses as exact rules (Part B) and
   previous-day candle features (Part C). 1,899 tests in one family; Benjamini-Hochberg at FDR 10 % over all of
   them. 154 are BH-significant, 142 with n >= 30. Log: `hypotheses.csv`.
2. Frozen before validation (`candidates_frozen.csv`, 170 rows): the 142 Suggestive tests plus the main form of each
   listed hypothesis H1-H6 for weekly and monthly expiry days (28 rows), frozen even when not significant.
3. One validation pass (`validation.csv`, sha256 of the frozen file recorded in each row). Pass rule fixed in advance:
   same sign, one-sided p < 0.05 against the validation base of the same rows, effect at least half the discovery
   effect. A candidate with validation n < 10 is not judged.
4. Robustness on discovery + validation (`robustness.csv`): drop the best 1 % of outcomes, per year, per weekday
   regime, per VIX tercile, neighbouring thresholds.

Terms. D0 = expiry session, D-k = k sessions before it, D+1 = the session after. `range_n` and `cc_n` = the day's
range and |close-to-close return| divided by the 14-day ATR known the evening before (so calm and wild years compare).
"Big move" = the next session moves at least 1 % away from the previous close at some point (`y_big_move_exc`).
Context W0 / M0 = the next session is a weekly / monthly expiry; X = the next session is not an expiry.

## Part A: what the index does around expiry (discovery, `eventstudy.csv`)
Weekly expiries, each position vs every other session of the weekly era (all discovery weeklies were Thursdays):
| | NIFTY range_n | p | BANKNIFTY range_n | p | BANKNIFTY persistence | p |
|---|---|---|---|---|---|---|
| D-4 | 0.921 vs 0.914 | 0.90 | 0.925 vs 0.939 | 0.73 | 0.55 vs 0.53 | 0.61 |
| D-3 | 0.959 vs 0.907 | 0.28 | 0.957 vs 0.934 | 0.56 | 0.57 vs 0.53 | 0.28 |
| D-2 | 0.901 vs 0.918 | 0.62 | 0.902 vs 0.944 | 0.19 | 0.54 vs 0.53 | 0.79 |
| D-1 | 0.850 vs 0.927 | 0.014 | 0.892 vs 0.946 | 0.08 | 0.54 vs 0.53 | 0.73 |
| D0 | **0.834 vs 0.931** | 0.006 (q 0.075) | 0.885 vs 0.948 | 0.045 | **0.43 vs 0.55** | 0.002 (q 0.033) |
| D+1 | 0.947 vs 0.909 | 0.47 | 0.966 vs 0.932 | 0.44 | 0.54 vs 0.53 | 0.85 |

- On weekly expiry days the index range was **smaller**, not larger, than on other days (NIFTY n = 156). The
  same-weekday placebo (NIFTY 2018, no weeklies, non-monthly Thursdays) was 0.903 vs 0.938 (n = 41, p = 0.59).
- BANKNIFTY weekly D0 closed in the direction opposite to D-1 more often (persistence 43 % vs 55 %).
- D-3 (Monday) gaps are larger and D-1 (Wednesday) gaps smaller; these are weekday effects of the weekend, not expiry.
- Minute realized volatility on weekly D0 was not different (NIFTY 0.683 vs 0.732, n = 48, p = 0.14).
- Monthly expiries vs matched non-monthly weeks and vs the calendar-shuffled placebo (2,000 draws,
  `placebo_shuffle.csv`): only 5 of 98 shuffle tests were BH-significant. The notable one: NIFTY monthly D-3 (the
  Monday before) averaged **-0.38 %** close-to-close vs +0.04 % in shuffled weeks (n = 60, shuffle p = 0.0035,
  q = 0.048). BANKNIFTY monthly D0 closed up 63 % vs 47 % (q = 0.09). Monthly D-4 ranges were larger (both underlyings, q <= 0.04).

Validation of these (`validation.csv`): the weekly D0 smaller range vanished (NIFTY 0.943 vs 0.930, n = 60);
BANKNIFTY D0 low persistence kept its sign (-0.08) but missed (p = 0.12); the monthly D-4 range and BANKNIFTY monthly
D0 up-close effects failed. NIFTY monthly D-3 passed on n = 18 (-0.03 % vs +0.26 %, effect -0.29, one-sided p = 0.033).
It is fragile: n < 30, and the discovery mean includes 2020-03-23 (-13 %); without the worst 1 % the disc+val effect
is still -0.22 % and 5 of 7 years are negative.

Weekday check (`bn_weekday_check.csv`, BANKNIFTY 2023-09 → 2024-06, after weeklies moved to Wednesday): expiry
Wednesdays range_n 1.01 (n = 33) and persistence 0.48; non-expiry Thursdays range_n 0.97 (n = 36), persistence 0.61.
Once the expiry moved, the expiry day was no longer the quieter day. With these n this is Observed only.

## Part B: the listed hypotheses (main forms, discovery; `candidates_frozen.csv` rows PPC142-169)
Each rule is decided at TCLOSE(t); t+1 is the expiry (W0 weekly, M0 monthly); thresholds are discovery quantiles.
| Hypothesis (rule) | NIFTY W0: n, rate vs base, p | NIFTY M0 | BANKNIFTY W0 | BANKNIFTY M0 |
|---|---|---|---|---|
| H1 rise then fall: 3-day return >= q80 and >= 2 up closes → expiry closes down | 32, 50 % vs 47 %, 0.86 | 11, 36 % vs 48 % | 45, 58 % vs 53 %, 0.56 | 10, 30 % vs 37 % |
| H2 decline then recovery: 3-day return <= q20 and >= 2 down closes → expiry closes up | 25, 44 % vs 53 %, 0.43 | 12, 33 % vs 52 % | 33, 58 % vs 47 %, 0.23 | 7 |
| H3 sideways (NR4) → big move on expiry | 46, 50 % vs 45 %, 0.56 | 18, 39 % vs 50 % | 51, 71 % vs 65 %, 0.46 | 19, 74 % vs 73 % |
| H4 big move (abs return >= q80) → reversal on expiry | 24, 29 % vs 45 %, 0.15 | 13 | 37, 62 % vs 57 %, 0.62 | 13 |
| H5 >= 2 failed upside breakouts in 3 days → down | 15, 47 % vs 47 % | 4 | 21, 48 % vs 53 % | 7 |
| H5 >= 2 failed downside breakouts → up | 12, 75 % vs 53 %, 0.15 | 4 | 15, 47 % vs 47 % | 3 |
| H6 close within 0.5 % of a 500 / 1000 round number → quiet expiry | 41, 32 % vs 24 %, 0.27 | 12 | 53, 15 % vs 24 %, 0.15 | 16 |

None is significant; the M0 cells are all n < 30. In validation the W0 cells have n = 2 to 28; NR4 and round-number
rules failed (n = 17-28), the rest had n < 10 and were not judged (labels in `validation.csv`). Variants (other thresholds, D-1 targets,
X and ALL contexts) are in `hypotheses.csv`. Two variants were BH-significant but on all days, not expiry days, and
both failed validation: after a 3-day decline, a >= q80 sharp rise next day (NIFTY X 20 % vs 11 %); after a narrow
3-day range, fewer big moves (volatility clustering, the opposite of "sideways then a big move").

## Part C: previous-day candle → next session (discovery)
1,294 single-feature tests (19 TCLOSE features and 5 T1515 features, low and high quintile, 4 targets, 4 contexts,
2 underlyings) and 31 two-condition rules built from discovery singles. BH-significant by target: big move 117 of 329;
gap up 5 of 387; open-to-close up 2 of 305; first-30-minute return up 3 of 304. In W0 / M0 contexts only big-move
tests were significant (NIFTY W0 9, M0 2 with n < 30; BANKNIFTY W0 10); none for gap, oc or ret30.
Direction tests (gap, oc, ret30) that were Suggestive all failed validation, e.g. BANKNIFTY 15:14 down >= 0.79 % from
the open → fewer gap-ups (42 % vs 64 %, n = 57; validation -6 pts, p = 0.23).

## Validation and robustness (`validation.csv`, `findings.csv`, `robustness.csv`)
170 frozen: 23 Passed-validation, 88 Rejected, 36 not judged (validation n < 10; mostly "VIX >= 22" or "ATR high"
rules, which almost never fired in calm 2023-24), 23 primaries Observed (validation n < 10; none had discovery support).
All 23 passed candidates are also robust (drop-best-1 % same sign, >= 2/3 of years and VIX terciles, neighbours).
22 of 23 are one family: **after a down day, a 5-day fall, a large range, a VIX jump or heavy futures volume, the
next session is more likely to move >= 1 % from the previous close; after >= 3 up closes it is less likely.**
| Example | Discovery n, rate vs base | Validation n, rate [95 % CI] vs base, p |
|---|---|---|
| NIFTY close-to-close <= -0.68 % → big move next session (PPC025) | 247, 69 % vs 46 % | 47, 45 % [31-59] vs 21 %, < 0.001 |
| BANKNIFTY close-to-close <= -0.91 % → big move (PPC092) | 246, 86 % vs 68 % | 38, 61 % [45-74] vs 40 %, 0.008 |
| NIFTY >= 3 up closes → big move less likely (PPC062) | 236, 34 % vs 46 % | 67, 12 % [6-22] vs 21 %, 0.035 |

This is not an expiry effect (`expiry_vs_nonexpiry.csv`, disc+val): e.g. NIFTY down-day rule, next session weekly
expiry 67 % vs base 39 % (n = 30), monthly 88 % vs 49 % (n = 17), non-expiry 64 % vs 40 % (n = 247). For BANKNIFTY the
lift is smaller on expiry days than on other days (down-day rule W0 +12 pts, X +23 pts).

## What a buyer of options could do with it (no option price was used here)
- Big-move family: the excursion is measured from the previous close, so it includes the overnight gap, which a TCLOSE
  signal (earliest entry: next open) cannot capture. VIX already rises after down days, so option premiums price part
  of it. Only an option-price test (final period, coordinator) can say whether a bought straddle / strangle at the next
  open earns anything.
- NIFTY monthly D-3 weakness: a put bought at the D-3 open would be the test; n = 18 in validation, so treat as a lead,
  not a result.

## Findings
| Id | Finding | n (disc / val) | Effect (disc / val) | Val 95 % CI | Label |
|---|---|---|---|---|---|
| A1 | NIFTY weekly D0 range smaller than other days | 156 / 60 | -0.10 / +0.01 ATR | 0.84-1.05 | Rejected |
| A2 | BANKNIFTY weekly D0 reverses D-1 direction more often | 201 / 60 | -12 / -8 pts | 32-58 % | Rejected (same sign, p 0.12) |
| A3 | NIFTY monthly D-3 return below shuffled weeks | 60 / 18 | -0.42 / -0.29 % | -0.27 to +0.22 % (mean) | Passed-validation, n < 30 |
| A4 | Monthly D-4 range larger (both) / BANKNIFTY monthly D0 up | 60 / 18 | +0.18-0.20 ATR / +17 pts | – | Rejected |
| B1-B6 | Listed pre-expiry sequences (rise→fall, fall→rise, NR4→big, big→reversal, failed breakouts, round numbers) | 3-53 per cell | none significant | – | Rejected / Observed (too small) |
| C1 | Down day / 5-day fall / big range / VIX jump / heavy futures volume → next-session big move; >= 3 up closes → fewer (22 rules) | 117-247 / 14-87 | 9-27 / 9-31 pts (abs) | see `findings.csv` | Passed-validation (generic, not expiry-specific) |
| C2 | Previous-day wick / gap / futures OI → next gap, oc or first-30-min direction (PPC029, 030, 085, 127, 128, 141) | 51-247 | 10-25 pts (abs) | – | Rejected |
| C3 | 15:14 intraday drop → next gap down (T1515) | 48-57 / 27-49 | -20 to -25 / -4 to -13 pts | – | Rejected |
| S | SENSEX expiry questions | – | – | – | Untestable (calendar only from 2024-10) |

## What this does NOT show
- No option was priced. A bigger chance of a 1 % move is not a profit for a bought straddle; premiums were not tested.
- Nothing is Validated; Passed-validation candidates wait for the coordinator's single final-period test.
- The big-move family is volatility clustering on all days, not an expiry pattern; expiry days add nothing measurable.
- Monthly results rest on 60 discovery and 18 validation expiries; weekly D0 in discovery is always Thursday, so
  expiry and weekday are mixed there; the BANKNIFTY Wednesday months (2023-09 →) are the only clean split and are short.
- Minute-based features and the 30-minute target have only about 300 discovery rows (2021-10 → 2022-12).
- Three-condition rules were not searched; 36 frozen rules (high-VIX ones) could not be judged in calm 2023-24.
