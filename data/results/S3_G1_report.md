# S3 G1 · NIFTY big-gap (≥ 0.5 %) follow-through confirmed at 09:30, long ATM, 25 % stop + 25 % trail: test window 2024-10-01 → 2026-10-28

Pre-registered: `strategies/S3_G1_gap_follow.md` (page commit 00b7f0f8 2026-10-30T10:14:05+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the premium paid; rupees at 1 lot.

Days 512. Primary cell: 33 trades. Not traded: 2 without prices.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (gap 0.5 % · confirm 15 min · stop 25 %)

- Trades 33, **win rate 24 %**, stop hit 15 %.
- Net per trade: **-4.3 % of the premium paid** (median -18.4 %), t -0.54; ₹-416 a trade (t -0.50), total ₹-13,725.
- Average premium 174.1 points (₹11,464); fees ₹74 a trade; net -4.28 % of margin a trade.
- Halves: +18.2 % / -12.7 %.
- Worst day ₹-5,420; average month ₹-915; deepest drawdown ₹-35,543.
- At 2x costs: -6.0 % of the premium paid.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-41,738, median ₹-30,756, 95th ₹-21,062.

## Grid (net % of the premium paid per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| gap 0.5 % · confirm 15 min · stop 25 % | -4.3 % · 33 · 24 % · -0.5 |
| gap 0.4 % · confirm 15 min · stop 25 % | -4.3 % · 48 · 25 % · -0.7 |
| gap 0.6 % · confirm 15 min · stop 25 % | -5.1 % · 27 · 22 % · -0.5 |
| gap 0.5 % · confirm 12 min · stop 25 % | -3.3 % · 37 · 24 % · -0.4 |
| gap 0.5 % · confirm 18 min · stop 25 % | -7.3 % · 35 · 23 % · -1.1 |
| gap 0.5 % · confirm 15 min · stop 20 % | -4.6 % · 33 · 21 % · -0.6 |
| gap 0.5 % · confirm 15 min · stop 30 % | -4.6 % · 33 · 24 % · -0.6 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 5 | -13.4 % | 20 % |
| VIX 13-20 | 19 | -0.1 % | 21 % |
| VIX >20 | 9 | -8.0 % | 33 % |
| Fri | 6 | -10.1 % | 17 % |
| Mon | 12 | +5.0 % | 17 % |
| Thu | 6 | -7.1 % | 17 % |
| Tue | 3 | -15.1 % | 33 % |
| Wed | 6 | -8.8 % | 50 % |
| other day | 33 | -4.3 % | 24 % |

## Side reports (not the gate)

Window 2024-10-01 → 2026-10-28; halves 2024-10-01 → 2025-09-30 and 2025-10-01 → 2026-10-28.

**Baseline (every big gap, no confirmation):** 86 trades, -1.0 % of the premium a trade (median -15.3 %, t -0.24), win rate 30 %.

| Side | Trades | Net % of premium | Win rate | t |
|---|---|---|---|---|
| CE | 16 | +6.0 % | 38 % | 0.4 |
| PE | 17 | -14.0 % | 12 % | -3.2 |

Primary exits: {'trail': 22, 'time': 6, 'stop': 5}.

## Primary trades

| day | gap_pct | legs | exit_at | reason | net_rs | net_pct_premium |
|---|---|---|---|---|---|---|
| 2024-11-25 | 1.45 | B24300CE@185.17>137.71 | 10:14 | stop | -1,242 | -26.8 % |
| 2025-02-04 | 0.64 | B23500CE@121.66>129.54 | 10:39 | trail | +521 | +5.7 % |
| 2025-03-20 | 0.55 | B23050CE@177.88>222.70 | 15:15 | time | +3,276 | +24.6 % |
| 2025-04-08 | 0.92 | B22550CE@156.43>116.51 | 09:50 | stop | -3,063 | -26.1 % |
| 2025-04-11 | 1.23 | B22800CE@241.35>231.09 | 10:36 | trail | -858 | -4.7 % |
| 2025-05-12 | 1.6 | B24600CE@132.46>443.12 | 15:15 | time | +23,184 | +233.4 % |
| 2025-06-23 | -0.56 | B24900PE@140.10>132.98 | 10:42 | trail | -605 | -5.8 % |
| 2025-06-24 | 0.88 | B25200CE@124.62>94.48 | 09:48 | trail | -2,326 | -24.9 % |
| 2025-08-18 | 1.25 | B25000CE@136.03>120.79 | 10:52 | trail | -1,212 | -11.9 % |
| 2026-01-22 | 0.7 | B25400CE@147.03>133.58 | 10:18 | trail | -943 | -9.9 % |
| 2026-01-30 | -0.67 | B25250PE@202.46>156.56 | 13:54 | trail | -3,056 | -23.2 % |
| 2026-03-04 | -1.86 | B24350PE@301.85>231.79 | 14:13 | trail | -4,639 | -23.6 % |
| 2026-03-09 | -2.46 | B23800PE@229.94>159.25 | 10:51 | stop | -4,669 | -31.2 % |
| 2026-03-12 | -0.8 | B23600PE@267.13>213.03 | 10:37 | trail | -3,598 | -20.7 % |
| 2026-03-23 | -1.34 | B22700PE@219.69>269.29 | 13:49 | trail | +3,136 | +22.0 % |
| 2026-03-27 | -0.56 | B23050PE@257.93>343.68 | 15:15 | time | +5,476 | +32.7 % |
| 2026-04-01 | 2.32 | B22900CE@329.54>247.51 | 11:05 | trail | -5,420 | -25.3 % |
| 2026-04-02 | -1.4 | B22250PE@292.30>246.66 | 12:36 | trail | -3,053 | -16.1 % |
| 2026-04-08 | 3.12 | B23900CE@235.97>268.49 | 15:15 | time | +2,026 | +13.2 % |
| 2026-04-15 | 1.44 | B24200CE@233.06>235.52 | 15:15 | time | +77 | +0.5 % |
| 2026-04-30 | -0.69 | B23900PE@197.08>194.03 | 12:11 | trail | -276 | -2.1 % |
| 2026-05-11 | -0.86 | B23950PE@122.66>119.35 | 11:11 | trail | -281 | -3.5 % |
| 2026-05-18 | -0.73 | B23350PE@122.26>95.47 | 10:34 | trail | -1,804 | -22.7 % |
| 2026-05-25 | 0.93 | B23950CE@124.22>93.88 | 12:46 | trail | -2,035 | -25.2 % |
| 2026-06-19 | -0.78 | B23950PE@125.93>91.99 | 10:13 | stop | -2,268 | -27.7 % |
| 2026-07-10 | 0.59 | B24200CE@105.88>92.63 | 11:41 | trail | -923 | -13.4 % |
| 2026-07-13 | -0.71 | B24050PE@111.05>83.13 | 09:42 | trail | -1,876 | -26.0 % |
| 2026-07-20 | -0.64 | B24200PE@112.71>90.94 | 10:11 | trail | -1,477 | -20.2 % |
| 2026-07-27 | 0.6 | B23950CE@82.26>65.02 | 10:08 | trail | -1,178 | -22.0 % |
| 2026-07-29 | 0.79 | B24200CE@135.62>149.00 | 15:15 | time | +799 | +9.1 % |
| 2026-09-02 | -0.82 | B23800PE@111.76>83.08 | 12:43 | stop | -1,925 | -26.5 % |
| 2026-09-11 | -0.88 | B23250PE@98.39>75.42 | 11:10 | trail | -1,552 | -24.3 % |
| 2026-10-22 | -0.54 | B22600PE@162.51>133.68 | 09:45 | trail | -1,943 | -18.4 % |

## Days without prices (primary cell)

- 2024-12-23: no price 23800 CE at 09:30
- 2026-10-21: no price 23100 CE at 09:30
