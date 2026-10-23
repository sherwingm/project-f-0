# S3 P7 · NIFTY expiry-day short iron fly ±4 14:30 → 15:15, no stop, 5 lots (lead from P2s / P6): test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_P7_expiry_late_fly_5lots.md` (page commit cd4ef41a 2026-10-23T11:36:27+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the credit; rupees at 1 lot.

Days 53. Primary cell: 51 trades. Not traded: 1 without prices, 1 event days.

## Verdict: **FAIL**

- ✔ net mean > 0
- ✔ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✔ neighbours net positive
- ✔ at least 30 trades

## Primary cell (fly ±4 14:30→15:15 no stop, 5 lots)

- Trades 51, **win rate 69 %**, stop hit 0 %.
- Net per trade: **+14.8 % of the credit** (median +29.1 %), t 1.59; ₹+158 a trade (t 0.14), total ₹+8,065.
- Average credit 34.3 points (₹10,545); fees ₹216 a trade; net +1.43 % of margin a trade.
- Halves: +33.0 % / -2.8 %.
- Worst day ₹-35,747; average month ₹+672; deepest drawdown ₹-62,685.
- At 2x costs: +10.0 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-81,888, median ₹-55,382, 95th ₹-37,124.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| fly ±4 14:30→15:15 no stop, 5 lots | +14.8 % · 51 · 69 % · 1.6 |
| fly ±4 14:30→15:25 no stop, 5 lots | +12.1 % · 51 · 71 % · 1.1 |
| fly ±4 14:45→15:15 no stop, 5 lots | +16.6 % · 51 · 73 % · 1.8 |
| fly ±4 14:45→15:25 no stop, 5 lots | +13.6 % · 51 · 69 % · 1.1 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 16 | -1.7 % | 62 % |
| VIX 13-20 | 35 | +22.3 % | 71 % |
| VIX >20 | 1 | +80.8 % | 100 % |
| Thu | 45 | +13.6 % | 67 % |
| Tue | 5 | +24.6 % | 80 % |
| Wed | 2 | +49.6 % | 100 % |
| other day | 51 | +14.8 % | 69 % |
| event day | 1 | +80.8 % | 100 % |

## Days without prices (primary cell)

- 2024-12-26: no price 23750 CE at 14:30
