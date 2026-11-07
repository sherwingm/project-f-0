# Tradeability: NIFTY ATM straddle on real option minutes

Written 2026-11-05. Design `reports/lld/tradeability.md` (written before the code). Code
`scripts/tradeability_common.py`, `scripts/tradeability_run.py` (one run, about 5 minutes). Outputs in
`results/tradeability/`: `trades.csv` (one row per trade), `skipped.csv`, `summary_signals.csv`,
`summary_expiry.csv`, `summary_splits.csv`, `run_stdout.txt`. Follows the "Tradeability" part of
`FINAL_TEST_PLAN.md`. Nothing was committed. No orders.

## Short answer
- **No Validated size signal is tradeable.** Every rule that predicts a *bigger* move (PPC032, OC13 = OC21, OC17,
  M143, and their union) loses money net of costs in every expiry x exit x slippage cell. The plan's pass rule
  (flagged beats unflagged and is positive) holds in 2 of 162 flagged cells, both M220 with exit (iii) at 0.5 %
  slippage: +0.8 % (expiry a, n 72, t 0.18) and +0.7 % (expiry b, n 97, t 0.20). That is noise, not an edge: t is
  about 0.2, it turns negative at 1 % slippage, and M220 predicts a *smaller* move, so a bought straddle doing
  better when it fires goes against the rule's own logic (corrected after the final review).
- **Expiry itself is not tradeable either** by buying the straddle. Expiry day (D0) and D-1 lose on average,
  like every other day.
- **But the expiry day has the big intraday swings.** On D0 the same-day straddle reached **+100 % or more at some
  minute on 22 of 107 days (21 %)**. Mean max up was +53 %, median +27 %. You cannot know the top in advance.
  Exit at 15:15 loses 7 % on average; a +20 % target wins 63 % of days but still loses 8 % on average.
- All results are negative at 0.5 %, 1 % and 2 % slippage. Costs make it worse, not the sign.

## What was traded (per plan)
| Item | Rule |
|---|---|
| Entry | buy CE + PE at the strike nearest the NIFTY 09:15 open (50-point grid), at the close of the 09:16 minute |
| Expiry (a) | nearest NIFTY expiry on or after the trade day (can be the day itself) |
| Expiry (b) | nearest NIFTY expiry after the trade day |
| Exit (i) | 15:15 close |
| Exit (ii) | first minute the straddle is up 20 % (gross), else 15:15 |
| Exit (iii) | 09:16 close of the next session (not possible when the contract expires on the trade day) |
| Slippage | per leg, entry and exit: s normally, 2s before 09:30 or from 15:00; s = 0.5 (base), 1, 2 % |
| Charges | charges.py formula, 1 lot (lot size from bhavcopy: 25, 75, 65); about 0.76 % of premium at lot 75 / 65, 1.5 % at lot 25 |
| Result | net % of premium = (sale - cost - charges) / cost |
| Max up | best straddle close while held / entry - 1, gross (before costs) |

Signal day t, trade day t+1. Flags from `results/final/flags_NIFTY.csv`. The 8 NIFTY rules labelled Validated (size)
are all used: PPC032, PPC062, OC13, OC17, OC21, M143, M218, M220. OC13 and OC21 are the same rule, so their rows
are identical. PPC062, M218 and M220 predict a *smaller* move; for them a straddle should do *worse* when flagged.
"UP5" = flagged by any of the five rules that predict a bigger move (PPC032, OC13, OC17, OC21, M143).
Benchmarks: every day, and unflagged days. Extra family (user request): every expiry day, every D-1, no signal.

Note: (a) and (b) differ only on expiry days. On every other day the nearest expiry on or after t+1 is also the
nearest one after it. So D-1 and "other" rows are the same for (a) and (b).

## Data
- Trades span 2024-09-26 to 2026-10-23: 503 days priced with expiry (a), 504 with (b), 359 of 359 minutes present on
  every priced day (09:17 to 15:15).
- Duplicates: expiry 2026-10-19 has rows from two sources for the same minute (upstox and kotak; prices differ on
  about 7 % of pairs). The upstox row was kept, as in the rest of that folder. No duplicate left (checked).
- Skipped and listed in `skipped.csv`, never filled:

| Reason | Days (a) | Dates |
|---|---|---|
| no option-minute folder or file | 65 | 2024-07-01 to 2024-09-25 (minutes start with expiry 2024-10-03); 2026-10-26 to 10-29 |
| ATM strike has no 09:16 bar | 7 | 2024-12-20 to 12-26 (the 2024-12-26 folder holds one strike only); 2026-10-21, 10-22, 10-28 |
| no lot size (Saturday sessions) | 2 | 2025-02-01, 2026-02-01 |
| exit (iii) not possible (expires that day) | 107 | every expiry day, expiry (a) |

## 1. Signals (expiry a, exit 15:15, slippage 0.5 %)
| Group | n | Win | Mean net | Median | t | Max up mean | Max up >= 100 % | vs unflagged, p |
|---|---|---|---|---|---|---|---|---|
| Every day | 503 | 31 % | -4.6 % | -8.6 % | -2.5 | +24 % | 4.8 % | |
| PPC032 flagged | 105 | 29 % | -10.1 % | -10.3 % | -2.7 | +23 % | 4.8 % | -6.9, 0.95 |
| PPC062 flagged (smaller) | 56 | 21 % | -6.3 % | -11.7 % | -0.8 | +23 % | 1.8 % | -1.9, 0.60 |
| OC13 = OC21 flagged | 244 | 31 % | -4.6 % | -8.2 % | -1.9 | +21 % | 2.9 % | 0.0, 0.50 |
| OC17 flagged | 243 | 32 % | -6.0 % | -7.7 % | -3.2 | +19 % | 1.6 % | -2.9, 0.79 |
| M143 flagged | 63 | 32 % | -9.5 % | -7.3 % | -1.6 | +25 % | 6.3 % | -5.7, 0.81 |
| M218 flagged (smaller) | 108 | 29 % | -3.8 % | -8.8 % | -0.9 | +25 % | 6.5 % | +1.0, 0.42 |
| M220 flagged (smaller) | 97 | 33 % | -3.3 % | -7.6 % | -0.7 | +28 % | 6.2 % | +1.5, 0.38 |
| UP5 flagged | 305 | 32 % | -4.0 % | -8.5 % | -1.7 | +24 % | 4.3 % | +1.5, 0.35 |
| UP5 unflagged | 195 | 30 % | -5.4 % | -8.5 % | -1.8 | +25 % | 5.6 % | |

"vs unflagged" = flagged mean minus unflagged mean, one-sided Welch p (flagged better).
Other exits and expiry (b): `summary_signals.csv`. Across all 6 expiry x exit cells at 0.5 % slippage, every flagged
group of a bigger-move rule has a negative mean. The only positive flagged mean is M220 with exit (iii)
(+0.8 % (a), n 72, t 0.2; p 0.09 vs unflagged), a smaller-move rule, so the sign is against its own logic.
"Worth trading" (flagged beats unflagged and is positive) holds in **2 of 162** flagged cells (column
`worth_trading` in `summary_signals.csv`, now computed for every rule; `size_view_consistent` = False for both):
M220, exit (iii), 0.5 % slippage, expiry (a) +0.83 % (n 72, t 0.18, diff +6.8 pp, p 0.090) and expiry (b)
+0.71 % (n 97, t 0.20, diff +6.0 pp, p 0.062). Both turn negative at 1 % slippage. It is false for every other
rule, exit, expiry and slippage, and for every bigger-move rule without exception.

Why a correct size forecast still loses: M143 flags fire mostly at high VIX (60 of 63 in the top VIX tercile).
The option is already priced for the move, so the straddle gains no edge.

## 2. Expiry family, no signal (slippage 0.5 %)
| Group (expiry, exit) | n | Win | Mean net | Median | t | Worst | Max up mean / median | >= 100 % |
|---|---|---|---|---|---|---|---|---|
| D0, (a) same-day, 15:15 | 107 | 36 % | -7.2 % | -25.9 % | -0.9 | -101 % | +53 % / +27 % | 21 % (22) |
| D0, (a), +20 % target | 107 | 63 % | -8.1 % | +17.5 % | -2.0 | -101 % | (capped) | |
| D0, (b) next week, 15:15 | 108 | 32 % | -3.5 % | -6.6 % | -2.7 | -28 % | +9 % / +4 % | 0 % |
| D0, (b), next 09:16 | 105 | 30 % | -2.0 % | -7.4 % | -1.0 | -28 % | +13 % / +6 % | 0 % |
| D-1, 15:15 | 107 | 30 % | -6.2 % | -12.0 % | -2.6 | -42 % | +20 % / +13 % | 0.9 % (1) |
| D-1, +20 % target | 107 | 41 % | -4.0 % | -7.0 % | -2.0 | -42 % | (capped) | |
| D-1, next 09:16 (into expiry) | 107 | 32 % | -7.7 % | -23.2 % | -1.7 | -63 % | +27 % / +14 % | 5.6 % (6) |
| Other days, 15:15 | 289 | 30 % | -3.0 % | -7.2 % | -2.8 | -38 % | +15 % / +9 % | 0.3 % (1) |

D0 weekly (84) vs monthly (23), (a), 15:15: mean -4.3 % vs -18.0 %. Neither D0 nor D-1 beats the other days
(one-sided p 0.67 and 0.74). D0 win rate with the +20 % target: 63 % (95 % CI 53-72 %), but the losing 37 % lose most
of the premium (worst -101 % after costs: 2024-10-24, straddle 155 -> 1.7).

## 3. Max up while held, by days to expiry (exit i, slippage 0.5 %, every day)
| Days to expiry | n | Mean net | Max up mean | Max up median | >= +100 % |
|---|---|---|---|---|---|
| 0 (expiry day, expiry a) | 107 | -7.2 % | +53 % | +27 % | 20.6 % (22) |
| 1 | 107 | -6.2 % | +20 % | +13 % | 0.9 % (1) |
| 2 | 107 | -3.5 % | +18 % | +11 % | 0 % |
| 3+ (expiry a) | 182 | -2.7 % | +14 % | +8 % | 0.5 % (1) |
| 3+ (expiry b, incl. D0 next week) | 290 | -3.0 % | +12 % | +6 % | 0.3 % (1) |

UP5 flagged on expiry day (n 48): max up mean +62 %, median +31 %, 23 % reach +100 %; mean net -1.1 %.
Max up is measured on minute closes after the fact. It is the most a perfect exit could get, not a result.

## 4. By VIX tercile of t (expiry a, exit 15:15, slippage 0.5 %)
Cut points 12.56 / 14.49 (VIX at t, all 577 final sessions).

| Group | Low VIX: n, mean | Mid: n, mean | High: n, mean |
|---|---|---|---|
| Every day | 190, -3.5 % | 141, -3.4 % | 172, -6.7 % |
| D0 | 39, -10.3 % | 31, -5.7 % | 37, -5.3 % |
| D-1 | 41, +0.8 % | 28, -5.0 % | 38, -14.8 % |
| UP5 flagged | 60, +2.9 % | 95, -2.8 % | 150, -7.5 % |
| PPC032 flagged | 21, +8.3 % | 29, -15.5 % | 55, -14.3 % |

The few positive cells are small (t below 1) and come from slicing many groups; they are not findings.
High VIX is the worst cell almost everywhere: the straddle is dearest exactly when the size rules fire.

## 5. Slippage (mean net %, expiry a)
| Group, exit | 0.5 % | 1 % | 2 % |
|---|---|---|---|
| Every day, 15:15 | -4.6 | -6.5 | -10.2 |
| UP5 flagged, 15:15 | -4.0 | -5.9 | -9.6 |
| D0, 15:15 | -7.2 | -9.1 | -12.7 |
| D0, +20 % target | -8.1 | -9.7 | -12.7 |
| D-1, 15:15 | -6.2 | -8.1 | -11.7 |

Edge minutes (09:16 entry, 15:15 / 09:16 exit) pay double, so 1 % means 2 % at both ends here.

## Drawdown
Drawdown = largest fall of the running sum of net % (one premium per trade), in trade-date order. Every-day
straddle, (a), 15:15: 2,736 % of one premium (the running sum mostly falls). UP5 flagged: 1,419 %. D0 same-day:
1,209 %. Full numbers in the summary CSVs (`dd`).

## Sensitivity (added after the final review; `scripts/tradeability_sensitivity.py`, `sensitivity.csv`)
Descriptive only. (a) Next-minute fill: all 314 target hits re-priced at the close of the next minute with both
legs. (b) Tick floor: slippage per leg = max(s % x price, Rs 0.05).

| Group, expiry a, slip 0.5 % | As run | Tick floor | Next-minute fill | Both |
|---|---|---|---|---|
| Every day, 15:15 | -4.59 % | -4.60 % | -4.59 % | -4.60 % |
| D0, 15:15 | -7.21 % | -7.25 % | -7.21 % | -7.25 % |
| D0, +20 % target | -8.08 % (win 63 %) | -8.10 % | -8.48 % | -8.50 % (win 61 %) |
| UP5 flagged, +20 % target | -3.40 % | -3.40 % | -3.36 % | -3.36 % |
| M220 flagged, exit (iii) | +0.83 % | +0.83 % | +0.83 % | +0.83 % |

Both effects are small and make the results slightly worse (or leave them unchanged). The same 2 M220 cells are
the only ones that meet the plan rule under every variant (`sensitivity_stdout.txt`). No conclusion changes.

## Limits
- Trade prices only, no bid / ask. Slippage is assumed; real ATM spreads on expiry day can be wider at the edges.
- Charges use the 2026-04-01 rates for the whole period (earlier exchange fees differ slightly).
- One lot. At lot 25 (to early 2025) flat brokerage is about 1.5 % of premium, twice the later share.
- Option minutes start with expiry 2024-10-03, so about 3 months of the final period (2024-07 to 09) cannot be
  priced. Flags priced: PPC032 105 of 117, PPC062 56 of 76, OC13 244 of 280, OC17 243 of 281, M143 63 of 71,
  M218 108 of 138, M220 97 of 126; all 503 of 577 sessions for the every-day benchmark.
- The +20 % trigger uses the minute close; an intraminute touch is not counted. The exit is filled at the close of
  the trigger minute, which a live order cannot do; see "Sensitivity" below for the next-minute fill.
- Slippage is a percentage with no tick floor; legs under Rs 2 on expiry day would really pay at least one 0.05
  tick. See "Sensitivity" below.
- p-values here are descriptive (many groups, no gate). The tradeability step is not a test with a BH family.
- Max up is hindsight. A rule that sells at +100 % would need its own pre-registered test on new data.
- No other strategy (strangles, selling, other strikes) was tried; the plan fixed the ATM straddle.
