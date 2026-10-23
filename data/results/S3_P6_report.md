# S3 P6 · NIFTY expiry-day short ATM straddle 14:30 → 15:15, no stop (lead from P2s): test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_P6_expiry_late_naked_straddle.md`. Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the credit; rupees at 1 lot.

Days 53. Primary cell: 50 trades. Not traded: 1 without prices, 2 event days.

## Verdict: **FAIL**

- ✔ net mean > 0
- ✔ net mean > 0 at 2x costs
- ✔ t >= 2
- ✔ positive in each half
- ✘ worst day smaller than the average month
- ✔ neighbours net positive
- ✔ at least 30 trades

## Primary cell (short straddle 14:30→15:15 no stop)

- Trades 50, **win rate 70 %**, stop hit 0 %.
- Net per trade: **+18.7 % of the credit** (median +32.8 %), t 2.45; ₹+255 a trade (t 1.38), total ₹+12,769.
- Average credit 37.0 points (₹2,111); fees ₹99 a trade; net +0.18 % of margin a trade.
- Halves: +29.5 % / +7.8 %.
- Worst day ₹-4,421; average month ₹+1,064; deepest drawdown ₹-8,876.
- At 2x costs: +9.2 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-9,637, median ₹-6,114, 95th ₹-4,421.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| short straddle 14:30→15:15 no stop | +18.7 % · 50 · 70 % · 2.4 |
| short straddle 14:30→15:25 no stop | +16.8 % · 50 · 72 % · 1.8 |
| short straddle 14:45→15:15 no stop | +16.0 % · 50 · 72 % · 1.9 |
| short straddle 14:45→15:25 no stop | +13.8 % · 50 · 68 % · 1.3 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 16 | +0.2 % | 62 % |
| VIX 13-20 | 35 | +20.9 % | 71 % |
| VIX >20 | 1 | +73.2 % | 100 % |
| Thu | 45 | +13.2 % | 67 % |
| Tue | 5 | +24.8 % | 80 % |
| Wed | 2 | +45.4 % | 100 % |
| other day | 50 | +18.7 % | 70 % |
| event day | 2 | -61.7 % | 50 % |

## Days without prices (primary cell)

- 2024-12-26: no price 23750 CE at 14:30
