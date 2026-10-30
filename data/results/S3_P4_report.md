# S3 P4 · NIFTY 15-min opening-range breakout, long ATM option, 25 % stop + 25 % trail: test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_P4_orb_directional.md` (page commit 4d2b38f4 2026-10-23T11:30:07+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the premium paid; rupees at 1 lot.

Days 248. Primary cell: 58 trades. Not traded: 8 without prices, 124 with VIX outside 0-13.999.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (OR 15 min · trail 25 % · stop 25 %)

- Trades 58, **win rate 31 %**, stop hit 16 %.
- Net per trade: **-2.6 % of the premium paid** (median -12.1 %), t -0.66; ₹-384 a trade (t -1.48), total ₹-22,297.
- Average premium 122.8 points (₹8,013); fees ₹66 a trade; net -2.64 % of margin a trade.
- Halves: +5.8 % / -6.8 %.
- Worst day ₹-3,863; average month ₹-2,477; deepest drawdown ₹-37,944.
- At 2x costs: -4.7 % of the premium paid.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-36,265, median ₹-27,905, 95th ₹-22,297.

## Grid (net % of the premium paid per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| OR 15 min · trail 20 % · stop 20 % | -2.6 % · 58 · 26 % · -0.8 |
| OR 15 min · trail 20 % · stop 25 % | -3.0 % · 58 · 26 % · -0.9 |
| OR 15 min · trail 20 % · stop 30 % | -3.4 % · 58 · 26 % · -1.0 |
| OR 15 min · trail 20 % · stop none | -2.5 % · 58 · 28 % · -0.7 |
| OR 15 min · trail 25 % · stop 20 % | -5.0 % · 58 · 28 % · -1.5 |
| OR 15 min · trail 25 % · stop 25 % | -2.6 % · 58 · 31 % · -0.7 |
| OR 15 min · trail 25 % · stop 30 % | -3.0 % · 58 · 31 % · -0.7 |
| OR 15 min · trail 25 % · stop none | -2.3 % · 58 · 33 % · -0.5 |
| OR 15 min · trail 30 % · stop 20 % | -3.4 % · 58 · 33 % · -1.0 |
| OR 15 min · trail 30 % · stop 25 % | -2.2 % · 58 · 36 % · -0.5 |
| OR 15 min · trail 30 % · stop 30 % | -2.0 % · 58 · 38 % · -0.5 |
| OR 15 min · trail 30 % · stop none | -1.4 % · 58 · 40 % · -0.3 |
| OR 30 min · trail 20 % · stop 20 % | -4.8 % · 47 · 28 % · -1.8 |
| OR 30 min · trail 20 % · stop 25 % | -4.9 % · 47 · 28 % · -1.8 |
| OR 30 min · trail 20 % · stop 30 % | -5.2 % · 47 · 28 % · -1.9 |
| OR 30 min · trail 20 % · stop none | -5.9 % · 47 · 30 % · -1.7 |
| OR 30 min · trail 25 % · stop 20 % | -5.7 % · 47 · 30 % · -1.5 |
| OR 30 min · trail 25 % · stop 25 % | -6.1 % · 47 · 30 % · -1.6 |
| OR 30 min · trail 25 % · stop 30 % | -6.4 % · 47 · 30 % · -1.7 |
| OR 30 min · trail 25 % · stop none | -6.7 % · 47 · 32 % · -1.5 |
| OR 30 min · trail 30 % · stop 20 % | -3.2 % · 47 · 36 % · -0.8 |
| OR 30 min · trail 30 % · stop 25 % | -3.9 % · 47 · 38 % · -0.9 |
| OR 30 min · trail 30 % · stop 30 % | -4.6 % · 47 · 38 % · -1.0 |
| OR 30 min · trail 30 % · stop none | -4.8 % · 47 · 40 % · -1.0 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 69 | -1.0 % | 32 % |
| VIX 13-20 | 167 | -3.7 % | 29 % |
| VIX >20 | 4 | -9.1 % | 25 % |
| Fri | 45 | +4.2 % | 42 % |
| Mon | 48 | -2.3 % | 29 % |
| Sat | 1 | -29.7 % | 0 % |
| Thu | 48 | +1.1 % | 38 % |
| Tue | 51 | -6.3 % | 22 % |
| Wed | 47 | -10.9 % | 19 % |
| other day | 233 | -2.5 % | 30 % |
| event day | 7 | -19.1 % | 14 % |

## Primary cell by filter (side report, not the gate)

| Filter | Trades | Net % of premium | Win rate | t |
|---|---|---|---|---|
| no filter | 240 | -3.0 % | 30 % | -1.5 |
| trend only | 118 | -1.3 % | 31 % | -0.4 |
| VIX < 14 only | 116 | -2.5 % | 30 % | -0.9 |
| both (primary) | 58 | -2.6 % | 31 % | -0.7 |
| both, calls | 28 | -8.9 % | 21 % | -2.1 |
| both, puts | 30 | +3.2 % | 40 % | 0.5 |

Primary exits: {'trail': 36, 'time': 13, 'stop': 9}; median signal time 09:35.

## Days without prices (primary cell)

- 2024-12-19: no breakout
- 2024-12-20: no price 24000 CE at 09:38
- 2024-12-23: no price 23700 PE at 09:38
- 2024-12-24: no price 23700 PE at 09:33
- 2025-04-15: no breakout
- 2025-05-09: no breakout
- 2025-05-19: no breakout
- 2025-09-25: no price 25000 PE at 10:46
