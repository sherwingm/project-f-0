# S3 R2_E1 · SENSEX long ATM straddle, 14:45 the session before an event → 14:45 on the event session: test window 2024-10-01 → 2026-10-28

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

- Trades 31, **win rate 16 %**, stop hit 0 %.
- Net per trade: **-2.8 % of the premium paid** (median -6.6 %), t -0.58; ₹-325 a trade (t -0.23), total ₹-10,074.
- Average premium 1184.8 points (₹23,695); fees ₹150 a trade; net -2.81 % of margin a trade.
- Halves: -7.7 % / +2.4 %.
- Worst day ₹-14,834; average month ₹-458; deepest drawdown ₹-43,617.
- At 2x costs: -4.4 % of the premium paid.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-60,345, median ₹-42,335, 95th ₹-28,014.

## Grid (net % of the premium paid per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| E-1 → E 14:45 | -2.8 % · 31 · 16 % · -0.6 |
| E-2 → E 14:45 | -3.8 % · 31 · 32 % · -0.8 |
| E-1 → E+1 14:45 | -6.7 % · 31 · 35 % · -1.3 |
| E-1 → E 12:00 | -1.4 % · 31 · 35 % · -0.4 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 10 | -6.6 % | 10 % |
| VIX 13-20 | 20 | -6.0 % | 15 % |
| VIX >20 | 1 | +99.8 % | 100 % |
| Fri | 2 | -26.1 % | 0 % |
| Thu | 7 | -11.6 % | 14 % |
| Tue | 7 | +5.1 % | 14 % |
| Wed | 15 | +0.7 % | 20 % |
| event day | 31 | -2.8 % | 16 % |

**R2 · SENSEX**, with the substitutions of `strategies/S3_buy_followups_2026-10-30.md` F2 (strike step 100, lot fixed at 20, SENSEX spot / sessions / expiries; events, India VIX, window and gate unchanged).

## E1 side reports (not the gate)

Window 2024-10-01 → 2026-10-28; halves 2024-10-01 → 2025-09-30 and 2025-10-01 → 2026-10-28. Events 32; without a session in the store: none.

| Event type | Trades | Net % of premium | Median | Win rate |
|---|---|---|---|---|
| Budget | 2 | -26.1 % | -26.1 % | 0 % |
| FOMC | 16 | -0.6 % | -6.3 % | 19 % |
| RBI | 12 | -1.8 % | -9.5 % | 17 % |
| US election | 1 | -2.9 % | -2.9 % | 0 % |

**Baseline (ordinary session pairs, E-1 → E 14:45 (no event)):** 467 trades, -2.5 % of the premium a trade (median -9.4 %, t -1.79), win rate 32 %.

## Primary trades

| day | event_day | event_type | legs | exit_at | reason | net_rs | net_pct_premium |
|---|---|---|---|---|---|---|---|
| 2024-10-08 | 2024-10-09 | RBI | B81500CE@539.43>478.45;B81500PE@561.90>403.62 | 14:45 | time | -4,523 | -20.5 % |
| 2024-11-05 | 2024-11-06 | US election | B79400CE@617.77>1084.55;B79400PE@598.88>104.08 | 14:45 | time | -712 | -2.9 % |
| 2024-11-07 | 2024-11-08 | FOMC | B79500CE@669.53>502.52;B79500PE@506.02>444.72 | 14:45 | time | -4,708 | -20.0 % |
| 2024-12-05 | 2024-12-06 | RBI | B82200CE@837.27>486.31;B82200PE@824.10>895.95 | 14:45 | time | -5,745 | -17.3 % |
| 2024-12-18 | 2024-12-19 | FOMC | B80100CE@481.60>108.85;B80100PE@344.71>974.65 | 14:45 | time | +5,000 | +30.3 % |
| 2025-01-29 | 2025-01-30 | FOMC | B76500CE@1030.93>1087.98;B76500PE@977.51>845.25 | 14:45 | time | -1,691 | -4.2 % |
| 2025-01-31 | 2025-02-01 | Budget | B77400CE@794.65>436.11;B77400PE@662.65>286.26 | 14:45 | time | -14,834 | -50.9 % |
| 2025-02-06 | 2025-02-07 | RBI | B77900CE@618.18>288.60;B77900PE@474.36>549.39 | 14:45 | time | -5,227 | -23.9 % |
| 2025-03-19 | 2025-03-20 | FOMC | B75500CE@514.71>1053.21;B75500PE@390.39>96.71 | 14:45 | time | +4,750 | +26.2 % |
| 2025-05-07 | 2025-05-08 | FOMC | B80700CE@596.97>496.50;B80700PE@687.77>710.93 | 14:45 | time | -1,699 | -6.6 % |
| 2025-06-05 | 2025-06-06 | RBI | B81500CE@539.89>841.77;B81500PE@482.40>179.10 | 14:45 | time | -171 | -0.8 % |
| 2025-06-18 | 2025-06-19 | FOMC | B81300CE@612.55>607.60;B81300PE@468.53>370.64 | 14:45 | time | -2,199 | -10.2 % |
| 2025-07-30 | 2025-07-31 | FOMC | B81500CE@450.29>409.79;B81500PE@333.91>350.34 | 14:45 | time | -612 | -3.9 % |
| 2025-08-05 | 2025-08-06 | RBI | B80700CE@487.42>350.84;B80700PE@453.61>483.62 | 14:45 | time | -2,266 | -12.0 % |
| 2025-09-17 | 2025-09-18 | FOMC | B82600CE@573.15>626.20;B82600PE@312.05>213.28 | 14:45 | time | -1,049 | -5.9 % |
| 2025-09-30 | 2025-10-01 | RBI | B80400CE@629.08>920.92;B80400PE@438.73>150.69 | 14:45 | time | -69 | -0.3 % |
| 2025-10-29 | 2025-10-30 | FOMC | B85000CE@688.63>358.20;B85000PE@464.06>662.62 | 14:45 | time | -2,781 | -12.1 % |
| 2025-12-04 | 2025-12-05 | RBI | B85100CE@542.85>770.33;B85100PE@360.90>161.59 | 14:45 | time | +425 | +2.4 % |
| 2025-12-10 | 2025-12-11 | FOMC | B84400CE@603.80>735.40;B84400PE@428.53>233.13 | 14:45 | time | -1,417 | -6.9 % |
| 2026-01-28 | 2026-01-29 | FOMC | B82100CE@870.53>1106.44;B82100PE@685.36>426.01 | 14:45 | time | -636 | -2.0 % |
| 2026-01-30 | 2026-02-01 | Budget | B82200CE@782.24>379.19;B82200PE@690.74>1082.66 | 14:45 | time | -386 | -1.3 % |
| 2026-02-05 | 2026-02-06 | RBI | B83300CE@590.94>570.83;B83300PE@487.42>361.19 | 14:45 | time | -3,067 | -14.2 % |
| 2026-03-18 | 2026-03-19 | FOMC | B76700CE@839.17>182.78;B76700PE@789.58>2413.02 | 14:45 | time | +19,132 | +58.7 % |
| 2026-04-07 | 2026-04-08 | RBI | B74300CE@831.64>3294.84;B74300PE@819.98>16.47 | 14:45 | time | +32,957 | +99.8 % |
| 2026-04-29 | 2026-04-30 | FOMC | B77600CE@869.02>615.01;B77600PE@690.69>905.45 | 14:45 | time | -952 | -3.0 % |
| 2026-06-04 | 2026-06-05 | RBI | B74400CE@739.88>682.87;B74400PE@536.47>512.42 | 14:45 | time | -1,773 | -7.0 % |
| 2026-06-17 | 2026-06-18 | FOMC | B77000CE@633.25>604.96;B77000PE@591.14>380.74 | 14:45 | time | -4,917 | -20.1 % |
| 2026-07-29 | 2026-07-30 | FOMC | B77700CE@539.68>469.99;B77700PE@528.43>470.73 | 14:45 | time | -2,688 | -12.6 % |
| 2026-08-04 | 2026-08-05 | RBI | B78300CE@371.70>381.04;B78300PE@315.62>307.80 | 14:45 | time | -97 | -0.7 % |
| 2026-09-16 | 2026-09-17 | FOMC | B74300CE@668.32>617.20;B74300PE@557.77>402.08 | 14:45 | time | -4,281 | -17.5 % |
| 2026-10-06 | 2026-10-07 | RBI | B72900CE@353.46>147.26;B72900PE@345.22>365.46 | 14:45 | time | -3,839 | -27.5 % |

## Days without prices (primary cell)

- 2025-04-08: no price 74400 CE at 14:45
