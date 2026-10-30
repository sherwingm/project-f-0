# S1 fade · 09:15 vs 09:16 entry counterfactual: tables (scanner/fade_entry_0916_cf.py)

Ledger saved_at 2026-10-29T15:29:58+05:30. Method: strategies/S1_fade_0916_entry_counterfactual.md. 09:16 prices are OBSERVED asks; 09:16 exits are SIMULATED at observed bids (not fills).

## Per trade

| day | symbol | type | strike | qty | status | e15_time | e15_price | x15_reason | x15_time | x15_price | net15 | e16_time | e16_price | e16_src | size_ok | walk_same | x16_reason | x16_time | x16_price | x16_by | net16 | diff_net | replay15_reason | replay15_net | dip15_1min_pct | dip16_1min_pct | comparable | comparable_1s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-23 | ADANIENSOL | PE | 1260.0 | 675 | unavailable: no eligible quote 09:16-09:20 | 09:15:00 | 10.55 | trail | 09:16:08 | 12.15 | 1013.84 |  |  |  |  |  |  |  |  |  |  |  | trail | 1013.84 | -56.9 |  | False | False |
| 2026-10-27 | RECLTD | CE | 310.0 | 1575 | available | 09:15:01 | 4.9 | stop | 09:16:01 | 2.85 | -3288.03 | 09:16:00 | 3.0 | probe | True | no (305) | stop | 09:17:29 | 2.15 | rows | -1394.57 | 1893.46 | stop | -3288.03 | -41.8 | -11.7 | True | True |
| 2026-10-27 | TATACONSUM | PE | 880.0 | 550 | available | 09:15:01 | 12.1 | stop | 09:16:01 | 5.25 | -3823.25 | 09:16:12 | 6.1 | obs-after_exit | True | no (910) | stop | 09:22:12 | 4.7 | rows | -823.68 | 2999.57 | stop | -3823.25 | -56.6 | -19.7 | False | False |
| 2026-10-27 | APLAPOLLO | PE | 1900.0 | 350 | available | 09:15:03 | 16.7 | stop | 09:16:01 | 11.05 | -2034.76 | 09:18:11 | 13.7 | obs-after_exit | True | unknown | stop | 09:19:55 | 10.8 | rows | -1071.6 | 963.16 | stop | -2034.76 | -33.8 | -15.0 | False | False |
| 2026-10-27 | SONACOMS | PE | 700.0 | 1225 | available | 09:15:03 | 6.5 | stop | 09:16:01 | 2.95 | -4406.47 | 09:16:27 | 3.3 | obs-after_exit | True | unknown | stop | 09:19:05 | 2.6 | rows | -912.63 | 3493.84 | stop | -4406.47 | -54.6 | -19.7 | False | False |
| 2026-10-27 | PAYTM | PE | 1400.0 | 725 | available | 09:15:03 | 8.8 | stop | 09:16:01 | 5.65 | -2341.69 | 09:17:09 | 7.2 | obs-after_exit | True | unknown | trail | 09:22:02 | 8.05 | rows | 555.5 | 2897.19 | stop | -2341.69 | -35.8 | -4.9 | False | False |
| 2026-10-27 | MANKIND | PE | 2200.0 | 250 | unchanged | 09:16:37 | 23.1 | stop | 09:17:43 | 18.15 | -1296.01 | 09:16:37 | 23.1 | actual | True | n/a | stop | 09:17:43 | 18.15 | actual | -1296.01 |  | stop | -1296.01 |  |  | True | True |
| 2026-10-28 | WAAREEENER | CE | 2400.0 | 175 | available | 09:15:03 | 31.85 | stop | 09:16:05 | 25.35 | -1195.73 | 09:16:00 | 26.75 | obs-held | True | no (2320) | stop | 09:33:45 | 21.4 | rows | -992.74 | 202.99 | stop | -1221.94 | -32.5 | -10.3 | False | True |
| 2026-10-28 | LT | PE | 3600.0 | 175 | available | 09:15:06 | 30.75 | stop | 09:16:01 | 18.45 | -2208.33 | 09:16:00 | 19.1 | obs-held | True | no (3700) | stop | 09:17:09 | 15.2 | rows | -736.31 | 1472.02 | stop | -2208.33 | -43.7 | -19.1 | False | True |
| 2026-10-28 | BAJAJ-AUTO | PE | 10000.0 | 75 | available | 09:15:22 | 79.85 | trail | 09:16:36 | 86.85 | 462.59 | 09:16:00 | 83.0 | obs-held | True | yes | trail | 09:17:00 | 89.85 | rows | 450.8 | -11.79 | trail | 369.02 | -10.4 | -9.2 | False | True |
| 2026-10-28 | MAZDOCK | CE | 1820.0 | 225 | available | 09:15:36 | 31.85 | trail | 09:16:14 | 34.9 | 620.74 | 09:16:00 | 31.85 | probe | True | yes | trail | 09:16:13 | 33.85 | rows | 384.94 | -235.8 | trail | 384.94 | -3.3 | -4.4 | True | True |
| 2026-10-28 | MARUTI | CE | 12000.0 | 50 | unchanged | 09:16:03 | 148.5 | stop | 09:21:43 | 115.55 | -1709.15 | 09:16:03 | 148.5 | actual | True | n/a | stop | 09:21:43 | 115.55 | actual | -1709.15 |  | stop | -1656.75 | -15.1 | -15.1 | True | True |
| 2026-10-29 | JSWENERGY | PE | 460.0 | 1075 | available | 09:15:03 | 6.6 | stop | 09:16:01 | 4.35 | -2478.12 | 09:16:00 | 4.55 | obs-held | True | no (470) | stop | 09:17:53 | 3.55 | rows | -1131.72 | 1346.4 | stop | -2478.12 | -36.4 | -4.4 | False | True |
| 2026-10-29 | ADANIPORTS | PE | 1700.0 | 475 | available | 09:15:05 | 16.9 | stop | 09:16:27 | 13.6 | -1630.72 | 09:16:00 | 15.75 | obs-held | True | yes | stop | 09:17:13 | 12.55 | rows | -1582.02 | 48.7 | stop | -1678.13 | -15.7 | -17.1 | False | True |
| 2026-10-29 | NAUKRI | PE | 1100.0 | 550 | available | 09:15:05 | 9.05 | trail | 09:20:22 | 9.9 | 407.6 | 09:16:00 | 7.85 | obs-held | True | yes | trail | 09:16:40 | 8.6 | rows | 354.29 | -53.31 | trail | 407.6 | -44.8 | -4.5 | False | True |
| 2026-10-29 | HEROMOTOCO | PE | 5000.0 | 150 | available | 09:15:06 | 51.0 | stop | 09:16:25 | 40.15 | -1689.72 | 09:16:00 | 46.35 | obs-held | True | yes | stop | 09:17:29 | 36.7 | rows | -1508.42 | 181.3 | stop | -1719.66 | -17.8 | -13.8 | False | True |
| 2026-10-29 | BANDHANBNK | PE | 140.0 | 3600 | unavailable: no eligible quote 09:16-09:20 | 09:15:18 | 2.17 | stop | 09:16:01 | 1.62 | -2041.92 |  |  |  |  |  |  |  |  |  |  |  | stop | -2041.92 | -27.2 |  | False | False |
| 2026-10-29 | TVSMOTOR | PE | 3900.0 | 175 | unchanged | 09:16:05 | 37.65 | trail | 09:16:50 | 43.5 | 958.96 | 09:16:05 | 37.65 | actual | True | n/a | trail | 09:16:50 | 43.5 | actual | 958.96 |  | trail | 426.23 | -10.6 | -10.6 | True | True |
| 2026-10-29 | CUB | PE | 205.0 | 2325 | unchanged | 09:17:51 | 2.24 | stop | 09:21:08 | 1.5 | -1776.74 | 09:17:51 | 2.24 | actual | True | n/a | stop | 09:21:08 | 1.5 | actual | -1776.74 |  | stop | -1776.74 | -17.4 | -17.4 | True | True |

## Skipped rows before the 09:16 entry (first 3)

| symbol | e16_skipped |
|---|---|
| ADANIENSOL | 09:16:00 spread above 10 % of the ask; 09:16:01 lot outside Rs 600-8,000; 09:16:02 lot outside Rs 600-8,000 (+210) |
| TATACONSUM | 09:16:02 spread above 10 % of the ask |
| APLAPOLLO | 09:16:02 stale (no trade today); 09:16:17 stale (no trade today); 09:17:12 stale (no trade today) |
| SONACOMS | 09:16:02 spread above 10 % of the ask |
| PAYTM | 09:16:02 spread above 10 % of the ask; 09:16:17 spread above 10 % of the ask |
| BANDHANBNK | 09:16:00 ask below Rs 2; 09:16:00 ask below Rs 2; 09:16:01 ask below Rs 2 (+134) |

## Groups


### All measured days, 27-29 Oct

Signals 18; available pairs 17 (changed 13, unchanged 4); unavailable 1.

| method | n | wins | win % | total net Rs | mean net % | median net % | avg win Rs | avg loss Rs | stop / trail / 15:20 | max drawdown Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 actual (booked) | 17 | 4 | 23.5 | -27429 | -23.95 | -23.02 | 612 | -2298 | 13 / 4 / 0 | -27429 |
| 09:15 replayed (same engine) | 17 | 4 | 23.5 | -28342 | -24.76 | -22.48 | 397 | -2302 | 13 / 4 / 0 | -28342 |
| 09:16 simulated | 17 | 5 | 29.4 | -12231 | -14.22 | -22.03 | 541 | -1245 | 12 / 5 / 0 | -12231 |

| 09:16 minus 09:15 actual, total Rs | mean pts (net %) | paired t (scale only) | 09:16 better / worse / same | 09:16 minus 09:15 replayed, total Rs | mean entry diff % (changed) | median 1-min dip 09:15 / 09:16 (changed) | median exit shift min (changed) |
|---|---|---|---|---|---|---|---|
| 15198 | 9.73 | 2.66 | 10 / 3 / 4 | 16111 | -21.9 | -35.8 / -11.7 | 1.5 |

### All signals incl. ADANIENSOL (23 Oct)

Signals 19; available pairs 17 (changed 13, unchanged 4); unavailable 2.

| method | n | wins | win % | total net Rs | mean net % | median net % | avg win Rs | avg loss Rs | stop / trail / 15:20 | max drawdown Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 actual (booked) | 17 | 4 | 23.5 | -27429 | -23.95 | -23.02 | 612 | -2298 | 13 / 4 / 0 | -27429 |
| 09:15 replayed (same engine) | 17 | 4 | 23.5 | -28342 | -24.76 | -22.48 | 397 | -2302 | 13 / 4 / 0 | -28342 |
| 09:16 simulated | 17 | 5 | 29.4 | -12231 | -14.22 | -22.03 | 541 | -1245 | 12 / 5 / 0 | -12231 |

| 09:16 minus 09:15 actual, total Rs | mean pts (net %) | paired t (scale only) | 09:16 better / worse / same | 09:16 minus 09:15 replayed, total Rs | mean entry diff % (changed) | median 1-min dip 09:15 / 09:16 (changed) | median exit shift min (changed) |
|---|---|---|---|---|---|---|---|
| 15198 | 9.73 | 2.66 | 10 / 3 / 4 | 16111 | -21.9 | -35.8 / -11.7 | 1.5 |

### 28-29 Oct only (fresh books)

Signals 12; available pairs 11 (changed 8, unchanged 3); unavailable 1.

| method | n | wins | win % | total net Rs | mean net % | median net % | avg win Rs | avg loss Rs | stop / trail / 15:20 | max drawdown Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 actual (booked) | 11 | 4 | 36.4 | -10239 | -14.35 | -21.45 | 612 | -1813 | 7 / 4 / 0 | -10239 |
| 09:15 replayed (same engine) | 11 | 4 | 36.4 | -11152 | -15.59 | -21.92 | 397 | -1820 | 7 / 4 / 0 | -11152 |
| 09:16 simulated | 11 | 4 | 36.4 | -7288 | -11.91 | -21.21 | 537 | -1348 | 7 / 4 / 0 | -7288 |

| 09:16 minus 09:15 actual, total Rs | mean pts (net %) | paired t (scale only) | 09:16 better / worse / same | 09:16 minus 09:15 replayed, total Rs | mean entry diff % (changed) | median 1-min dip 09:15 / 09:16 (changed) | median exit shift min (changed) |
|---|---|---|---|---|---|---|---|
| 2951 | 2.44 | 1.21 | 5 / 3 / 3 | 3864 | -13.8 | -25.15 / -9.75 | 0.9500000000000001 |

### 27 Oct only (previous-day books)

Signals 6; available pairs 6 (changed 5, unchanged 1); unavailable 0.

| method | n | wins | win % | total net Rs | mean net % | median net % | avg win Rs | avg loss Rs | stop / trail / 15:20 | max drawdown Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 actual (booked) | 6 | 0 | 0.0 | -17190 | -41.56 | -39.65 |  | -2865 | 6 / 0 / 0 | -17190 |
| 09:15 replayed (same engine) | 6 | 0 | 0.0 | -17190 | -41.56 | -39.65 |  | -2865 | 6 / 0 / 0 | -17190 |
| 09:16 simulated | 6 | 1 | 16.7 | -4943 | -18.46 | -22.51 | 556.0 | -1100 | 5 / 1 / 0 | -4943 |

| 09:16 minus 09:15 actual, total Rs | mean pts (net %) | paired t (scale only) | 09:16 better / worse / same | 09:16 minus 09:15 replayed, total Rs | mean entry diff % (changed) | median 1-min dip 09:15 / 09:16 (changed) | median exit shift min (changed) |
|---|---|---|---|---|---|---|---|
| 12247 | 23.09 | 3.24 | 5 / 0 / 1 | 12247 | -34.8 | -41.8 / -15.0 | 3.9 |

### 23 Oct ADANIENSOL only

Signals 1; available pairs 0 (changed 0, unchanged 0); unavailable 1.

| method | n |
|---|---|
| 09:15 actual (booked) | 0 |
| 09:15 replayed (same engine) | 0 |
| 09:16 simulated | 0 |

## Robustness


### 27-29 Oct without the largest difference (SONACOMS)

Signals 17; available pairs 16 (changed 12, unchanged 4); unavailable 1.

| method | n | wins | win % | total net Rs | mean net % | median net % | avg win Rs | avg loss Rs | stop / trail / 15:20 | max drawdown Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 actual (booked) | 16 | 4 | 25.0 | -23022 | -21.99 | -22.73 | 612 | -2123 | 12 / 4 / 0 | -23022 |
| 09:15 replayed (same engine) | 16 | 4 | 25.0 | -23936 | -22.85 | -22.46 | 397 | -2127 | 12 / 4 / 0 | -23936 |
| 09:16 simulated | 16 | 5 | 31.2 | -11318 | -13.7 | -21.86 | 541 | -1275 | 11 / 5 / 0 | -11318 |

| 09:16 minus 09:15 actual, total Rs | mean pts (net %) | paired t (scale only) | 09:16 better / worse / same | 09:16 minus 09:15 replayed, total Rs | mean entry diff % (changed) | median 1-min dip 09:15 / 09:16 (changed) | median exit shift min (changed) |
|---|---|---|---|---|---|---|---|
| 11704 | 8.29 | 2.32 | 9 / 3 / 4 | 12617 | -19.6 | -34.8 / -11.0 | 1.3 |

### 28-29 Oct without the largest difference (LT)

Signals 11; available pairs 10 (changed 7, unchanged 3); unavailable 1.

| method | n | wins | win % | total net Rs | mean net % | median net % | avg win Rs | avg loss Rs | stop / trail / 15:20 | max drawdown Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 actual (booked) | 10 | 4 | 40.0 | -8030 | -11.68 | -20.88 | 612 | -1747 | 6 / 4 / 0 | -8030 |
| 09:15 replayed (same engine) | 10 | 4 | 40.0 | -8944 | -13.05 | -21.41 | 397 | -1755 | 6 / 4 / 0 | -8944 |
| 09:16 simulated | 10 | 4 | 40.0 | -6552 | -10.9 | -21.18 | 537 | -1450 | 6 / 4 / 0 | -6552 |

| 09:16 minus 09:15 actual, total Rs | mean pts (net %) | paired t (scale only) | 09:16 better / worse / same | 09:16 minus 09:15 replayed, total Rs | mean entry diff % (changed) | median 1-min dip 09:15 / 09:16 (changed) | median exit shift min (changed) |
|---|---|---|---|---|---|---|---|
| 1478 | 0.78 | 0.62 | 4 / 3 / 3 | 2392 | -10.3 | -17.8 / -9.2 | 0.8 |

### 27-29 Oct, valid comparable quotes only (as committed)

Signals 6; available pairs 6 (changed 2, unchanged 4); unavailable 0.

| method | n | wins | win % | total net Rs | mean net % | median net % | avg win Rs | avg loss Rs | stop / trail / 15:20 | max drawdown Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 actual (booked) | 6 | 2 | 33.3 | -6490 | -16.5 | -22.73 | 790 | -2017 | 4 / 2 / 0 | -6490 |
| 09:15 replayed (same engine) | 6 | 2 | 33.3 | -7206 | -18.27 | -22.38 | 406 | -2004 | 4 / 2 / 0 | -7206 |
| 09:16 simulated | 6 | 2 | 33.3 | -4833 | -14.86 | -22.73 | 672 | -1544 | 4 / 2 / 0 | -4833 |

| 09:16 minus 09:15 actual, total Rs | mean pts (net %) | paired t (scale only) | 09:16 better / worse / same | 09:16 minus 09:15 replayed, total Rs | mean entry diff % (changed) | median 1-min dip 09:15 / 09:16 (changed) | median exit shift min (changed) |
|---|---|---|---|---|---|---|---|
| 1658 | 1.63 | 0.69 | 1 / 1 / 4 | 2374 | -19.4 | -22.549999999999997 / -8.05 | 0.75 |

### 28-29 Oct, valid comparable quotes only (as committed)

Signals 4; available pairs 4 (changed 1, unchanged 3); unavailable 0.

| method | n | wins | win % | total net Rs | mean net % | median net % | avg win Rs | avg loss Rs | stop / trail / 15:20 | max drawdown Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 actual (booked) | 4 | 2 | 50.0 | -1906 | -8.48 | -7.18 | 790 | -1743 | 2 / 2 / 0 | -2527 |
| 09:15 replayed (same engine) | 4 | 2 | 50.0 | -2622 | -11.15 | -8.47 | 406 | -1717 | 2 / 2 / 0 | -3007 |
| 09:16 simulated | 4 | 2 | 50.0 | -2142 | -9.3 | -8.82 | 672 | -1743 | 2 / 2 / 0 | -2527 |

| 09:16 minus 09:15 actual, total Rs | mean pts (net %) | paired t (scale only) | 09:16 better / worse / same | 09:16 minus 09:15 replayed, total Rs | mean entry diff % (changed) | median 1-min dip 09:15 / 09:16 (changed) | median exit shift min (changed) |
|---|---|---|---|---|---|---|---|
| -236 | -0.82 | -1.0 | 0 / 1 / 3 | 480 | 0.0 | -3.3 / -4.4 | 0.0 |

### 27-29 Oct, comparable incl. 1-s exit-check rows (post hoc)

Signals 13; available pairs 13 (changed 9, unchanged 4); unavailable 0.

| method | n | wins | win % | total net Rs | mean net % | median net % | avg win Rs | avg loss Rs | stop / trail / 15:20 | max drawdown Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 actual (booked) | 13 | 4 | 30.8 | -14823 | -17.14 | -22.09 | 612 | -1919 | 9 / 4 / 0 | -14823 |
| 09:15 replayed (same engine) | 13 | 4 | 30.8 | -15736 | -18.2 | -22.31 | 397 | -1925 | 9 / 4 / 0 | -15736 |
| 09:16 simulated | 13 | 4 | 30.8 | -9979 | -14.07 | -21.7 | 537 | -1348 | 9 / 4 / 0 | -9979 |

| 09:16 minus 09:15 actual, total Rs | mean pts (net %) | paired t (scale only) | 09:16 better / worse / same | 09:16 minus 09:15 replayed, total Rs | mean entry diff % (changed) | median 1-min dip 09:15 / 09:16 (changed) | median exit shift min (changed) |
|---|---|---|---|---|---|---|---|
| 4844 | 3.07 | 1.62 | 6 / 3 / 4 | 5757 | -16.6 | -32.5 / -10.3 | 1.1 |

### 28-29 Oct, comparable incl. 1-s exit-check rows (post hoc)

Signals 11; available pairs 11 (changed 8, unchanged 3); unavailable 0.

| method | n | wins | win % | total net Rs | mean net % | median net % | avg win Rs | avg loss Rs | stop / trail / 15:20 | max drawdown Rs |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 actual (booked) | 11 | 4 | 36.4 | -10239 | -14.35 | -21.45 | 612 | -1813 | 7 / 4 / 0 | -10239 |
| 09:15 replayed (same engine) | 11 | 4 | 36.4 | -11152 | -15.59 | -21.92 | 397 | -1820 | 7 / 4 / 0 | -11152 |
| 09:16 simulated | 11 | 4 | 36.4 | -7288 | -11.91 | -21.21 | 537 | -1348 | 7 / 4 / 0 | -7288 |

| 09:16 minus 09:15 actual, total Rs | mean pts (net %) | paired t (scale only) | 09:16 better / worse / same | 09:16 minus 09:15 replayed, total Rs | mean entry diff % (changed) | median 1-min dip 09:15 / 09:16 (changed) | median exit shift min (changed) |
|---|---|---|---|---|---|---|---|
| 2951 | 2.44 | 1.21 | 5 / 3 / 3 | 3864 | -13.8 | -25.15 / -9.75 | 0.9500000000000001 |

### Standing-book variant (book in force at 09:16:00, probe-polled contracts)

| day | symbol | e16_price | stand_e16_price | net16 | stand_net16 | net15 |
|---|---|---|---|---|---|---|
| 2026-10-27 | RECLTD | 3.0 | 3.0 | -1394.57 | -1394.57 | -3288.03 |
| 2026-10-28 | LT | 19.1 | 19.25 | -736.31 | -745.11 | -2208.33 |
| 2026-10-28 | BAJAJ-AUTO | 83.0 | 84.0 | 450.8 | -1435.75 | 462.59 |
| 2026-10-28 | MAZDOCK | 31.85 | 31.85 | 384.94 | 384.94 | 620.74 |
| 2026-10-29 | JSWENERGY | 4.55 | 4.55 | -1131.72 | -1131.72 | -2478.12 |
| 2026-10-29 | ADANIPORTS | 15.75 | 15.7 | -1582.02 | -1558.26 | -1630.72 |
| 2026-10-29 | NAUKRI | 7.85 | 7.9 | 354.29 | 326.78 | 407.6 |
| 2026-10-29 | HEROMOTOCO | 46.35 | 46.35 | -1508.42 | -1508.42 | -1689.72 |
