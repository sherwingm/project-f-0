# S1 v10 fade · sub-Rs 2 entries (the trades the Rs 2 floor refuses)

Numbers only. Pre-registered: strategies/S1_v10_subfloor_entry.md. Windows: day 0 in 2022-01-01 .. 2024-12-31 and 2025-01-01 .. 2026-09-25. v10's walk with the floor at one tick; the lot-cost rule (Rs 600-8,000) and the liquidity rule (>= 50 contracts on day 0) unchanged. Sub-Rs 2 = walk fill (open + 1 tick) below Rs 2. Primary cost model: entry = open + 2 ticks (ask + 1 tick), exit = close - 2 ticks (bid - 1 tick), charges from server/charges.py (Rs 20 brokerage an order), no % slippage. Net % is of the lot value at entry. t is date-clustered. Max drawdown is on cumulative net Rs in day-0 order. "high 2x" = day 0's option high >= 2 x entry. Trade list: data/results/S1_v10_subfloor_trades.csv.

**Verdict: the sub-Rs 2 trades do not add money on top of the >= Rs 2 set.** Under the pre-registered tick model (entry = open + Rs 0.10, exit = close - Rs 0.10, real charges), the 140 sub-Rs 2 trades made Rs -52,517 in total (2022-24: Rs -23,251, 2025-26: Rs -29,267), winning 34.3 % of the time, mean +13.8 % a trade (t 0.579). Without the single best trade the pooled total is Rs -101,429. Conditions failed: 1, 2, 3. The result depends on the cost of crossing the spread: with 1 tick each side instead of 2, the same trades make Rs 29,304 (t 0.953), still far from the pass bar. This is descriptive and not out of sample. The live floor stays at Rs 2; the live shadow-entry track is the fresh test.

## Pass criterion

- 1. total > 0 in each window: **no**
- 2. pooled mean > 0 with t >= 2: **no**
- 3. pooled total > 0 without the largest winner (KALYANKJIL 2025-08-08, Rs 48,911): **no**

## Comparison with the >= Rs 2 set

| set | n | win_pct | mean_pct | median_pct | total_rs | t | max_dd_rs | high_2x_pct | charges_pct_of_lot |
|---|---|---|---|---|---|---|---|---|---|
| >= Rs 2, existing model (open+1 / close-1 tick, % slippage), 2022-24 | 436 | 36.5 | 3.56 | -17.49 | 24190 | 0.905 |  |  |  |
| >= Rs 2, existing model (open+1 / close-1 tick, % slippage), 2025-26 | 434 | 40.1 | 5.63 | -17.02 | 126164 | 1.345 |  |  |  |
| >= Rs 2, this study's tick model (recomputed, not re-run), 2022-24 | 436 | 37.4 | 5.14 | -16.54 | 67299 | 1.292 | 102,595 | 23.2 | 1.08 |
| >= Rs 2, this study's tick model (recomputed, not re-run), 2025-26 | 434 | 41.2 | 7.88 | -16.16 | 187998 | 1.851 | 43,078 | 28.1 | 1.05 |
| sub-Rs 2, tick model, 2022-24 | 81 | 37 | -1.44 | -18.7 | -23251 | -0.147 | 53,288 | 28.4 | 1.06 |
| sub-Rs 2, tick model, 2025-26 | 59 | 30.5 | 34.77 | -32.3 | -29267 | 0.629 | 58,368 | 22 | 1.09 |
| sub-Rs 2, tick model, pooled | 140 | 34.3 | 13.82 | -23.7 | -52517 | 0.579 | 58,368 | 25.7 | 1.07 |

## By entry band, 2022-24

| group | n | win_pct | mean_pct | median_pct | total_rs | max_dd_rs | t | high_2x_pct | charges_pct_of_lot |
|---|---|---|---|---|---|---|---|---|---|
| < Rs 0.50 | 5 | 20 | -53.97 | -80.67 | -18886 | 19,734 | -1.705 | 40 | 1.63 |
| Rs 0.50-1 | 28 | 28.6 | -12.53 | -27.72 | -27716 | 28,843 | -1.041 | 28.6 | 1 |
| Rs 1-1.50 | 27 | 44.4 | 22.22 | -8.87 | 32934 | 17,403 | 0.959 | 25.9 | 1.05 |
| Rs 1.50-2 | 21 | 42.9 | -4.55 | -11.63 | -9584 | 19,531 | -0.37 | 28.6 | 1 |
| all sub-Rs 2 | 81 | 37 | -1.44 | -18.7 | -23251 | 53,288 | -0.147 | 28.4 | 1.06 |

## By entry band, 2025-26

| group | n | win_pct | mean_pct | median_pct | total_rs | max_dd_rs | t | high_2x_pct | charges_pct_of_lot |
|---|---|---|---|---|---|---|---|---|---|
| < Rs 0.50 | 2 | 0 | -98.16 | -98.16 | -11186 | 11,186 | -41.899 | 0 | 0.66 |
| Rs 0.50-1 | 7 | 28.6 | -18.34 | -11.03 | -10298 | 13,072 | -1.284 | 14.3 | 0.91 |
| Rs 1-1.50 | 26 | 34.6 | 104.24 | -36.12 | 11943 | 32,398 | 0.836 | 26.9 | 1.25 |
| Rs 1.50-2 | 24 | 29.2 | -13.92 | -29.47 | -19726 | 24,953 | -1.306 | 20.8 | 1 |
| all sub-Rs 2 | 59 | 30.5 | 34.77 | -32.3 | -29267 | 58,368 | 0.629 | 22 | 1.09 |

## By entry band, pooled

| group | n | win_pct | mean_pct | median_pct | total_rs | max_dd_rs | t | high_2x_pct | charges_pct_of_lot |
|---|---|---|---|---|---|---|---|---|---|
| < Rs 0.50 | 7 | 14.3 | -66.59 | -91.95 | -30071 | 30,919 | -2.856 | 28.6 | 1.35 |
| Rs 0.50-1 | 35 | 28.6 | -13.69 | -22.75 | -38014 | 39,838 | -1.374 | 25.7 | 0.98 |
| Rs 1-1.50 | 53 | 39.6 | 62.46 | -14.62 | 44877 | 32,398 | 1.009 | 26.4 | 1.15 |
| Rs 1.50-2 | 45 | 35.6 | -9.55 | -19.8 | -29309 | 43,617 | -1.198 | 24.4 | 1 |
| all sub-Rs 2 | 140 | 34.3 | 13.82 | -23.7 | -52517 | 58,368 | 0.579 | 25.7 | 1.07 |

## By sessions to expiry after day 0 (pooled)

| group | n | win_pct | mean_pct | median_pct | total_rs | max_dd_rs | t | high_2x_pct | charges_pct_of_lot |
|---|---|---|---|---|---|---|---|---|---|
| <= 2 sessions | 11 | 36.4 | 16.13 | -28.03 | 15954 | 14,608 | 0.276 | 54.5 | 1.1 |
| 3-5 sessions | 22 | 31.8 | -28.15 | -47.45 | -41533 | 51,296 | -1.742 | 40.9 | 1.06 |
| > 5 sessions | 107 | 34.6 | 22.22 | -18.7 | -26938 | 70,202 | 0.728 | 19.6 | 1.07 |
| all sub-Rs 2 | 140 | 34.3 | 13.82 | -23.7 | -52517 | 58,368 | 0.579 | 25.7 | 1.07 |

## By strike distance out of the money from the previous close (pooled)

| group | n | win_pct | mean_pct | median_pct | total_rs | max_dd_rs | t | high_2x_pct | charges_pct_of_lot |
|---|---|---|---|---|---|---|---|---|---|
| <= 2 % OTM (incl. ITM) | 29 | 31 | -14.43 | -40.35 | -32253 | 44,505 | -0.899 | 41.4 | 1.16 |
| 2-5 % OTM | 35 | 40 | 4.78 | -18.43 | 8090 | 24,135 | 0.275 | 28.6 | 1.02 |
| 5-10 % OTM | 55 | 32.7 | 41.45 | -25.83 | -17286 | 38,256 | 0.703 | 16.4 | 1.09 |
| > 10 % OTM | 21 | 33.3 | -4.45 | -11.63 | -11069 | 31,226 | -0.336 | 23.8 | 0.99 |
| all sub-Rs 2 | 140 | 34.3 | 13.82 | -23.7 | -52517 | 58,368 | 0.579 | 25.7 | 1.07 |

## Sensitivity: 1 tick each side (open + Rs 0.05, close - Rs 0.05), same charges

| window | n | win_pct | mean_pct | median_pct | total_rs | max_dd_rs | t | high_2x_pct | charges_pct_of_lot |
|---|---|---|---|---|---|---|---|---|---|
| 2022-24 | 81 | 38.3 | 8.47 | -9.12 | 25628 | 29,452 | 0.84 | 30.9 | 1.13 |
| 2025-26 | 59 | 33.9 | 44.49 | -26.31 | 3676 | 41,417 | 0.774 | 23.7 | 1.15 |
| pooled | 140 | 36.4 | 23.65 | -14.95 | 29304 | 41,417 | 0.953 | 27.9 | 1.14 |

## Liquidity funnel

| window | refused_by_rs2_floor | traded_floor_free_sub_rs2 | sub_rs2_strikes_on_walk_paths | with_ge_50_contracts | share_liquid_pct | two_sided_quote |
|---|---|---|---|---|---|---|
| 2022-24 | 85 | 81 | 203 | 169 | 83.3 | not in the data |
| 2025-26 | 61 | 59 | 112 | 104 | 92.9 | not in the data |


The walk only takes a strike with >= 50 contracts, so every traded strike passed it. The share above is over all the sub-Rs 2 strikes the walk passed on the way. NSE's bhavcopy has no bid or ask, so whether a two-sided quote existed cannot be checked; the live shadow-entry track checks it.
