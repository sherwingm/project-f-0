# S1 fade · carry with a profit-target sell, held to T-1

Pre-registered: strategies/S1_fade_target_carry.md (4df933e7, before the candles were fetched). Numbers only; nothing live changes. Real charges both legs, one lot. Net % of the premium paid.

## Data

331 of 339 trades complete (97.6 %; the bar is 90 %). T-1 = the trading-calendar session before expiry (bhavcopy calendar), and the trade needs candles on day 0 and on that day. Checks: v12 recomputed equals the file's v12 net % (± 0.05) on 100.0 % of trades (bar 95 %); the 09:16 open + 1 tick equals the file's entry on 100.0 %.

Dropped:

| why | trades |
|---|---|
| no candles on T-1 (2024-10-30) | 1 |
| no candles on T-1 (2024-11-27) | 1 |
| no candles on T-1 (2025-02-25) | 2 |
| no candles on T-1 (2025-05-28) | 1 |
| no candles on T-1 (2026-05-25) | 1 |
| no day-0 candles | 2 |


## Whole sample

| rule | n | win % | mean % | median % | total Rs | t | worst % | vs v12 mean diff | vs v12 t | filled at target | mean % at target | sold at T-1 | mean % at T-1 | median sessions held |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v12 | 331 | 55 | 2.16 | 5.7 | 58048 | 1.445 | -71.6 |  |  |  |  |  |  |  |
| C50 | 331 | 60.7 | -8.2 | 48.6 | -120200 | -2.32 | -102.2 | -10.36 | -2.976 | 200 | 48.8 | 131 | -95.2 | 2 |
| C100 | 331 | 44.4 | -9.44 | -85 | -105774 | -1.946 | -103.9 | -11.6 | -2.318 | 144 | 98.7 | 187 | -92.7 | 6 |
| H50 | 331 | 60.4 | -3.02 | 13.7 | -31076 | -1.451 | -69.3 | -5.18 | -2.976 |  |  |  |  |  |


## Halves (train before 2025-11-03, test from it)

| half | rule | n | win % | mean % | median % | total Rs | t | worst % | vs v12 mean diff | vs v12 t | filled at target | mean % at target | sold at T-1 | mean % at T-1 | median sessions held |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| test | v12 | 184 | 56 | 2.58 | 6.3 | 42310 | 1.289 | -71.6 |  |  |  |  |  |  |  |
| test | C50 | 184 | 63 | -4.7 | 48.8 | -19274 | -1.043 | -100.8 | -7.28 | -1.526 | 115 | 48.8 | 69 | -93.9 | 2 |
| test | C100 | 184 | 44.6 | -9.07 | -81.3 | -52424 | -1.426 | -100.9 | -11.65 | -1.728 | 79 | 98.7 | 105 | -90.2 | 6.5 |
| test | H50 | 184 | 62.5 | -1.06 | 13.9 | 11518 | -0.417 | -62.2 | -3.64 | -1.526 |  |  |  |  |  |
| train | v12 | 147 | 53.7 | 1.63 | 4.9 | 15738 | 0.725 | -43.4 |  |  |  |  |  |  |  |
| train | C50 | 147 | 57.8 | -12.57 | 48.5 | -100926 | -2.241 | -102.2 | -14.21 | -2.778 | 85 | 48.8 | 62 | -96.7 | 3 |
| train | C100 | 147 | 44.2 | -9.9 | -85.9 | -53350 | -1.314 | -103.9 | -11.54 | -1.532 | 65 | 98.6 | 82 | -95.9 | 5 |
| train | H50 | 147 | 57.8 | -5.47 | 13.4 | -42594 | -1.597 | -69.3 | -7.1 | -2.778 |  |  |  |  |  |


## Verdict (pre-registered bar)

- **C50: FAIL** — mean > 0 with t >= 2: NO; above v12, paired t >= 2: NO; test: mean > 0 and above v12: NO; train: mean > 0 and above v12: NO
- **C100 (secondary): FAIL** — mean > 0 with t >= 2: NO; above v12, paired t >= 2: NO; test: mean > 0 and above v12: NO; train: mean > 0 and above v12: NO
- **H50 (secondary): FAIL** — mean > 0 with t >= 2: NO; above v12, paired t >= 2: NO; test: mean > 0 and above v12: NO; train: mean > 0 and above v12: NO

H50 needs two lots live (half by v12, half carried); only 17 % of these trades fit two lots in ₹8,000, so a pass would need a ₹16,000 cap per signal. A pass on C50 / C100 / H50 only justifies a paper shadow record (the user's call); the idea came from looking at this data's max up, so a pass is weaker than an out-of-sample one.
