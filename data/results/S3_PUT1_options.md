# S3 PUT1 puts on real NIFTY option prices · 2024-10-01 → 2026-10-28 (descriptive, not a gate)

At-the-money put, nearest weekly expiry, 1 lot, bought the minute after the downside breakout, sold at 15:15. No stop, no target. Real minute prices, slippage and charges (`scanner/s3_engine.py`).

- Breakout days: 263; priced: 259; skipped: 4 (no price 22550 PE at 10:07, no price 23700 PE at 09:33, no price 23700 PE at 09:38, no price 25000 PE at 10:46)
- **Sold at 15:15, after costs:** mean -1.2 % of premium, median -8.0 %, t -0.35, won 41 %, total ₹-66,730 (average premium paid ₹8,625 a lot)
- **Max up (highest minute high after entry):** mean +45 %, median +28 %; by minute closes: mean +42 %, median +25 %

| Max up reached (minute high) | Trades | Share |
|---|---|---|
| ≥ +0 % | 252 | 97 % |
| ≥ +25 % | 136 | 53 % |
| ≥ +50 % | 83 | 32 % |
| ≥ +100 % | 38 | 15 % |
| ≥ +200 % | 3 | 1 % |
| ≥ +400 % | 0 | 0 % |

| Days to expiry | Trades | Mean at 15:15 | Max up mean | Max up median |
|---|---|---|---|---|
| 0.0 | 1 | +54.0 % | +124 % | +124 % |
| 1.0 | 57 | -8.1 % | +53 % | +36 % |
| 2.0 | 51 | +3.2 % | +54 % | +35 % |
| 3.0 | 53 | +4.3 % | +46 % | +29 % |
| 4+ | 97 | -2.9 % | +35 % | +20 % |

| Year | Trades | Mean at 15:15 | Total ₹ |
|---|---|---|---|
| 2024 | 32 | +3.1 % | 1,340 |
| 2025 | 123 | -6.1 % | -70,428 |
| 2026 | 104 | +3.4 % | 2,358 |

Biggest max-up days:

| Day | Entry | Paid | Max up | At 15:15 |
|---|---|---|---|---|
| 2026-02-19 | 09:31 | 110.3 | +252 % | +236 % |
| 2025-12-08 | 09:36 | 72.1 | +238 % | +193 % |
| 2026-08-24 | 09:59 | 36.6 | +200 % | +136 % |
| 2024-11-12 | 09:32 | 102.0 | +198 % | +174 % |
| 2026-01-09 | 09:34 | 79.4 | +183 % | +114 % |
