# S1 v10 fade · descriptive backtest 2022-01-01 .. 2024-12-31

Numbers only. strategies/S1_v10_backtest_2025_26.md.

Descriptive only: no gate, no promotion, no rule change follows. **Not out of sample**: 2021-2024 is S1's test window, already used by v2-v7 and v9, the fade pattern was seen on 2021-2026 in S1 v9, and the E2 exit was chosen after the eight carried trades were seen. Entry is day 0's open + 1 tick; the live fill is the ask at the first poll that fits, later and dearer. The live liquidity test (two-sided quote, spread <= 10 %) is a >= 50 contract count here.

Net % of premium after charges and slippage. Headline tables use the trades valid under both exits (436 of 436 traded; exclusions below). t is date-clustered on day 0.

## All trades

| group | exit | n | hit_pct | mean_pct | median_pct | p10 | p90 | t | total_rs | avg_lot_rs | held_sessions | exit_stop_pct | exit_trail_pct | exit_t_minus_1_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | E1 same day | 436 | 36.5 | 3.56 | -17.49 | -70 | 101.9 | 0.905 | 24190 | 6329 | 0 |  |  |  |
| all | E2 carry rule | 436 | 23.9 | -4.02 | -34.44 | -73.5 | 117 | -0.78 | -138522 | 6329 | 1.4 | 69.7 | 26.1 | 4.1 |

## Puts (strong numbers) and calls (weak numbers)

| group | exit | n | hit_pct | mean_pct | median_pct | p10 | p90 | t | total_rs | avg_lot_rs | held_sessions | exit_stop_pct | exit_trail_pct | exit_t_minus_1_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PE | E1 same day | 318 | 35.5 | 3.69 | -21.87 | -70.4 | 97.9 | 0.708 | -10592 | 6342 | 0 |  |  |  |
| PE | E2 carry rule | 318 | 22 | -3.52 | -34.87 | -72.9 | 116.9 | -0.539 | -115732 | 6342 | 1.3 | 71.7 | 23.6 | 4.7 |
| CE | E1 same day | 118 | 39 | 3.21 | -11.31 | -66.4 | 110.9 | 0.539 | 34782 | 6293 | 0 |  |  |  |
| CE | E2 carry rule | 118 | 28.8 | -5.36 | -33.05 | -75.7 | 105.2 | -0.697 | -22789 | 6293 | 1.8 | 64.4 | 33.1 | 2.5 |

## By period (day 0)

| group | exit | n | hit_pct | mean_pct | median_pct | p10 | p90 | t | total_rs | avg_lot_rs | held_sessions | exit_stop_pct | exit_trail_pct | exit_t_minus_1_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 H1 | E1 same day | 87 | 39.1 | 11.86 | -13.69 | -64.1 | 122.4 | 1.46 | 53343 | 6262 | 0 |  |  |  |
| 2022 H1 | E2 carry rule | 87 | 27.6 | 30 | -29.96 | -64.5 | 168 | 1.572 | 176464 | 6262 | 2 | 66.7 | 26.4 | 6.9 |
| 2022 H2 | E1 same day | 12 | 58.3 | 17.3 | 22.05 | -44.4 | 51.6 | 0.94 | 17507 | 6726 | 0 |  |  |  |
| 2022 H2 | E2 carry rule | 12 | 16.7 | -12.41 | -28.43 | -44.7 | 7.4 | -0.956 | -7451 | 6726 | 1.7 | 66.7 | 33.3 | 0 |
| 2023 H1 | E1 same day | 83 | 24.1 | -14.19 | -33.88 | -73.6 | 73 | -1.584 | -94682 | 6034 | 0 |  |  |  |
| 2023 H1 | E2 carry rule | 83 | 19.3 | -24.73 | -44.48 | -74.1 | 30.1 | -2.828 | -132524 | 6034 | 1 | 79.5 | 20.5 | 0 |
| 2023 H2 | E1 same day | 73 | 39.7 | 1.43 | -11.39 | -62.6 | 76.8 | 0.206 | -6891 | 6393 | 0 |  |  |  |
| 2023 H2 | E2 carry rule | 73 | 23.3 | -3.51 | -35.45 | -65.9 | 111.1 | -0.33 | -21935 | 6393 | 1.8 | 63 | 30.1 | 6.8 |
| 2024 H1 | E1 same day | 87 | 39.1 | 5.35 | -16.12 | -67.1 | 91.6 | 0.557 | 24057 | 6492 | 0 |  |  |  |
| 2024 H1 | E2 carry rule | 87 | 24.1 | -6.48 | -34.12 | -67.1 | 117.3 | -0.831 | -55841 | 6492 | 1.4 | 71.3 | 23 | 5.7 |
| 2024 H2 | E1 same day | 94 | 37.2 | 9.79 | -20.99 | -83.5 | 129.9 | 0.995 | 30857 | 6400 | 0 |  |  |  |
| 2024 H2 | E2 carry rule | 94 | 25.5 | -14.27 | -35.75 | -86.5 | 87.2 | -2.058 | -97233 | 6400 | 1 | 68.1 | 29.8 | 2.1 |

## Side report: entry at day 0's premium VWAP + 1 tick

| group | exit | n | hit_pct | mean_pct | median_pct | p10 | p90 | t | total_rs | avg_lot_rs | held_sessions | exit_stop_pct | exit_trail_pct | exit_t_minus_1_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | E1 same day | 431 | 23.9 | -14.24 | -15.75 | -43.1 | 16 | -10.876 | -358364 | 6429 | 0 |  |  |  |
| all | E2 carry rule | 431 | 13.5 | -20.48 | -33.5 | -61.1 | 24.5 | -5.519 | -520205 | 6429 | 1.5 | 78.9 | 18.6 | 2.6 |

## The stock's day-0 open to close, signed (positive = it moved against the headline, as the fade bets)

| side | n | stock_open_to_close_signed_mean_pct | t |
|---|---|---|---|
| PE | 317 | 0.244 | 1.251 |
| CE | 118 | 0.701 | 2.036 |
| all | 435 | 0.368 | 2.413 |

## Exclusions by exit (counted; "none" = valid)

| entry | e1_none | e2_none |
|---|---|---|
| open | 436 | 436 |
| vwap | 431 | 431 |

## Signals removed, in order

| entry | signals | traded | walk_no_liquid_strike_in_band | premium_below_2 | walk_below_band |
|---|---|---|---|---|---|
| open | 557 | 436 | 32 | 85 | 4 |
| vwap | 557 | 431 | 35 | 85 | 6 |
