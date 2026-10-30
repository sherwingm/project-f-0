# S3 R2_Q1 · SENSEX long ATM straddle after a quiet spell, 14:45 → 14:45 three sessions later: test window 2024-10-01 → 2026-10-28

Pre-registered: `strategies/S3_Q1_squeeze_straddle.md` (page commit 00b7f0f8 2026-10-30T10:14:05+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the premium paid; rupees at 1 lot.

Days 512. Primary cell: 31 trades. Not traded: 2 without prices.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (lookback 5 · pct 20 · hold 3)

- Trades 31, **win rate 26 %**, stop hit 0 %.
- Net per trade: **-8.4 % of the premium paid** (median -12.9 %), t -1.71; ₹-1,523 a trade (t -1.48), total ₹-47,215.
- Average premium 1030.0 points (₹20,601); fees ₹141 a trade; net -8.38 % of margin a trade.
- Halves: -2.3 % / -16.9 %.
- Worst day ₹-9,850; average month ₹-3,632; deepest drawdown ₹-64,712.
- At 2x costs: -10.0 % of the premium paid.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-74,735, median ₹-57,926, 95th ₹-47,215.

## Grid (net % of the premium paid per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| lookback 5 · pct 20 · hold 3 | -8.4 % · 31 · 26 % · -1.7 |
| lookback 5 · pct 16 · hold 3 | -5.9 % · 26 · 27 % · -1.0 |
| lookback 5 · pct 24 · hold 3 | -3.5 % · 38 · 34 % · -0.8 |
| lookback 4 · pct 20 · hold 3 | -8.2 % · 31 · 19 % · -1.2 |
| lookback 6 · pct 20 · hold 3 | -4.0 % · 31 · 32 % · -0.7 |
| lookback 5 · pct 20 · hold 2 | -1.1 % · 39 · 28 % · -0.2 |
| lookback 5 · pct 20 · hold 4 | -4.9 % · 25 · 28 % · -0.6 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 26 | -11.6 % | 23 % |
| VIX 13-20 | 5 | +8.3 % | 40 % |
| Fri | 6 | +1.1 % | 50 % |
| Mon | 9 | -7.9 % | 22 % |
| Thu | 5 | -0.9 % | 40 % |
| Tue | 7 | -11.7 % | 14 % |
| Wed | 4 | -27.4 % | 0 % |
| other day | 31 | -8.4 % | 26 % |

**R2 · SENSEX**, with the substitutions of `strategies/S3_buy_followups_2026-10-30.md` F2 (strike step 100, lot fixed at 20, SENSEX spot / sessions / expiries; events, India VIX, window and gate unchanged).

## Q1 side reports (not the gate)

Window 2024-10-01 → 2026-10-28. Primary signals skipped: ['2024-10-17: no price 80900 CE at 14:45', '2025-09-26: no price 80400 CE at 14:45'].

**Baseline (every 4th session, 3-session straddle, no filter):** 116 trades, -0.5 % of the premium a trade (median -14.4 %, t -0.11), win rate 31 %.

## Primary trades

| day | exit_session | legs | exit_at | reason | net_rs | net_pct_premium |
|---|---|---|---|---|---|---|
| 2024-12-13 | 2024-12-18 | B82000CE@566.57>86.47;B82000PE@576.72>1828.81 | 14:45 | time | +15,261 | +66.7 % |
| 2025-02-24 | 2025-02-28 | B74600CE@751.74>78.20;B74600PE@440.39>1073.45 | 14:45 | time | -959 | -4.0 % |
| 2025-03-03 | 2025-03-06 | B73200CE@646.72>1188.37;B73200PE@499.54>125.37 | 14:45 | time | +3,195 | +13.9 % |
| 2025-06-11 | 2025-06-16 | B82500CE@531.64>54.77;B82500PE@448.63>805.95 | 14:45 | time | -2,527 | -12.9 % |
| 2025-06-20 | 2025-06-25 | B82200CE@784.25>844.01;B82200PE@651.69>283.33 | 14:45 | time | -6,323 | -22.0 % |
| 2025-07-02 | 2025-07-07 | B83200CE@546.47>311.29;B83200PE@411.20>159.95 | 14:45 | time | -9,850 | -51.4 % |
| 2025-07-08 | 2025-07-11 | B83500CE@505.77>60.60;B83500PE@443.86>886.15 | 14:45 | time | -197 | -1.0 % |
| 2025-07-14 | 2025-07-17 | B82100CE@616.67>522.33;B82100PE@423.26>201.64 | 14:45 | time | -6,451 | -31.0 % |
| 2025-07-18 | 2025-07-23 | B81700CE@709.13>1122.91;B81700PE@425.62>66.96 | 14:45 | time | +952 | +4.2 % |
| 2025-07-24 | 2025-07-29 | B82200CE@648.17>164.18;B82200PE@455.37>1004.95 | 14:45 | time | +1,162 | +5.3 % |
| 2025-08-08 | 2025-08-13 | B80000CE@673.35>898.49;B80000PE@423.61>136.66 | 14:45 | time | -1,380 | -6.3 % |
| 2025-08-19 | 2025-08-22 | B81600CE@500.14>207.16;B81600PE@378.33>381.53 | 14:45 | time | -5,920 | -33.7 % |
| 2025-08-25 | 2025-08-29 | B81600CE@618.53>42.54;B81600PE@426.02>1548.02 | 14:45 | time | +10,755 | +51.5 % |
| 2025-09-02 | 2025-09-05 | B80300CE@601.99>658.09;B80300PE@428.88>191.99 | 14:45 | time | -3,752 | -18.2 % |
| 2025-09-10 | 2025-09-15 | B81300CE@588.28>726.35;B81300PE@332.76>85.27 | 14:45 | time | -2,322 | -12.6 % |
| 2025-09-16 | 2025-09-19 | B82300CE@563.50>672.77;B82300PE@408.88>141.74 | 14:45 | time | -3,292 | -16.9 % |
| 2025-09-22 | 2025-09-25 | B82100CE@673.25>176.07;B82100PE@352.25>715.21 | 14:45 | time | -2,822 | -13.8 % |
| 2025-09-30 | 2025-10-06 | B80400CE@629.08>1488.32;B80400PE@438.73>32.64 | 14:45 | time | +8,900 | +41.7 % |
| 2025-10-10 | 2025-10-15 | B82600CE@431.25>222.53;B82600PE@290.55>142.93 | 14:45 | time | -7,241 | -50.2 % |
| 2025-10-16 | 2025-10-23 | B83600CE@751.84>1621.85;B83600PE@568.68>89.10 | 14:45 | time | +7,637 | +28.9 % |
| 2025-12-04 | 2025-12-09 | B85100CE@542.85>126.86;B85100PE@360.90>548.39 | 14:45 | time | -4,698 | -26.0 % |
| 2025-12-16 | 2025-12-19 | B84700CE@603.00>510.39;B84700PE@383.21>190.59 | 14:45 | time | -5,835 | -29.6 % |
| 2025-12-22 | 2025-12-26 | B85500CE@591.64>155.52;B85500PE@432.30>532.97 | 14:45 | time | -6,839 | -33.4 % |
| 2025-12-29 | 2026-01-01 | B84700CE@614.56>787.44;B84700PE@366.82>107.61 | 14:45 | time | -1,864 | -9.5 % |
| 2026-01-02 | 2026-01-07 | B85600CE@363.06>12.14;B85600PE@268.54>716.40 | 14:45 | time | +1,811 | +14.3 % |
| 2026-01-08 | 2026-01-13 | B84300CE@549.84>31.69;B84300PE@302.30>792.37 | 14:45 | time | -695 | -4.1 % |
| 2026-06-22 | 2026-06-25 | B77200CE@717.77>496.31;B77200PE@532.65>483.37 | 14:45 | time | -5,558 | -22.2 % |
| 2026-07-30 | 2026-08-04 | B77700CE@474.71>760.43;B77700PE@475.47>113.13 | 14:45 | time | -1,669 | -8.8 % |
| 2026-08-12 | 2026-08-17 | B77700CE@673.35>510.98;B77700PE@375.72>202.33 | 14:45 | time | -6,846 | -32.6 % |
| 2026-08-18 | 2026-08-21 | B77400CE@614.71>569.14;B77400PE@426.77>230.19 | 14:45 | time | -4,977 | -23.9 % |
| 2026-08-24 | 2026-08-27 | B77300CE@680.89>546.65;B77300PE@416.92>314.62 | 14:45 | time | -4,868 | -22.2 % |

## Days without prices (primary cell)

- 2024-10-17: no price 80900 CE at 14:45
- 2025-09-26: no price 80400 CE at 14:45
