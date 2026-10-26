# S3 R1b · SENSEX long straddle 14:45→15:25, 1 lot: test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_R1_sensex_late_expiry_replication.md` (page commit 4efb9321 2026-10-23T14:19:37+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the premium paid; rupees at 1 lot.

Days 51. Primary cell: 49 trades. Not traded: 2 without prices.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (long straddle 14:45→15:25, 1 lot)

- Trades 49, **win rate 24 %**, stop hit 0 %.
- Net per trade: **-20.6 % of the premium paid** (median -37.7 %), t -1.69; ₹-427 a trade (t -1.62), total ₹-20,905.
- Average premium 108.3 points (₹2,166); fees ₹99 a trade; net -20.58 % of margin a trade.
- Halves: -17.6 % / -23.5 %.
- Worst day ₹-5,050; average month ₹-1,742; deepest drawdown ₹-23,601.
- At 2x costs: -28.0 % of the premium paid.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-31,780, median ₹-24,757, 95th ₹-20,905.

## Grid (net % of the premium paid per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| long straddle 14:45→15:25, 1 lot | -20.6 % · 49 · 24 % · -1.7 |
| long straddle 14:30→15:25, 1 lot | -9.2 % · 51 · 37 % · -0.8 |
| long straddle 15:00→15:25, 1 lot | -19.9 % · 50 · 32 % · -1.6 |
| long straddle 14:45→15:15, 1 lot | -19.3 % · 49 · 27 % · -1.6 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 13 | +12.6 % | 38 % |
| VIX 13-20 | 35 | -32.3 % | 20 % |
| VIX >20 | 1 | -41.8 % | 0 % |
| Fri | 11 | -14.7 % | 27 % |
| Thu | 6 | -6.4 % | 33 % |
| Tue | 32 | -25.3 % | 22 % |
| other day | 48 | -19.1 % | 25 % |
| event day | 1 | -93.5 % | 0 % |

## Days without prices (primary cell)

- 2025-03-25: no price 78000 PE at 14:45
- 2025-06-24: no price 82000 CE at 14:45
