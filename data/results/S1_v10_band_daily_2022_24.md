# S1 v10 fade · cheap-option bands, 2022-24 on daily data: before (15:20) vs after (B30)

Numbers only. strategies/S1_v10_band12_trail.md, addendum 2. Daily option open / high / low / close (no minute data exists before Oct 2024). Entry = day 0's open + Rs 0.10; before = close - Rs 0.10; after = B30 (hold until +100 %, then a 30 % trailing stop) as a range, because daily data cannot order the prices inside the day. Real charges. v10's own trades use the backtest's existing costs. t date-clustered.

## Before vs after, 2022-24

| band | exit | n | win_pct | mean_pct | median_pct | total_rs | max_dd_rs | t |
|---|---|---|---|---|---|---|---|---|
| Rs 1-2 | BEFORE: 15:20 exit | 221 | 31.7 | -8.79 | -28.28 | -41050 | 61162 | -1.697 |
| Rs 1-2 | AFTER: B30, optimistic | 221 | 35.7 | 1.72 | -27.07 | 5242 | 34950 | 0.286 |
| Rs 1-2 | AFTER: B30, pessimistic | 221 | 31.7 | -23.32 | -28.28 | -147772 | 149770 | -8.172 |
| Rs 0.50-1 | BEFORE: 15:20 exit | 151 | 21.2 | -20.04 | -31.04 | -83822 | 90895 | -3.972 |
| Rs 0.50-1 | AFTER: B30, optimistic | 151 | 24.5 | -13.91 | -31.04 | -59968 | 68671 | -2.457 |
| Rs 0.50-1 | AFTER: B30, pessimistic | 151 | 21.2 | -29.3 | -31.04 | -124657 | 125023 | -9.319 |

## By year

| band | year | n | before_rs | after_opt_rs | after_pes_rs | armed_pct |
|---|---|---|---|---|---|---|
| Rs 1-2 | 2022 | 46 | -20635 | -16816 | -31857 | 17.4 |
| Rs 1-2 | 2023 | 86 | -19257 | 11989 | -63175 | 23.3 |
| Rs 1-2 | 2024 | 89 | -1159 | 10069 | -52740 | 24.7 |
| Rs 0.50-1 | 2022 | 35 | -19031 | -10026 | -25829 | 20 |
| Rs 0.50-1 | 2023 | 62 | -36082 | -24002 | -49251 | 14.5 |
| Rs 0.50-1 | 2024 | 54 | -28709 | -25939 | -49577 | 13 |

## With v10's Rs 2+ trades (2022-24)

| band | set | n | total_rs | win_pct |
|---|---|---|---|---|
| - | v10 as today (Rs 2+ only) | 436 | 24190 | 36.5 |
| Rs 1-2 | v10 + band, BEFORE (15:20) | 657 | -16859 | 34.9 |
| Rs 1-2 | v10 + band, AFTER optimistic | 657 | 29432 | 36.2 |
| Rs 1-2 | v10 + band, AFTER pessimistic | 657 | -123582 | 34.9 |
| Rs 0.50-1 | v10 + band, BEFORE (15:20) | 587 | -59632 | 32.5 |
| Rs 0.50-1 | v10 + band, AFTER optimistic | 587 | -35778 | 33.4 |
| Rs 0.50-1 | v10 + band, AFTER pessimistic | 587 | -100467 | 32.5 |

## Check of the daily method on 2025 (where minute data exists)

| band | exit | minute data (real) | minute n | daily | daily n | daily optimistic | daily pessimistic |
|---|---|---|---|---|---|---|---|
| Rs 1-2 | 15:20 | 36757 | 95 | 38,962 | 107 |  |  |
| Rs 1-2 | B30 | 47775 | 95 |  | 107 | 87,724 | -63,823 |
| Rs 0.50-1 | 15:20 | -29559 | 66 | -30,857 | 79 |  |  |
| Rs 0.50-1 | B30 | 1293 | 66 |  | 79 | 932 | -55,627 |


The daily 'before' buys at the open; the minute test bought at the 09:15 minute's close (after the opening spike), so the daily numbers are expected to look better. 2025 Nov-Dec uses the Rs 0.01 tick and Rs 0.04 a side.
