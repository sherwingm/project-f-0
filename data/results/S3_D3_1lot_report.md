# S3 D3_1lot · placebo: short straddle 14:30→15:15 on non-expiry days, 1 lot: test window 2024-10-01 → 2025-09-30

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

## Primary cell (placebo: short straddle 14:30→15:15 on non-expiry days, 1 lot)

- Trades 186, **win rate 39 %**, stop hit 0 %.
- Net per trade: **-1.7 % of the credit** (median -0.9 %), t -3.31; ₹-203 a trade (t -3.01), total ₹-37,685.
- Average credit 237.6 points (₹14,772); fees ₹129 a trade; net -0.11 % of margin a trade.
- Halves: -1.3 % / -2.1 %.
- Worst day ₹-6,755; average month ₹-3,140; deepest drawdown ₹-41,770.
- At 2x costs: -4.3 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-43,951, median ₹-39,403, 95th ₹-37,685.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| placebo: short straddle 14:30→15:15 on non-expiry days, 1 lot | -1.7 % · 186 · 39 % · -3.3 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 56 | -2.1 % | 38 % |
| VIX 13-20 | 131 | -1.4 % | 40 % |
| VIX >20 | 4 | -4.7 % | 25 % |
| Fri | 46 | -1.1 % | 37 % |
| Mon | 49 | -0.9 % | 45 % |
| Thu | 4 | -3.5 % | 25 % |
| Tue | 47 | -3.4 % | 34 % |
| Wed | 45 | -1.3 % | 40 % |
| other day | 186 | -1.7 % | 39 % |
| event day | 5 | -1.7 % | 40 % |

## Days without prices (primary cell)

- 2024-12-20: no price 23700 CE at 14:30
- 2024-12-23: no price 23750 CE at 14:30
- 2024-12-24: no price 23750 CE at 14:30
- 2025-08-23: no expiry
