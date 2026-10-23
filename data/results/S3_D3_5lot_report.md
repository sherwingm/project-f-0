# S3 D3_5lot · placebo: short straddle 14:30→15:15 on non-expiry days, 5 lots: test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_D3_D5_placebo_tail_sensex.md` (page commit 5ec11e89 2026-10-23T14:20:55+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the credit; rupees at 1 lot.

Days 195. Primary cell: 186 trades. Not traded: 4 without prices, 5 event days.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✔ neighbours net positive
- ✔ at least 30 trades

## Primary cell (placebo: short straddle 14:30→15:15 on non-expiry days, 5 lots)

- Trades 186, **win rate 47 %**, stop hit 0 %.
- Net per trade: **-1.0 % of the credit** (median -0.2 %), t -1.98; ₹-635 a trade (t -1.89), total ₹-118,192.
- Average credit 237.6 points (₹73,862); fees ₹270 a trade; net -0.06 % of margin a trade.
- Halves: -0.4 % / -1.6 %.
- Worst day ₹-33,397; average month ₹-9,849; deepest drawdown ₹-163,464.
- At 2x costs: -2.9 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-162,470, median ₹-135,127, 95th ₹-119,043.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| placebo: short straddle 14:30→15:15 on non-expiry days, 5 lots | -1.0 % · 186 · 47 % · -2.0 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 56 | -1.5 % | 45 % |
| VIX 13-20 | 131 | -0.7 % | 49 % |
| VIX >20 | 4 | -4.5 % | 25 % |
| Fri | 46 | -0.6 % | 39 % |
| Mon | 49 | -0.3 % | 51 % |
| Thu | 4 | -3.0 % | 50 % |
| Tue | 47 | -2.6 % | 47 % |
| Wed | 45 | -0.4 % | 51 % |
| other day | 186 | -1.0 % | 47 % |
| event day | 5 | -1.0 % | 40 % |

## Days without prices (primary cell)

- 2024-12-20: no price 23700 CE at 14:30
- 2024-12-23: no price 23750 CE at 14:30
- 2024-12-24: no price 23750 CE at 14:30
- 2025-08-23: no expiry
