# S3 diagnostics: NIFTY (descriptive, no trades)

DECISIONS.md "S3 · index options". Spot sections use 2021-10 → latest; option sections use the test window 2024-10-01 → 2025-09-30 only. Script: `python -m scanner.s3_diagnostics`.

Data caveat: until the Upstox path-band re-fill lands, days whose at-the-money strike is missing are left out of section 3. Those are the weeks after a > 5 % move, so section 3 leans towards calm weeks and flatters option sellers.

## 1. Last 30 minutes (15:00 → 15:29), NIFTY spot
2021-10-21 → 2026-10-21: 259 expiry days, 954 other days.

| Group | Days | Std of 15:00→15:29 return | Variance vs other days |
|---|---|---|---|
| Expiry days | 259 | 0.197 % | 1.31x |
| Other days | 954 | 0.172 % | 1.00x |

Same weekday, expiry vs not (controls for a weekday effect):

| Weekday | Expiry days | Other days | Variance ratio |
|---|---|---|---|
| Thursday | 192 | 47 | 1.33x |
| Tuesday | 52 | 192 | 1.07x |
| Wednesday | 10 | 234 | 2.62x |

By year:

| Year | Expiry days | Variance ratio |
|---|---|---|
| 2021 | 11 | 0.71x |
| 2022 | 51 | 1.10x |
| 2023 | 51 | 1.03x |
| 2024 | 52 | 1.71x |
| 2025 | 54 | 1.96x |
| 2026 | 40 | 1.56x |

Pooled ratio 95 % bootstrap interval: 0.97x to 1.73x.

Does the last half hour reverse the day's move (prev close → 15:00)?

| Group | Days | Opposite sign | Slope of r_last on r_day | t |
|---|---|---|---|---|
| Expiry days | 259 | 46 % | -0.005 | -0.3 |
| Other days | 954 | 47 % | -0.007 | -1.0 |

## 2. Round-number pinning (the number check), NIFTY spot at 15:29
Share of days whose close is within 10 points of a multiple. With no pinning it is 20 % for 100 and 4 % for 500; the 15:00 column shows where the index was half an hour earlier.

| Multiple | Group | Days | Within 10 pts at 15:29 | at 15:00 | z vs chance (15:29) |
|---|---|---|---|---|---|
| 100 | Expiry days | 259 | 16.6 % | 23.2 % | -1.4 |
| 100 | Other days | 954 | 19.2 % | 17.8 % | -0.6 |
| 500 | Expiry days | 259 | 3.5 % | 3.5 % | -0.4 |
| 500 | Other days | 954 | 4.2 % | 4.0 % | +0.3 |

## 3a. ATM straddle at 15:00 vs its payoff at expiry (test window 2024-10 → 2025-09)
`edge` = (straddle price − |expiry close − strike|) / straddle price: what a seller held to expiry keeps, before costs and slippage. Days without both ATM prices at 15:00: 46.

| VIX band | Days | Mean edge | Median edge | Seller wins | t by expiry | Mean IV | Mean RV | IV − RV |
|---|---|---|---|---|---|---|---|---|
| All | 201 | +13.1 % | +30.7 % | 65 % | 0.7 | 14.0 | 11.4 | +2.6 |
| 13-20 | 126 | +11.7 % | +32.9 % | 63 % | 0.6 | 15.4 | 12.4 | +3.0 |
| <13 | 69 | +21.2 % | +30.2 % | 70 % | 0.0 | 10.3 | 8.7 | +1.5 |
| >20 | 6 | -51.8 % | -73.9 % | 33 % | -1.0 | 27.8 | 20.1 | +7.8 |

By days to expiry:

| DTE | Days | Mean edge | Worst | t by expiry |
|---|---|---|---|---|
| 1 | 42 | +8.9 % | -128 % | 0.9 |
| 2 | 39 | +8.8 % | -261 % | 0.7 |
| 3-4 | 38 | +21.4 % | -199 % | 1.7 |
| 5-7 | 81 | +15.3 % | -187 % | 1.2 |
| 8+ | 1 | -146.8 % | -147 % | nan |

## 3b. Expiry-day ATM straddle by time of day (test window; strike fixed at the 09:20 ATM)
45 expiry days; 9 without the ATM strike or spot at 09:20 (2024-10-24, 2024-12-26, 2025-02-13, 2025-02-27, 2025-03-06, 2025-05-08, 2025-05-29, 2025-06-26, 2025-09-25). These are filled by the queued Upstox re-fill (path band).

| Time | Median value vs 09:20 | Mean | Days below 09:20 |
|---|---|---|---|
| 09:20 | 100 % | 100 % | 0 % |
| 10:00 | 92 % | 97 % | 71 % |
| 11:15 | 89 % | 98 % | 60 % |
| 12:30 | 89 % | 101 % | 62 % |
| 13:30 | 81 % | 106 % | 58 % |
| 14:15 | 76 % | 109 % | 60 % |
| 14:45 | 76 % | 107 % | 58 % |
| 15:00 | 87 % | 107 % | 53 % |
| 15:15 | 87 % | 106 % | 56 % |
| 15:25 | 90 % | 106 % | 60 % |

Short straddle 09:20 → 14:45 held without a stop, before costs: mean -7.5 %, median +24.3 %, wins 58 %, worst -429 %, t -0.5 (45 days). Descriptive only: P1 is judged on its pre-registered page with stops and costs.

## 3c. Max pain at 09:20 vs the close (test window)
45 expiry days. The close was nearer max pain than the 09:20 index was on 20 % of days. Placebo: a point the same distance on the other side of 09:20. The close ended nearer max pain than that point on 49 % of days (50 % = no pull). Mean |close − max pain| 146 pts vs |09:20 − max pain| 58 pts. Max pain uses only the strikes in our ±5 % band.
