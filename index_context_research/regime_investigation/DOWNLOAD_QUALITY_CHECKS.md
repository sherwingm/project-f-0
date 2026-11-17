# Download quality checks (17 Nov 2026)

Every number below is computed by `scripts/quality_checks.py` from the downloaded files and existing project files.

## 1. NSE all-index file: NIFTY 50 vs data/eod2/nifty 50.csv
- Overlap 2188 days (2018-01-01 to 2026-11-13); median absolute difference 0.0000 %; days differing by more than 0.1 %: 0; maximum 0.000 %.
- NSE file covers 2190 dates, 2018-01-01 to 2026-11-17; 181 index names (sector, midcap, smallcap, VIX and others).
## 2. India VIX: NSE index file vs store vix_daily.parquet
- Overlap 2155 days; median absolute difference 0.000 %; days above 2 %: 1; maximum 4.58 %.
## 3. FII / DII cash (stockezee, third party): its NIFTY close and VIX vs NSE's own files
- 218 rows, 2025-12-01 to 2026-11-17; includes Sunday special sessions (e.g. 2026-02-01, 2026-11-08).
- NIFTY close: 215 overlapping days, maximum difference 0.384 %, days above 0.05 %: 31. VIX: 215 days, maximum difference 2.08 %.
- Rows per month: 2025-12 22, 2026-01 20, 2026-02 21, 2026-03 19, 2026-04 20, 2026-05 19, 2026-06 21, 2026-07 23, 2026-08 21, 2026-10 20, 2026-11 12. **2026-09 has no rows at all (the source archive is empty for September 2026).**
- Provenance: FII / DII cash net values equal NSE's combined NSE-BSE-MSEI table on 2026-11-17 (4,195.38 / 196.93 crore); no other day could be compared to an official file, so every other day is unverified.
## 4. GIFT NIFTY futures bhavcopy (near-month NIFTY)
- 867 trading days, 2023-07-03 to 2026-11-17; days with a zero open (no trade in session 1): 0.
- GIFT 06:30 open vs previous NIFTY cash close (includes futures carry of about 0.2-0.4 %): median 0.31 %, inter-quartile 0.02 to 0.56 %.
- Correlation with the ACTUAL NIFTY opening gap (09:15 open vs previous close), 825 days: GIFT open-based 0.79; GIFT previous-settlement-based 0.60. (This is a descriptive check that the GIFT fields carry overnight information, not a trading test.)
- Timing: `open` is the first trade of the GIFT session that starts 06:30 IST of the trade date (before any 09:30-13:00 IST entry); `prev_settle` is the previous trade date's settlement as published with this file; their exact publication clock times are not stated in the files (stated limitation).
## 5. Market breadth aggregates (NSE full equity bhavcopy, EQ series)
- 1324 days, 2021-10-01 to 2026-11-17; equities per day median 1887; advances+declines+unchanged equals n_eq on 100 % of days.
- Correlation of advance share with that day's NIFTY return: 0.73 (a sanity check; breadth should move with the index).
## 6. Yahoo series (global markets)
- ASX200_1d.csv: 2250 rows, 2018-01-01 to 2026-11-17, missing closes 2, largest one-step move 9.7 %, steps above 10 %: 0.
- BRENT_1d.csv: 2237 rows, 2018-01-02 to 2026-11-17, missing closes 2, largest one-step move 24.4 %, steps above 10 %: 18.
- DXY_1d.csv: 2700 rows, 2018-01-02 to 2026-11-17, missing closes 466, largest one-step move 2.1 %, steps above 10 %: 0.
- ES_F_1d.csv: 2237 rows, 2018-01-02 to 2026-11-17, missing closes 2, largest one-step move 10.4 %, steps above 10 %: 1.
- ES_F_60m.csv: 14516 rows, 2024-11-17 to 2026-11-17, missing closes 3081, largest one-step move 6.7 %, steps above 10 %: 0.
- GOLD_1d.csv: 2237 rows, 2018-01-02 to 2026-11-17, missing closes 3, largest one-step move 10.8 %, steps above 10 %: 1.
- GSPC_1d.csv: 2232 rows, 2018-01-02 to 2026-11-17, missing closes 0, largest one-step move 12.0 %, steps above 10 %: 1.
- HSI_1d.csv: 2184 rows, 2018-01-02 to 2026-11-17, missing closes 1, largest one-step move 13.2 %, steps above 10 %: 1.
- IXIC_1d.csv: 2232 rows, 2018-01-02 to 2026-11-17, missing closes 0, largest one-step move 12.3 %, steps above 10 %: 2.
- KOSPI_1d.csv: 2175 rows, 2018-01-02 to 2026-11-17, missing closes 1, largest one-step move 17.9 %, steps above 10 %: 3.
- N225_1d.csv: 2176 rows, 2018-01-04 to 2026-11-17, missing closes 13, largest one-step move 12.4 %, steps above 10 %: 2.
- NQ_F_1d.csv: 2237 rows, 2018-01-02 to 2026-11-17, missing closes 2, largest one-step move 11.9 %, steps above 10 %: 2.
- NQ_F_60m.csv: 14516 rows, 2024-11-17 to 2026-11-17, missing closes 3082, largest one-step move 7.7 %, steps above 10 %: 0.
- NSEI_1d.csv: 2191 rows, 2018-01-02 to 2026-11-17, missing closes 4, largest one-step move 13.0 %, steps above 10 %: 1.
- SSEC_1d.csv: 2150 rows, 2018-01-02 to 2026-11-17, missing closes 1, largest one-step move 8.1 %, steps above 10 %: 0.
- TWII_1d.csv: 2155 rows, 2018-01-02 to 2026-11-17, missing closes 2, largest one-step move 9.7 %, steps above 10 %: 0.
- US10Y_1d.csv: 2232 rows, 2018-01-02 to 2026-11-17, missing closes 0, largest one-step move 49.9 %, steps above 10 %: 25.
- USDINR_1d.csv: 2317 rows, 2018-01-01 to 2026-11-17, missing closes 6, largest one-step move 3.0 %, steps above 10 %: 0.
- USDINR_60m.csv: 12519 rows, 2024-11-18 to 2026-11-17, missing closes 2650, largest one-step move 1.1 %, steps above 10 %: 0.
- VIX_US_1d.csv: 2316 rows, 2018-01-02 to 2026-11-17, missing closes 82, largest one-step move 115.6 %, steps above 10 %: 338.
- WTI_1d.csv: 2237 rows, 2018-01-02 to 2026-11-17, missing closes 3, largest one-step move 306.0 %, steps above 10 %: 26.
- S&P 500 new download vs the project's cached file: 1630 overlapping days, maximum difference 0.000 %.
- Brent: DECISIONS.md records Yahoo daily vs hourly Brent disagreeing by 4-7 % on some days; only the daily series was downloaded, and its largest one-day move is 24.4 %. Treat crude with caution.