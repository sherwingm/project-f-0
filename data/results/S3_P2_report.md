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

- Trades 52, **win rate 29 %**; the index moved more than the premium paid on 38 % of days (break-even before costs).
- Net per trade: **-34.8 % of the premium** (median -47.9 %), t -3.08; ₹-296 a trade (t -1.41), total ₹-15,404.
- Average premium paid 28.3 points (₹1,765); fees ₹98 a trade.
- Halves: -63.3 % / -8.5 %.
- Worst day ₹-4,048; average month ₹-1,284; deepest drawdown ₹-16,605.
- At 2x costs: -45.6 % of the premium.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-25,127, median ₹-19,357, 95th ₹-15,404.

## Grid (net % of premium per trade · trades · win rate · t)

| Entry | Exit | Target | Result |
|---|---|---|---|
| 14:30 | 15:15 | none | -33.5 % · 52 · 25 % · -3.7 |
| 14:30 | 15:15 | +50 % | -24.9 % · 52 · 35 % · -2.7 |
| 14:30 | 15:15 | +100 % | -24.8 % · 52 · 33 % · -2.5 |
| 14:30 | 15:25 | none | -31.5 % · 52 · 27 % · -3.0 |
| 14:30 | 15:25 | +50 % | -26.6 % · 52 · 37 % · -2.8 |
| 14:30 | 15:25 | +100 % | -25.3 % · 52 · 35 % · -2.4 |
| 14:45 | 15:15 | none | -37.2 % · 52 · 19 % · -4.1 |
| 14:45 | 15:15 | +50 % | -23.9 % · 52 · 37 % · -2.4 |
| 14:45 | 15:15 | +100 % | -27.2 % · 52 · 25 % · -2.5 |
| 14:45 | 15:25 | none | -34.8 % · 52 · 29 % · -3.1 |
| 14:45 | 15:25 | +50 % | -27.0 % · 52 · 40 % · -2.6 |
| 14:45 | 15:25 | +100 % | -29.1 % · 52 · 33 % · -2.5 |
| 15:00 | 15:15 | none | -30.2 % · 52 · 29 % · -3.4 |
| 15:00 | 15:15 | +50 % | -26.3 % · 52 · 31 % · -2.8 |
| 15:00 | 15:15 | +100 % | -26.4 % · 52 · 29 % · -2.7 |
| 15:00 | 15:25 | none | -37.4 % · 52 · 29 % · -3.5 |
| 15:00 | 15:25 | +50 % | -34.6 % · 52 · 33 % · -3.3 |
| 15:00 | 15:25 | +100 % | -35.6 % · 52 · 29 % · -3.2 |

## Primary cell by group (side report)

| Group | Trades | Net % of premium | Win rate |
|---|---|---|---|
| VIX <13 | 16 | -1.6 % | 50 % |
| VIX 13-20 | 34 | -58.1 % | 18 % |
| VIX >20 | 2 | +94.4 % | 50 % |
| Thu | 45 | -36.7 % | 29 % |
| Tue | 5 | -9.4 % | 40 % |
| Wed | 2 | -55.6 % | 0 % |
| event day | 1 | -92.9 % | 0 % |
| other day | 51 | -33.7 % | 29 % |

## Days without prices (primary cell)

- 2024-12-26: no price 23750 CE at 14:45
