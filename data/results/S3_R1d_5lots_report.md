# S3 R1d_5lots · SENSEX placebo short straddle (non-expiry day, nearest weekly) 14:30→15:15, 5 lots: test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_R1_sensex_late_expiry_replication.md` (page commit 4efb9321 2026-10-23T14:19:37+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the credit; rupees at 1 lot.

Days 196. Primary cell: 187 trades. Not traded: 4 without prices, 5 event days.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✔ neighbours net positive
- ✔ at least 30 trades

## Primary cell (placebo short straddle (non-expiry day, nearest weekly) 14:30→15:15, 5 lots)

- Trades 187, **win rate 34 %**, stop hit 0 %.
- Net per trade: **-1.0 % of the credit** (median -1.0 %), t -2.49; ₹-868 a trade (t -2.54), total ₹-162,231.
- Average credit 827.3 points (₹82,734); fees ₹291 a trade; net -0.09 % of margin a trade.
- Halves: -0.1 % / -1.9 %.
- Worst day ₹-32,598; average month ₹-13,519; deepest drawdown ₹-192,552.
- At 2x costs: -2.9 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-198,967, median ₹-173,487, 95th ₹-162,231.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| placebo short straddle (non-expiry day, nearest weekly) 14:30→15:15, 5 lots | -1.0 % · 187 · 34 % · -2.5 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 59 | -2.2 % | 27 % |
| VIX 13-20 | 130 | -0.5 % | 37 % |
| VIX >20 | 3 | -6.6 % | 0 % |
| Fri | 36 | -1.4 % | 28 % |
| Mon | 47 | +1.3 % | 53 % |
| Thu | 44 | -1.6 % | 27 % |
| Tue | 18 | -2.5 % | 39 % |
| Wed | 47 | -2.4 % | 21 % |
| other day | 187 | -1.0 % | 34 % |
| event day | 5 | -5.4 % | 20 % |

## Days without prices (primary cell)

- 2024-10-21: no price 81400 PE at 14:30
- 2024-10-22: no price 80600 CE at 14:30
- 2025-03-24: no price 78000 PE at 14:30
- 2025-04-07: no price 72600 CE at 14:30
