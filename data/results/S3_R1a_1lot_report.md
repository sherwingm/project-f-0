# S3 R1a_1lot · SENSEX short straddle 14:30→15:15, 1 lot: test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_R1_sensex_late_expiry_replication.md` (page commit 4efb9321 2026-10-23T14:19:37+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the credit; rupees at 1 lot.

Days 51. Primary cell: 50 trades. Not traded: 0 without prices, 1 event days.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (short straddle 14:30→15:15, 1 lot)

- Trades 50, **win rate 56 %**, stop hit 0 %.
- Net per trade: **-6.5 % of the credit** (median +2.9 %), t -0.52; ₹-142 a trade (t -0.48), total ₹-7,100.
- Average credit 134.9 points (₹2,697); fees ₹101 a trade; net -0.08 % of margin a trade.
- Halves: -12.3 % / -1.1 %.
- Worst day ₹-6,024; average month ₹-592; deepest drawdown ₹-16,374.
- At 2x costs: -13.0 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-24,802, median ₹-17,258, 95th ₹-11,703.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| short straddle 14:30→15:15, 1 lot | -6.5 % · 50 · 56 % · -0.5 |
| short straddle 14:30→15:25, 1 lot | -5.3 % · 50 · 54 % · -0.4 |
| short straddle 14:45→15:15, 1 lot | +2.7 % · 48 · 67 % · 0.2 |
| short straddle 14:45→15:25, 1 lot | +3.9 % · 48 · 67 % · 0.3 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 13 | -20.0 % | 62 % |
| VIX 13-20 | 37 | +2.4 % | 57 % |
| VIX >20 | 1 | -75.0 % | 0 % |
| Fri | 11 | -13.4 % | 45 % |
| Thu | 6 | -7.4 % | 50 % |
| Tue | 34 | -1.6 % | 62 % |
| other day | 50 | -6.5 % | 56 % |
| event day | 1 | +76.4 % | 100 % |
