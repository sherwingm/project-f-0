# S1 v10 fade · intraday timeline and stop-loss study 2022-2024

Descriptive only: no rule changes. NOT real option minute prices: proxies from the stock's 1-minute candles (strategies/S1_v10_stoploss_study_2025_26.md and its addendum). Not out of sample, and 12 exits are compared, so the best one looks better than it is. Stops and targets fill at their level (optimistic). Read a stop level only where proxies A and B agree.

## Exact check on real prices: single stops and targets (all 436 trades)

Added after the proxy results were seen: computed from the option's REAL day high / low / close, no proxy. A single stop or target only depends on whether the real low / high crossed it. Fills at the level (optimistic in a fast move). The proxies put the same-day exit far above the real close (both miss the fall in option value after results and time decay), so their absolute levels are not reliable.

| exit | n | mean_pct | median_pct | hit_pct | t | total_rs | trades the level fired on (%) | those trades' real 15:20 result (%) |
|---|---|---|---|---|---|---|---|---|
| Same day 15:20, no stop (real close) | 436 | 3.56 | -17.49 | 36.5 | 0.905 | 24190 | 0 |  |
| Stop -20 % | 436 | 3.28 | -22.67 | 23.2 | 0.921 | 26063 | 71.6 | -19.6 |
| Stop -30 % | 436 | 3.88 | -32.52 | 28.4 | 1.027 | 31659 | 58.7 | -30.6 |
| Stop -40 % | 436 | 3.86 | -28.39 | 33 | 1.007 | 40691 | 44.3 | -40.7 |
| Stop -50 % | 436 | 3.65 | -22.43 | 34.6 | 0.938 | 25945 | 31.4 | -50.3 |
| Target +30 % | 436 | -3.96 | 24.26 | 58.9 | -2.068 | -135496 | 57.8 | 43.3 |
| Target +50 % | 436 | -1.84 | -2.07 | 49.5 | -0.803 | -88904 | 42 | 63.1 |
| Target +100 % | 436 | 1.13 | -15.14 | 39.7 | 0.395 | -18695 | 23.9 | 110.4 |

## Timeline (the same under both proxies: it follows the stock's own low and high)

| trades | peak came before the dip (%) | median peak time | median dip time | peak in the first 30 minutes (%) | dip in the first 30 minutes (%) |
|---|---|---|---|---|---|
| 429 | 46.2 | 09:45 | 09:30 | 49.9 | 57.3 |

### When the peak and the dip happen (share of trades by half-hour)

| half-hour | peaks (%) | dips (%) |
|---|---|---|
| 09:00 | 42.2 | 49.7 |
| 09:30 | 12.8 | 12.1 |
| 10:00 | 7 | 4.2 |
| 10:30 | 3.7 | 3.5 |
| 11:00 | 3.5 | 3.3 |
| 11:30 | 2.1 | 3.7 |
| 12:00 | 2.6 | 2.3 |
| 12:30 | 2.3 | 2.8 |
| 13:00 | 1.6 | 1.6 |
| 13:30 | 1.9 | 1.6 |
| 14:00 | 4.9 | 4 |
| 14:30 | 5.8 | 3.3 |
| 15:00 | 9.6 | 7.9 |

## Proxy A (pre-registered)

Trades 429 of 436; excluded {'no_minute_history': 7, 'stock_did_not_move': 0, 'no_option_prices': 0}. Calibration, median absolute error in % of the entry: 09:15 vs real open 0.0, 15:20 vs real close 23.3, high 12.8, low 12.7. Same-day exit at the REAL close: mean 3.57 %.

### Price levels touched

| touched -20 % (%) | median minutes to -20 % | touched +30 % (%) | median minutes to +30 % | touched +50 % (%) | touched +30 % and sold below entry at 15:20 (%) |
|---|---|---|---|---|---|
| 66.2 | 3 | 60.6 | 2 | 42.4 | 10.7 |

### Exits compared (net % of premium after charges and slippage)

| exit | n | mean_pct | median_pct | hit_pct | t | total_rs |
|---|---|---|---|---|---|---|
| Same day 15:20, no stop (the live rule) | 429 | 21.78 | 6.53 | 54.8 | 4.531 | 564109 |
| Stop -20 % | 429 | 11.03 | -22.66 | 32.6 | 2.416 | 272408 |
| Stop -30 % | 429 | 10.52 | -32.5 | 39.6 | 2.269 | 268083 |
| Stop -40 % | 429 | 12.35 | -10.45 | 45.2 | 2.63 | 322401 |
| Target +30 % | 429 | 0.56 | 24.37 | 65.5 | 0.304 | 30680 |
| Target +50 % | 429 | 4.31 | 12.73 | 59 | 2.021 | 126607 |
| Target +100 % | 429 | 12.2 | 7.83 | 55.9 | 4.387 | 333846 |
| Stop -20 % + target +30 % | 429 | -2.13 | -22.61 | 44.3 | -1.741 | -48108 |
| Stop -20 % + target +50 % | 429 | -0.15 | -22.63 | 38 | -0.101 | -560 |
| Stop -30 % + target +50 % | 429 | -1.44 | -32.49 | 44.3 | -0.843 | -33088 |
| Trail 25 % below the highest value | 429 | 7.63 | -6.33 | 43.8 | 3.068 | 187757 |
| Stop -20 % armed from 09:45 | 429 | 21.81 | -22.61 | 43.6 | 4.763 | 562757 |

### By side

| side | exit | n | mean_pct | median_pct | hit_pct | t | total_rs |
|---|---|---|---|---|---|---|---|
| PE | Same day 15:20, no stop (the live rule) | 314 | 21.58 | 4.31 | 53.5 | 3.372 | 391436 |
| PE | Stop -20 % | 314 | 12.44 | -22.65 | 32.5 | 2.044 | 218849 |
| PE | Stop -30 % | 314 | 10.7 | -32.5 | 38.9 | 1.743 | 185859 |
| PE | Stop -40 % | 314 | 11.09 | -16.87 | 42.7 | 1.777 | 195741 |
| PE | Target +30 % | 314 | 0.51 | 24.36 | 64.6 | 0.228 | 8409 |
| PE | Target +50 % | 314 | 3.23 | 10.72 | 57.3 | 1.234 | 57428 |
| PE | Target +100 % | 314 | 10.87 | 6.11 | 54.8 | 3.185 | 205974 |
| PE | Stop -20 % + target +30 % | 314 | -1.66 | -22.61 | 44.9 | -1.076 | -27533 |
| PE | Stop -20 % + target +50 % | 314 | -0.52 | -22.63 | 37.3 | -0.275 | -9669 |
| PE | Stop -30 % + target +50 % | 314 | -2.17 | -32.49 | 43.3 | -1.033 | -45148 |
| PE | Trail 25 % below the highest value | 314 | 7.29 | -6.94 | 42.7 | 2.384 | 120526 |
| PE | Stop -20 % armed from 09:45 | 314 | 21.24 | -22.61 | 41.7 | 3.486 | 394468 |
| CE | Same day 15:20, no stop (the live rule) | 115 | 22.34 | 9.09 | 58.3 | 3.205 | 172672 |
| CE | Stop -20 % | 115 | 7.16 | -22.67 | 33 | 1.266 | 53560 |
| CE | Stop -30 % | 115 | 10.05 | -32.53 | 41.7 | 1.641 | 82224 |
| CE | Stop -40 % | 115 | 15.79 | 5.98 | 52.2 | 2.562 | 126660 |
| CE | Target +30 % | 115 | 0.7 | 24.38 | 67.8 | 0.197 | 22271 |
| CE | Target +50 % | 115 | 7.26 | 29.11 | 63.5 | 1.709 | 69178 |
| CE | Target +100 % | 115 | 15.82 | 9.22 | 59.1 | 2.877 | 127872 |
| CE | Stop -20 % + target +30 % | 115 | -3.41 | -22.61 | 42.6 | -1.519 | -20574 |
| CE | Stop -20 % + target +50 % | 115 | 0.86 | -22.62 | 40 | 0.288 | 9108 |
| CE | Stop -30 % + target +50 % | 115 | 0.54 | -32.49 | 47 | 0.152 | 12060 |
| CE | Trail 25 % below the highest value | 115 | 8.55 | -4.77 | 47 | 1.745 | 67231 |
| CE | Stop -20 % armed from 09:45 | 115 | 23.38 | -4.32 | 48.7 | 3.827 | 168289 |

### Mean net % by half-year

| exit | 2022 H1 | 2022 H2 | 2023 H1 | 2023 H2 | 2024 H1 | 2024 H2 |
|---|---|---|---|---|---|---|
| Same day 15:20, no stop (the live rule) | 23.7 | 27.8 | 1.4 | 17.7 | 25.9 | 36.6 |
| Stop -20 % | 4.1 | 4.1 | 2.3 | 6 | 16.5 | 24.9 |
| Stop -30 % | 5.6 | -2.4 | -0.1 | 6.8 | 15.9 | 24 |
| Stop -40 % | 16.1 | 2.2 | -2.5 | 6.3 | 13.8 | 26.5 |
| Target +30 % | 1.4 | 9.3 | -10.1 | 5.1 | 4.5 | 1.2 |
| Target +50 % | 2.9 | 16.6 | -5.6 | 7.7 | 8.1 | 6.9 |
| Target +100 % | 11.5 | 23.9 | -5.4 | 12.6 | 17.8 | 21.6 |
| Stop -20 % + target +30 % | -5.8 | -2.6 | -4.8 | 0.7 | 2.2 | -2.3 |
| Stop -20 % + target +50 % | -6.6 | -0.1 | -1.7 | 1.8 | 5.6 | 0.6 |
| Stop -30 % + target +50 % | -6.9 | -6.7 | -2.1 | 0.8 | 3.2 | -0.9 |
| Trail 25 % below the highest value | 6.4 | -5.9 | -1.3 | 11.6 | 10.2 | 13.2 |
| Stop -20 % armed from 09:45 | 17.3 | 11.7 | 10.7 | 14.7 | 26.3 | 38.3 |

## Proxy B (range-anchored, addendum)

Trades 429 of 436; excluded {'no_minute_history': 7, 'stock_did_not_move': 0, 'no_option_prices': 0}. Calibration, median absolute error in % of the entry: 09:15 vs real open 12.8, 15:20 vs real close 14.8, high 0.0, low 0.0. Same-day exit at the REAL close: mean 3.57 %.

### Price levels touched

| touched -20 % (%) | median minutes to -20 % | touched +30 % (%) | median minutes to +30 % | touched +50 % (%) | touched +30 % and sold below entry at 15:20 (%) |
|---|---|---|---|---|---|
| 72 | 1 | 57.6 | 1 | 42 | 12.8 |

### Exits compared (net % of premium after charges and slippage)

| exit | n | mean_pct | median_pct | hit_pct | t | total_rs |
|---|---|---|---|---|---|---|
| Same day 15:20, no stop (the live rule) | 429 | 24.06 | -2.01 | 48.5 | 4.683 | 561431 |
| Stop -20 % | 429 | 11.12 | -22.68 | 25.4 | 2.255 | 223192 |
| Stop -30 % | 429 | 14.03 | -32.52 | 33.3 | 2.77 | 293188 |
| Stop -40 % | 429 | 16.17 | -16.69 | 40.1 | 3.219 | 362762 |
| Target +30 % | 429 | 0.78 | 24.26 | 61.3 | 0.468 | 1935 |
| Target +50 % | 429 | 5.39 | 11.41 | 54.8 | 2.617 | 116465 |
| Target +100 % | 429 | 12.33 | -0.26 | 49.7 | 4.56 | 290129 |
| Stop -20 % + target +30 % | 429 | -3.33 | -22.62 | 40.8 | -2.619 | -111857 |
| Stop -20 % + target +50 % | 429 | -0.31 | -22.63 | 34.7 | -0.196 | -44760 |
| Stop -30 % + target +50 % | 429 | -0.86 | -32.49 | 41.7 | -0.474 | -56185 |
| Trail 25 % below the highest value | 429 | 9.92 | -5.41 | 44.5 | 3.158 | 176484 |
| Stop -20 % armed from 09:45 | 429 | 22.42 | -22.62 | 37.1 | 4.424 | 525660 |

### By side

| side | exit | n | mean_pct | median_pct | hit_pct | t | total_rs |
|---|---|---|---|---|---|---|---|
| PE | Same day 15:20, no stop (the live rule) | 314 | 25.29 | -5.65 | 46.2 | 3.667 | 405100 |
| PE | Stop -20 % | 314 | 12.73 | -22.67 | 24.5 | 1.939 | 173276 |
| PE | Stop -30 % | 314 | 14.93 | -32.52 | 31.2 | 2.208 | 205036 |
| PE | Stop -40 % | 314 | 17.58 | -18.04 | 37.9 | 2.594 | 263491 |
| PE | Target +30 % | 314 | 0.29 | 24.24 | 59.9 | 0.136 | -15866 |
| PE | Target +50 % | 314 | 4.29 | 7.13 | 52.5 | 1.671 | 54591 |
| PE | Target +100 % | 314 | 10.44 | -5.51 | 47.1 | 3.161 | 166067 |
| PE | Stop -20 % + target +30 % | 314 | -3.2 | -22.62 | 40.8 | -2.159 | -80716 |
| PE | Stop -20 % + target +50 % | 314 | -0.52 | -22.63 | 33.8 | -0.283 | -40493 |
| PE | Stop -30 % + target +50 % | 314 | -1.95 | -32.49 | 39.5 | -0.921 | -68150 |
| PE | Trail 25 % below the highest value | 314 | 10.81 | -5.65 | 44.6 | 2.748 | 124135 |
| PE | Stop -20 % armed from 09:45 | 314 | 22.99 | -22.63 | 35 | 3.463 | 375677 |
| CE | Same day 15:20, no stop (the live rule) | 115 | 20.69 | 5.83 | 54.8 | 3.121 | 156331 |
| CE | Stop -20 % | 115 | 6.75 | -22.69 | 27.8 | 1.168 | 49916 |
| CE | Stop -30 % | 115 | 11.56 | -32.5 | 39.1 | 1.726 | 88153 |
| CE | Stop -40 % | 115 | 12.34 | -3.55 | 46.1 | 1.811 | 99271 |
| CE | Target +30 % | 115 | 2.13 | 24.35 | 65.2 | 0.706 | 17801 |
| CE | Target +50 % | 115 | 8.4 | 23.51 | 60.9 | 2.307 | 61874 |
| CE | Target +100 % | 115 | 17.51 | 8.76 | 56.5 | 3.462 | 124062 |
| CE | Stop -20 % + target +30 % | 115 | -3.7 | -22.63 | 40.9 | -1.656 | -31141 |
| CE | Stop -20 % + target +50 % | 115 | 0.24 | -22.64 | 37.4 | 0.083 | -4267 |
| CE | Stop -30 % + target +50 % | 115 | 2.13 | -11.55 | 47.8 | 0.637 | 11965 |
| CE | Trail 25 % below the highest value | 115 | 7.51 | -3.93 | 44.3 | 1.643 | 52349 |
| CE | Stop -20 % armed from 09:45 | 115 | 20.84 | -22.61 | 42.6 | 3.352 | 149983 |

### Mean net % by half-year

| exit | 2022 H1 | 2022 H2 | 2023 H1 | 2023 H2 | 2024 H1 | 2024 H2 |
|---|---|---|---|---|---|---|
| Same day 15:20, no stop (the live rule) | 28.6 | 32.7 | 4.1 | 19.8 | 25.6 | 38.1 |
| Stop -20 % | 12.1 | 20.2 | 0.8 | 3.4 | 14.4 | 20.9 |
| Stop -30 % | 16.1 | 14.5 | -0.4 | 14.2 | 16.1 | 22.8 |
| Stop -40 % | 17.7 | 26.9 | -2 | 16.9 | 18.7 | 26.7 |
| Target +30 % | 3.2 | 8.9 | -5.4 | 2.4 | 1.5 | 1.1 |
| Target +50 % | 7.4 | 20.2 | -2.1 | 5.7 | 8.5 | 5.3 |
| Target +100 % | 14.3 | 28.2 | -5.4 | 15.1 | 17.1 | 17.9 |
| Stop -20 % + target +30 % | -0.8 | 5.6 | -4.8 | -2.4 | -3.8 | -5.8 |
| Stop -20 % + target +50 % | 2.1 | 11.3 | -3.2 | 0.6 | 1.8 | -4.1 |
| Stop -30 % + target +50 % | 1.5 | 6.4 | -2.4 | 0.3 | 1.6 | -5.7 |
| Trail 25 % below the highest value | 9.3 | -1.9 | 2.8 | 13.3 | 9.3 | 16.4 |
| Stop -20 % armed from 09:45 | 23.3 | 24.1 | 11.3 | 11.5 | 22.7 | 39 |
