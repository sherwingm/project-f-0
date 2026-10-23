# S3 P6 · NIFTY expiry-day short ATM straddle 14:30 → 15:15, no stop (lead from P2s): test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_P6_expiry_late_naked_straddle.md` (page commit fafc55f8 2026-10-23T11:33:19+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the credit; rupees at 1 lot.

Days 53. Primary cell: 51 trades. Not traded: 1 without prices, 1 event days.

## Verdict: **FAIL**

- ✔ net mean > 0
- ✔ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✔ neighbours net positive
- ✔ at least 30 trades

## Primary cell (short straddle 14:30→15:15 no stop)

- Trades 51, **win rate 71 %**, stop hit 0 %.
- Net per trade: **+15.2 % of the credit** (median +31.9 %), t 1.77; ₹+106 a trade (t 0.45), total ₹+5,392.
- Average credit 37.2 points (₹2,254); fees ₹100 a trade; net +0.12 % of margin a trade.
- Halves: +31.0 % / -0.0 %.
- Worst day ₹-7,107; average month ₹+449; deepest drawdown ₹-10,697.
- At 2x costs: +6.5 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-15,353, median ₹-10,191, 95th ₹-7,107.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| short straddle 14:30→15:15 no stop | +15.2 % · 51 · 71 % · 1.8 |
| short straddle 14:30→15:25 no stop | +13.1 % · 51 · 71 % · 1.3 |
| short straddle 14:45→15:15 no stop | +14.4 % · 51 · 73 % · 1.7 |
| short straddle 14:45→15:25 no stop | +12.0 % · 51 · 69 % · 1.1 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 16 | +0.2 % | 62 % |
| VIX 13-20 | 35 | +22.0 % | 74 % |
| VIX >20 | 1 | +73.2 % | 100 % |
| Thu | 45 | +14.1 % | 69 % |
| Tue | 5 | +24.8 % | 80 % |
| Wed | 2 | +45.4 % | 100 % |
| other day | 51 | +15.2 % | 71 % |
| event day | 1 | +73.2 % | 100 % |

## Days without prices (primary cell)

- 2024-12-26: no price 23750 CE at 14:30
