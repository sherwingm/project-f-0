# S2 step 2 put backtest report

Numbers only. strategies/S2_step2_short_buildup_put.md.

Signals (step 1's cell): 970; window to 2026-09-25; 1 bought put, Rs 600-8,000 a lot, exit at d+5 (50 % stop, T-1), fill = day d+1 VWAP + 1 tick, net of charges and slippage.

## Main table (net % of premium)

| variant | n | win_pct | mean_pct | median_pct | t | total_rs | avg_lot_rs | exit_0_stop_pct | exit_1_time_pct | exit_2_t_minus_1_pct | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h5 | 580 | 23.1 | -14.21 | -47.42 | -2.709 | -513704 | 6567 | 46.7 | 53.3 | 0 | -34.82 | -6.74 | -37.58 | 10.3 | -3.88 | -24.79 |
| h3 | 583 | 28 | -7.88 | -25.38 | -1.713 | -256956 | 6572 | 24.4 | 75.6 | 0 | -23.59 | -1.92 | -20.7 | 16.42 | -3.86 | -22.68 |
| h5_nostop | 578 | 24 | -15.22 | -39.88 | -2.858 | -544710 | 6570 | 0 | 100 | 0 | -36.94 | -5.63 | -40.25 | 8.77 | -5.43 | -24.83 |

## Signals removed by each filter

| variant | signals | traded | walk_no_liquid_strike_in_band | lottery_refused | in_ban_on_entry_day | walk_below_band | no_strike_or_expiry | outside_window |
|---|---|---|---|---|---|---|---|---|
| h5 | 970 | 585 | 247 | 88 | 41 | 3 | 1 | 5 |
| h3 | 970 | 585 | 248 | 88 | 42 | 3 | 1 | 3 |
| h5_nostop | 970 | 585 | 247 | 88 | 41 | 3 | 1 | 5 |

## The same trades as a 5-session short stock position (step 1's measure)

{'n': 580, 'short_stock_5d_mean': np.float64(0.661), 'short_stock_5d_t': 3.161}

## By strike distance below the stock (h5)

| strike below the stock | n | win_pct | mean_pct | median_pct | t | total_rs | avg_lot_rs | exit_0_stop_pct | exit_1_time_pct | exit_2_t_minus_1_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| above spot | 4 | 25 | -11.73 | -11.9 | -0.816 | -3089 | 4880 | 0 | 100 | 0 |
| 0-2 % | 31 | 25.8 | -30.91 | -53.23 | -3.318 | -63198 | 6095 | 51.6 | 48.4 | 0 |
| 2-5 % | 126 | 23 | -7 | -42.95 | -0.382 | -48945 | 6858 | 44.4 | 55.6 | 0 |
| 5-10 % | 249 | 23.3 | -9.7 | -40.43 | -1.474 | -149288 | 6685 | 43 | 57 | 0 |
| > 10 % | 170 | 22.4 | -23.16 | -54.87 | -4.319 | -249183 | 6305 | 54.1 | 45.9 | 0 |

## Pass test (h5)

| test | value | result |
|---|---|---|
| net mean > 0 after costs (% of premium) | -14.21 | fail |
| date-clustered t >= 2 | -2.709 | fail |
| positive in >= 5 of 6 years incl. 2025 and 2026 | 1 of 6 (2025 -3.88, 2026 -24.79) | fail |
| N >= 200 | 580 | pass |
| OVERALL |  | FAIL |
