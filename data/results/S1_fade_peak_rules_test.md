# S1 fade · peak-pattern study, phase C: the frozen rule on the test half

strategies/S1_fade_peak_patterns.md (addendum 2026-10-22). Test = day 0 from 2025-11-03: 185 live trades (1 lot), 144 refused (max lots under Rs 8,000). Same walker as phase B, tick Rs 0.01, real charges.

## Frozen rule R2 stall 20 (live set): **FAIL**

mean 1.55 %, vs v12 -1.65 points (t -0.838). Pass needs mean > 0 and the difference > 0 with t >= 2. R4 and the others are descriptive.

## Live set

| rule | n | win % | mean % | median % | total Rs | diff vs v12 | diff t | better/worse/same | mean w/o best 3 | mean % on peak >= 40 % | kept (mean net / mean peak, peak >= 40 %) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v12 | 185 | 56.2 | 3.2 | 6.29 | 48845 | 0 |  | 0/0/185 | 1.22 | 15.18 | 0.134 |
| R1 range trail | 185 | 37.3 | 2.21 | -14.73 | 45509 | -0.99 | -0.435 | 33/73/79 | -2.05 | 18.44 | 0.162 |
| R2 stall 20 | 185 | 34.1 | 1.55 | -20.88 | 36298 | -1.65 | -0.838 | 40/70/75 | -1.36 | 18.93 | 0.166 |
| R3 half-profit floor | 185 | 54.6 | 0.88 | 4.42 | 22606 | -2.32 | -2.196 | 19/65/101 | -0.7 | 12.04 | 0.106 |
| R4 half-profit + wick top | 185 | 55.1 | 0.91 | 4.43 | 22959 | -2.29 | -2.965 | 19/59/107 | -0.21 | 11.85 | 0.104 |
| R5 hold to close | 185 | 24.9 | 0.01 | -21.03 | 23467 | -3.18 | -1.203 | 40/71/74 | -2.84 | 18.63 | 0.164 |

## Refused set

| rule | n | win % | mean % | median % | total Rs | diff vs v12 | diff t | better/worse/same | mean w/o best 3 | mean % on peak >= 40 % | kept (mean net / mean peak, peak >= 40 %) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v12 | 144 | 55.6 | 3.69 | 3.92 | 39364 | 0 |  | 0/0/144 | 1.76 | 20.64 | 0.178 |
| R1 range trail | 144 | 43.1 | 3.57 | -6.68 | 40964 | -0.12 | -0.04 | 29/45/70 | -0.74 | 22.53 | 0.194 |
| R2 stall 20 | 144 | 37.5 | 2.25 | -15.51 | 27660 | -1.44 | -0.517 | 26/60/58 | -2 | 21.14 | 0.182 |
| R3 half-profit floor | 144 | 54.2 | 1.79 | 3.22 | 18794 | -1.9 | -1.132 | 12/50/82 | -0.89 | 18.09 | 0.156 |
| R4 half-profit + wick top | 144 | 54.9 | 3.6 | 3.36 | 37392 | -0.09 | -0.04 | 14/42/88 | 0.14 | 21.45 | 0.185 |
| R5 hold to close | 144 | 25.7 | -2.95 | -21.73 | -30613 | -6.64 | -1.632 | 23/63/58 | -6.48 | 15.08 | 0.13 |
