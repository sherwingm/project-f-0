# S1 fade · cheap options (< Rs 10) only when >= 7 / >= 10 sessions before expiry, same-day v12 exit

Pre-registered: strategies/S1_fade_cheap_dte.md. 707 contracts with day-0 minutes (Oct 2024 - Aug 2026), 591 with one lot Rs 600-8,000 at entry B (09:16 open + 1 tick). v12 exit on 1-minute candles, real charges. t date-clustered.

## The test

| rule | n | mean % | t | half 1 mean % | half 2 mean % | baseline mean % | pass |
|---|---|---|---|---|---|---|---|
| Rule-7: B < Rs 10, >= 7 sessions to expiry | 260 | -1.05 | -0.457 | -1.09 | -1.01 | 2.86 | False |
| Rule-10: B < Rs 10, >= 10 sessions to expiry | 185 | -1.48 | -0.523 | 0.46 | -2.66 | 2.86 | False |

## Groups

| group | period | n | win % | mean % | median % | total Rs | t |
|---|---|---|---|---|---|---|---|
| Baseline: B >= Rs 2, any expiry gap | all | 339 | 55.2 | 2.86 | 5.8 | 68160 | 1.79 |
| Baseline: B >= Rs 2, any expiry gap | Oct24-Oct25 | 154 | 53.9 | 2.46 | 4.9 | 19315 | 0.968 |
| Baseline: B >= Rs 2, any expiry gap | Nov25-Sep26 | 185 | 56.2 | 3.2 | 6.3 | 48845 | 1.568 |
| Rule-7: B < Rs 10, >= 7 sessions to expiry | all | 260 | 50.8 | -1.05 | 1.2 | 1054 | -0.457 |
| Rule-7: B < Rs 10, >= 7 sessions to expiry | Oct24-Oct25 | 116 | 52.6 | -1.09 | 2.3 | -4476 | -0.275 |
| Rule-7: B < Rs 10, >= 7 sessions to expiry | Nov25-Sep26 | 144 | 49.3 | -1.01 | -1.7 | 5530 | -0.378 |
| Rule-10: B < Rs 10, >= 10 sessions to expiry | all | 185 | 48.6 | -1.48 | -1.8 | -5269 | -0.523 |
| Rule-10: B < Rs 10, >= 10 sessions to expiry | Oct24-Oct25 | 70 | 51.4 | 0.46 | 2.3 | -3630 | 0.078 |
| Rule-10: B < Rs 10, >= 10 sessions to expiry | Nov25-Sep26 | 115 | 47 | -2.66 | -2.3 | -1639 | -0.89 |

## Breakdown (one lot Rs 600-8,000)

| part | n | win % | mean % | median % | total Rs | t |
|---|---|---|---|---|---|---|
| B < Rs 2 (refused today) | 252 | 45.6 | -3.82 | -4.4 | -14846 | -1.538 |
| B Rs 2-10 | 150 | 54.7 | 2.39 | 5.8 | 14231 | 0.863 |
| B < Rs 10, < 7 sessions to expiry | 142 | 45.8 | -2.34 | -14.5 | -1670 | -0.626 |
|    of which B < Rs 2, < 7 sessions | 90 | 43.3 | -4.56 | -21.1 | -8851 | -0.872 |
| B < Rs 10, 7-9 sessions to expiry | 75 | 56 | 0.02 | 3.1 | 6323 | 0.006 |
|    of which B < Rs 2, 7-9 sessions | 45 | 48.9 | -5.28 | -3.7 | -3067 | -1.02 |
| B < Rs 10, >= 10 sessions to expiry | 185 | 48.6 | -1.48 | -1.8 | -5269 | -0.523 |
|    of which B < Rs 2, >= 10 sessions | 117 | 46.2 | -2.69 | -2.7 | -2929 | -0.913 |


Options under Rs 0.50 at the old opening print are not in the minute sets, so the cheapest ones are missing.
