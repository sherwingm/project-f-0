# S3 R2_G1 · SENSEX big-gap (≥ 0.5 %) follow-through confirmed at 09:30, long ATM, 25 % stop + 25 % trail: test window 2024-10-01 → 2026-10-28

Pre-registered: `strategies/S3_G1_gap_follow.md` (page commit 00b7f0f8 2026-10-30T10:14:05+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the premium paid; rupees at 1 lot.

Days 512. Primary cell: 35 trades. Not traded: 3 without prices.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (gap 0.5 % · confirm 15 min · stop 25 %)

- Trades 35, **win rate 34 %**, stop hit 11 %.
- Net per trade: **-2.3 % of the premium paid** (median -15.4 %), t -0.45; ₹-355 a trade (t -0.63), total ₹-12,428.
- Average premium 608.0 points (₹12,160); fees ₹75 a trade; net -2.35 % of margin a trade.
- Halves: +18.2 % / -11.8 %.
- Worst day ₹-4,678; average month ₹-777; deepest drawdown ₹-29,905.
- At 2x costs: -4.0 % of the premium paid.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-35,087, median ₹-24,377, 95th ₹-16,591.

## Grid (net % of the premium paid per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| gap 0.5 % · confirm 15 min · stop 25 % | -2.3 % · 35 · 34 % · -0.5 |
| gap 0.4 % · confirm 15 min · stop 25 % | -1.0 % · 46 · 35 % · -0.2 |
| gap 0.6 % · confirm 15 min · stop 25 % | -6.7 % · 27 · 30 % · -1.3 |
| gap 0.5 % · confirm 12 min · stop 25 % | -2.5 % · 43 · 28 % · -0.5 |
| gap 0.5 % · confirm 18 min · stop 25 % | -7.7 % · 33 · 30 % · -2.1 |
| gap 0.5 % · confirm 15 min · stop 20 % | -2.2 % · 35 · 31 % · -0.4 |
| gap 0.5 % · confirm 15 min · stop 30 % | -2.6 % · 35 · 34 % · -0.5 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 5 | -14.9 % | 20 % |
| VIX 13-20 | 22 | +2.2 % | 36 % |
| VIX >20 | 8 | -7.1 % | 38 % |
| Fri | 7 | +2.9 % | 43 % |
| Mon | 14 | -6.1 % | 21 % |
| Thu | 6 | -9.2 % | 33 % |
| Tue | 3 | +40.7 % | 100 % |
| Wed | 5 | -16.9 % | 20 % |
| other day | 35 | -2.3 % | 34 % |

**R2 · SENSEX**, with the substitutions of `strategies/S3_buy_followups_2026-10-30.md` F2 (strike step 100, lot fixed at 20, SENSEX spot / sessions / expiries; events, India VIX, window and gate unchanged).

## Side reports (not the gate)

Window 2024-10-01 → 2026-10-28; halves 2024-10-01 → 2025-09-30 and 2025-10-01 → 2026-10-28.

**Baseline (every big gap, no confirmation):** 99 trades, -2.3 % of the premium a trade (median -15.4 %, t -0.68), win rate 28 %.

| Side | Trades | Net % of premium | Win rate | t |
|---|---|---|---|---|
| CE | 18 | +2.0 % | 44 % | 0.2 |
| PE | 17 | -6.9 % | 24 % | -1.1 |

Primary exits: {'trail': 24, 'time': 7, 'stop': 4}.

## Primary trades

| day | gap_pct | legs | exit_at | reason | net_rs | net_pct_premium |
|---|---|---|---|---|---|---|
| 2024-11-25 | 1.36 | B80400CE@650.34>466.75 | 12:50 | stop | -3,743 | -28.8 % |
| 2024-12-23 | 0.57 | B78700CE@647.67>522.23 | 12:04 | trail | -2,582 | -19.9 % |
| 2025-02-03 | -0.67 | B77100PE@301.60>257.60 | 10:42 | trail | -940 | -15.6 % |
| 2025-02-04 | 0.65 | B77700CE@641.48>1050.44 | 15:15 | time | +8,086 | +63.0 % |
| 2025-02-24 | -0.55 | B74800PE@287.57>275.81 | 11:42 | trail | -296 | -5.1 % |
| 2025-02-28 | -0.55 | B73900PE@314.45>545.36 | 14:45 | trail | +4,547 | +72.3 % |
| 2025-03-18 | 0.59 | B74600CE@647.47>1023.51 | 15:15 | time | +7,428 | +57.4 % |
| 2025-04-11 | 1.34 | B75000CE@636.87>648.74 | 10:24 | trail | +160 | +1.2 % |
| 2025-05-12 | 1.7 | B81400CE@257.58>491.78 | 10:47 | trail | +4,616 | +89.6 % |
| 2025-06-24 | 0.78 | B82700CE@604.81>618.69 | 12:40 | trail | +201 | +1.7 % |
| 2025-08-18 | 0.89 | B81700CE@315.82>270.24 | 10:26 | trail | -972 | -15.4 % |
| 2026-01-22 | 0.67 | B82600CE@703.50>569.04 | 10:19 | trail | -2,765 | -19.6 % |
| 2026-03-09 | -2.36 | B76600PE@975.60>753.51 | 10:51 | trail | -4,527 | -23.2 % |
| 2026-03-12 | -0.64 | B76000PE@1013.19>783.61 | 10:58 | trail | -4,678 | -23.1 % |
| 2026-03-23 | -1.07 | B73200PE@864.70>962.56 | 13:50 | trail | +1,865 | +10.8 % |
| 2026-03-25 | 0.79 | B75000CE@1257.71>1331.55 | 15:15 | time | +1,367 | +5.4 % |
| 2026-03-27 | -0.52 | B74400PE@1124.90>1512.13 | 15:15 | time | +7,629 | +33.9 % |
| 2026-04-01 | 2.52 | B73900CE@525.51>403.22 | 10:23 | trail | -2,513 | -23.9 % |
| 2026-04-02 | -1.19 | B71800PE@1157.71>936.05 | 13:21 | trail | -4,527 | -19.6 % |
| 2026-04-23 | -0.68 | B77900PE@813.40>888.03 | 15:15 | time | +1,404 | +8.6 % |
| 2026-04-30 | -0.62 | B76500PE@701.79>654.21 | 12:14 | trail | -1,030 | -7.3 % |
| 2026-05-11 | -0.91 | B76500PE@589.78>564.21 | 11:20 | trail | -586 | -5.0 % |
| 2026-05-18 | -0.64 | B74400PE@643.20>535.81 | 10:37 | trail | -2,221 | -17.3 % |
| 2026-05-20 | -0.5 | B74700PE@386.47>293.28 | 10:30 | trail | -1,926 | -24.9 % |
| 2026-05-25 | 0.96 | B76300CE@451.04>353.77 | 12:48 | trail | -2,010 | -22.3 % |
| 2026-06-12 | 1.19 | B74700CE@641.24>472.87 | 12:43 | stop | -3,438 | -26.8 % |
| 2026-06-19 | -0.72 | B76600PE@513.55>401.58 | 14:04 | trail | -2,307 | -22.5 % |
| 2026-06-25 | 0.52 | B77400CE@547.22>582.03 | 13:14 | trail | +622 | +5.7 % |
| 2026-07-10 | 0.85 | B77400CE@587.52>520.74 | 15:15 | time | -1,408 | -12.0 % |
| 2026-07-13 | -0.78 | B76900PE@439.39>323.82 | 09:58 | stop | -2,375 | -27.0 % |
| 2026-07-27 | 0.61 | B76700CE@452.25>526.88 | 15:15 | time | +1,421 | +15.7 % |
| 2026-09-02 | -0.61 | B76200PE@225.82>167.66 | 10:19 | stop | -1,219 | -27.0 % |
| 2026-09-11 | -0.79 | B74300PE@482.40>360.44 | 11:14 | trail | -2,505 | -26.0 % |
| 2026-10-05 | 0.6 | B72500CE@514.51>408.15 | 10:22 | trail | -2,195 | -21.3 % |
| 2026-10-21 | 0.66 | B74500CE@362.70>315.22 | 09:51 | trail | -1,012 | -14.0 % |

## Days without prices (primary cell)

- 2025-03-20: no price 76000 CE at 09:30
- 2025-04-08: no price 74300 CE at 09:30
- 2026-07-29: no price 77500 CE at 09:30
