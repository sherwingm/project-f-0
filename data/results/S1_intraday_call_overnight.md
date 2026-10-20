# S1 · call one minute after a strong market-hours result, sold at the next open

Pre-registered: strategies/S1_intraday_strong_call_overnight.md. Entry = the close of the minute after the announcement + 1 tick; exit = the next session's 09:15 minute close - 1 tick; real charges. 1 lot, Rs 600-8,000, >= Rs 2, from the strike nearest the spot upward. t is date-clustered.

## Test: **FAIL (closed with its numbers)**

| test | value | pass |
|---|---|---|
| 1 at least 60 trades | 64 | True |
| 2 mean > 0 and t >= 2 (1 tick) | -13.17 % / t -1.507 | False |
| 3a mean > 0 in 2024-25 | -19.48 | False |
| 3b mean > 0 in 2026 | -3.33 | False |

## Results

| costs | period | n | win_pct | mean_pct | median_pct | total_rs | t |
|---|---|---|---|---|---|---|---|
| 1 tick | all | 64 | 29.7 | -13.17 | -31.72 | -55115 | -1.507 |
| 1 tick | 2024-25 | 39 | 28.2 | -19.48 | -30.54 | -49903 | -2.278 |
| 1 tick | 2026 | 25 | 32 | -3.33 | -41.31 | -5212 | -0.183 |
| 2 ticks | all | 64 | 29.7 | -13.61 | -32.14 | -57141 | -1.559 |
| 2 ticks | 2024-25 | 39 | 28.2 | -20.1 | -30.94 | -51633 | -2.358 |
| 2 ticks | 2026 | 25 | 32 | -3.49 | -41.64 | -5509 | -0.191 |

## Did the stock move? (stock from the entry minute to the next open, from the path study)

| group | n | stock to next open, raw % | adjusted % | option net % |
|---|---|---|---|---|
| all trades | 64 | 0.538 | 0.48 | -13.17 |
| winners | 19 | 2.817 | 2.663 | 69.46 |
| losers | 45 | -0.424 | -0.442 | -48.06 |

## Cases

| outcome | cases |
|---|---|
| traded | 64 |
| no_strike_fits | 38 |
| premium_below_2 | 13 |
| no_next_0915_candle | 3 |

Trades: data/results/S1_intraday_call_overnight_trades.csv.
