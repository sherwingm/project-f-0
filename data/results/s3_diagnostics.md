# S3 diagnostics: NIFTY (descriptive, no trades)

DECISIONS.md "S3 · index options". Spot sections use 2021-10 → latest; option sections use the test window 2024-10-01 → 2025-09-30 only. Script: `python -m scanner.s3_diagnostics`.

Data: after the Upstox path-band re-fill (2026-10-22), 107 of 108 NIFTY expiry days have the ATM and ±4-strike prices at 09:20 / 10:00 / 11:15 / 14:45; 2024-12-26 has one strike only. Before the re-fill the missing days were the weeks after a > 5 % move, and the straddle edge read +13 % (t 0.7) instead of the figures below.

## 1. Last 30 minutes (15:00 → 15:29), NIFTY spot
2021-10-21 → 2026-10-22: 256 expiry days, 958 other days.

| Group | Days | Std of 15:00→15:29 return | Variance vs other days |
|---|---|---|---|
| Expiry days | 256 | 0.198 % | 1.33x |
| Other days | 958 | 0.172 % | 1.00x |

Same weekday, expiry vs not (controls for a weekday effect):

| Weekday | Expiry days | Other days | Variance ratio |
|---|---|---|---|
| Thursday | 190 | 50 | 1.41x |
| Tuesday | 52 | 192 | 1.07x |

By year:

| Year | Expiry days | Variance ratio |
|---|---|---|
| 2021 | 11 | 0.71x |
| 2022 | 51 | 1.10x |
| 2023 | 51 | 1.03x |
| 2024 | 52 | 1.71x |
| 2025 | 52 | 2.05x |
| 2026 | 39 | 1.62x |

Pooled ratio 95 % bootstrap interval: 1.01x to 1.73x.

Does the last half hour reverse the day's move (prev close → 15:00)?

| Group | Days | Opposite sign | Slope of r_last on r_day | t |
|---|---|---|---|---|
| Expiry days | 256 | 46 % | -0.005 | -0.3 |
| Other days | 958 | 47 % | -0.007 | -1.0 |

## 2. Round-number pinning (the number check), NIFTY spot at 15:29
Share of days whose close is within 10 points of a multiple. With no pinning it is 20 % for 100 and 4 % for 500; the 15:00 column shows where the index was half an hour earlier.

| Multiple | Group | Days | Within 10 pts at 15:29 | at 15:00 | z vs chance (15:29) |
|---|---|---|---|---|---|
| 100 | Expiry days | 256 | 16.4 % | 23.4 % | -1.4 |
| 100 | Other days | 958 | 19.2 % | 17.7 % | -0.6 |
| 500 | Expiry days | 256 | 3.5 % | 3.5 % | -0.4 |
| 500 | Other days | 958 | 4.2 % | 4.0 % | +0.3 |

## 3a. ATM straddle at 15:00 vs its payoff at expiry (test window 2024-10 → 2025-09)
`edge` = (straddle price − |expiry close − strike|) / straddle price: what a seller held to expiry keeps, before costs and slippage. Days without both ATM prices at 15:00: 9.

| VIX band | Days | Mean edge | Median edge | Seller wins | t by expiry | Mean IV | Mean RV | IV − RV |
|---|---|---|---|---|---|---|---|---|
| All | 238 | +6.8 % | +25.4 % | 60 % | 0.1 | 14.1 | 11.5 | +2.6 |
| 13-20 | 160 | +4.9 % | +24.8 % | 57 % | 0.0 | 15.3 | 12.4 | +2.9 |
| <13 | 72 | +15.9 % | +28.8 % | 67 % | -0.4 | 10.3 | 8.8 | +1.5 |
| >20 | 6 | -51.8 % | -73.9 % | 33 % | -1.0 | 27.8 | 20.1 | +7.8 |

By days to expiry:

| DTE | Days | Mean edge | Worst | t by expiry |
|---|---|---|---|---|
| 1 | 47 | +6.0 % | -128 % | 0.6 |
| 2 | 46 | +5.7 % | -261 % | 0.5 |
| 3-4 | 46 | +10.0 % | -199 % | 0.9 |
| 5-7 | 97 | +7.4 % | -187 % | 0.6 |
| 8+ | 2 | -50.7 % | -147 % | nan |

## 3b. Expiry-day ATM straddle by time of day (test window; strike fixed at the 09:20 ATM)
51 expiry days; 2 without the ATM strike or spot at 09:20 (2024-12-26, 2025-02-13).

| Time | Median value vs 09:20 | Mean | Days below 09:20 |
|---|---|---|---|
| 09:20 | 100 % | 100 % | 0 % |
| 10:00 | 92 % | 98 % | 69 % |
| 11:15 | 87 % | 95 % | 61 % |
| 12:30 | 89 % | 99 % | 61 % |
| 13:30 | 81 % | 103 % | 61 % |
| 14:15 | 80 % | 108 % | 59 % |
| 14:45 | 81 % | 106 % | 59 % |
| 15:00 | 87 % | 108 % | 53 % |
| 15:15 | 87 % | 105 % | 55 % |
| 15:25 | 90 % | 106 % | 59 % |

Short straddle 09:20 → 14:45 held without a stop, before costs: mean -5.8 %, median +19.2 %, wins 59 %, worst -429 %, t -0.5 (51 days). Descriptive only: P1 is judged on its pre-registered page with stops and costs.

## 3c. Max pain at 09:20 vs the close (test window)
51 expiry days. The close was nearer max pain than the 09:20 index was on 18 % of days. Placebo: a point the same distance on the other side of 09:20. The close ended nearer max pain than that point on 43 % of days (50 % = no pull). Mean |close − max pain| 151 pts vs |09:20 − max pain| 58 pts. Max pain uses only the strikes in our ±5 % band.
