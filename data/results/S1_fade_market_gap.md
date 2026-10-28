# S1 v12 fade · what Nifty does by 09:15 (the gap) vs the fade's failures

335 backtest trades. Gap = Nifty open vs the previous close, known at 09:15, before the 09:16 buy. The day's close is not. The gap and the close move point the same way on 72 % of these days.

## Fail rate by gap direction (p = 0.011)

| group | trades | fail % | mean net % | total Rs |
|---|---|---|---|---|
| gap down | 158 | 52.5 | 1.62 | 24638 |
| gap up | 177 | 38.4 | 3.92 | 41981 |

## By side

| group | trades | fail % | mean net % | total Rs |
|---|---|---|---|---|
| CE / gap down | 42 | 42.9 | 4.9 | 11768 |
| CE / gap up | 52 | 46.2 | 2.38 | 5756 |
| PE / gap down | 116 | 56 | 0.43 | 12870 |
| PE / gap up | 125 | 35.2 | 4.55 | 36224 |

## Gap with the trade (down for a put, up for a call) vs against it (p = 0.004)

| group | trades | fail % | mean net % | total Rs |
|---|---|---|---|---|
| gap against the trade | 167 | 37.1 | 4.64 | 47993 |
| gap with the trade | 168 | 53 | 1.04 | 18626 |

## By gap size

| group | trades | fail % | mean net % | total Rs |
|---|---|---|---|---|
| < -0.5 | 30 | 50 | 4.42 | 6741 |
| -0.5..-0.2 | 57 | 52.6 | 1.97 | 13506 |
| -0.2..0 | 71 | 53.5 | 0.16 | 4391 |
| 0..+0.2 | 74 | 36.5 | 1.75 | 17222 |
| +0.2..+0.5 | 71 | 36.6 | 7.56 | 21269 |
| > +0.5 | 32 | 46.9 | 0.83 | 3489 |
