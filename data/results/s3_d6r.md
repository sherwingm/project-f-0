# S3 D6R: D6's selling structures re-run on 2018-2021 (descriptive)

Page `strategies/S3_D6R_shortvol_2018_2021.md` at commit `248f0130 2026-10-29T20:18:02+05:30`. Script `scanner/s3_d6r.py`. Spot = NSE official NIFTY 50 close.

| Structure | Period | Trades | Win rate | Mean net % of credit | Median | t | Worst | Mean % of margin |
|---|---|---|---|---|---|---|---|---|
| **weekly ATM straddle** | 2018-01 → 2021-12 | 161 | 60 % | -1.5 % | +24.4 % | -0.20 | -486 % | -0.61 % |
| weekly ATM straddle | monthly-only, to Feb 2019 | 12 | 42 % | -28.0 % | -52.2 % | -1.18 | -155 % | -7.10 % |
| weekly ATM straddle | 2018 | 11 | 36 % | -38.9 % | -53.4 % | -1.69 | -155 % | -10.30 % |
| weekly ATM straddle | 2019 | 46 | 61 % | -0.8 % | +22.0 % | -0.06 | -387 % | +0.35 % |
| weekly ATM straddle | 2020 | 52 | 52 % | -12.8 % | +9.1 % | -0.89 | -486 % | -2.22 % |
| weekly ATM straddle | 2021 | 52 | 73 % | +17.2 % | +38.4 % | 1.63 | -206 % | +2.21 % |
| **monthly put k 0.94** | 2018-01 → 2021-12 | 47 | 91 % | -67.6 % | +98.9 % | -0.46 | -6862 % | +0.44 % |
| monthly put k 0.94 | 2018 | 11 | 82 % | +29.6 % | +98.4 % | 0.59 | -453 % | +0.67 % |
| monthly put k 0.94 | 2019 | 12 | 100 % | +98.7 % | +98.8 % | 788.45 | +98 % | +1.97 % |
| monthly put k 0.94 | 2020 | 12 | 83 % | -489.7 % | +99.4 % | -0.85 | -6862 % | -3.67 % |
| monthly put k 0.94 | 2021 | 12 | 100 % | +99.0 % | +99.1 % | 634.01 | +98 % | +2.79 % |
| **monthly put k 0.98** | 2018-01 → 2021-12 | 47 | 81 % | -17.1 % | +99.5 % | -0.33 | -2092 % | +0.86 % |
| monthly put k 0.98 | 2018 | 11 | 73 % | -73.8 % | +99.4 % | -0.82 | -721 % | -3.10 % |
| monthly put k 0.98 | 2019 | 12 | 83 % | +53.6 % | +99.5 % | 1.49 | -324 % | +4.01 % |
| monthly put k 0.98 | 2020 | 12 | 75 % | -133.5 % | +99.6 % | -0.74 | -2092 % | -3.60 % |
| monthly put k 0.98 | 2021 | 12 | 92 % | +80.6 % | +99.5 % | 4.26 | -127 % | +5.80 % |

## Check: official close vs the 15:29 minute close (weekly straddle, expiries 2021-10-21 → 2021-12-31)

10 common trades. Mean net % of credit: official +43.8 %, 15:29 +37.2 %; mean |difference| 10.6 points.
