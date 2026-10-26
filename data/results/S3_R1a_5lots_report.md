# S3 R1a_5lots · SENSEX short straddle 14:30→15:15, 5 lots: test window 2024-10-01 → 2025-09-30

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

## Primary cell (short straddle 14:30→15:15, 5 lots)

- Trades 50, **win rate 56 %**, stop hit 0 %.
- Net per trade: **-2.7 % of the credit** (median +7.3 %), t -0.22; ₹-332 a trade (t -0.22), total ₹-16,621.
- Average credit 134.9 points (₹13,485); fees ₹126 a trade; net -0.04 % of margin a trade.
- Halves: -8.8 % / +2.9 %.
- Worst day ₹-29,740; average month ₹-1,385; deepest drawdown ₹-79,226.
- At 2x costs: -5.4 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-115,705, median ₹-77,865, 95th ₹-51,509.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| short straddle 14:30→15:15, 5 lots | -2.7 % · 50 · 56 % · -0.2 |
| short straddle 14:30→15:25, 5 lots | -1.6 % · 50 · 60 % · -0.1 |
| short straddle 14:45→15:15, 5 lots | +7.6 % · 48 · 67 % · 0.6 |
| short straddle 14:45→15:25, 5 lots | +8.7 % · 48 · 71 % · 0.7 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 13 | -16.2 % | 62 % |
| VIX 13-20 | 37 | +6.2 % | 57 % |
| VIX >20 | 1 | -73.7 % | 0 % |
| Fri | 11 | -9.6 % | 45 % |
| Thu | 6 | -3.9 % | 50 % |
| Tue | 34 | +2.2 % | 62 % |
| other day | 50 | -2.7 % | 56 % |
| event day | 1 | +81.0 % | 100 % |
