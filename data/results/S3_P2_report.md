# S3 P2 · NIFTY expiry-day long straddle 14:45 → 15:25: test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_P2_expiry_last30_straddle.md`. Engine `scanner/s3_engine.py`. Mean, t and halves on net % of the premium paid; rupees at 1 lot.

Expiry days 53. Primary cell: 52 trades; 1 without prices.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (buy the ATM CE + PE at 14:45, sell at 15:25)

- Trades 52, **win rate 27 %**; the index moved more than the premium paid on 38 % of days (break-even before costs).
- Net per trade: **-35.8 % of the premium** (median -50.5 %), t -3.17; ₹-286 a trade (t -1.38), total ₹-14,853.
- Average premium paid 28.3 points (₹1,669); fees ₹98 a trade.
- Halves: -65.2 % / -8.5 %.
- Worst day ₹-4,048; average month ₹-1,238; deepest drawdown ₹-16,054.
- At 2x costs: -47.4 % of the premium.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-24,528, median ₹-18,802, 95th ₹-14,853.

## Grid (net % of premium per trade · trades · win rate · t)

| Entry | Exit | Target | Result |
|---|---|---|---|
| 14:30 | 15:15 | none | -34.3 % · 52 · 25 % · -3.8 |
| 14:30 | 15:15 | +50 % | -25.6 % · 52 · 35 % · -2.8 |
| 14:30 | 15:15 | +100 % | -25.5 % · 52 · 33 % · -2.6 |
| 14:30 | 15:25 | none | -32.2 % · 52 · 27 % · -3.0 |
| 14:30 | 15:25 | +50 % | -27.3 % · 52 · 37 % · -2.9 |
| 14:30 | 15:25 | +100 % | -26.1 % · 52 · 35 % · -2.5 |
| 14:45 | 15:15 | none | -38.1 % · 52 · 19 % · -4.2 |
| 14:45 | 15:15 | +50 % | -24.9 % · 52 · 37 % · -2.5 |
| 14:45 | 15:15 | +100 % | -28.1 % · 52 · 25 % · -2.6 |
| 14:45 | 15:25 | none | -35.8 % · 52 · 27 % · -3.2 |
| 14:45 | 15:25 | +50 % | -27.9 % · 52 · 38 % · -2.7 |
| 14:45 | 15:25 | +100 % | -30.1 % · 52 · 31 % · -2.6 |
| 15:00 | 15:15 | none | -31.9 % · 52 · 29 % · -3.6 |
| 15:00 | 15:15 | +50 % | -28.0 % · 52 · 31 % · -2.9 |
| 15:00 | 15:15 | +100 % | -28.1 % · 52 · 29 % · -2.8 |
| 15:00 | 15:25 | none | -39.1 % · 52 · 27 % · -3.7 |
| 15:00 | 15:25 | +50 % | -36.3 % · 52 · 31 % · -3.4 |
| 15:00 | 15:25 | +100 % | -37.3 % · 52 · 27 % · -3.4 |

## Primary cell by group (side report)

| Group | Trades | Net % of premium | Win rate |
|---|---|---|---|
| VIX <13 | 16 | -1.6 % | 50 % |
| VIX 13-20 | 34 | -59.5 % | 15 % |
| VIX >20 | 2 | +94.4 % | 50 % |
| Thu | 45 | -37.8 % | 27 % |
| Tue | 5 | -9.4 % | 40 % |
| Wed | 2 | -55.6 % | 0 % |
| event day | 2 | +10.8 % | 50 % |
| other day | 50 | -37.6 % | 26 % |

## Days without prices (primary cell)

- 2024-12-26: no price 23750 CE at 14:45
