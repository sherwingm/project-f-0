# S3 P7 · NIFTY expiry-day short iron fly ±4 14:30 → 15:15, no stop, 5 lots (lead from P2s / P6): test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_P7_expiry_late_fly_5lots.md`. Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the credit; rupees at 1 lot.

Days 53. Primary cell: 50 trades. Not traded: 1 without prices, 2 event days.

## Verdict: **FAIL**

- ✔ net mean > 0
- ✔ net mean > 0 at 2x costs
- ✔ t >= 2
- ✔ positive in each half
- ✘ worst day smaller than the average month
- ✔ neighbours net positive
- ✔ at least 30 trades

## Primary cell (fly ±4 14:30→15:15 no stop, 5 lots)

- Trades 50, **win rate 70 %**, stop hit 0 %.
- Net per trade: **+18.8 % of the credit** (median +30.2 %), t 2.25; ₹+931 a trade (t 1.01), total ₹+46,534.
- Average credit 34.1 points (₹9,856); fees ₹213 a trade; net +2.66 % of margin a trade.
- Halves: +32.4 % / +5.2 %.
- Worst day ₹-22,884; average month ₹+3,878; deepest drawdown ₹-47,697.
- At 2x costs: +13.7 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-52,153, median ₹-33,497, 95th ₹-22,884.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| fly ±4 14:30→15:15 no stop, 5 lots | +18.8 % · 50 · 70 % · 2.2 |
| fly ±4 14:30→15:25 no stop, 5 lots | +16.4 % · 50 · 72 % · 1.6 |
| fly ±4 14:45→15:15 no stop, 5 lots | +18.9 % · 50 · 72 % · 2.1 |
| fly ±4 14:45→15:25 no stop, 5 lots | +16.1 % · 50 · 68 % · 1.4 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 16 | -1.7 % | 62 % |
| VIX 13-20 | 35 | +21.8 % | 71 % |
| VIX >20 | 1 | +80.8 % | 100 % |
| Thu | 45 | +13.2 % | 67 % |
| Tue | 5 | +24.6 % | 80 % |
| Wed | 2 | +49.6 % | 100 % |
| other day | 50 | +18.8 % | 70 % |
| event day | 2 | -62.0 % | 50 % |

## Days without prices (primary cell)

- 2024-12-26: no price 23750 CE at 14:30
