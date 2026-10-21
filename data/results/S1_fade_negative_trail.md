# S1 fade · negative trailing stops (step down at -20 %, then trail or reset), realistic entry

Pre-registered: strategies/S1_fade_negative_trail.md. 409 trades; train before 2025-11-03 (189), test from it (220). Net % of premium after charges; t date-clustered.

## The test: **FAIL**

Train winner: **N2-35**: test mean 0.31 %, vs v11 -1.42 points (t -0.996).

## All variants

| variant | train mean % | test mean % | test t | test diff vs v11 | diff t | all mean % | all t | win % | worst % |
|---|---|---|---|---|---|---|---|---|---|
| v11 | 3.34 | 1.73 | 0.635 | 0 |  | 2.47 | 0.876 | 26.2 | -51.3 |
| v10 | 3.97 | 2.56 | 0.583 | 0.83 | 0.244 | 3.21 | 0.849 | 41.3 | -95.6 |
| N1 | 1.89 | 1.07 | 0.381 | -0.66 | -1.214 | 1.45 | 0.498 | 27.9 | -55.4 |
| N2-30 | 1.54 | 0.55 | 0.178 | -1.18 | -0.913 | 1.01 | 0.342 | 31.5 | -51.3 |
| N2-35 | 2.99 | 0.31 | 0.1 | -1.42 | -0.996 | 1.54 | 0.441 | 34.5 | -52 |
| N2-40 | 1.72 | -0.43 | -0.138 | -2.16 | -1.335 | 0.56 | 0.159 | 35.7 | -52 |
| N3a | 2.98 | 1.63 | 0.561 | -0.1 | -0.099 | 2.25 | 0.787 | 27.4 | -55.4 |
| N3b | 2.1 | 1.29 | 0.451 | -0.44 | -0.602 | 1.66 | 0.568 | 29.6 | -55.4 |


N1 = step to -25 % then trail 5 % below the peak; N2-x = ladder to a floor (= a stop at -x %); N3a = step to -25 %, break-even once back at the buy price, then hold; N3b = the same, then trail 5 % below the peak.
