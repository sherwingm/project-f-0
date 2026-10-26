# S3 R1d_1lot · SENSEX placebo short straddle (non-expiry day, nearest weekly) 14:30→15:15, 1 lot: test window 2024-10-01 → 2025-09-30

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

## Primary cell (placebo short straddle (non-expiry day, nearest weekly) 14:30→15:15, 1 lot)

- Trades 187, **win rate 32 %**, stop hit 0 %.
- Net per trade: **-1.5 % of the credit** (median -1.4 %), t -3.74; ₹-249 a trade (t -3.65), total ₹-46,569.
- Average credit 827.3 points (₹16,547); fees ₹134 a trade; net -0.13 % of margin a trade.
- Halves: -0.6 % / -2.5 %.
- Worst day ₹-6,595; average month ₹-3,881; deepest drawdown ₹-49,340.
- At 2x costs: -3.9 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-52,042, median ₹-47,765, 95th ₹-46,569.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| placebo short straddle (non-expiry day, nearest weekly) 14:30→15:15, 1 lot | -1.5 % · 187 · 32 % · -3.7 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 59 | -2.9 % | 25 % |
| VIX 13-20 | 130 | -1.0 % | 35 % |
| VIX >20 | 3 | -6.9 % | 0 % |
| Fri | 36 | -1.9 % | 22 % |
| Mon | 47 | +0.7 % | 53 % |
| Thu | 44 | -2.1 % | 25 % |
| Tue | 18 | -3.1 % | 33 % |
| Wed | 47 | -2.8 % | 21 % |
| other day | 187 | -1.5 % | 32 % |
| event day | 5 | -5.8 % | 20 % |

## Days without prices (primary cell)

- 2024-10-21: no price 81400 PE at 14:30
- 2024-10-22: no price 80600 CE at 14:30
- 2025-03-24: no price 78000 PE at 14:30
- 2025-04-07: no price 72600 CE at 14:30
