# S3 P1 · NIFTY expiry-day iron fly: test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_P1_expiry_day_fly.md`. Engine `scanner/s3_engine.py`. Mean, t and halves on net % of the credit; rupees at 1 lot (25 before 2025-01-31, 65-75 after).

Expiry days 53. Primary cell: 37 trades. Not traded: 1 without prices, 2 event days, 13 with VIX outside 13-20.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (fly, 11:15, stop 30 %, exit 14:45, VIX 13-20)

- Trades 37, **win rate 41 %**, stop hit 49 %.
- Net per trade: **-4.9 % of the credit** (median -33.7 %), t -0.68; ₹-438 a trade (t -1.55), total ₹-16,188.
- Halves: +0.3 % / -15.7 %.
- Worst day ₹-3,544; average month ₹-1,799; deepest drawdown ₹-16,950.
- At 2x costs: -14.6 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-24,513, median ₹-19,359, 95th ₹-16,188.

## Grid (net % of credit per trade · trades · win rate · t)

| Structure | Entry | Stop | VIX 13-20 | All VIX |
|---|---|---|---|---|
| fly | 09:20 | 20 % | -10.3 % · 36 · 22 % · -1.7 | -8.2 % · 50 · 26 % · -1.6 |
| fly | 09:20 | 25 % | -12.8 % · 36 · 25 % · -2.0 | -9.8 % · 50 · 30 % · -1.8 |
| fly | 09:20 | 30 % | -11.4 % · 36 · 33 % · -1.6 | -8.1 % · 50 · 38 % · -1.4 |
| fly | 09:20 | 35 % | -12.5 % · 36 · 36 % · -1.8 | -9.6 % · 50 · 40 % · -1.6 |
| fly | 09:20 | none | -20.2 % · 36 · 44 % · -1.9 | -15.4 % · 50 · 50 % · -1.7 |
| fly | 10:00 | 20 % | -1.9 % · 36 · 39 % · -0.3 | -1.6 % · 50 · 38 % · -0.3 |
| fly | 10:00 | 25 % | -2.5 % · 36 · 42 % · -0.3 | -1.7 % · 50 · 42 % · -0.3 |
| fly | 10:00 | 30 % | -4.7 % · 36 · 42 % · -0.6 | -4.2 % · 50 · 42 % · -0.6 |
| fly | 10:00 | 35 % | -5.9 % · 36 · 42 % · -0.7 | -4.9 % · 50 · 42 % · -0.7 |
| fly | 10:00 | none | -8.7 % · 36 · 53 % · -0.7 | -8.9 % · 50 · 52 % · -0.9 |
| fly | 11:15 | 20 % | -7.1 % · 37 · 32 % · -1.0 | -4.0 % · 50 · 36 % · -0.7 |
| fly | 11:15 | 25 % | -8.9 % · 37 · 32 % · -1.3 | -5.8 % · 50 · 36 % · -1.0 |
| fly | 11:15 | 30 % | -4.9 % · 37 · 41 % · -0.7 | -2.4 % · 50 · 44 % · -0.4 |
| fly | 11:15 | 35 % | -7.0 % · 37 · 41 % · -0.9 | -4.1 % · 50 · 44 % · -0.6 |
| fly | 11:15 | none | -9.7 % · 37 · 49 % · -0.9 | -10.7 % · 50 · 50 % · -1.1 |
| straddle | 09:20 | 20 % | +2.2 % · 36 · 39 % · 0.3 | +1.6 % · 50 · 38 % · 0.3 |
| straddle | 09:20 | 25 % | -0.8 % · 36 · 39 % · -0.1 | -0.0 % · 50 · 40 % · -0.0 |
| straddle | 09:20 | 30 % | +0.0 % · 36 · 42 % · 0.0 | +1.5 % · 50 · 44 % · 0.2 |
| straddle | 09:20 | 35 % | -2.3 % · 36 · 42 % · -0.3 | -1.1 % · 50 · 44 % · -0.2 |
| straddle | 09:20 | none | -19.8 % · 36 · 53 % · -1.1 | -11.6 % · 50 · 56 % · -0.9 |
| straddle | 10:00 | 20 % | +2.6 % · 36 · 36 % · 0.3 | +2.2 % · 50 · 36 % · 0.3 |
| straddle | 10:00 | 25 % | +5.6 % · 36 · 42 % · 0.7 | +5.2 % · 50 · 42 % · 0.8 |
| straddle | 10:00 | 30 % | +5.1 % · 36 · 44 % · 0.6 | +3.8 % · 50 · 44 % · 0.5 |
| straddle | 10:00 | 35 % | +5.6 % · 36 · 47 % · 0.6 | +4.7 % · 50 · 48 % · 0.6 |
| straddle | 10:00 | none | -8.6 % · 36 · 58 % · -0.5 | -6.9 % · 50 · 60 % · -0.5 |
| straddle | 11:15 | 20 % | +1.1 % · 37 · 38 % · 0.1 | +2.9 % · 50 · 40 % · 0.5 |
| straddle | 11:15 | 25 % | +2.2 % · 37 · 43 % · 0.3 | +3.1 % · 50 · 44 % · 0.5 |
| straddle | 11:15 | 30 % | -0.0 % · 37 · 46 % · -0.0 | +3.0 % · 50 · 48 % · 0.4 |
| straddle | 11:15 | 35 % | +2.1 % · 37 · 51 % · 0.3 | +3.8 % · 50 · 52 % · 0.5 |
| straddle | 11:15 | none | -0.9 % · 37 · 59 % · -0.1 | -1.6 % · 50 · 58 % · -0.2 |

## Primary cell without the VIX filter, by VIX band and weekday (side report)

| Group | Trades | Net % of credit | Win rate |
|---|---|---|---|
| <13 | 13 | +4.7 % | 54 % |
| 13-20 | 37 | -4.9 % | 41 % |
| Thu | 44 | -2.3 % | 43 % |
| Tue | 5 | +4.7 % | 60 % |
| Wed | 1 | -42.1 % | 0 % |

## Days without prices (primary cell)

- 2024-12-26: no price 23750 CE at 11:15
