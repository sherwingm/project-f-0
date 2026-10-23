# S3 P3 · NIFTY 1-3 DTE iron condor (T-2 15:00, 0.175 delta, wings 2, 50 % target, 100 % stop): test window 2024-10-01 → 2025-09-30

Pre-registered: `strategies/S3_P3_short_dte_condor.md`. Engine `scanner/s3_engine.py`, runner `scanner/s3_pods.py`. Mean, t and halves on net % of the credit; rupees at 1 lot.

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
- Net per trade: **-13.9 % of the credit** (median +32.3 %), t -1.25; ₹-52 a trade (t -0.41), total ₹-2,552.
- Average credit 20.7 points (₹1,176); fees ₹198 a trade; net -4.01 % of margin a trade.
- Halves: -34.5 % / +4.0 %.
- Worst day ₹-2,155; average month ₹-196; deepest drawdown ₹-5,872.
- At 2x costs: -40.6 % of the credit.
- Monte Carlo deepest drawdown (10,000 reshuffles): 5th pct ₹-10,388, median ₹-7,115, 95th ₹-4,816.

## Grid (net % of the credit per trade · trades · win rate · t)

| Cell | Result |
|---|---|
| T-1 15:00 · delta 0.15 · wings 2 · target 50 % · stop 100 % | -17.5 % · 49 · 71 % · -1.4 |
| T-1 15:00 · delta 0.15 · wings 2 · target 50 % · stop 200 % | -37.1 % · 49 · 71 % · -2.1 |
| T-1 15:00 · delta 0.15 · wings 2 · target 50 % · stop none | -44.8 % · 49 · 76 % · -1.8 |
| T-1 15:00 · delta 0.15 · wings 2 · target none · stop 100 % | -10.3 % · 49 · 65 % · -0.6 |
| T-1 15:00 · delta 0.15 · wings 2 · target none · stop 200 % | -30.7 % · 49 · 69 % · -1.4 |
| T-1 15:00 · delta 0.15 · wings 2 · target none · stop none | -39.2 % · 49 · 78 % · -1.2 |
| T-1 15:00 · delta 0.15 · wings 4 · target 50 % · stop 100 % | -7.1 % · 49 · 78 % · -0.6 |
| T-1 15:00 · delta 0.15 · wings 4 · target 50 % · stop 200 % | -22.4 % · 49 · 78 % · -1.4 |
| T-1 15:00 · delta 0.15 · wings 4 · target 50 % · stop none | -23.9 % · 49 · 86 % · -0.9 |
| T-1 15:00 · delta 0.15 · wings 4 · target none · stop 100 % | +3.5 % · 49 · 67 % · 0.2 |
| T-1 15:00 · delta 0.15 · wings 4 · target none · stop 200 % | -20.2 % · 49 · 69 % · -0.9 |
| T-1 15:00 · delta 0.15 · wings 4 · target none · stop none | -25.9 % · 49 · 80 % · -0.8 |
| T-1 15:00 · delta 0.175 · wings 2 · target 50 % · stop 100 % | -17.8 % · 49 · 71 % · -1.5 |
| T-1 15:00 · delta 0.175 · wings 2 · target 50 % · stop 200 % | -28.5 % · 49 · 76 % · -1.7 |
| T-1 15:00 · delta 0.175 · wings 2 · target 50 % · stop none | -44.2 % · 49 · 80 % · -1.8 |
| T-1 15:00 · delta 0.175 · wings 2 · target none · stop 100 % | -16.3 % · 49 · 59 % · -1.0 |
| T-1 15:00 · delta 0.175 · wings 2 · target none · stop 200 % | -38.2 % · 49 · 63 % · -1.7 |
| T-1 15:00 · delta 0.175 · wings 2 · target none · stop none | -56.5 % · 49 · 67 % · -1.8 |
| T-1 15:00 · delta 0.175 · wings 4 · target 50 % · stop 100 % | -3.0 % · 49 · 80 % · -0.3 |
| T-1 15:00 · delta 0.175 · wings 4 · target 50 % · stop 200 % | -21.1 % · 49 · 80 % · -1.3 |
| T-1 15:00 · delta 0.175 · wings 4 · target 50 % · stop none | -28.0 % · 49 · 84 % · -1.2 |
| T-1 15:00 · delta 0.175 · wings 4 · target none · stop 100 % | -2.0 % · 49 · 61 % · -0.1 |
| T-1 15:00 · delta 0.175 · wings 4 · target none · stop 200 % | -22.2 % · 49 · 65 % · -1.0 |
| T-1 15:00 · delta 0.175 · wings 4 · target none · stop none | -36.9 % · 49 · 69 % · -1.2 |
| T-1 15:00 · delta 0.2 · wings 2 · target 50 % · stop 100 % | -7.4 % · 49 · 78 % · -0.7 |
| T-1 15:00 · delta 0.2 · wings 2 · target 50 % · stop 200 % | -28.9 % · 49 · 78 % · -1.7 |
| T-1 15:00 · delta 0.2 · wings 2 · target 50 % · stop none | -37.9 % · 49 · 82 % · -1.7 |
| T-1 15:00 · delta 0.2 · wings 2 · target none · stop 100 % | -8.6 % · 49 · 59 % · -0.6 |
| T-1 15:00 · delta 0.2 · wings 2 · target none · stop 200 % | -33.8 % · 49 · 61 % · -1.6 |
| T-1 15:00 · delta 0.2 · wings 2 · target none · stop none | -40.3 % · 49 · 65 % · -1.5 |
| T-1 15:00 · delta 0.2 · wings 4 · target 50 % · stop 100 % | +1.2 % · 49 · 80 % · 0.1 |
| T-1 15:00 · delta 0.2 · wings 4 · target 50 % · stop 200 % | -16.5 % · 49 · 80 % · -1.0 |
| T-1 15:00 · delta 0.2 · wings 4 · target 50 % · stop none | -20.4 % · 49 · 84 % · -1.0 |
| T-1 15:00 · delta 0.2 · wings 4 · target none · stop 100 % | +2.5 % · 49 · 59 % · 0.2 |
| T-1 15:00 · delta 0.2 · wings 4 · target none · stop 200 % | -18.3 % · 49 · 63 % · -0.9 |
| T-1 15:00 · delta 0.2 · wings 4 · target none · stop none | -24.9 % · 49 · 67 % · -0.9 |
| T-2 15:00 · delta 0.15 · wings 2 · target 50 % · stop 100 % | -11.5 % · 49 · 76 % · -1.1 |
| T-2 15:00 · delta 0.15 · wings 2 · target 50 % · stop 200 % | -18.2 % · 49 · 82 % · -1.2 |
| T-2 15:00 · delta 0.15 · wings 2 · target 50 % · stop none | -50.3 % · 49 · 84 % · -1.8 |
| T-2 15:00 · delta 0.15 · wings 2 · target none · stop 100 % | -5.4 % · 49 · 63 % · -0.3 |
| T-2 15:00 · delta 0.15 · wings 2 · target none · stop 200 % | -4.9 % · 49 · 76 % · -0.2 |
| T-2 15:00 · delta 0.15 · wings 2 · target none · stop none | -48.6 % · 49 · 80 % · -1.3 |
| T-2 15:00 · delta 0.15 · wings 4 · target 50 % · stop 100 % | -2.7 % · 49 · 78 % · -0.3 |
| T-2 15:00 · delta 0.15 · wings 4 · target 50 % · stop 200 % | -8.6 % · 49 · 84 % · -0.6 |
| T-2 15:00 · delta 0.15 · wings 4 · target 50 % · stop none | -45.7 % · 49 · 86 % · -1.5 |
| T-2 15:00 · delta 0.15 · wings 4 · target none · stop 100 % | +8.0 % · 49 · 65 % · 0.5 |
| T-2 15:00 · delta 0.15 · wings 4 · target none · stop 200 % | +5.1 % · 49 · 76 % · 0.3 |
| T-2 15:00 · delta 0.15 · wings 4 · target none · stop none | -46.8 % · 49 · 80 % · -1.1 |
| T-2 15:00 · delta 0.175 · wings 2 · target 50 % · stop 100 % | -13.9 % · 49 · 73 % · -1.3 |
| T-2 15:00 · delta 0.175 · wings 2 · target 50 % · stop 200 % | -24.3 % · 49 · 80 % · -1.5 |
| T-2 15:00 · delta 0.175 · wings 2 · target 50 % · stop none | -32.7 % · 49 · 84 % · -1.5 |
| T-2 15:00 · delta 0.175 · wings 2 · target none · stop 100 % | -8.9 % · 49 · 59 % · -0.6 |
| T-2 15:00 · delta 0.175 · wings 2 · target none · stop 200 % | -22.5 % · 49 · 67 % · -1.0 |
| T-2 15:00 · delta 0.175 · wings 2 · target none · stop none | -36.0 % · 49 · 73 % · -1.2 |
| T-2 15:00 · delta 0.175 · wings 4 · target 50 % · stop 100 % | +4.4 % · 49 · 80 % · 0.4 |
| T-2 15:00 · delta 0.175 · wings 4 · target 50 % · stop 200 % | -4.1 % · 49 · 84 % · -0.3 |
| T-2 15:00 · delta 0.175 · wings 4 · target 50 % · stop none | -33.6 % · 49 · 86 % · -1.3 |
| T-2 15:00 · delta 0.175 · wings 4 · target none · stop 100 % | +10.2 % · 49 · 63 % · 0.7 |
| T-2 15:00 · delta 0.175 · wings 4 · target none · stop 200 % | -2.2 % · 49 · 69 % · -0.1 |
| T-2 15:00 · delta 0.175 · wings 4 · target none · stop none | -38.2 % · 49 · 73 % · -1.1 |
| T-2 15:00 · delta 0.2 · wings 2 · target 50 % · stop 100 % | -3.8 % · 49 · 78 % · -0.4 |
| T-2 15:00 · delta 0.2 · wings 2 · target 50 % · stop 200 % | -11.5 % · 49 · 84 % · -0.8 |
| T-2 15:00 · delta 0.2 · wings 2 · target 50 % · stop none | -18.7 % · 49 · 86 % · -1.0 |
| T-2 15:00 · delta 0.2 · wings 2 · target none · stop 100 % | -2.6 % · 49 · 61 % · -0.2 |
| T-2 15:00 · delta 0.2 · wings 2 · target none · stop 200 % | -12.6 % · 49 · 67 % · -0.6 |
| T-2 15:00 · delta 0.2 · wings 2 · target none · stop none | -25.7 % · 49 · 69 % · -1.0 |
| T-2 15:00 · delta 0.2 · wings 4 · target 50 % · stop 100 % | +3.8 % · 49 · 78 % · 0.4 |
| T-2 15:00 · delta 0.2 · wings 4 · target 50 % · stop 200 % | -5.0 % · 49 · 84 % · -0.3 |
| T-2 15:00 · delta 0.2 · wings 4 · target 50 % · stop none | -21.5 % · 49 · 86 % · -1.0 |
| T-2 15:00 · delta 0.2 · wings 4 · target none · stop 100 % | +7.3 % · 49 · 61 % · 0.5 |
| T-2 15:00 · delta 0.2 · wings 4 · target none · stop 200 % | +1.8 % · 49 · 71 % · 0.1 |
| T-2 15:00 · delta 0.2 · wings 4 · target none · stop none | -24.2 % · 49 · 73 % · -0.8 |
| T-3 15:00 · delta 0.15 · wings 2 · target 50 % · stop 100 % | -25.1 % · 48 · 69 % · -2.1 |
| T-3 15:00 · delta 0.15 · wings 2 · target 50 % · stop 200 % | -51.4 % · 48 · 73 % · -2.6 |
| T-3 15:00 · delta 0.15 · wings 2 · target 50 % · stop none | -49.2 % · 48 · 83 % · -1.9 |
| T-3 15:00 · delta 0.15 · wings 2 · target none · stop 100 % | -9.1 % · 48 · 60 % · -0.6 |
| T-3 15:00 · delta 0.15 · wings 2 · target none · stop 200 % | -34.9 % · 48 · 67 % · -1.5 |
| T-3 15:00 · delta 0.15 · wings 2 · target none · stop none | -48.0 % · 48 · 73 % · -1.5 |
| T-3 15:00 · delta 0.15 · wings 4 · target 50 % · stop 100 % | -13.6 % · 48 · 69 % · -1.2 |
| T-3 15:00 · delta 0.15 · wings 4 · target 50 % · stop 200 % | -32.6 % · 48 · 75 % · -1.8 |
| T-3 15:00 · delta 0.15 · wings 4 · target 50 % · stop none | -43.2 % · 48 · 83 % · -1.5 |
| T-3 15:00 · delta 0.15 · wings 4 · target none · stop 100 % | +2.7 % · 48 · 60 % · 0.2 |
| T-3 15:00 · delta 0.15 · wings 4 · target none · stop 200 % | -19.2 % · 48 · 67 % · -0.9 |
| T-3 15:00 · delta 0.15 · wings 4 · target none · stop none | -33.7 % · 48 · 73 % · -1.0 |
| T-3 15:00 · delta 0.175 · wings 2 · target 50 % · stop 100 % | -27.9 % · 48 · 65 % · -2.3 |
| T-3 15:00 · delta 0.175 · wings 2 · target 50 % · stop 200 % | -39.0 % · 48 · 75 % · -2.1 |
| T-3 15:00 · delta 0.175 · wings 2 · target 50 % · stop none | -41.8 % · 48 · 81 % · -1.8 |
| T-3 15:00 · delta 0.175 · wings 2 · target none · stop 100 % | -8.5 % · 48 · 58 % · -0.5 |
| T-3 15:00 · delta 0.175 · wings 2 · target none · stop 200 % | -31.8 % · 48 · 65 % · -1.4 |
| T-3 15:00 · delta 0.175 · wings 2 · target none · stop none | -43.2 % · 48 · 69 % · -1.5 |
| T-3 15:00 · delta 0.175 · wings 4 · target 50 % · stop 100 % | -12.3 % · 48 · 69 % · -1.1 |
| T-3 15:00 · delta 0.175 · wings 4 · target 50 % · stop 200 % | -33.6 % · 48 · 75 % · -1.8 |
| T-3 15:00 · delta 0.175 · wings 4 · target 50 % · stop none | -34.5 % · 48 · 81 % · -1.4 |
| T-3 15:00 · delta 0.175 · wings 4 · target none · stop 100 % | +4.1 % · 48 · 60 % · 0.3 |
| T-3 15:00 · delta 0.175 · wings 4 · target none · stop 200 % | -17.5 % · 48 · 67 % · -0.8 |
| T-3 15:00 · delta 0.175 · wings 4 · target none · stop none | -26.9 % · 48 · 69 % · -1.0 |
| T-3 15:00 · delta 0.2 · wings 2 · target 50 % · stop 100 % | -24.2 % · 48 · 65 % · -2.0 |
| T-3 15:00 · delta 0.2 · wings 2 · target 50 % · stop 200 % | -39.7 % · 48 · 73 % · -2.2 |
| T-3 15:00 · delta 0.2 · wings 2 · target 50 % · stop none | -41.1 % · 48 · 77 % · -2.0 |
| T-3 15:00 · delta 0.2 · wings 2 · target none · stop 100 % | -6.0 % · 48 · 58 % · -0.4 |
| T-3 15:00 · delta 0.2 · wings 2 · target none · stop 200 % | -34.6 % · 48 · 62 % · -1.5 |
| T-3 15:00 · delta 0.2 · wings 2 · target none · stop none | -35.7 % · 48 · 67 % · -1.4 |
| T-3 15:00 · delta 0.2 · wings 4 · target 50 % · stop 100 % | -12.8 % · 48 · 67 % · -1.1 |
| T-3 15:00 · delta 0.2 · wings 4 · target 50 % · stop 200 % | -41.0 % · 48 · 71 % · -2.1 |
| T-3 15:00 · delta 0.2 · wings 4 · target 50 % · stop none | -26.2 % · 48 · 81 % · -1.2 |
| T-3 15:00 · delta 0.2 · wings 4 · target none · stop 100 % | +6.8 % · 48 · 60 % · 0.4 |
| T-3 15:00 · delta 0.2 · wings 4 · target none · stop 200 % | -29.4 % · 48 · 62 % · -1.3 |
| T-3 15:00 · delta 0.2 · wings 4 · target none · stop none | -27.0 % · 48 · 67 % · -1.0 |

## Primary cell without the VIX / event filters, by group (side report)

| Group | Trades | Net % | Win rate |
|---|---|---|---|
| VIX <13 | 15 | +13.6 % | 87 % |
| VIX 13-20 | 36 | -23.2 % | 69 % |
| Fri | 5 | +1.7 % | 80 % |
| Mon | 5 | -41.2 % | 60 % |
| Tue | 41 | -10.5 % | 76 % |
| other day | 49 | -13.9 % | 73 % |
| event day | 2 | +26.0 % | 100 % |

## Primary cell with the research's regime filters (side report, not the gate)

| Filter | Trades | Net % of credit | Win rate |
|---|---|---|---|
| none | 49 | -13.9 % | 73 % |
| VIX 14-20 | 28 | -20.5 % | 71 % |
| ADX < 20 | 10 | -2.5 % | 80 % |
| VIX 14-20 and ADX < 20 | 4 | -17.7 % | 75 % |

Average |delta| of the shorts: CE 0.174, PE 0.177; average distance CE +268 pts, PE -252 pts. Exits: {'target': 36, 'stop': 13}.

## Days without prices (primary cell)

- 2024-12-23: no strike near delta 0.175
- 2025-04-07: no price 21050 PE at 15:00
