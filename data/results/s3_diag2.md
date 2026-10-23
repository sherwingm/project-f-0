# S3 D2: expiry natural experiments (spot, descriptive)

Pre-registered: `strategies/S3_D2_expiry_natural_experiments.md`. r_last = 15:00 → 15:29. Ratio = variance after / before; difference-in-differences (DiD) = weekday ratio / control ratio, with a 95 % bootstrap interval.

## 1. NIFTY: Thursday lost the weekly expiry, Tuesday gained it (cut 2025-09-01)

| Weekday | Days before → after | Weekday ratio | Control (Mon/Wed/Fri) ratio | DiD |
|---|---|---|---|---|
| Thursday (expiry → no expiry) | 190 → 47 | 0.75x | 0.81x | **0.92x** (0.43-1.96) |
| Tuesday (no expiry → expiry) | 191 → 52 | 1.07x | 0.81x | **1.31x** (0.62-2.90) |

## 2. BANKNIFTY: Wednesday lost the weekly expiry (weekly Wednesdays 2023-09-06 → 2024-11-13)

| Weekday | Days before → after | Weekday ratio | Control (Mon/Tue/Thu/Fri, no expiry) ratio | DiD |
|---|---|---|---|---|
| Wednesday (expiry → no expiry) | 53 → 85 | 0.43x | 1.02x | **0.42x** (0.20-0.92) |

## 3. BANKNIFTY: does the last half hour reverse the day's move? (2023-2025)

| Group | Days | Opposite sign | Slope of r_last on r_day | t |
|---|---|---|---|---|
| Expiry days | 127 | 55 % | -0.076 | -3.2 |
| Other days | 609 | 47 % | -0.014 | -1.7 |
| Expiry days 2023 | 55 | 40 % | 0.039 | 0.9 |
| Expiry days 2024 | 53 | 72 % | -0.122 | -4.1 |
| Expiry days 2025 | 19 | 53 % | -0.154 | -1.5 |
