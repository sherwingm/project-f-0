# S1 arms A / B · prev (live exit) vs new (+ the fade's -20 % stop), 2025-04-01 to 2026-09-25

Numbers only. Pre-registered: strategies/S1_arms_ab_stop20_study.md. Trades: the live rules (S1 v7 old_expiry) re-run 2026-10-20 (arm B 74 trades as recorded; arm A 175 vs 172 recorded on 2026-10-14, the data has grown). Same entry (d1's VWAP + 1 tick) for both; new adds a -20 % stop on 1-minute prices from the session after entry, filled at min(stop, minute open) - 1 tick; else prev's exit. Net after charges and % slippage. t of the per-trade difference (new - prev), date-clustered.

## Prev vs new

| arm | exit | n | win_pct | mean_pct | median_pct | total_rs | mean_diff_pct | t_diff |
|---|---|---|---|---|---|---|---|---|
| A | prev (S1 v7: 50 % stop at a close, 5-session decay, T-1) | 173 | 15.6 | -7.36 | -57.71 | -87902 |  |  |
| A | new (+ -20 % stop from d1+1 09:16, minutes) | 173 | 6.9 | -11.51 | -25.03 | -132357 | -4.15 | -0.437 |
| B | prev (S1 v7: 50 % stop at a close, 5-session decay, T-1) | 73 | 16.4 | -14.82 | -57.02 | -70163 |  |  |
| B | new (+ -20 % stop from d1+1 09:16, minutes) | 73 | 9.6 | -7.14 | -24.87 | -32478 | 7.69 | 0.736 |

## By year (Rs)

| arm | year | n | prev_rs | new_rs |
|---|---|---|---|---|
| A | 2025 | 71 | -220174 | -109790 |
| A | 2026 | 102 | 132272 | -22567 |
| B | 2025 | 25 | -67428 | -24675 |
| B | 2026 | 48 | -2734 | -7803 |

## The stopped trades

| arm | stopped | stopped on d1+1 | back above entry before prev's exit | reached +50 % | prev better on these | prev on these Rs | new on these Rs |
|---|---|---|---|---|---|---|---|
| A | 161 / 173 | 121 | 46 % | 24 % | 25 | -269022 | -313477 |
| B | 66 / 73 | 52 | 44 % | 21 % | 10 | -166283 | -128598 |

Excluded (both columns): {'no_minute_candles': 2, 'missing_minutes': 1}. Trades: data/results/S1_arms_ab_stop20_trades.csv.
