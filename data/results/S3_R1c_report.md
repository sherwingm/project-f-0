# S3 R1c · SENSEX short iron fly ±6 14:30→15:15, 5 lots: test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_R1_sensex_late_expiry_replication.md` (page commit 4efb9321 2026-10-23T14:19:37+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the credit; rupees at 1 lot.

Days 51. Primary cell: 49 trades. Not traded: 1 without prices, 1 event days.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (short iron fly ±6 14:30→15:15, 5 lots)

- Trades 49, **win rate 53 %**, stop hit 0 %.
- Net per trade: **-8.7 % of the credit** (median +1.4 %), t -0.66; ₹-1,358 a trade (t -0.92), total ₹-66,544.
- Average credit 122.7 points (₹12,271); fees ₹221 a trade; net -3.64 % of margin a trade.
- Halves: -17.8 % / +0.1 %.
- Worst day ₹-31,064; average month ₹-5,545; deepest drawdown ₹-94,722.
- At 2x costs: -12.7 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-137,224, median ₹-101,753, 95th ₹-75,027.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| short iron fly ±6 14:30→15:15, 5 lots | -8.7 % · 49 · 53 % · -0.7 |
| short iron fly ±6 14:30→15:25, 5 lots | -7.9 % · 49 · 53 % · -0.6 |
| short iron fly ±6 14:45→15:15, 5 lots | +1.9 % · 48 · 65 % · 0.1 |
| short iron fly ±6 14:45→15:25, 5 lots | +2.7 % · 48 · 65 % · 0.2 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 12 | -15.9 % | 58 % |
| VIX 13-20 | 37 | -1.7 % | 54 % |
| VIX >20 | 1 | -95.6 % | 0 % |
| Fri | 11 | -18.4 % | 45 % |
| Thu | 5 | +9.3 % | 60 % |
| Tue | 34 | -5.7 % | 56 % |
| other day | 49 | -8.7 % | 53 % |
| event day | 1 | +76.3 % | 100 % |

## Days without prices (primary cell)

- 2025-09-25: no price 82000 CE at 14:30
