# S1 fade · the -20 % stop plus a trailing stop (start and gap from 2 %), realistic entry

Pre-registered: strategies/S1_fade_trail20_grid.md. 409 trades; train before 2025-11-03 (189), test from it (220). Net % of premium after charges; t date-clustered. The test half is not fully fresh (see the pre-registration).

## The test: **FAIL**

Train winner: **stop 20 + trail start 10 gap 5**: test mean 3.69 % (t 2.188), vs v11 +1.97 points (t 0.803).

## All trades: mean net % by start and gap (v11 = 2.47 %)

| start A % | gap 2 % | gap 5 % | gap 10 % | gap 15 % | gap 20 % |
|---|---|---|---|---|---|
| 2 | 2.91 | 3.14 | 2.61 | 2.11 | 1.63 |
| 5 | 3.21 | 3.26 | 2.6 | 2.01 | 1.55 |
| 10 | 3.44 | 3.39 | 2.7 | 2.09 | 1.53 |
| 20 | 2.71 | 2.58 | 2.36 | 1.78 | 1.36 |

## Every variant

| variant | train mean % | train t | test mean % | test t | win % (all) | test diff vs v11 | diff t | all mean % | all t |
|---|---|---|---|---|---|---|---|---|---|
| v11 | 3.34 | 0.638 | 1.73 | 0.635 | 26.2 | 0 |  | 2.47 | 0.876 |
| stop 20 + trail start 10 gap 5 | 3.04 | 1.374 | 3.69 | 2.188 | 55.7 | 1.97 | 0.803 | 3.39 | 2.486 |
| stop 20 + trail start 5 gap 5 | 2.93 | 1.322 | 3.53 | 2.196 | 53.5 | 1.81 | 0.729 | 3.26 | 2.434 |
| stop 20 + trail start 2 gap 5 | 2.72 | 1.256 | 3.51 | 2.199 | 50.1 | 1.78 | 0.714 | 3.14 | 2.391 |
| stop 20 + trail start 10 gap 2 | 2.72 | 1.239 | 4.06 | 2.27 | 56.2 | 2.34 | 0.964 | 3.44 | 2.464 |
| stop 20 + trail start 5 gap 2 | 2.54 | 1.16 | 3.79 | 2.216 | 55.7 | 2.06 | 0.835 | 3.21 | 2.352 |
| stop 20 + trail start 10 gap 10 | 2.41 | 1.077 | 2.96 | 1.738 | 51.8 | 1.23 | 0.514 | 2.7 | 1.963 |
| stop 20 + trail start 2 gap 10 | 2.39 | 1.102 | 2.79 | 1.768 | 47.7 | 1.06 | 0.437 | 2.61 | 1.988 |
| stop 20 + trail start 5 gap 10 | 2.32 | 1.035 | 2.84 | 1.785 | 48.9 | 1.11 | 0.461 | 2.6 | 1.94 |
| stop 20 + trail start 2 gap 2 | 2.08 | 0.967 | 3.62 | 2.127 | 52.1 | 1.89 | 0.763 | 2.91 | 2.154 |
| stop 20 + trail start 20 gap 5 | 1.98 | 0.843 | 3.08 | 1.609 | 50.1 | 1.36 | 0.567 | 2.58 | 1.721 |
| stop 20 + trail start 20 gap 2 | 1.88 | 0.811 | 3.42 | 1.739 | 50.6 | 1.69 | 0.717 | 2.71 | 1.8 |
| stop 20 + trail start 20 gap 10 | 1.63 | 0.697 | 2.99 | 1.616 | 50.1 | 1.26 | 0.532 | 2.36 | 1.608 |
| stop 20 + trail start 2 gap 15 | 1.31 | 0.595 | 2.8 | 1.398 | 44.3 | 1.08 | 0.429 | 2.11 | 1.425 |
| stop 20 + trail start 5 gap 15 | 1.18 | 0.523 | 2.72 | 1.362 | 44.7 | 1 | 0.399 | 2.01 | 1.343 |
| stop 20 + trail start 10 gap 15 | 1.11 | 0.493 | 2.94 | 1.468 | 45.2 | 1.21 | 0.487 | 2.09 | 1.395 |
| stop 20 + trail start 20 gap 15 | 0.43 | 0.184 | 2.94 | 1.422 | 49.6 | 1.21 | 0.5 | 1.78 | 1.146 |
| stop 20 + trail start 2 gap 20 | 0.3 | 0.123 | 2.76 | 1.4 | 40.8 | 1.04 | 0.434 | 1.63 | 1.046 |
| stop 20 + trail start 5 gap 20 | 0.16 | 0.066 | 2.75 | 1.392 | 40.8 | 1.02 | 0.428 | 1.55 | 0.995 |
| stop 20 + trail start 10 gap 20 | 0.02 | 0.009 | 2.83 | 1.425 | 40.8 | 1.1 | 0.462 | 1.53 | 0.976 |
| stop 20 + trail start 20 gap 20 | -0.44 | -0.175 | 2.9 | 1.421 | 44 | 1.18 | 0.509 | 1.36 | 0.846 |
