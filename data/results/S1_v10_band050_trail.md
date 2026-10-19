# S1 v10 fade · Rs 0.50-1 band: +20 % target with a trailing stop, 1-minute prices

Numbers only. Pre-registered: strategies/S1_v10_band050_trail.md. Entry: the 09:15 minute's close + 2 ticks. Target: entry x 1.20, filled at the first minute whose high >= target + 1 tick. Trailing stop: peak x (1 - trail) against each minute's low before the peak updates, filled at min(stop, open) - 2 ticks; stop first when both touch in a minute. Else the 15:19 minute's close - 2 ticks. Real charges. Net % of the lot value at entry. t date-clustered. Trades: data/results/S1_v10_band050_trades.csv.

**Verdict: R10 (chosen on 2025) does not pass on 2026.** On the 58 trades of 2026 it made Rs -36,802 (mean -24.8 % a trade, t -10.478, win rate 12.1 %) against Rs -58,074 for the 15:20 exit. Under the pre-registration, the Rs 1-2 step is not run on this rule.

## Pass criterion (2026, the chosen rule)

- total net Rs > 0 on 2026: **no**
- mean net % > 0 with t >= 2 on 2026: **no**
- beats the 15:20 baseline's total on 2026: **yes**

## Choose: 2025 (chosen: R10, highest total net Rs)

| variant | n | win_pct | mean_pct | median_pct | total_rs | max_dd_rs | t | target_pct | stop_pct | 15:20_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline 15:20 | 66 | 25.8 | -18.2 | -33.36 | -29559 | 45773 | -2.263 | 0 | 0 | 100 |
| R10 | 66 | 15.2 | -25.57 | -27.55 | -37024 | 37024 | -11.756 | 15.2 | 84.8 | 0 |
| R20 | 66 | 24.2 | -25.56 | -34.18 | -37056 | 37056 | -8.526 | 24.2 | 75.8 | 0 |
| R30 | 66 | 33.3 | -25.6 | -41.39 | -37942 | 37942 | -7.525 | 33.3 | 65.2 | 1.5 |

## Test: 2026 (only the chosen rule counts; the others for information)

| variant | n | win_pct | mean_pct | median_pct | total_rs | max_dd_rs | t | target_pct | stop_pct | 15:20_pct |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline 15:20 | 58 | 12.1 | -41.68 | -48.13 | -58074 | 58074 | -7.856 | 0 | 0 | 100 |
| R10 | 58 | 12.1 | -24.75 | -28.42 | -36802 | 36802 | -10.478 | 12.1 | 87.9 | 0 |
| R20 | 58 | 25.9 | -22.22 | -33.54 | -31940 | 31940 | -6.112 | 25.9 | 74.1 | 0 |
| R30 | 58 | 32.8 | -23.57 | -39.34 | -33898 | 33898 | -6.429 | 32.8 | 65.5 | 1.7 |

## Funnel

| contracts | simulated | no_minute_candles | no_entry_minute |
|---|---|---|---|
| 147 | 124 | 5 | 18 |
