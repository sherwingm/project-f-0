# S3 X1 · NIFTY expiry-day ATM put, bought the evening before · 2022-01-03 → 2024-09-30

Pre-registered: `strategies/S3_X1_expiry_day_buy.md`. Daily bhavcopy prices, 1 lot, 1 % slippage each way, real charges.

## Verdict: **FAIL**

- ✔ at least 100 trades
- ✘ mean > 0
- ✘ t ≥ 2
- ✘ both halves positive
- ✘ worst trade (₹) smaller than the average month's gain
- ✘ neighbours positive

- Halves: 2022-01-03 → 2023-05-31: -2.1 % (73) / 2023-06-01 → 2024-09-30: -16.1 % (69)
- Average month (primary): ₹-1,249; worst trade ₹-4,328
- Expiry days: 143; skipped rows: 7 (2023-06-28 overnight · PE · 0 out · target 200 % · stop 50 %: no 18800 PE row; 2023-06-28 overnight · PE · 0 out · target 100 % · stop 50 %: no 18800 PE row; 2023-06-28 overnight · PE · 0 out · target 300 % · stop 50 %: no 18800 PE row; 2023-06-28 overnight · PE · 1 out · target 200 % · stop 50 %: no 18750 PE row; 2023-06-28 overnight · CE · 0 out · target 200 % · stop 50 %: no 18800 CE row; 2023-06-28 overnight · PE · 0 out · target none · stop 50 %: no 18800 PE row; 2023-06-28 overnight · PE · 0 out · target 200 %: no 18800 PE row)

| Cell | Trades | Paid (median ₹) | Mean net | Median | t | Won | Target hit | Max up mean | Max up median | ≥ +100 % | Total ₹ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| primary (gate): overnight · PE · 0 out · target 200 % · stop 50 % | 142 | 61.7 | -8.9 % | -52.4 % | -1.06 | 18 % | 17 % | +102 % | +59 % | 39 % | -41,224 |
| neighbour (gate): overnight · PE · 0 out · target 100 % · stop 50 % | 142 | 61.7 | -19.8 % | -52.4 % | -3.11 | 20 % | 20 % | +102 % | +59 % | 39 % | -85,121 |
| neighbour (gate): overnight · PE · 0 out · target 300 % · stop 50 % | 142 | 61.7 | -3.2 % | -52.4 % | -0.32 | 18 % | 11 % | +102 % | +59 % | 39 % | -18,973 |
| neighbour (gate): overnight · PE · 1 out · target 200 % · stop 50 % | 142 | 42.0 | -17.3 % | -53.7 % | -2.02 | 15 % | 15 % | +118 % | +55 % | 37 % | -54,121 |
| side: overnight · CE · 0 out · target 200 % · stop 50 % | 142 | 67.9 | -16.1 % | -52.1 % | -2.31 | 18 % | 10 % | +94 % | +58 % | 35 % | -77,000 |
| side: open · PE · 0 out · target 200 % · stop 50 % | 143 | 57.6 | -7.9 % | -52.1 % | -1.05 | 21 % | 14 % | +134 % | +81 % | 41 % | -62,808 |
| side: overnight · PE · 0 out · target none · stop 50 % | 142 | 61.7 | -0.7 % | -52.4 % | -0.06 | 18 % | 0 % | +102 % | +59 % | 39 % | -9,034 |
| side: overnight · PE · 0 out · target 200 % | 142 | 61.7 | -13.0 % | -97.0 % | -1.23 | 30 % | 22 % | +102 % | +59 % | 39 % | -51,057 |

Daily prices cannot show whether the low or the high came first. 6 of 142 primary days touched both the stop and the target; the gate counts them as stopped (worst case). Target first instead (best case, not the gate):

| Cell | Trades | Paid (median ₹) | Mean net | Median | t | Won | Target hit | Max up mean | Max up median | ≥ +100 % | Total ₹ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| primary, target first | 142 | 61.7 | +1.7 % | -52.4 % | 0.18 | 23 % | 21 % | +102 % | +59 % | 39 % | 4,653 |

Primary exits: stop 87, gap stop 26, target 22, close 5, gap target 2

| Year | Trades | Mean net | Max up median | ≥ +100 % | Total ₹ |
|---|---|---|---|---|---|
| 2022 | 52 | +3.1 % | +50 % | 33 % | -3,837 |
| 2023 | 51 | -10.8 % | +88 % | 47 % | -11,299 |
| 2024 | 39 | -22.4 % | +31 % | 36 % | -26,087 |
