# S1 v12 fade · is the market up or down when the fade fails?

339 backtest trades (2024-10-17 to 2026-08-17), v12 exit, real charges. Market = Nifty 50 close on day 0 vs the previous close (daily file; it includes the overnight gap). Fail = net < 0. Fisher exact p-values.

## The failures only (152 trades)

Market up on **45 %** of failing days, down on 55 %. Across all trades the market was up on 49 % of days.

## Fail rate by market direction (p = 0.190)

| group | trades | fail % | stopped % | mean net % | total Rs |
|---|---|---|---|---|---|
| down | 173 | 48.6 | 43.9 | 2.46 | 36479 |
| up | 166 | 41 | 36.1 | 3.28 | 31680 |

## By side (puts are the weak-result trades, calls the strong ones)

| group | trades | fail % | stopped % | mean net % | total Rs |
|---|---|---|---|---|---|
| CE / down | 54 | 50 | 44.4 | 0.12 | 2139 |
| CE / up | 42 | 35.7 | 31 | 8.4 | 17501 |
| PE / down | 119 | 47.9 | 43.7 | 3.53 | 34340 |
| PE / up | 124 | 42.7 | 37.9 | 1.54 | 14179 |

## Market with the trade vs against it (p = 1.000)

With = market down for a put, up for a call.

| group | trades | fail % | stopped % | mean net % | total Rs |
|---|---|---|---|---|---|
| market against the trade | 178 | 44.9 | 39.9 | 1.11 | 16318 |
| market with the trade | 161 | 44.7 | 40.4 | 4.8 | 51841 |

## By size of the Nifty move

| group | trades | fail % | stopped % | mean net % | total Rs |
|---|---|---|---|---|---|
| < -1 % | 26 | 38.5 | 30.8 | 7.5 | 12522 |
| -1 to -0.5 | 53 | 45.3 | 39.6 | 5.41 | 19634 |
| -0.5 to 0 | 94 | 53.2 | 50 | -0.59 | 4322 |
| 0 to +0.5 | 80 | 41.2 | 36.2 | 2.58 | 19995 |
| +0.5 to +1 | 60 | 38.3 | 35 | 5.62 | 13541 |
| > +1 % | 26 | 46.2 | 38.5 | 0 | -1856 |

## Days with a big move (|Nifty| >= 0.5 %, 165 trades)

| group | trades | fail % | stopped % | mean net % | total Rs |
|---|---|---|---|---|---|
| down | 79 | 43 | 36.7 | 6.1 | 32157 |
| up | 86 | 40.7 | 36 | 3.92 | 11684 |

## Speed: CSV vs Parquet vs Feather (data/results/S1_v10_bandv10_minutes.csv)

| format | size MB | read s (mean of 3) | read x faster than CSV |
|---|---|---|---|
| CSV | 15.2 | 0.394 | 1 |
| Parquet | 2.2 | 0.107 | 3.7 |
| Feather | 5.8 | 0.088 | 4.5 |


Trade table with the market column: data/results/S1_fade_market_direction_trades.parquet (and .feather).
