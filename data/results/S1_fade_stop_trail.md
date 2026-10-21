# S1 fade · wider stops, a 1-minute wait, trailing stops and re-entry (realistic entry)

Pre-registered: strategies/S1_fade_stop_trail_study.md. 409 trades, entry = 09:16 open + 1 tick; train = before 2025-11-03 (189), test = from 2025-11-03 (220). Net % of premium after real charges; t date-clustered. 71 variants.

## The test: **FAIL**

Train winner: **stop 35 touch from 09:30**. On test: mean 0.84 % (t 0.273); vs v11 -0.88 points (t -0.519). Pass needs test mean > 0 and the difference to v11 > 0 with t >= 2.

## v11 (baseline)

| variant | train mean % | train t | test mean % | test t | test win % | test worst % | test diff vs v11 | diff t | all mean % |
|---|---|---|---|---|---|---|---|---|---|
| stop 20 touch from 09:17 | 3.34 | 0.638 | 1.73 | 0.635 | 26.8 | -51.3 | 0 |  | 2.47 |

## Best of each family on train, shown on test

| family | variant | train mean % | train t | test mean % | test t | test win % | test worst % | test diff vs v11 | diff t | all mean % |
|---|---|---|---|---|---|---|---|---|---|---|
| stop width | stop 35 touch from 09:30 | 6.53 | 0.992 | 0.84 | 0.273 | 37.7 | -59.8 | -0.88 | -0.519 | 3.47 |
| re-entry | v11 + re-entry | 2.57 | 0.507 | 0.63 | 0.208 | 31.8 | -55.1 | -1.09 | -0.676 | 1.53 |
| trailing | no stop + trail A0 D15 | 1.54 | 0.678 | 3.91 | 1.851 | 45.9 | -50.1 | 2.19 | 0.839 | 2.82 |

## Top 15 on train

| variant | train mean % | train t | test mean % | test t | test win % | test worst % | test diff vs v11 | diff t | all mean % |
|---|---|---|---|---|---|---|---|---|---|
| stop 35 touch from 09:30 | 6.53 | 0.992 | 0.84 | 0.273 | 37.7 | -59.8 | -0.88 | -0.519 | 3.47 |
| stop 40 touch from 09:30 | 6.52 | 0.99 | 0.72 | 0.23 | 39.1 | -59.8 | -1.01 | -0.554 | 3.4 |
| stop 30 touch from 10:00 | 6.47 | 1.009 | 3.47 | 0.845 | 38.6 | -73 | 1.74 | 0.581 | 4.85 |
| stop 30 wait1m from 10:00 | 6.27 | 0.975 | 3.25 | 0.799 | 38.6 | -71.2 | 1.52 | 0.517 | 4.64 |
| stop 40 wait1m from 09:30 | 6.21 | 0.939 | 1.51 | 0.453 | 40 | -61.5 | -0.21 | -0.093 | 3.69 |
| stop 35 wait1m from 09:30 | 6.09 | 0.919 | 0.61 | 0.196 | 38.2 | -61.5 | -1.12 | -0.642 | 3.14 |
| stop 30 wait1m from 09:30 | 5.93 | 0.895 | 0.8 | 0.258 | 35.9 | -61.5 | -0.92 | -0.554 | 3.17 |
| stop 35 touch from 10:00 | 5.79 | 0.895 | 2.94 | 0.721 | 39.5 | -73 | 1.21 | 0.407 | 4.25 |
| stop 40 touch from 10:00 | 5.79 | 0.888 | 2.83 | 0.69 | 40 | -73 | 1.11 | 0.365 | 4.2 |
| stop 40 wait1m from 10:00 | 5.66 | 0.868 | 2.89 | 0.703 | 40.5 | -71.2 | 1.16 | 0.386 | 4.17 |
| stop 30 touch from 09:30 | 5.65 | 0.853 | 0.71 | 0.228 | 35 | -59.8 | -1.02 | -0.636 | 2.99 |
| stop 50 wait1m from 09:30 | 5.48 | 0.846 | 2.96 | 0.723 | 41.8 | -61.5 | 1.23 | 0.405 | 4.12 |
| stop 35 wait1m from 10:00 | 5.47 | 0.848 | 2.66 | 0.655 | 39.5 | -71.2 | 0.94 | 0.315 | 3.96 |
| stop 50 touch from 09:30 | 5.42 | 0.83 | 3.24 | 0.79 | 41.8 | -62.5 | 1.51 | 0.496 | 4.25 |
| stop 50 wait1m from 10:00 | 4.95 | 0.768 | 2.76 | 0.672 | 41.8 | -71.2 | 1.04 | 0.34 | 3.77 |

## Stop width only (touch, from 09:17)

| variant | train mean % | train t | test mean % | test t | test win % | test worst % | test diff vs v11 | diff t | all mean % |
|---|---|---|---|---|---|---|---|---|---|
| no stop | 3.97 | 0.62 | 2.56 | 0.583 | 42.7 | -89.2 | 0.83 | 0.244 | 3.21 |
| stop 20 touch from 09:17 | 3.34 | 0.638 | 1.73 | 0.635 | 26.8 | -51.3 | 0 |  | 2.47 |
| stop 25 touch from 09:17 | 1.91 | 0.361 | 1.8 | 0.611 | 30.5 | -51.3 | 0.08 | 0.067 | 1.85 |
| stop 28 touch from 09:17 | 1.42 | 0.266 | 0.47 | 0.158 | 30.9 | -51.3 | -1.25 | -1.041 | 0.91 |
| stop 30 touch from 09:17 | 1.54 | 0.292 | 0.55 | 0.178 | 32.7 | -51.3 | -1.18 | -0.913 | 1.01 |
| stop 35 touch from 09:17 | 2.99 | 0.447 | 0.31 | 0.1 | 35.9 | -52 | -1.42 | -0.996 | 1.54 |
| stop 40 touch from 09:17 | 1.72 | 0.257 | -0.43 | -0.138 | 37.3 | -52 | -2.16 | -1.335 | 0.56 |
| stop 50 touch from 09:17 | 3.16 | 0.49 | 1.91 | 0.483 | 40.9 | -62.5 | 0.18 | 0.068 | 2.49 |


All variants: data/results/S1_fade_stop_trail_variants.csv.
