# S3 P3 · NIFTY 1-3 DTE iron condor (T-2 15:00, 0.175 delta, wings 2, 50 % target, 100 % stop): test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_P3_short_dte_condor.md` (page commit 6baa57f7 2026-10-23T11:16:37+05:30). Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the credit; rupees at 1 lot.

Days 53. Primary cell: 49 trades. Not traded: 2 without prices, 2 event days.

## Verdict: **FAIL**

- ✘ net mean > 0
- ✘ net mean > 0 at 2x costs
- ✘ t >= 2
- ✘ positive in each half
- ✘ worst day smaller than the average month
- ✘ neighbours net positive
- ✔ at least 30 trades

## Primary cell (T-2 15:00 · delta 0.175 · wings 2 · target 50 % · stop 100 %)

- Trades 49, **win rate 73 %**, stop hit 27 %.
- Net per trade: **-12.2 % of the credit** (median +34.6 %), t -1.09; ₹-52 a trade (t -0.38), total ₹-2,539.
- Average credit 20.7 points (₹1,274); fees ₹199 a trade; net -3.47 % of margin a trade.
- Halves: -30.8 % / +4.0 %.
- Worst day ₹-2,610; average month ₹-195; deepest drawdown ₹-6,635.
- At 2x costs: -36.9 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-11,167, median ₹-7,684, 95th ₹-5,112.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| T-1 15:00 · delta 0.15 · wings 2 · target 50 % · stop 100 % | -14.4 % · 49 · 78 % · -1.2 |
| T-1 15:00 · delta 0.15 · wings 2 · target 50 % · stop 200 % | -34.0 % · 49 · 78 % · -1.9 |
| T-1 15:00 · delta 0.15 · wings 2 · target 50 % · stop none | -41.7 % · 49 · 82 % · -1.6 |
| T-1 15:00 · delta 0.15 · wings 2 · target none · stop 100 % | -7.2 % · 49 · 65 % · -0.4 |
| T-1 15:00 · delta 0.15 · wings 2 · target none · stop 200 % | -27.7 % · 49 · 69 % · -1.2 |
| T-1 15:00 · delta 0.15 · wings 2 · target none · stop none | -36.1 % · 49 · 78 % · -1.1 |
| T-1 15:00 · delta 0.15 · wings 4 · target 50 % · stop 100 % | -5.1 % · 49 · 80 % · -0.4 |
| T-1 15:00 · delta 0.15 · wings 4 · target 50 % · stop 200 % | -20.4 % · 49 · 80 % · -1.3 |
| T-1 15:00 · delta 0.15 · wings 4 · target 50 % · stop none | -21.8 % · 49 · 88 % · -0.8 |
| T-1 15:00 · delta 0.15 · wings 4 · target none · stop 100 % | +5.5 % · 49 · 67 % · 0.3 |
| T-1 15:00 · delta 0.15 · wings 4 · target none · stop 200 % | -18.1 % · 49 · 69 % · -0.8 |
| T-1 15:00 · delta 0.15 · wings 4 · target none · stop none | -23.8 % · 49 · 80 % · -0.7 |
| T-1 15:00 · delta 0.175 · wings 2 · target 50 % · stop 100 % | -15.3 % · 49 · 76 % · -1.3 |
| T-1 15:00 · delta 0.175 · wings 2 · target 50 % · stop 200 % | -25.9 % · 49 · 80 % · -1.6 |
| T-1 15:00 · delta 0.175 · wings 2 · target 50 % · stop none | -41.6 % · 49 · 84 % · -1.7 |
| T-1 15:00 · delta 0.175 · wings 2 · target none · stop 100 % | -13.7 % · 49 · 59 % · -0.8 |
| T-1 15:00 · delta 0.175 · wings 2 · target none · stop 200 % | -35.7 % · 49 · 63 % · -1.6 |
| T-1 15:00 · delta 0.175 · wings 2 · target none · stop none | -54.0 % · 49 · 67 % · -1.8 |
| T-1 15:00 · delta 0.175 · wings 4 · target 50 % · stop 100 % | -1.3 % · 49 · 80 % · -0.1 |
| T-1 15:00 · delta 0.175 · wings 4 · target 50 % · stop 200 % | -19.4 % · 49 · 80 % · -1.2 |
| T-1 15:00 · delta 0.175 · wings 4 · target 50 % · stop none | -26.3 % · 49 · 84 % · -1.1 |
| T-1 15:00 · delta 0.175 · wings 4 · target none · stop 100 % | -0.3 % · 49 · 61 % · -0.0 |
| T-1 15:00 · delta 0.175 · wings 4 · target none · stop 200 % | -20.5 % · 49 · 65 % · -0.9 |
| T-1 15:00 · delta 0.175 · wings 4 · target none · stop none | -35.2 % · 49 · 69 % · -1.2 |
| T-1 15:00 · delta 0.2 · wings 2 · target 50 % · stop 100 % | -5.3 % · 49 · 78 % · -0.5 |
| T-1 15:00 · delta 0.2 · wings 2 · target 50 % · stop 200 % | -26.8 % · 49 · 78 % · -1.6 |
| T-1 15:00 · delta 0.2 · wings 2 · target 50 % · stop none | -35.8 % · 49 · 82 % · -1.6 |
| T-1 15:00 · delta 0.2 · wings 2 · target none · stop 100 % | -6.5 % · 49 · 59 % · -0.4 |
| T-1 15:00 · delta 0.2 · wings 2 · target none · stop 200 % | -31.7 % · 49 · 61 % · -1.5 |
| T-1 15:00 · delta 0.2 · wings 2 · target none · stop none | -38.2 % · 49 · 65 % · -1.4 |
| T-1 15:00 · delta 0.2 · wings 4 · target 50 % · stop 100 % | +2.6 % · 49 · 80 % · 0.2 |
| T-1 15:00 · delta 0.2 · wings 4 · target 50 % · stop 200 % | -15.1 % · 49 · 80 % · -1.0 |
| T-1 15:00 · delta 0.2 · wings 4 · target 50 % · stop none | -19.0 % · 49 · 84 % · -0.9 |
| T-1 15:00 · delta 0.2 · wings 4 · target none · stop 100 % | +3.9 % · 49 · 59 % · 0.3 |
| T-1 15:00 · delta 0.2 · wings 4 · target none · stop 200 % | -16.9 % · 49 · 63 % · -0.8 |
| T-1 15:00 · delta 0.2 · wings 4 · target none · stop none | -23.5 % · 49 · 67 % · -0.9 |
| T-2 15:00 · delta 0.15 · wings 2 · target 50 % · stop 100 % | -9.3 % · 49 · 78 % · -0.9 |
| T-2 15:00 · delta 0.15 · wings 2 · target 50 % · stop 200 % | -16.0 % · 49 · 84 % · -1.1 |
| T-2 15:00 · delta 0.15 · wings 2 · target 50 % · stop none | -48.1 % · 49 · 86 % · -1.7 |
| T-2 15:00 · delta 0.15 · wings 2 · target none · stop 100 % | -3.2 % · 49 · 63 % · -0.2 |
| T-2 15:00 · delta 0.15 · wings 2 · target none · stop 200 % | -2.6 % · 49 · 76 % · -0.1 |
| T-2 15:00 · delta 0.15 · wings 2 · target none · stop none | -46.4 % · 49 · 80 % · -1.3 |
| T-2 15:00 · delta 0.15 · wings 4 · target 50 % · stop 100 % | -1.3 % · 49 · 78 % · -0.1 |
| T-2 15:00 · delta 0.15 · wings 4 · target 50 % · stop 200 % | -7.2 % · 49 · 84 % · -0.5 |
| T-2 15:00 · delta 0.15 · wings 4 · target 50 % · stop none | -44.3 % · 49 · 86 % · -1.5 |
| T-2 15:00 · delta 0.15 · wings 4 · target none · stop 100 % | +9.4 % · 49 · 65 % · 0.6 |
| T-2 15:00 · delta 0.15 · wings 4 · target none · stop 200 % | +6.5 % · 49 · 76 % · 0.3 |
| T-2 15:00 · delta 0.15 · wings 4 · target none · stop none | -45.4 % · 49 · 80 % · -1.1 |
| T-2 15:00 · delta 0.175 · wings 2 · target 50 % · stop 100 % | -12.2 % · 49 · 73 % · -1.1 |
| T-2 15:00 · delta 0.175 · wings 2 · target 50 % · stop 200 % | -22.5 % · 49 · 80 % · -1.4 |
| T-2 15:00 · delta 0.175 · wings 2 · target 50 % · stop none | -31.0 % · 49 · 84 % · -1.4 |
| T-2 15:00 · delta 0.175 · wings 2 · target none · stop 100 % | -7.2 % · 49 · 59 % · -0.5 |
| T-2 15:00 · delta 0.175 · wings 2 · target none · stop 200 % | -20.7 % · 49 · 67 % · -1.0 |
| T-2 15:00 · delta 0.175 · wings 2 · target none · stop none | -34.2 % · 49 · 73 % · -1.1 |
| T-2 15:00 · delta 0.175 · wings 4 · target 50 % · stop 100 % | +5.5 % · 49 · 80 % · 0.5 |
| T-2 15:00 · delta 0.175 · wings 4 · target 50 % · stop 200 % | -3.0 % · 49 · 84 % · -0.2 |
| T-2 15:00 · delta 0.175 · wings 4 · target 50 % · stop none | -32.5 % · 49 · 86 % · -1.2 |
| T-2 15:00 · delta 0.175 · wings 4 · target none · stop 100 % | +11.3 % · 49 · 63 % · 0.8 |
| T-2 15:00 · delta 0.175 · wings 4 · target none · stop 200 % | -1.1 % · 49 · 69 % · -0.1 |
| T-2 15:00 · delta 0.175 · wings 4 · target none · stop none | -37.1 % · 49 · 73 % · -1.1 |
| T-2 15:00 · delta 0.2 · wings 2 · target 50 % · stop 100 % | -2.1 % · 49 · 78 % · -0.2 |
| T-2 15:00 · delta 0.2 · wings 2 · target 50 % · stop 200 % | -9.8 % · 49 · 84 % · -0.7 |
| T-2 15:00 · delta 0.2 · wings 2 · target 50 % · stop none | -17.0 % · 49 · 86 % · -0.9 |
| T-2 15:00 · delta 0.2 · wings 2 · target none · stop 100 % | -0.9 % · 49 · 61 % · -0.1 |
| T-2 15:00 · delta 0.2 · wings 2 · target none · stop 200 % | -10.9 % · 49 · 67 % · -0.5 |
| T-2 15:00 · delta 0.2 · wings 2 · target none · stop none | -24.0 % · 49 · 69 % · -0.9 |
| T-2 15:00 · delta 0.2 · wings 4 · target 50 % · stop 100 % | +4.9 % · 49 · 78 % · 0.5 |
| T-2 15:00 · delta 0.2 · wings 4 · target 50 % · stop 200 % | -3.9 % · 49 · 84 % · -0.3 |
| T-2 15:00 · delta 0.2 · wings 4 · target 50 % · stop none | -20.5 % · 49 · 86 % · -0.9 |
| T-2 15:00 · delta 0.2 · wings 4 · target none · stop 100 % | +8.4 % · 49 · 61 % · 0.5 |
| T-2 15:00 · delta 0.2 · wings 4 · target none · stop 200 % | +2.9 % · 49 · 71 % · 0.1 |
| T-2 15:00 · delta 0.2 · wings 4 · target none · stop none | -23.2 % · 49 · 73 % · -0.8 |
| T-3 15:00 · delta 0.15 · wings 2 · target 50 % · stop 100 % | -21.8 % · 49 · 69 % · -1.9 |
| T-3 15:00 · delta 0.15 · wings 2 · target 50 % · stop 200 % | -47.6 % · 49 · 73 % · -2.5 |
| T-3 15:00 · delta 0.15 · wings 2 · target 50 % · stop none | -45.4 % · 49 · 84 % · -1.8 |
| T-3 15:00 · delta 0.15 · wings 2 · target none · stop 100 % | -9.6 % · 49 · 59 % · -0.6 |
| T-3 15:00 · delta 0.15 · wings 2 · target none · stop 200 % | -36.8 % · 49 · 65 % · -1.6 |
| T-3 15:00 · delta 0.15 · wings 2 · target none · stop none | -49.9 % · 49 · 71 % · -1.6 |
| T-3 15:00 · delta 0.15 · wings 4 · target 50 % · stop 100 % | -11.2 % · 49 · 69 % · -1.0 |
| T-3 15:00 · delta 0.15 · wings 4 · target 50 % · stop 200 % | -29.8 % · 49 · 76 % · -1.7 |
| T-3 15:00 · delta 0.15 · wings 4 · target 50 % · stop none | -40.2 % · 49 · 84 % · -1.4 |
| T-3 15:00 · delta 0.15 · wings 4 · target none · stop 100 % | +1.5 % · 49 · 59 % · 0.1 |
| T-3 15:00 · delta 0.15 · wings 4 · target none · stop 200 % | -19.9 % · 49 · 65 % · -0.9 |
| T-3 15:00 · delta 0.15 · wings 4 · target none · stop none | -34.1 % · 49 · 71 % · -1.0 |
| T-3 15:00 · delta 0.175 · wings 2 · target 50 % · stop 100 % | -24.9 % · 49 · 65 % · -2.1 |
| T-3 15:00 · delta 0.175 · wings 2 · target 50 % · stop 200 % | -35.7 % · 49 · 76 % · -2.0 |
| T-3 15:00 · delta 0.175 · wings 2 · target 50 % · stop none | -38.5 % · 49 · 82 % · -1.7 |
| T-3 15:00 · delta 0.175 · wings 2 · target none · stop 100 % | -9.2 % · 49 · 57 % · -0.6 |
| T-3 15:00 · delta 0.175 · wings 2 · target none · stop 200 % | -34.0 % · 49 · 63 % · -1.5 |
| T-3 15:00 · delta 0.175 · wings 2 · target none · stop none | -49.4 % · 49 · 67 % · -1.7 |
| T-3 15:00 · delta 0.175 · wings 4 · target 50 % · stop 100 % | -10.1 % · 49 · 69 % · -0.9 |
| T-3 15:00 · delta 0.175 · wings 4 · target 50 % · stop 200 % | -31.0 % · 49 · 76 % · -1.7 |
| T-3 15:00 · delta 0.175 · wings 4 · target 50 % · stop none | -31.9 % · 49 · 82 % · -1.4 |
| T-3 15:00 · delta 0.175 · wings 4 · target none · stop 100 % | +2.7 % · 49 · 59 % · 0.2 |
| T-3 15:00 · delta 0.175 · wings 4 · target none · stop 200 % | -21.0 % · 49 · 65 % · -0.9 |
| T-3 15:00 · delta 0.175 · wings 4 · target none · stop none | -30.3 % · 49 · 67 % · -1.1 |
| T-3 15:00 · delta 0.2 · wings 2 · target 50 % · stop 100 % | -21.1 % · 49 · 65 % · -1.8 |
| T-3 15:00 · delta 0.2 · wings 2 · target 50 % · stop 200 % | -36.3 % · 49 · 73 % · -2.0 |
| T-3 15:00 · delta 0.2 · wings 2 · target 50 % · stop none | -37.7 % · 49 · 78 % · -1.8 |
| T-3 15:00 · delta 0.2 · wings 2 · target none · stop 100 % | -6.9 % · 49 · 57 % · -0.4 |
| T-3 15:00 · delta 0.2 · wings 2 · target none · stop 200 % | -36.8 % · 49 · 61 % · -1.6 |
| T-3 15:00 · delta 0.2 · wings 2 · target none · stop none | -39.7 % · 49 · 65 % · -1.6 |
| T-3 15:00 · delta 0.2 · wings 4 · target 50 % · stop 100 % | -10.8 % · 49 · 67 % · -1.0 |
| T-3 15:00 · delta 0.2 · wings 4 · target 50 % · stop 200 % | -38.4 % · 49 · 71 % · -2.0 |
| T-3 15:00 · delta 0.2 · wings 4 · target 50 % · stop none | -23.9 % · 49 · 82 % · -1.1 |
| T-3 15:00 · delta 0.2 · wings 4 · target none · stop 100 % | +5.2 % · 49 · 59 % · 0.3 |
| T-3 15:00 · delta 0.2 · wings 4 · target none · stop 200 % | -32.3 % · 49 · 61 % · -1.4 |
| T-3 15:00 · delta 0.2 · wings 4 · target none · stop none | -31.4 % · 49 · 65 % · -1.2 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 15 | +13.6 % | 87 % |
| VIX 13-20 | 36 | -20.8 % | 69 % |
| Fri | 5 | +1.7 % | 80 % |
| Mon | 5 | -41.2 % | 60 % |
| Tue | 41 | -8.4 % | 76 % |
| other day | 49 | -12.2 % | 73 % |
| event day | 2 | +26.0 % | 100 % |

## Primary cell with the research's regime filters (side report, not the gate)

| Filter | Trades | Net % of credit | Win rate |
|---|---|---|---|
| none | 49 | -12.2 % | 73 % |
| VIX 14-20 | 28 | -17.4 % | 71 % |
| ADX < 20 | 9 | -6.6 % | 78 % |
| VIX 14-20 and ADX < 20 | 4 | -17.7 % | 75 % |

Average |delta| of the shorts: CE 0.174, PE 0.177; average distance CE +268 pts, PE -252 pts. Exits: {'target': 36, 'stop': 13}.

## Days without prices (primary cell)

- 2024-12-23: no strike near delta 0.175
- 2025-04-07: no price 21050 PE at 15:00
