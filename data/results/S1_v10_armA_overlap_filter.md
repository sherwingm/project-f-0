# S1 fade · drop the trades where Arm A also fires (H = hindsight close, O = the 09:15 open)

Numbers only. Pre-registered: strategies/S1_v10_armA_overlap_filter.md. v10 backtest trades, entry at the option's day-0 open, E1 same-day exit, net after charges. A trade is dropped when its stock is up >= 2 % more than its sector (and < 10 % raw): H at the day-0 close (Arm A's own signal, known only after the fade's sale), O at the day-0 open (known at 09:15). t is date-clustered.

## Test (O, both sides): **FAIL (nothing changes)**

| test | n | value | pass |
|---|---|---|---|
| 1a O-dropped lose in 2022-24 (mean < 0) | 79 | 12.41 | False |
| 1b O-dropped lose in 2025-26 (mean < 0) | 69 | -15.35 | True |
| 2 pooled O-dropped t <= -2 | 148 | -0.07 | False |
| 3 O-dropped lose under v11 (minutes, mean < 0) | 78 | 4.69 | False |

## All groups, v10 exit (E1)

| window | side | group | n | win_pct | mean_pct | median_pct | total_rs | t |
|---|---|---|---|---|---|---|---|---|
| 2022-24 | all | all trades | 436 | 36.5 | 3.56 | -17.49 | 24190 | 0.905 |
| 2022-24 | all | H keep | 327 | 41.3 | 10.48 | -11.76 | 154001 | 2.038 |
| 2022-24 | all | H drop | 107 | 22.4 | -17.42 | -43.64 | -129138 | -2.37 |
| 2022-24 | all | H unknown (kept) | 2 | 0 | -5.72 | -5.72 | -672 | -7.587 |
| 2022-24 | all | O keep | 355 | 36.3 | 1.64 | -16.53 | 10073 | 0.418 |
| 2022-24 | all | O drop | 79 | 38 | 12.41 | -25.08 | 14789 | 1.024 |
| 2022-24 | all | O unknown (kept) | 2 | 0 | -5.72 | -5.72 | -672 | -7.587 |
| 2022-24 | PE | all trades | 318 | 35.5 | 3.69 | -21.87 | -10592 | 0.708 |
| 2022-24 | PE | H keep | 229 | 45.9 | 20.71 | -7.88 | 235373 | 2.91 |
| 2022-24 | PE | H drop | 87 | 9.2 | -40.9 | -50.14 | -245293 | -8.332 |
| 2022-24 | PE | H unknown (kept) | 2 | 0 | -5.72 | -5.72 | -672 | -7.587 |
| 2022-24 | PE | O keep | 241 | 35.3 | 1.28 | -21.29 | -15015 | 0.244 |
| 2022-24 | PE | O drop | 75 | 37.3 | 11.67 | -25.24 | 5096 | 0.911 |
| 2022-24 | PE | O unknown (kept) | 2 | 0 | -5.72 | -5.72 | -672 | -7.587 |
| 2022-24 | CE | all trades | 118 | 39 | 3.21 | -11.31 | 34782 | 0.539 |
| 2022-24 | CE | H keep | 98 | 30.6 | -13.42 | -16.46 | -81373 | -2.868 |
| 2022-24 | CE | H drop | 20 | 80 | 84.71 | 101.08 | 116155 | 4.222 |
| 2022-24 | CE | O keep | 114 | 38.6 | 2.41 | -12.54 | 25089 | 0.406 |
| 2022-24 | CE | O drop | 4 | 50 | 26.26 | 2.43 | 9694 | 0.65 |
| 2025-26 | all | all trades | 434 | 40.1 | 5.64 | -17.02 | 126164 | 1.345 |
| 2025-26 | all | H keep | 308 | 47.4 | 15.36 | -4.41 | 276285 | 3.015 |
| 2025-26 | all | H drop | 126 | 22.2 | -18.13 | -43.69 | -150122 | -2.99 |
| 2025-26 | all | O keep | 365 | 42.7 | 9.6 | -14.48 | 188251 | 2 |
| 2025-26 | all | O drop | 69 | 26.1 | -15.35 | -36.44 | -62087 | -2.005 |
| 2025-26 | PE | all trades | 322 | 40.7 | 7.06 | -15.96 | 126231 | 1.289 |
| 2025-26 | PE | H keep | 218 | 56.4 | 30.78 | 7.78 | 415111 | 4.408 |
| 2025-26 | PE | H drop | 104 | 7.7 | -42.68 | -48.12 | -288880 | -12.603 |
| 2025-26 | PE | O keep | 259 | 44.4 | 12.55 | -8.12 | 181346 | 2.014 |
| 2025-26 | PE | O drop | 63 | 25.4 | -15.53 | -36.44 | -55114 | -1.871 |
| 2025-26 | CE | all trades | 112 | 38.4 | 1.55 | -22.57 | -68 | 0.201 |
| 2025-26 | CE | H keep | 90 | 25.6 | -22.01 | -34.95 | -138826 | -4.227 |
| 2025-26 | CE | H drop | 22 | 90.9 | 97.93 | 59.01 | 138758 | 5.101 |
| 2025-26 | CE | O keep | 106 | 38.7 | 2.4 | -21.33 | 6905 | 0.303 |
| 2025-26 | CE | O drop | 6 | 33.3 | -13.5 | -45.27 | -6973 | -0.46 |
| 2022-26 | all | all trades | 870 | 38.3 | 4.59 | -17.02 | 150354 | 1.603 |
| 2022-26 | all | H keep | 635 | 44.3 | 12.85 | -8.4 | 430286 | 3.552 |
| 2022-26 | all | H drop | 233 | 22.3 | -17.8 | -43.64 | -279260 | -3.795 |
| 2022-26 | all | H unknown (kept) | 2 | 0 | -5.72 | -5.72 | -672 | -7.587 |
| 2022-26 | all | O keep | 720 | 39.6 | 5.68 | -15.98 | 198324 | 1.827 |
| 2022-26 | all | O drop | 148 | 32.4 | -0.53 | -27.98 | -47298 | -0.07 |
| 2022-26 | all | O unknown (kept) | 2 | 0 | -5.72 | -5.72 | -672 | -7.587 |
| 2022-26 | PE | all trades | 640 | 38.1 | 5.38 | -17.31 | 115639 | 1.428 |
| 2022-26 | PE | H keep | 447 | 51 | 25.62 | 0.98 | 650484 | 5.135 |
| 2022-26 | PE | H drop | 191 | 8.4 | -41.87 | -49.22 | -534173 | -14.472 |
| 2022-26 | PE | H unknown (kept) | 2 | 0 | -5.72 | -5.72 | -672 | -7.587 |
| 2022-26 | PE | O keep | 500 | 40 | 7.12 | -15.8 | 166330 | 1.736 |
| 2022-26 | PE | O drop | 138 | 31.9 | -0.74 | -27.98 | -50019 | -0.091 |
| 2022-26 | PE | O unknown (kept) | 2 | 0 | -5.72 | -5.72 | -672 | -7.587 |
| 2022-26 | CE | all trades | 230 | 38.7 | 2.4 | -16.17 | 34715 | 0.497 |
| 2022-26 | CE | H keep | 188 | 28.2 | -17.53 | -28.05 | -220198 | -4.99 |
| 2022-26 | CE | H drop | 42 | 85.7 | 91.64 | 82.27 | 254913 | 6.647 |
| 2022-26 | CE | O keep | 220 | 38.6 | 2.4 | -16.17 | 31994 | 0.493 |
| 2022-26 | CE | O drop | 10 | 40 | 2.4 | -18.64 | 2721 | 0.103 |

## Minute trades (Oct 2024 to Sep 2026): v11 exit and v10 exit

| window | side | group | n | win_pct | mean_pct | median_pct | total_rs | t |
|---|---|---|---|---|---|---|---|---|
| v11 exit (minutes) | all | all trades | 468 | 24.6 | 8.83 | -21.07 | 216629 | 2.373 |
| v11 exit (minutes) | all | H keep | 333 | 27 | 11.9 | -21.07 | 221029 | 2.446 |
| v11 exit (minutes) | all | H drop | 135 | 18.5 | 1.27 | -21.07 | -4400 | 0.257 |
| v11 exit (minutes) | all | O keep | 390 | 25.6 | 9.66 | -21.06 | 198880 | 2.466 |
| v11 exit (minutes) | all | O drop | 78 | 19.2 | 4.69 | -21.08 | 17749 | 0.475 |
| v11 exit (minutes) | PE | all trades | 342 | 25.1 | 10.45 | -21.04 | 189475 | 2.106 |
| v11 exit (minutes) | PE | H keep | 232 | 33.6 | 22.84 | -20.95 | 316057 | 3.296 |
| v11 exit (minutes) | PE | H drop | 110 | 7.3 | -15.69 | -21.14 | -126582 | -6.242 |
| v11 exit (minutes) | PE | O keep | 269 | 26.8 | 11.75 | -21.02 | 168294 | 2.215 |
| v11 exit (minutes) | PE | O drop | 73 | 19.2 | 5.66 | -21.08 | 21181 | 0.534 |
| v11 exit (minutes) | CE | all trades | 126 | 23 | 4.44 | -21.14 | 27155 | 0.821 |
| v11 exit (minutes) | CE | H keep | 101 | 11.9 | -13.24 | -21.26 | -95027 | -4.159 |
| v11 exit (minutes) | CE | H drop | 25 | 68 | 75.85 | 50.36 | 122182 | 3.846 |
| v11 exit (minutes) | CE | O keep | 121 | 23.1 | 5.01 | -21.14 | 30586 | 0.897 |
| v11 exit (minutes) | CE | O drop | 5 | 20 | -9.47 | -21.45 | -3432 | -0.793 |
| v10 exit (minutes) | all | all trades | 468 | 40.4 | 7.3 | -16.92 | 170405 | 1.711 |
| v10 exit (minutes) | all | H keep | 333 | 47.4 | 17.17 | -3.98 | 329999 | 3.166 |
| v10 exit (minutes) | all | H drop | 135 | 23 | -17.03 | -42.36 | -159594 | -2.82 |
| v10 exit (minutes) | all | O keep | 390 | 42.8 | 9.6 | -14.18 | 196602 | 2.094 |
| v10 exit (minutes) | all | O drop | 78 | 28.2 | -4.19 | -32.49 | -26196 | -0.363 |
| v10 exit (minutes) | PE | all trades | 342 | 40.9 | 9.89 | -15.8 | 173922 | 1.696 |
| v10 exit (minutes) | PE | H keep | 232 | 56 | 33.75 | 7.78 | 473374 | 4.404 |
| v10 exit (minutes) | PE | H drop | 110 | 9.1 | -40.41 | -48.12 | -299452 | -9.663 |
| v10 exit (minutes) | PE | O keep | 269 | 44.2 | 13.09 | -8.54 | 187229 | 2.119 |
| v10 exit (minutes) | PE | O drop | 73 | 28.8 | -1.89 | -31.82 | -13307 | -0.154 |
| v10 exit (minutes) | CE | all trades | 126 | 38.9 | 0.27 | -23.58 | -3516 | 0.039 |
| v10 exit (minutes) | CE | H keep | 101 | 27.7 | -20.91 | -31.95 | -143375 | -4.18 |
| v10 exit (minutes) | CE | H drop | 25 | 84 | 85.84 | 57.4 | 139858 | 4.666 |
| v10 exit (minutes) | CE | O keep | 121 | 39.7 | 1.84 | -21.87 | 9373 | 0.262 |
| v10 exit (minutes) | CE | O drop | 5 | 20 | -37.72 | -60.33 | -12889 | -1.858 |

## How many of Arm A's days the open already shows (2022-26, trades with both known)

| H (close) | drop | keep |
|---|---|---|
| drop | 95 | 138 |
| keep | 53 | 582 |

## H against the real Arm A trades (2025-04-01 to 2026-09-25)

| H flag | False | True |
|---|---|---|
| drop | 25 | 80 |
| keep | 263 | 0 |

## Other thresholds for O (descriptive only, not the test)

| threshold | group | window | n | win_pct | mean_pct | median_pct | total_rs | t |
|---|---|---|---|---|---|---|---|---|
| AR open >= 1 % | keep | 2022-24 | 301 | 36.9 | 3.44 | -15.99 | 33519 | 0.789 |
| AR open >= 1 % | keep | 2025-26 | 294 | 43.9 | 10.55 | -11.88 | 163678 | 2.161 |
| AR open >= 1 % | drop | 2022-24 | 133 | 36.1 | 3.97 | -25.68 | -8656 | 0.484 |
| AR open >= 1 % | drop | 2025-26 | 140 | 32.1 | -4.69 | -29.69 | -37514 | -0.637 |
| AR open >= 3 % | keep | 2022-24 | 394 | 36.5 | 2.11 | -16.73 | 15391 | 0.585 |
| AR open >= 3 % | keep | 2025-26 | 397 | 41.8 | 7.62 | -15.64 | 157534 | 1.695 |
| AR open >= 3 % | drop | 2022-24 | 40 | 37.5 | 18.31 | -25.38 | 9472 | 0.802 |
| AR open >= 3 % | drop | 2025-26 | 37 | 21.6 | -15.72 | -41.35 | -31370 | -1.254 |

Trades: data/results/S1_v10_armA_overlap_filter_trades.csv.
