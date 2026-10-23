# S3 D2: expiry natural experiments (spot, descriptive)

Pre-registered: `strategies/S3_D2_expiry_natural_experiments.md`. r_last = 15:00 → 15:29. Ratio = variance after / before; difference-in-differences (DiD) = weekday ratio / control ratio, with a 95 % bootstrap interval.

## 1. NIFTY: Thursday lost the weekly expiry, Tuesday gained it (cut 2025-09-01)

| Weekday | Days before → after | Weekday ratio | Control (Mon/Wed/Fri) ratio | DiD |
|---|---|---|---|---|
| Thursday (expiry → no expiry) | 190 → 49 | 0.72x | 0.81x | **0.89x** (0.40-1.82) |
| Tuesday (no expiry → expiry) | 191 → 52 | 1.07x | 0.81x | **1.31x** (0.62-2.90) |

## 2. BANKNIFTY: Wednesday lost the weekly expiry (weekly Wednesdays 2023-09-06 → 2024-11-13)

| Weekday | Days before → after | Weekday ratio | Control (Mon/Tue/Thu/Fri, no expiry) ratio | DiD |
|---|---|---|---|---|
| Wednesday (expiry → no expiry) | 53 → 91 | 0.41x | 1.04x | **0.39x** (0.18-0.86) |

## 3. BANKNIFTY: does the last half hour reverse the day's move? (2023-2025)

| Group | Days | Opposite sign | Slope of r_last on r_day | t |
|---|---|---|---|---|
| Expiry days | 111 | 52 % | -0.074 | -2.8 |
| Other days | 625 | 48 % | -0.015 | -1.8 |
| Expiry days 2023 | 51 | 37 % | 0.051 | 1.1 |
| Expiry days 2024 | 48 | 69 % | -0.117 | -3.8 |
| Expiry days 2025 | 12 | 50 % | -0.226 | -1.5 |
