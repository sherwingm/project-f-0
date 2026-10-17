# S1 v10 fade · descriptive backtest 2025-01-01 .. 2026-09-25

Numbers only. strategies/S1_v10_backtest_2025_26.md.

Descriptive only: no gate, no promotion, no rule change follows. **Not out of sample**: 2025-01-01 onward is the holdout S1 v8 already used, the fade pattern was seen on 2021-2026 in S1 v9, and the E2 exit was chosen after the eight carried trades were seen. Entry is day 0's open + 1 tick; the live fill is the ask at the first poll that fits, later and dearer. The live liquidity test (two-sided quote, spread <= 10 %) is a >= 50 contract count here.

Net % of premium after charges and slippage. Headline tables use the trades valid under both exits (433 of 434 traded; exclusions below). t is date-clustered on day 0.

## All trades

| group | exit | n | hit_pct | mean_pct | median_pct | p10 | p90 | t | total_rs | avg_lot_rs | held_sessions | exit_stop_pct | exit_trail_pct | exit_t_minus_1_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | E1 same day | 433 | 40 | 5.6 | -17.07 | -67.6 | 109.8 | 1.332 | 124446 | 6333 | 0 |  |  |  |
| all | E2 carry rule | 433 | 24.2 | -10.78 | -36.52 | -70.3 | 71.7 | -2.595 | -286244 | 6333 | 1.4 | 67.7 | 30 | 2.3 |

## Puts (strong numbers) and calls (weak numbers)

| group | exit | n | hit_pct | mean_pct | median_pct | p10 | p90 | t | total_rs | avg_lot_rs | held_sessions | exit_stop_pct | exit_trail_pct | exit_t_minus_1_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PE | E1 same day | 322 | 40.7 | 7.06 | -15.96 | -67.6 | 116.8 | 1.289 | 126231 | 6370 | 0 |  |  |  |
| PE | E2 carry rule | 322 | 24.8 | -8.78 | -35.58 | -70.4 | 71.9 | -1.656 | -167729 | 6370 | 1.4 | 67.1 | 30.1 | 2.8 |
| CE | E1 same day | 111 | 37.8 | 1.36 | -23.27 | -65.7 | 95.8 | 0.175 | -1786 | 6226 | 0 |  |  |  |
| CE | E2 carry rule | 111 | 22.5 | -16.58 | -37.92 | -69.7 | 66.2 | -2.358 | -118515 | 6226 | 1.4 | 69.4 | 29.7 | 0.9 |

## By period (day 0)

| group | exit | n | hit_pct | mean_pct | median_pct | p10 | p90 | t | total_rs | avg_lot_rs | held_sessions | exit_stop_pct | exit_trail_pct | exit_t_minus_1_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025 H1 | E1 same day | 90 | 36.7 | 2.61 | -20.21 | -69.5 | 79.1 | 0.241 | 1700 | 6335 | 0 |  |  |  |
| 2025 H1 | E2 carry rule | 90 | 25.6 | -0.44 | -43.24 | -71.6 | 133 | -0.034 | 8231 | 6335 | 1.4 | 70 | 27.8 | 2.2 |
| 2025 H2 | E1 same day | 123 | 40.7 | 5.66 | -17.37 | -70.6 | 100.2 | 0.933 | 47819 | 5999 | 0 |  |  |  |
| 2025 H2 | E2 carry rule | 123 | 22.8 | -13.45 | -36.44 | -72.2 | 61.1 | -2.189 | -92569 | 5999 | 1.4 | 69.1 | 27.6 | 3.3 |
| 2026 H1 | E1 same day | 136 | 45.6 | 9.9 | -8.56 | -66.8 | 119.6 | 1.254 | 84144 | 6519 | 0 |  |  |  |
| 2026 H1 | E2 carry rule | 136 | 27.2 | -14.32 | -34.6 | -69.3 | 58 | -2.207 | -120277 | 6519 | 1.3 | 64 | 33.8 | 2.2 |
| 2026 Q3 | E1 same day | 84 | 33.3 | 1.73 | -19.59 | -60.2 | 109.4 | 0.174 | -9217 | 6518 | 0 |  |  |  |
| 2026 Q3 | E2 carry rule | 84 | 20.2 | -12.2 | -35.27 | -64.1 | 68.1 | -1.392 | -81629 | 6518 | 1.4 | 69 | 29.8 | 1.2 |

## Side report: entry at day 0's premium VWAP + 1 tick

| group | exit | n | hit_pct | mean_pct | median_pct | p10 | p90 | t | total_rs | avg_lot_rs | held_sessions | exit_stop_pct | exit_trail_pct | exit_t_minus_1_pct |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all | E1 same day | 434 | 24.9 | -14.91 | -15.85 | -46.3 | 17.2 | -12.752 | -398896 | 6573 | 0 |  |  |  |
| all | E2 carry rule | 434 | 11.1 | -24.94 | -35.93 | -59.9 | 3.3 | -7.83 | -700290 | 6573 | 1.4 | 80.2 | 18.4 | 1.4 |

## The stock's day-0 open to close, signed (positive = it moved against the headline, as the fade bets)

| side | n | stock_open_to_close_signed_mean_pct | t |
|---|---|---|---|
| PE | 322 | 0.625 | 3.087 |
| CE | 111 | 0.698 | 2.197 |
| all | 433 | 0.644 | 4.216 |

## Exclusions by exit (counted; "none" = valid)

| entry | e1_none | e2_none | e2_contract_changed | e2_price_adjusted |
|---|---|---|---|---|
| open | 434 | 433 | 1 | 0 |
| vwap | 436 | 434 | 1 | 1 |

## Signals removed, in order

| entry | signals | traded | premium_below_2 | walk_below_band | walk_no_liquid_strike_in_band |
|---|---|---|---|---|---|
| open | 499 | 434 | 61 | 1 | 3 |
| vwap | 499 | 436 | 54 | 0 | 9 |
