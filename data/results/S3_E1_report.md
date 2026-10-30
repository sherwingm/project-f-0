# S3 E1 · NIFTY long ATM straddle, 14:45 the session before an event → 14:45 on the event session: test window 2024-10-01 → 2026-10-28

Pre-registered: `strategies/S3_E1_event_straddle.md` (page commit 00b7f0f8 2026-10-30T10:14:05+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the premium paid; rupees at 1 lot.

Days 32. Primary cell: 31 trades. Not traded: 1 without prices.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (E-1 → E 14:45)

- Trades 31, **win rate 26 %**, stop hit 0 %.
- Net per trade: **-6.1 % of the premium paid** (median -8.9 %), t -1.55; ₹-738 a trade (t -0.60), total ₹-22,868.
- Average premium 369.1 points (₹23,979); fees ₹150 a trade; net -6.15 % of margin a trade.
- Halves: -11.3 % / -0.7 %.
- Worst day ₹-15,607; average month ₹-994; deepest drawdown ₹-48,290.
- At 2x costs: -7.8 % of the premium paid.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-63,250, median ₹-44,643, 95th ₹-29,710.

## Grid (net % of the premium paid per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| E-1 → E 14:45 | -6.1 % · 31 · 26 % · -1.6 |
| E-2 → E 14:45 | -7.0 % · 31 · 32 % · -1.8 |
| E-1 → E+1 14:45 | -6.3 % · 31 · 35 % · -1.2 |
| E-1 → E 12:00 | -3.1 % · 31 · 32 % · -1.0 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 10 | -7.3 % | 30 % |
| VIX 13-20 | 19 | -8.0 % | 21 % |
| VIX >20 | 2 | +16.9 % | 50 % |
| Fri | 2 | -22.4 % | 0 % |
| Thu | 7 | -12.0 % | 29 % |
| Tue | 8 | -4.7 % | 38 % |
| Wed | 14 | -1.7 % | 21 % |
| event day | 31 | -6.1 % | 26 % |

## E1 side reports (not the gate)

Window 2024-10-01 → 2026-10-28; halves 2024-10-01 → 2025-09-30 and 2025-10-01 → 2026-10-28. Events 32; without a session in the store: none.

| Event type | Trades | Net % of premium | Median | Win rate |
|---|---|---|---|---|
| Budget | 2 | -22.4 % | -22.4 % | 0 % |
| FOMC | 15 | -3.0 % | -6.2 % | 20 % |
| RBI | 13 | -6.6 % | -14.3 % | 38 % |
| US election | 1 | -14.3 % | -14.3 % | 0 % |

**Baseline (ordinary session pairs, E-1 → E 14:45 (no event)):** 472 trades, -3.0 % of the premium a trade (median -8.6 %, t -2.53), win rate 32 %.

## Primary trades

| day | event_day | event_type | legs | exit_at | reason | net_rs | net_pct_premium |
|---|---|---|---|---|---|---|---|
| 2024-10-08 | 2024-10-09 | RBI | B24950CE@124.07>111.44;B24950PE@146.78>69.05 | 14:45 | time | -2,365 | -34.9 % |
| 2024-11-05 | 2024-11-06 | US election | B24200CE@152.11>268.00;B24200PE@171.70>13.93 | 14:45 | time | -1,159 | -14.3 % |
| 2024-11-07 | 2024-11-08 | FOMC | B24200CE@188.84>131.09;B24200PE@164.72>152.88 | 14:45 | time | -1,852 | -20.9 % |
| 2024-12-05 | 2024-12-06 | RBI | B24800CE@227.73>140.05;B24800PE@228.49>236.31 | 14:45 | time | -2,114 | -18.5 % |
| 2025-01-29 | 2025-01-30 | FOMC | B23150CE@359.14>396.96;B23150PE@324.31>255.96 | 14:45 | time | -2,501 | -4.9 % |
| 2025-01-31 | 2025-02-01 | Budget | B23500CE@283.61>154.57;B23500PE@231.35>154.37 | 14:45 | time | -15,607 | -40.4 % |
| 2025-02-06 | 2025-02-07 | RBI | B23550CE@241.05>125.62;B23550PE@154.02>189.85 | 14:45 | time | -6,123 | -20.7 % |
| 2025-03-19 | 2025-03-20 | FOMC | B22950CE@176.63>310.29;B22950PE@153.66>49.70 | 14:45 | time | +2,070 | +8.4 % |
| 2025-04-08 | 2025-04-09 | RBI | B22600CE@351.15>200.44;B22600PE@304.77>364.57 | 14:45 | time | -7,016 | -14.3 % |
| 2025-05-07 | 2025-05-08 | FOMC | B24400CE@223.01>194.67;B24400PE@232.41>283.43 | 14:45 | time | +1,522 | +4.5 % |
| 2025-06-05 | 2025-06-06 | RBI | B24750CE@222.05>336.31;B24750PE@161.50>71.74 | 14:45 | time | +1,671 | +5.8 % |
| 2025-06-18 | 2025-06-19 | FOMC | B24800CE@219.44>203.43;B24800PE@193.56>174.82 | 14:45 | time | -2,770 | -8.9 % |
| 2025-07-30 | 2025-07-31 | FOMC | B24850CE@183.36>175.32;B24850PE@125.27>131.69 | 14:45 | time | -271 | -1.2 % |
| 2025-08-05 | 2025-08-06 | RBI | B24650CE@79.60>36.22;B24650PE@100.30>115.27 | 14:45 | time | -2,253 | -16.7 % |
| 2025-09-17 | 2025-09-18 | FOMC | B25300CE@144.77>157.46;B25300PE@73.16>42.74 | 14:45 | time | -1,461 | -8.9 % |
| 2025-09-30 | 2025-10-01 | RBI | B24650CE@165.57>261.59;B24650PE@111.40>31.89 | 14:45 | time | +1,091 | +5.2 % |
| 2025-10-29 | 2025-10-30 | FOMC | B26050CE@180.50>77.56;B26050PE@114.17>178.10 | 14:45 | time | -3,066 | -13.9 % |
| 2025-12-04 | 2025-12-05 | RBI | B26000CE@119.59>195.42;B26000PE@93.57>26.42 | 14:45 | time | +517 | +3.2 % |
| 2025-12-10 | 2025-12-11 | FOMC | B25750CE@152.21>203.93;B25750PE@110.05>43.93 | 14:45 | time | -1,219 | -6.2 % |
| 2026-01-28 | 2026-01-29 | FOMC | B25250CE@235.32>313.13;B25250PE@191.55>108.11 | 14:45 | time | -526 | -1.9 % |
| 2026-01-30 | 2026-02-01 | Budget | B25300CE@208.89>60.84;B25300PE@198.44>330.69 | 14:45 | time | -1,182 | -4.5 % |
| 2026-02-05 | 2026-02-06 | RBI | B25600CE@157.99>140.94;B25600PE@116.73>79.20 | 14:45 | time | -3,677 | -20.6 % |
| 2026-03-18 | 2026-03-19 | FOMC | B23800CE@205.87>31.69;B23800PE@232.86>745.85 | 14:45 | time | +21,818 | +76.5 % |
| 2026-04-07 | 2026-04-08 | RBI | B23050CE@339.54>997.89;B23050PE@350.69>27.66 | 14:45 | time | +21,553 | +48.0 % |
| 2026-04-29 | 2026-04-30 | FOMC | B24250CE@187.28>109.35;B24250PE@196.48>270.74 | 14:45 | time | -392 | -1.6 % |
| 2026-06-04 | 2026-06-05 | RBI | B23450CE@174.77>146.07;B23450PE@142.21>133.78 | 14:45 | time | -2,552 | -12.4 % |
| 2026-06-17 | 2026-06-18 | FOMC | B24050CE@150.00>142.33;B24050PE@162.36>94.82 | 14:45 | time | -5,021 | -24.7 % |
| 2026-07-29 | 2026-07-30 | FOMC | B24250CE@132.16>111.99;B24250PE@129.70>103.78 | 14:45 | time | -3,125 | -18.4 % |
| 2026-08-04 | 2026-08-05 | RBI | B24450CE@176.88>209.05;B24450PE@132.01>114.57 | 14:45 | time | +814 | +4.0 % |
| 2026-09-16 | 2026-09-17 | FOMC | B23250CE@155.12>145.27;B23250PE@156.33>96.96 | 14:45 | time | -4,633 | -22.9 % |
| 2026-10-06 | 2026-10-07 | RBI | B22700CE@175.57>103.28;B22700PE@142.66>170.29 | 14:45 | time | -3,041 | -14.7 % |

## Days without prices (primary cell)

- 2024-12-18: no price 24200 CE at 14:45
