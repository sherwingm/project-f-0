# S3 P4 · NIFTY 15-min opening-range breakout, long ATM option, 25 % stop + 25 % trail: test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_P4_orb_directional.md` (page commit 4d2b38f4 2026-10-23T11:30:07+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the premium paid; rupees at 1 lot.

Days 247. Primary cell: 59 trades. Not traded: 6 without prices, 126 with VIX outside 0-13.999.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (OR 15 min · trail 25 % · stop 25 %)

- Trades 59, **win rate 29 %**, stop hit 20 %.
- Net per trade: **-3.6 % of the premium paid** (median -14.7 %), t -0.91; ₹-442 a trade (t -1.72), total ₹-26,049.
- Average premium 120.7 points (₹7,909); fees ₹65 a trade; net -3.64 % of margin a trade.
- Halves: +5.5 % / -7.7 %.
- Worst day ₹-3,863; average month ₹-2,894; deepest drawdown ₹-41,245.
- At 2x costs: -5.7 % of the premium paid.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-38,997, median ₹-30,931, 95th ₹-26,049.

## Grid (net % of the premium paid per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| OR 15 min · trail 20 % · stop 20 % | -3.5 % · 59 · 24 % · -1.1 |
| OR 15 min · trail 20 % · stop 25 % | -4.1 % · 59 · 24 % · -1.2 |
| OR 15 min · trail 20 % · stop 30 % | -4.3 % · 59 · 24 % · -1.3 |
| OR 15 min · trail 20 % · stop none | -3.3 % · 59 · 27 % · -0.9 |
| OR 15 min · trail 25 % · stop 20 % | -5.8 % · 59 · 25 % · -1.8 |
| OR 15 min · trail 25 % · stop 25 % | -3.6 % · 59 · 29 % · -0.9 |
| OR 15 min · trail 25 % · stop 30 % | -3.9 % · 59 · 29 % · -1.0 |
| OR 15 min · trail 25 % · stop none | -3.1 % · 59 · 32 % · -0.7 |
| OR 15 min · trail 30 % · stop 20 % | -4.2 % · 59 · 31 % · -1.2 |
| OR 15 min · trail 30 % · stop 25 % | -3.1 % · 59 · 34 % · -0.7 |
| OR 15 min · trail 30 % · stop 30 % | -2.9 % · 59 · 36 % · -0.7 |
| OR 15 min · trail 30 % · stop none | -2.2 % · 59 · 39 % · -0.5 |
| OR 30 min · trail 20 % · stop 20 % | -5.3 % · 47 · 28 % · -1.9 |
| OR 30 min · trail 20 % · stop 25 % | -5.5 % · 47 · 28 % · -2.0 |
| OR 30 min · trail 20 % · stop 30 % | -5.9 % · 47 · 28 % · -2.0 |
| OR 30 min · trail 20 % · stop none | -7.3 % · 47 · 30 % · -2.0 |
| OR 30 min · trail 25 % · stop 20 % | -6.1 % · 47 · 30 % · -1.7 |
| OR 30 min · trail 25 % · stop 25 % | -6.6 % · 47 · 30 % · -1.8 |
| OR 30 min · trail 25 % · stop 30 % | -7.1 % · 47 · 30 % · -1.9 |
| OR 30 min · trail 25 % · stop none | -8.0 % · 47 · 32 % · -1.8 |
| OR 30 min · trail 30 % · stop 20 % | -3.6 % · 47 · 34 % · -0.9 |
| OR 30 min · trail 30 % · stop 25 % | -4.3 % · 47 · 36 % · -1.0 |
| OR 30 min · trail 30 % · stop 30 % | -5.1 % · 47 · 36 % · -1.2 |
| OR 30 min · trail 30 % · stop none | -6.1 % · 47 · 38 % · -1.2 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 69 | -1.3 % | 32 % |
| VIX 13-20 | 168 | -3.6 % | 29 % |
| VIX >20 | 4 | -19.6 % | 0 % |
| Fri | 46 | +3.8 % | 41 % |
| Mon | 49 | -2.5 % | 31 % |
| Thu | 48 | +1.0 % | 35 % |
| Tue | 51 | -7.1 % | 20 % |
| Wed | 47 | -10.9 % | 19 % |
| other day | 235 | -2.9 % | 29 % |
| event day | 6 | -15.9 % | 17 % |

## Primary cell by filter (side report, not the gate)

| Filter | Trades | Net % of premium | Win rate | t |
|---|---|---|---|---|
| no filter | 241 | -3.2 % | 29 % | -1.6 |
| trend only | 120 | -1.7 % | 30 % | -0.5 |
| VIX < 14 only | 115 | -2.7 % | 30 % | -1.0 |
| both (primary) | 59 | -3.6 % | 29 % | -0.9 |
| both, calls | 28 | -9.0 % | 21 % | -2.1 |
| both, puts | 31 | +1.2 % | 35 % | 0.2 |

Primary exits: {'trail': 35, 'stop': 12, 'time': 12}; median signal time 09:35.

## Days without prices (primary cell)

- 2024-12-19: no breakout
- 2024-12-20: no price 24000 CE at 09:38
- 2024-12-23: no price 23700 PE at 09:38
- 2024-12-24: no price 23700 PE at 09:33
- 2025-04-15: no breakout
- 2025-09-25: no price 25000 PE at 10:46
