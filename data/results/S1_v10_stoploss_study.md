# S1 v10 fade · intraday timeline and stop-loss study 2025-2026

Descriptive only: no rule changes. NOT real option minute prices: proxies from the stock's 1-minute candles (strategies/S1_v10_stoploss_study_2025_26.md and its addendum). Not out of sample, and 12 exits are compared, so the best one looks better than it is. Stops and targets fill at their level (optimistic). Read a stop level only where proxies A and B agree.

## Exact check on real prices: single stops and targets (all 434 trades)

Added after the proxy results were seen: computed from the option's REAL day high / low / close, no proxy. A single stop or target only depends on whether the real low / high crossed it. Fills at the level (optimistic in a fast move). The proxies put the same-day exit far above the real close (both miss the fall in option value after results and time decay), so their absolute levels are not reliable.

| exit | n | mean_pct | median_pct | hit_pct | t | total_rs | trades the level fired on (%) | those trades' real 15:20 result (%) |
|---|---|---|---|---|---|---|---|---|
| Same day 15:20, no stop (real close) | 434 | 5.64 | -17.02 | 40.1 | 1.345 | 126164 | 0 |  |
| Stop -20 % | 434 | 6.22 | -22.77 | 24.9 | 1.762 | 147707 | 71.4 | -20.8 |
| Stop -30 % | 434 | 5.05 | -32.55 | 31.6 | 1.37 | 113719 | 59 | -29 |
| Stop -40 % | 434 | 3.61 | -34.5 | 35 | 0.942 | 71904 | 48.6 | -35.8 |
| Stop -50 % | 434 | 3.38 | -25.81 | 37.1 | 0.817 | 66542 | 37.3 | -43.9 |
| Target +30 % | 434 | -2.04 | 24.21 | 63.8 | -1.075 | -77372 | 62.2 | 42.7 |
| Target +50 % | 434 | 1.75 | 24.55 | 54.8 | 0.751 | 19144 | 48.6 | 58.3 |
| Target +100 % | 434 | 7.13 | -10.02 | 45.4 | 2.233 | 141799 | 28.6 | 94.8 |

## Timeline (the same under both proxies: it follows the stock's own low and high)

| trades | peak came before the dip (%) | median peak time | median dip time | peak in the first 30 minutes (%) | dip in the first 30 minutes (%) |
|---|---|---|---|---|---|
| 424 | 43.9 | 09:53 | 09:26 | 47.6 | 58.7 |

### When the peak and the dip happen (share of trades by half-hour)

| half-hour | peaks (%) | dips (%) |
|---|---|---|
| 09:00 | 41.7 | 53.5 |
| 09:30 | 9.7 | 9.9 |
| 10:00 | 6.8 | 5.7 |
| 10:30 | 2.1 | 2.6 |
| 11:00 | 5.7 | 1.7 |
| 11:30 | 3.1 | 3.8 |
| 12:00 | 2.4 | 3.1 |
| 12:30 | 2.1 | 2.6 |
| 13:00 | 2.6 | 1.9 |
| 13:30 | 3.1 | 2.4 |
| 14:00 | 3.8 | 2.4 |
| 14:30 | 5 | 2.4 |
| 15:00 | 12 | 8.3 |

## Proxy A (pre-registered)

Trades 424 of 434; excluded {'no_minute_history': 10, 'stock_did_not_move': 0, 'no_option_prices': 0}. Calibration, median absolute error in % of the entry: 09:15 vs real open 0.0, 15:20 vs real close 24.2, high 14.6, low 14.4. Same-day exit at the REAL close: mean 5.54 %.

### Price levels touched

| touched -20 % (%) | median minutes to -20 % | touched +30 % (%) | median minutes to +30 % | touched +50 % (%) | touched +30 % and sold below entry at 15:20 (%) |
|---|---|---|---|---|---|
| 62.5 | 1 | 63.2 | 0 | 50.9 | 11.8 |

### Exits compared (net % of premium after charges and slippage)

| exit | n | mean_pct | median_pct | hit_pct | t | total_rs |
|---|---|---|---|---|---|---|
| Same day 15:20, no stop (the live rule) | 424 | 28.3 | 10.75 | 55.9 | 6.058 | 764858 |
| Stop -20 % | 424 | 18.65 | -22.67 | 35.4 | 4.754 | 492901 |
| Stop -30 % | 424 | 19.51 | -32.48 | 42.9 | 4.854 | 518595 |
| Stop -40 % | 424 | 17.99 | -13.36 | 46.2 | 4.417 | 483631 |
| Target +30 % | 424 | 2.35 | 24.27 | 67.7 | 1.464 | 69074 |
| Target +50 % | 424 | 7.85 | 40.95 | 61.1 | 3.814 | 223806 |
| Target +100 % | 424 | 18.82 | 14.55 | 57.3 | 6.565 | 506880 |
| Stop -20 % + target +30 % | 424 | 0.13 | -18.81 | 49.3 | 0.11 | 9810 |
| Stop -20 % + target +50 % | 424 | 4.01 | -22.62 | 41.7 | 2.479 | 109959 |
| Stop -30 % + target +50 % | 424 | 4.09 | -1.24 | 49.8 | 2.264 | 119871 |
| Trail 25 % below the highest value | 424 | 19.76 | -1.51 | 48.3 | 5.629 | 493868 |
| Stop -20 % armed from 09:45 | 424 | 32.18 | -21.16 | 46.7 | 7.381 | 845720 |

### By side

| side | exit | n | mean_pct | median_pct | hit_pct | t | total_rs |
|---|---|---|---|---|---|---|---|
| PE | Same day 15:20, no stop (the live rule) | 316 | 29.08 | 8.58 | 54.7 | 4.818 | 597935 |
| PE | Stop -20 % | 316 | 20.3 | -22.67 | 36.1 | 4.145 | 409032 |
| PE | Stop -30 % | 316 | 21.26 | -32.48 | 43.7 | 4.218 | 430073 |
| PE | Stop -40 % | 316 | 19.69 | -8.12 | 46.5 | 3.828 | 404836 |
| PE | Target +30 % | 316 | 2.64 | 24.27 | 67.7 | 1.296 | 57566 |
| PE | Target +50 % | 316 | 8.1 | 41.27 | 60.8 | 3.21 | 178670 |
| PE | Target +100 % | 316 | 18.28 | 16.03 | 56.6 | 5.104 | 375827 |
| PE | Stop -20 % + target +30 % | 316 | 0.66 | 0.34 | 50.3 | 0.478 | 20325 |
| PE | Stop -20 % + target +50 % | 316 | 4.65 | -22.62 | 42.7 | 2.624 | 99960 |
| PE | Stop -30 % + target +50 % | 316 | 5.14 | 3.55 | 50.9 | 2.459 | 115968 |
| PE | Trail 25 % below the highest value | 316 | 20.97 | -0.41 | 48.7 | 5.221 | 409955 |
| PE | Stop -20 % armed from 09:45 | 316 | 33.45 | -22.59 | 46.8 | 6.097 | 666309 |
| CE | Same day 15:20, no stop (the live rule) | 108 | 26.01 | 11.82 | 59.3 | 3.18 | 166923 |
| CE | Stop -20 % | 108 | 13.84 | -22.75 | 33.3 | 1.997 | 83869 |
| CE | Stop -30 % | 108 | 14.4 | -32.48 | 40.7 | 1.975 | 88522 |
| CE | Stop -40 % | 108 | 13.02 | -21.55 | 45.4 | 1.73 | 78795 |
| CE | Target +30 % | 108 | 1.51 | 24.2 | 67.6 | 0.455 | 11508 |
| CE | Target +50 % | 108 | 7.14 | 30.34 | 62 | 1.712 | 45136 |
| CE | Target +100 % | 108 | 20.41 | 12.66 | 59.3 | 3.418 | 131053 |
| CE | Stop -20 % + target +30 % | 108 | -1.42 | -22.59 | 46.3 | -0.63 | -10515 |
| CE | Stop -20 % + target +50 % | 108 | 2.12 | -22.64 | 38.9 | 0.665 | 9999 |
| CE | Stop -30 % + target +50 % | 108 | 1.02 | -21.55 | 46.3 | 0.276 | 3903 |
| CE | Trail 25 % below the highest value | 108 | 16.23 | -3.29 | 47.2 | 2.277 | 83914 |
| CE | Stop -20 % armed from 09:45 | 108 | 28.46 | -18.33 | 46.3 | 3.731 | 179411 |

### Mean net % by half-year

| exit | 2025 H1 | 2025 H2 | 2026 H1 | 2026 Q3 |
|---|---|---|---|---|
| Same day 15:20, no stop (the live rule) | 25.6 | 24.4 | 30 | 34.3 |
| Stop -20 % | 10.3 | 21 | 19.2 | 23 |
| Stop -30 % | 12.5 | 21.5 | 19 | 24.6 |
| Stop -40 % | 12.1 | 20.8 | 16.4 | 22.3 |
| Target +30 % | 3.5 | -0.3 | 2.1 | 5.4 |
| Target +50 % | 7.8 | 7 | 7.1 | 10.2 |
| Target +100 % | 15.3 | 16 | 20.2 | 24.5 |
| Stop -20 % + target +30 % | -3.2 | -0.8 | -0.4 | 5.8 |
| Stop -20 % + target +50 % | -1.4 | 4.8 | 3.1 | 9.8 |
| Stop -30 % + target +50 % | 0.4 | 5 | 2 | 9.7 |
| Trail 25 % below the highest value | 14.4 | 20.5 | 14.1 | 32.9 |
| Stop -20 % armed from 09:45 | 29.5 | 30.1 | 32.6 | 37.4 |

## Proxy B (range-anchored, addendum)

Trades 424 of 434; excluded {'no_minute_history': 10, 'stock_did_not_move': 0, 'no_option_prices': 0}. Calibration, median absolute error in % of the entry: 09:15 vs real open 14.6, 15:20 vs real close 15.6, high 0.0, low 0.0. Same-day exit at the REAL close: mean 5.54 %.

### Price levels touched

| touched -20 % (%) | median minutes to -20 % | touched +30 % (%) | median minutes to +30 % | touched +50 % (%) | touched +30 % and sold below entry at 15:20 (%) |
|---|---|---|---|---|---|
| 71.2 | 0 | 61.6 | 0 | 48.1 | 13 |

### Exits compared (net % of premium after charges and slippage)

| exit | n | mean_pct | median_pct | hit_pct | t | total_rs |
|---|---|---|---|---|---|---|
| Same day 15:20, no stop (the live rule) | 424 | 26.09 | 2.23 | 52.4 | 5.148 | 646660 |
| Stop -20 % | 424 | 13.43 | -22.76 | 27.8 | 3.071 | 329148 |
| Stop -30 % | 424 | 14.4 | -32.55 | 37.5 | 3.172 | 354738 |
| Stop -40 % | 424 | 14.58 | -34.89 | 42.5 | 3.12 | 356667 |
| Target +30 % | 424 | 1.99 | 24.18 | 65.3 | 1.162 | 36876 |
| Target +50 % | 424 | 8.06 | 29.68 | 59.9 | 3.79 | 193597 |
| Target +100 % | 424 | 17.86 | 7.42 | 55.2 | 5.969 | 431484 |
| Stop -20 % + target +30 % | 424 | -3.87 | -22.63 | 41 | -3.183 | -115857 |
| Stop -20 % + target +50 % | 424 | 0.13 | -22.67 | 36.3 | 0.081 | -16154 |
| Stop -30 % + target +50 % | 424 | 1.27 | -32.48 | 46.2 | 0.657 | 17239 |
| Trail 25 % below the highest value | 424 | 16.18 | -3.03 | 46 | 4.699 | 352734 |
| Stop -20 % armed from 09:45 | 424 | 27.1 | -22.61 | 41.5 | 5.688 | 674848 |

### By side

| side | exit | n | mean_pct | median_pct | hit_pct | t | total_rs |
|---|---|---|---|---|---|---|---|
| PE | Same day 15:20, no stop (the live rule) | 316 | 27.42 | 3.67 | 53.2 | 4.204 | 514407 |
| PE | Stop -20 % | 316 | 14.42 | -22.73 | 28.5 | 2.603 | 266320 |
| PE | Stop -30 % | 316 | 16.62 | -32.51 | 39.2 | 2.831 | 309898 |
| PE | Stop -40 % | 316 | 16.54 | -21 | 44 | 2.747 | 306964 |
| PE | Target +30 % | 316 | 3.34 | 24.24 | 67.4 | 1.649 | 53988 |
| PE | Target +50 % | 316 | 9 | 32.22 | 61.4 | 3.514 | 162863 |
| PE | Target +100 % | 316 | 18.06 | 8.72 | 56 | 5.096 | 333594 |
| PE | Stop -20 % + target +30 % | 316 | -2.63 | -22.62 | 43.4 | -1.923 | -61094 |
| PE | Stop -20 % + target +50 % | 316 | 1.17 | -22.65 | 38 | 0.615 | 9462 |
| PE | Stop -30 % + target +50 % | 316 | 3.21 | -12.13 | 48.7 | 1.428 | 53756 |
| PE | Trail 25 % below the highest value | 316 | 16.24 | -0.96 | 48.1 | 4.102 | 279280 |
| PE | Stop -20 % armed from 09:45 | 316 | 28.54 | -22.61 | 42.4 | 4.627 | 537596 |
| CE | Same day 15:20, no stop (the live rule) | 108 | 22.2 | -0.45 | 50 | 2.711 | 132253 |
| CE | Stop -20 % | 108 | 10.54 | -22.94 | 25.9 | 1.537 | 62829 |
| CE | Stop -30 % | 108 | 7.89 | -32.73 | 32.4 | 1.107 | 44840 |
| CE | Stop -40 % | 108 | 8.84 | -42.33 | 38 | 1.102 | 49703 |
| CE | Target +30 % | 108 | -1.99 | 22.98 | 59.3 | -0.557 | -17112 |
| CE | Target +50 % | 108 | 5.32 | 24.49 | 55.6 | 1.233 | 30734 |
| CE | Target +100 % | 108 | 17.29 | 6.08 | 52.8 | 2.955 | 97890 |
| CE | Stop -20 % + target +30 % | 108 | -7.52 | -22.75 | 34.3 | -3.238 | -54763 |
| CE | Stop -20 % + target +50 % | 108 | -2.89 | -22.81 | 31.5 | -0.94 | -25617 |
| CE | Stop -30 % + target +50 % | 108 | -4.41 | -32.57 | 38.9 | -1.212 | -36517 |
| CE | Trail 25 % below the highest value | 108 | 16 | -7.12 | 39.8 | 2.231 | 73455 |
| CE | Stop -20 % armed from 09:45 | 108 | 22.9 | -22.62 | 38.9 | 2.948 | 137252 |

### Mean net % by half-year

| exit | 2025 H1 | 2025 H2 | 2026 H1 | 2026 Q3 |
|---|---|---|---|---|
| Same day 15:20, no stop (the live rule) | 28.4 | 22.4 | 30.4 | 22.5 |
| Stop -20 % | 16.5 | 12.6 | 19.1 | 2.8 |
| Stop -30 % | 15.9 | 12.9 | 20.2 | 6.2 |
| Stop -40 % | 17.2 | 14.3 | 19.1 | 5.4 |
| Target +30 % | -2.4 | 1.2 | 4.8 | 3.4 |
| Target +50 % | 2.3 | 8.5 | 10.7 | 9.4 |
| Target +100 % | 11.1 | 20.7 | 19.5 | 18.2 |
| Stop -20 % + target +30 % | -7.6 | -2.6 | -1.9 | -4.8 |
| Stop -20 % + target +50 % | -3.6 | 2.8 | 1.6 | -2.2 |
| Stop -30 % + target +50 % | -3.9 | 2.4 | 3.7 | 1.1 |
| Trail 25 % below the highest value | 16.9 | 17.7 | 12.8 | 18.4 |
| Stop -20 % armed from 09:45 | 29.2 | 23.6 | 31.6 | 23.2 |
