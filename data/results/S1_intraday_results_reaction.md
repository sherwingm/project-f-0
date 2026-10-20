# S1 · results filed during market hours: fade or keep going? (step 1, stock only)

Pre-registered: strategies/S1_intraday_results_reaction.md. 1-minute closes; R15 = the move from the last minute before the announcement to 15 minutes after it; RA = from there to the 15:20 close (the test). Moves are minus NIFTY 50's over the same minutes unless marked raw. t is date-clustered. continue_pct = the share of cases where RA went the same way as R15.

Cases: 669 filings; with usable minutes: 644.

## Test: **FAIL: no bucket passes; step 1 closes, no option test**

| bucket | n 22-24 | mean RA 22-24 | n 25-26 | mean RA 25-26 | pooled t | same sign | |mean| >= 0.5 both | |t| >= 3 | pattern | PASS |
|---|---|---|---|---|---|---|---|---|---|---|
| <= -3 % | 17 | -0.518 | 11 | 0.219 | -0.678 | False | False | False | - | False |
| -3..-1 % | 78 | -0.018 | 53 | -0.435 | -0.848 | True | False | False | continuation | False |
| +1..+3 % | 60 | 0.101 | 65 | -0.189 | -0.275 | False | False | False | - | False |
| >= +3 % | 9 | -0.247 | 27 | 0.246 | 0.321 | False | False | False | - | False |

## By first-15-minute move (adjusted)

| R15 bucket (adjusted) | window | n | mean_RA | median_RA | continue_pct | t |
|---|---|---|---|---|---|---|
| <= -3 % | 2022-24 | 17 | -0.518 | -0.282 | 52.9 | -1.069 |
| <= -3 % | 2025-26 | 11 | 0.219 | 0.533 | 45.5 | 0.522 |
| <= -3 % | all | 28 | -0.228 | -0.057 | 50 | -0.678 |
| -3..-1 % | 2022-24 | 78 | -0.018 | 0.092 | 46.2 | -0.072 |
| -3..-1 % | 2025-26 | 53 | -0.435 | -0.165 | 54.7 | -1.095 |
| -3..-1 % | all | 131 | -0.187 | 0.017 | 49.6 | -0.848 |
| -1..+1 % | 2022-24 | 197 | -0.051 | -0.199 | 44.7 | -0.406 |
| -1..+1 % | 2025-26 | 127 | -0 | 0.025 | 47.2 | -0.001 |
| -1..+1 % | all | 324 | -0.031 | -0.12 | 45.7 | -0.318 |
| +1..+3 % | 2022-24 | 60 | 0.101 | -0.189 | 46.7 | 0.328 |
| +1..+3 % | 2025-26 | 65 | -0.189 | -0.122 | 44.6 | -0.93 |
| +1..+3 % | all | 125 | -0.05 | -0.147 | 45.6 | -0.275 |
| >= +3 % | 2022-24 | 9 | -0.247 | -0.147 | 44.4 | -0.274 |
| >= +3 % | 2025-26 | 27 | 0.246 | 0.388 | 59.3 | 0.581 |
| >= +3 % | all | 36 | 0.123 | 0.236 | 55.6 | 0.321 |

## Same, raw moves

| R15 bucket (raw) | window | n | mean_RA | median_RA | continue_pct | t |
|---|---|---|---|---|---|---|
| <= -3 % | 2022-24 | 17 | -0.219 | 0.202 | 47.1 | -0.38 |
| <= -3 % | 2025-26 | 12 | 0.306 | 0.128 | 50 | 0.643 |
| <= -3 % | all | 29 | -0.002 | 0.202 | 48.3 | -0.005 |
| -3..-1 % | 2022-24 | 78 | -0.112 | -0.01 | 50 | -0.434 |
| -3..-1 % | 2025-26 | 51 | -0.389 | -0.092 | 52.9 | -0.933 |
| -3..-1 % | all | 129 | -0.221 | -0.053 | 51.2 | -0.982 |
| -1..+1 % | 2022-24 | 194 | -0.074 | -0.194 | 42.8 | -0.545 |
| -1..+1 % | 2025-26 | 126 | -0.063 | -0.056 | 50.8 | -0.387 |
| -1..+1 % | all | 320 | -0.069 | -0.137 | 45.9 | -0.669 |
| +1..+3 % | 2022-24 | 63 | 0.207 | 0.132 | 50.8 | 0.665 |
| +1..+3 % | 2025-26 | 69 | -0.241 | -0.205 | 44.9 | -1.155 |
| +1..+3 % | all | 132 | -0.027 | -0.158 | 47.7 | -0.145 |
| >= +3 % | 2022-24 | 9 | -0.146 | -0.234 | 44.4 | -0.151 |
| >= +3 % | 2025-26 | 25 | 0.41 | 0.586 | 64 | 0.894 |
| >= +3 % | all | 34 | 0.262 | 0.296 | 58.8 | 0.632 |

## By the fade's numbers class (adjusted)

| class | R15 bucket | n | mean_RA | median_RA | continue_pct | t |
|---|---|---|---|---|---|---|
| strong | <= -3 % | 9 | -0.318 | -1.214 | 55.6 | -0.597 |
| strong | -3..-1 % | 43 | 0.092 | 0.352 | 44.2 | 0.234 |
| strong | -1..+1 % | 106 | 0.068 | -0.115 | 50.9 | 0.366 |
| strong | +1..+3 % | 55 | 0.008 | -0.078 | 49.1 | 0.037 |
| strong | >= +3 % | 16 | -0.245 | -0.284 | 43.8 | -0.365 |
| weak | <= -3 % | 6 | -0.574 | -0.262 | 66.7 | -0.861 |
| weak | -3..-1 % | 10 | -1.097 | -0.462 | 70 | -0.528 |
| weak | -1..+1 % | 35 | 0.071 | 0.025 | 48.6 | 0.238 |
| weak | +1..+3 % | 13 | -0.144 | -0.122 | 46.2 | -0.35 |
| weak | >= +3 % | 2 | 0.216 | 0.216 | 50 | 0.69 |
| neither | <= -3 % | 13 | -0.007 | 0.517 | 38.5 | -0.013 |
| neither | -3..-1 % | 78 | -0.224 | 0.004 | 50 | -1.228 |
| neither | -1..+1 % | 183 | -0.107 | -0.144 | 42.1 | -0.926 |
| neither | +1..+3 % | 57 | -0.084 | -0.471 | 42.1 | -0.264 |
| neither | >= +3 % | 18 | 0.439 | 0.659 | 66.7 | 0.881 |

## By year (outer buckets, adjusted)

| year | R15 bucket | n | mean_RA | median_RA | continue_pct | t |
|---|---|---|---|---|---|---|
| 2022 | <= -3 % | 3 | 0.345 | 0.517 | 33.3 | 0.255 |
| 2022 | -3..-1 % | 14 | -0.514 | -0.234 | 57.1 | -0.96 |
| 2022 | +1..+3 % | 10 | -0.266 | -0.722 | 30 | -0.406 |
| 2022 | >= +3 % | 2 | -1.706 | -1.706 | 50 | -0.548 |
| 2023 | <= -3 % | 7 | -1.34 | -1.612 | 71.4 | -1.721 |
| 2023 | -3..-1 % | 33 | 0.155 | -0.009 | 54.5 | 0.389 |
| 2023 | +1..+3 % | 29 | -0.337 | -0.699 | 41.4 | -0.945 |
| 2023 | >= +3 % | 2 | -0.871 | -0.871 | 50 | -0.664 |
| 2024 | <= -3 % | 7 | -0.067 | 0.128 | 42.9 | -0.099 |
| 2024 | -3..-1 % | 31 | 0.021 | 0.315 | 32.3 | 0.05 |
| 2024 | +1..+3 % | 21 | 0.88 | 0.275 | 61.9 | 1.333 |
| 2024 | >= +3 % | 5 | 0.585 | -0.147 | 40 | 0.498 |
| 2025 | <= -3 % | 4 | 1.188 | 1.62 | 25 | 2.485 |
| 2025 | -3..-1 % | 22 | -0.954 | -0.158 | 54.5 | -1.226 |
| 2025 | +1..+3 % | 33 | -0.011 | -0.056 | 48.5 | -0.047 |
| 2025 | >= +3 % | 11 | 0.232 | 0.989 | 63.6 | 0.348 |
| 2026 | <= -3 % | 7 | -0.334 | -0.359 | 57.1 | -0.689 |
| 2026 | -3..-1 % | 31 | -0.065 | -0.165 | 54.8 | -0.169 |
| 2026 | +1..+3 % | 32 | -0.372 | -0.758 | 40.6 | -1.121 |
| 2026 | >= +3 % | 16 | 0.256 | 0.206 | 56.2 | 0.45 |

## Timing check: is the stored time late?

| window | n | mean |B15| (15 min before t0) | mean |R15| (first 15 min) | mean |RA| (after, to 15:20) |
|---|---|---|---|---|
| all | 644 | 0.528 | 1.354 | 1.342 |
| 2022-24 | 361 | 0.49 | 1.202 | 1.322 |
| 2025-26 | 283 | 0.577 | 1.549 | 1.367 |

## The loss question: v10 backtest fade trades whose filing came in market hours the session before

| fade side | group | trades | mean R15+RA on the filing day % | fade win % | fade total Rs (15:20) |
|---|---|---|---|---|---|
| CE | filing day moved WITH the fade's bet (R15+RA) | 26 | 2.26 | 34.6 | 10309 |
| CE | filing day moved AGAINST it | 33 | -2.52 | 30.3 | -14604 |
| PE | filing day moved WITH the fade's bet (R15+RA) | 98 | -1.61 | 28.6 | -33314 |
| PE | filing day moved AGAINST it | 91 | 2.41 | 46.2 | -12916 |

248 fade trades matched. The fade buys at the next session's open; this shows whether the filing day had already moved its way.

## Cases without usable minutes

| year | why | cases |
|---|---|---|
| 2024 | minutes_do_not_cover_t0_to_1520 | 1 |
| 2024 | no_minutes | 1 |
| 2026 | minutes_do_not_cover_t0_to_1520 | 23 |

## Extra, seen after the test (descriptive, not pre-registered)
The v10 backtest fade trades (entry = open, 15:20 exit), split by whether the filing came in market hours (09:15-14:50) the session before:

| window | filing | trades | total Rs | mean % | t |
|---|---|---|---|---|---|
| 2022-24 | in market hours | 131 | -43,558 | -5.56 | -1.06 |
| 2022-24 | other times | 305 | +67,748 | +7.48 | 1.53 |
| 2025-26 | in market hours | 131 | -8,298 | +0.17 | 0.03 |
| 2025-26 | other times | 303 | +1,34,462 | +8.00 | 1.45 |
| all | in market hours | 262 | -51,856 | -2.70 | -0.73 |
| all | other times | 608 | +2,02,210 | +7.74 | 2.10 |

The fade's backtest profit comes from filings made outside market hours (after the close or before the open). This was found after looking, so it needs its own pre-registered test before any rule change.
