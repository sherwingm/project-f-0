# S3 P1 · NIFTY expiry-day iron fly: test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_P1_expiry_day_fly.md`. Engine `scanner/s3_engine.py`. Mean, t and halves on net % of the credit; rupees at 1 lot (25 before 2025-01-31, 65-75 after).

Expiry days 53. Primary cell: 37 trades. Not traded: 1 without prices, 1 event days, 14 with VIX outside 13-20.

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
- Net per trade: **-4.0 % of the credit** (median -33.7 %), t -0.56; ₹-441 a trade (t -1.44), total ₹-16,330.
- Halves: +1.6 % / -15.7 %.
- Worst day ₹-3,544; average month ₹-1,814; deepest drawdown ₹-17,092.
- At 2x costs: -12.9 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-25,763, median ₹-20,126, 95th ₹-16,330.

## Grid (net % of credit per trade · trades · win rate · t)

| Structure | Entry | Stop | VIX 13-20 | All VIX |
|---|---|---|---|---|
| fly | 09:20 | 20 % | -9.7 % · 36 · 22 % · -1.6 | -8.1 % · 51 · 25 % · -1.6 |
| fly | 09:20 | 25 % | -12.1 % · 36 · 25 % · -1.9 | -9.7 % · 51 · 29 % · -1.8 |
| fly | 09:20 | 30 % | -10.7 % · 36 · 33 % · -1.6 | -8.2 % · 51 · 37 % · -1.4 |
| fly | 09:20 | 35 % | -11.9 % · 36 · 36 % · -1.7 | -9.8 % · 51 · 39 % · -1.6 |
| fly | 09:20 | none | -19.5 % · 36 · 44 % · -1.8 | -13.6 % · 51 · 51 % · -1.5 |
| fly | 10:00 | 20 % | -1.2 % · 36 · 39 % · -0.2 | -1.6 % · 51 · 37 % · -0.3 |
| fly | 10:00 | 25 % | -1.7 % · 36 · 42 % · -0.2 | -1.7 % · 51 · 41 % · -0.3 |
| fly | 10:00 | 30 % | -4.0 % · 36 · 42 % · -0.5 | -4.4 % · 51 · 41 % · -0.7 |
| fly | 10:00 | 35 % | -5.1 % · 36 · 42 % · -0.6 | -5.1 % · 51 · 41 % · -0.8 |
| fly | 10:00 | none | -7.9 % · 36 · 53 % · -0.7 | -7.4 % · 51 · 53 % · -0.8 |
| fly | 11:15 | 20 % | -6.3 % · 37 · 32 % · -0.9 | -3.8 % · 51 · 35 % · -0.6 |
| fly | 11:15 | 25 % | -8.1 % · 37 · 32 % · -1.1 | -5.7 % · 51 · 35 % · -0.9 |
| fly | 11:15 | 30 % | -4.0 % · 37 · 41 % · -0.6 | -2.4 % · 51 · 43 % · -0.4 |
| fly | 11:15 | 35 % | -6.2 % · 37 · 41 % · -0.8 | -4.2 % · 51 · 43 % · -0.6 |
| fly | 11:15 | none | -8.9 % · 37 · 49 % · -0.8 | -10.8 % · 51 · 49 % · -1.2 |
| straddle | 09:20 | 20 % | +2.4 % · 36 · 39 % · 0.3 | +1.3 % · 51 · 37 % · 0.2 |
| straddle | 09:20 | 25 % | -0.6 % · 36 · 39 % · -0.1 | -0.4 % · 51 · 39 % · -0.1 |
| straddle | 09:20 | 30 % | +0.3 % · 36 · 42 % · 0.0 | +0.9 % · 51 · 43 % · 0.1 |
| straddle | 09:20 | 35 % | -2.1 % · 36 · 42 % · -0.3 | -1.7 % · 51 · 43 % · -0.3 |
| straddle | 09:20 | none | -19.6 % · 36 · 53 % · -1.1 | -10.0 % · 51 · 57 % · -0.8 |
| straddle | 10:00 | 20 % | +2.9 % · 36 · 36 % · 0.4 | +1.9 % · 51 · 35 % · 0.3 |
| straddle | 10:00 | 25 % | +5.9 % · 36 · 42 % · 0.7 | +4.8 % · 51 · 41 % · 0.7 |
| straddle | 10:00 | 30 % | +5.4 % · 36 · 44 % · 0.6 | +3.1 % · 51 · 43 % · 0.4 |
| straddle | 10:00 | 35 % | +5.9 % · 36 · 47 % · 0.6 | +4.0 % · 51 · 47 % · 0.5 |
| straddle | 10:00 | none | -8.3 % · 36 · 58 % · -0.5 | -5.7 % · 51 · 61 % · -0.4 |
| straddle | 11:15 | 20 % | +1.4 % · 37 · 38 % · 0.2 | +2.5 % · 51 · 39 % · 0.4 |
| straddle | 11:15 | 25 % | +2.6 % · 37 · 43 % · 0.4 | +2.7 % · 51 · 43 % · 0.4 |
| straddle | 11:15 | 30 % | +0.4 % · 37 · 46 % · 0.0 | +2.3 % · 51 · 47 % · 0.3 |
| straddle | 11:15 | 35 % | +2.5 % · 37 · 51 % · 0.3 | +3.1 % · 51 · 51 % · 0.4 |
| straddle | 11:15 | none | -0.6 % · 37 · 59 % · -0.1 | -1.9 % · 51 · 57 % · -0.2 |

## Primary cell without the VIX filter, by VIX band and weekday (side report)

| Group | Trades | Net % of credit | Win rate |
|---|---|---|---|
| <13 | 14 | +1.8 % | 50 % |
| 13-20 | 37 | -4.0 % | 41 % |
| Thu | 45 | -2.3 % | 42 % |
| Tue | 5 | +4.7 % | 60 % |
| Wed | 1 | -42.1 % | 0 % |

## Days without prices (primary cell)

- 2024-12-26: no price 23750 CE at 11:15
