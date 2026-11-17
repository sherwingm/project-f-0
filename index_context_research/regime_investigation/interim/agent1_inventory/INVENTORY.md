# Data inventory for the regime investigation (Agent 1, 17 Nov 2026)

Read-only. Every number is from `inventory_checks.py`, `inventory_checks2.py`, `inventory_checks3.py` (outputs `checks_output*.txt`). Machine-readable table: `inventory.csv`. Paths: `STORE` = `C:/Users/sherw/fo-index-data/data/index`; `EXT` = `index_context_research/regime_investigation/external_data`. Nothing was downloaded, nothing was proxied. Missing stays missing. (A folder `interim/agent1_data_inventory/` from an earlier pass exists; it was not read or changed.)

Calendar used for "NSE session": the Nifty 50 rows of `EXT/nse_index_closes.csv` (2,190 days, 2018-01-01 to 2026-11-17). Three full weekend sessions (2024-01-20, 2025-02-01, 2026-02-01) are in the minute store but NOT in that file; the Muhurat evenings (2022-10-24, 2024-11-01, 2025-10-21) are in that file but not in the minute store.

## 0. Findings the coordinator must act on (read first)

1. **GIFT `prev_settle` is not the previous row's `settlement`.** It differs on 817 of 825 matched days (std 0.41 %). Its difference to the previous row's settlement correlates 0.50 with the S&P 500 return of the US session that ended at about 01:30-02:30 IST of that day (and -0.11 with the other alignment). So `prev_settle(D)` already contains the US-hours move; the row's own `settlement` is a session-1 value. Against the actual NIFTY 09:15 gap (825 days): `open(D)/prev_settle(D)-1` has std 0.30 % and correlation 0.49; `open(D)/settlement(previous row)-1` has std 0.49 % and correlation 0.74; the actual gap has std 0.55 %. Amendment 1 says "open / the previous trade date's GIFT settlement": implemented with the `prev_settle` column it measures only the 02:45-06:30 leftover, not the overnight move. Implemented with the previous row's `settlement` it is the full overnight move. The two are different variables; the choice must be fixed and stated before use. (Which one the draft in `interim/agent3b_gift_regimes/` used was not checked by me.)
2. **Breadth file has 60 rows on NSE holiday dates; 57 are exact copies of the previous row** (the 3 others, 2021-11-05, 2024-01-22, 2024-05-20, are not copies and unexplained). NSE session 2022-08-08 has no row. 2021-11-04 duplicates 2021-11-03. Always key breadth by the NSE session calendar, never "previous row".
3. **Yahoo daily timestamps: do not use `local_offset_s`.** It is a constant (the exchange offset at download time) and shifts dates in summer. Key rule: date = UTC date of `timestamp_utc`, except USD/INR (`(stamp + 1 h)` date) and ASX 200 (`(stamp + 12 h)` date). The last row of every series (2026-11-17) is partial or empty (Nikkei, Hang Seng, KOSPI, Shanghai, Taiwan have no close; S&P volume 846 M vs 4-5 B). Drop all rows dated 2026-11-17 except NSE ones.
4. **FII / DII cash covers only part of the trades**: previous-session values exist for 59 of 154 G1-F trades (102 of 259 G1; 96 of 240 G1-C; 43 of 108 XP). 87 G1-F trades are before 2025-12; 8 have a previous session in the empty September 2026.
5. **Calendar mismatches affect a few trades**: G1-C trades on the Budget weekend sessions 2025-02-01 and 2026-02-01 have no NSE index file row, no GIFT row, no breadth row. Trades whose previous full session is a weekend special session absent from the NSE file: G1-F 2025-02-03; G1 2024-11-04 and 2025-02-03; G1-C 2025-10-23 and 2026-02-02. GIFT has no row on 2025-01-01 and 2026-01-01 (GIFT closed; NSE open): 2 G1-F trades, 2 G1 trades, 2 G1-C trades.
6. **VIX**: use `index_data.load.vix_1m` only (raw minutes are corrupt on 455 days, 2021-10-20 to 2023-08-22). `vix_daily.parquet` ends 2026-10-23 with a NaN close; 13 days have no daily reference (incl. special sessions, so the repair falls back to the day's median there). One residual row: 2025-04-07 09:15 open 13.76 against a close of 22.8.
7. **`nifty_1s` (2026-11-02 to 2026-11-17) overlaps the prospective holdout.** Do not use.
8. **Brent/WTI** are continuous front-month series: Brent -14.5 % on 2026-04-01 while WTI moved -1.2 %. Crude stays flagged. **US 10-year**: use yield-point differences (the "49.9 % move" in the quality note is March 2020 relative change, not an error). **ASX 200 open** equals the previous close on 64.7 % of days (unusable gap). **USD/INR daily** open equals close on 66 % of days; it is a London-day bar, so "previous Indian-session change" (Amendment 1) cannot be built from it.

## 1. NIFTY price and returns; NIFTY BANK; SENSEX

- **Exists:** yes. Minute: `STORE/spot_1m/{NIFTY50,NIFTYBANK,SENSEX}/YYYY-MM.parquet` (61 files each). Daily: `EXT/nse_index_closes.csv` (Nifty 50, Nifty Bank; NOT SENSEX); `STORE/index_close_daily.parquet` (NIFTY50, NIFTYBANK, INDIAVIX, 2018-01-01 to 2025-09-30 only); Yahoo `NSEI_1d.csv` (identical to the NSE file, max diff 5e-8).
- **Coverage:** minute 2021-10-20 to 2026-10-29, 1,241 dates each (VIX 1,242). Daily 2018-01-01 to 2026-11-17.
- **Frequency / completeness:** 1 minute, 376 bars (09:15-15:30). Short days: NIFTY 2021-11-04 (43), 2021-11-10 (358), 2022-03-07 (373); NIFTY BANK also 2022-03-07 (326); SENSEX 2023-12-23 (16, Saturday). No NaN, no duplicate timestamps, no high<low, no within-day 1-minute move above 2 %. Minute store lacks 2026-10-30 and the Muhurat evenings. 09:15 bar is a single print on 70 % of days in 2021 only; index volume is always 0. Whether a stamp labels the start or the end of the minute was not verified (engine convention governs).
- **Availability rule:** minute bars are live. Previous-session close/high/low and today's 09:15 open are known before any entry (XP at 09:16 uses the 09:15 bar open). Daily NSE rows for D are published after the close (evening; clock not in the file).
- **Alignment key:** trade date and minute; previous session via the NSE-file calendar plus the 3 weekend specials (see finding 5).
- **Used before:** NIFTY minutes in all replays and in `context_dataset.csv` (`gap_pct`). NIFTY BANK and SENSEX spot never used as conditions.
- **Missing:** SENSEX daily file (derive from minutes); anything after 2026-10-29 in the minute store.

## 2. India VIX

- **Files:** minute `STORE/spot_1m/INDIAVIX/` (read through `vix_1m`); daily `STORE/vix_daily.parquet` (2008-03-03 to 2026-10-23, 4,567 rows, last close NaN); NSE file `India VIX` rows (2018-01-01 to 2026-11-17, 2,190); `index_close_daily.parquet` (to 2025-09-30).
- **Quality (verified):** raw minute file: 76,741 high rows and 83,459 close rows (about 17 % of 466,351) are x100 or /100 off the day's daily close, on 455 days from 2021-10-20 to 2023-08-22. `vix_1m` repairs this: afterwards 0 high/close rows and 1 open + 1 low row (2025-04-07 09:15) are more than 50 % off. NSE-file VIX vs the store: median diff 0.000 %, one day above 2 %.
- **Availability:** minute live; previous close known; VIX at the signal minute known at entry.
- **Used before:** `vix_signal`, `vix_chg5`, `vix_pct1y` in `context_dataset.csv`.
- **Missing:** VIX daily close for 2026-10-23 in the store (the NSE file has it).

## 3. GIFT NIFTY

- **Files:** NEW `EXT/gift_bhavcopy_futures.csv` (all contracts 29,777 rows; NIFTY near-month 867 days, 2023-07-03 to 2026-11-17; columns trade_date, contract, prev_settle, open, high, low, close, settlement, net_change, oi, traded_qty, ...). OLD (git-ignored): `index_context_research/data/gift/gift_dsp_futures.csv` (daily settlements, 861 days 2023-07-10 to 2026-11-13) and `gift_oi_futures.csv` (combined OI, 865 day headers 2023-07-03 to 2026-11-13).
- **Near-month rule used for checks:** the earliest unexpired NIFTY contract on each date (41 distinct contracts). On expiry day this is the expiring contract.
- **Completeness:** 0 near-month days with a zero open; 0 with high<low or open outside the range; `oi` is empty on 864 of 867 near-month rows (OI exists only in the old combined file); `net_change` missing once. No row on NSE sessions 2024-01-01, 2025-01-01, 2026-01-01, 2024-11-01, 2025-10-21, and on the 3 weekend specials; 40 GIFT dates are NSE holidays.
- **Rules:** `open` of row D = first trade of the 06:30 IST session of D (supported by corr 0.74 with the NIFTY 09:15 gap, median premium over the 09:15 cash open 0.21 %); known before any entry. `prev_settle` of row D: see finding 1 (contains the US-hours move; known by about 02:45 IST of D by inference only). `high`, `low`, `close`, `settlement`, `traded_qty` of row D include the session until 15:40 IST or later and are NOT known before a 09:30-13:00 entry: excluded. The file clock time is not stated; the file is an after-the-fact record, the fields above describe events earlier than 09:15.
- **Alignment key:** row of the trade date D. No fallback to another day when missing. Trade coverage: G1-F 152 of 154, G1 257 of 259, G1-C 238 of 240, XP 108 of 108.
- **Used before:** only the older daily-settlement proxies (`gift_basis`, `gift_ret_prev`).
- **Missing:** the 09:00 IST level and any intraday GIFT history (PREREG and manifest agree).

## 4. Opening gaps; intraday volatility

- **Exists as derivable, not as a table:** gap = 09:15 open / previous full-session close - 1 from the NIFTY minute store (1,241 days); intraday range, trend, opening-range width from the same minutes.
- **Availability:** gap known at 09:15. Intraday measures must be cut at the entry minute (no later bar).
- **Used before:** `gap_pct`; opening-range width as a G1-F filter only.
- **Caveat:** the previous close must follow the session calendar (finding 5).

## 5. FII and DII cash

- **File:** `EXT/fii_dii_cash_stockezee.csv` (third party). 218 rows, 2025-12-01 to 2026-11-17: 216 of the 237 NSE sessions plus 2 non-sessions (2026-02-01 Budget Sunday, 2026-11-08 Muhurat). September 2026 (21 sessions) has no rows. Columns: FII and DII cash net (crore; positive = net buying, corr with same-day NIFTY return 0.39 and -0.30), FII index futures/options and stock futures/options flows, VIX, NIFTY close (3 NaN: 2026-02-01, 2026-07-24, 2026-11-08).
- **Quality:** NIFTY close agrees with NSE within 0.384 % at most (31 days above 0.05 %); the cash net values are verified against NSE on 2026-11-17 only. FII and DII are strongly offsetting (corr -0.85).
- **Availability:** published after the close; previous-session values only. Alignment: previous NSE session of the trade date.
- **Used before:** never. **Missing:** everything before 2025-12-01 and September 2026.

## 6. Participant-wise derivatives positioning

- **Files:** `g1_research/data/external/participant_oi/YYYY-MM-DD.csv`, 1,280 files, 2021-09-01 to 2026-11-06. Rows Client, DII, FII, Pro, TOTAL; columns index and stock futures long/short and index and stock options call/put long/short, total long/short.
- **Quality (verified):** no date gaps against the NSE calendar; every header date equals the filename (an earlier regex failure was mine, fixed); 1,279 files have 15 columns, 1 has 16; no NaN; TOTAL long equals short in the 128 files sampled. FII index-futures long moves by more than 50 % in a day on 24 days (not examined).
- **Availability:** end-of-day positions published in the evening; previous session only. No file after 2026-11-06 (trades end 2026-10-27, so all trade sets are covered except the 1 G1-F/G1/G1-C trade whose previous session was a weekend special).
- **Used before:** FII index-futures long share and its 1-day change (`fii_fut_longshare`, `fii_fut_chg`). Unused: DII, Client, Pro, all options positions.

## 7. NIFTY futures price and OI; options minute data, OI, chain; expiry calendars

- **Futures daily:** `STORE/options_daily/{NIFTY,BANKNIFTY}/YYYY-MM.parquet`, rows with `FinInstrmTp == IDF`: 2018-01-01 to 2026-10-29, 2,177 dates, 3 expiries per day, OHLC, settlement, OI and change in OI. Both underlyings miss 2021-03-30. After the close; previous session only. Used: `fut_oi_chg`, `fut_px_chg`. **Futures intraday history: none** (only the FUT rows of `nifty_1s`, Nov 2026).
- **Options minute with OI:** `STORE/options_1m/NIFTY/<expiry>/<date>.parquet`: 111 expiry folders (2024-10-03 to 2026-11-09), 3,227 contract-day files, trading dates 2024-08-02 to 2026-10-28 (555, every NSE session). SENSEX: 109 folders, 528 dates, 2024-09-06 to 2026-10-28, missing 2024-09-09 to 2024-09-12. **No BANKNIFTY option minutes** (daily only). In a 60-file sample about 49 % of rows are zero-volume fillers (not prices, per `load.py`), 16 % have OI 0, 98 % are Upstox-sourced. No IV stored (derived in the context dataset). Used: `atm_iv`, `iv_skew`, `pcr_oi`.
- **Chain snapshots:** `STORE/chain_eod/` 9 days (2026-10-16 to 2026-10-29); too short. **`nifty_1s`:** 12 sessions (2026-11-02 to 2026-11-17), 1-second NIFTY, options and futures: overlaps the prospective window; do not use.
- **Expiry calendar:** `STORE/expiries.parquet` has only 49 FUTURE expiries (2026-10-19 to 2031). History must come from the option folder names (NIFTY, 111 expiries since 2024-10) or from `XpryDt` in the daily files (2018 on). Weekdays of the 111 NIFTY folders: Tuesday 57, Thursday 46, Monday 6, Wednesday 2. Expiry-day flag and days to expiry were built before (`expiry_day`, `dte`).
- **Holidays:** `data/nse_holidays.json` holds 2026 only (fetched 2026-10-14); `data/special_sessions.json` is an empty list although three weekend sessions are in the store.

## 8. US and Asian markets; USD/INR; crude; gold; dollar index; US VIX; US yields

All in `EXT/yahoo/`, downloaded 2026-11-17, hashes verified against the manifest (25 files, 0 mismatches). Rows and usable rows: Nikkei 2,176/2,163; Hang Seng 2,184/2,183; KOSPI 2,175/2,174; Shanghai 2,150/2,149; Taiwan 2,155/2,153; ASX 200 2,250/2,248; S&P 500 2,232/2,232; Nasdaq 2,232/2,232; US VIX 2,316/2,234; DXY 2,700/2,234 (466 empty Sunday rows); US 10-year 2,232/2,232; WTI 2,237/2,234; Brent 2,237/2,235; gold 2,237/2,234; USD/INR 2,317/2,311; ES and NQ futures 2,237/2,235. Hourly (2024-11-17 to 2026-11-17): ES, NQ (14,516 rows, 21 % NaN closes), USD/INR (12,519 rows, 21 % NaN).

Timing rules (stamp meaning checked: stamps are the bar OPEN time in UTC):
- **Nikkei** open 05:30 IST, close 11:30 IST. **KOSPI** open 05:30. **Taiwan** open 06:30. **Hang Seng and Shanghai** open 07:00 IST (09:30 local; the brief said 06:45), close about 13:30 and 12:30 IST. Open gaps (open/previous close - 1) are pre-entry; high, low, close of the same day are not (they fall inside 09:30-13:00). Open gaps look usable: standard deviations 0.75 % Nikkei, 0.94 % Hang Seng, 1.0 % KOSPI, 0.57 % Shanghai, 0.59 % Taiwan, zero-gap share about 0. Exceptions: KOSPI has 2 days with open=high=low=close; ASX 200 open is unusable (64.7 % equal to the previous close).
- **US cash (S&P, Nasdaq, US VIX, 10-year):** the bar dated D finishes at about 01:30 IST (summer) or 02:30 IST (winter) of the next calendar date. Rule: Indian session T uses the latest US bar dated before T (a Friday bar serves Monday). The bar dated T itself is NOT known.
- **Futures and commodities (ES, NQ, WTI, Brent, gold, DXY):** the bar dated D is the Globex day finishing 17:00 ET (02:30/03:30 IST of D+1). Same rule as the US. Hourly bars are stamped at their START: for a 09:16 entry the last complete bar is stamped 07:30 IST (an 08:30 bar ends 09:30); for 09:30 entries 08:30 is complete. 456 of 480 Indian sessions (2024-11-18 to 2026-10-28) have an ES/NQ bar stamped 06:00-09:15 IST; 477 for USD/INR.
- **USD/INR daily:** London-day bar, closes 04:30/05:30 IST of D+1; usable for D+1. Not an Indian-session change.
- Used before: S&P 500 only (`us_prev_ret`, from `data/parents/yf_GSPC.csv`; the new file is identical, max diff 0.000 %). Old caches in `data/parents/` (to 2026-09-25): USD/INR, Brent, copper, aluminium, iron ore, Infosys: Brent equals the new Brent exactly. No other series was used.
- Gaps in coverage of the trade sets: US data for the 20 trades where `us_prev_ret` is NaN were not re-derived.

## 9. Breadth; sector and index performance

- **Breadth:** `EXT/nse_breadth_daily.csv`, 1,324 rows, 2021-10-01 to 2026-11-17 (advances, declines, unchanged, turnover shares, delivery %; all EQ-series equities that day, so no survivorship, but the universe grows from 1,544 to 2,760). Identity advances+declines+unchanged = n_eq holds on all rows; advance share vs NIFTY return corr 0.73. Problems: finding 2. Availability: after the close; previous session only. Used before: no (the older `breadth_prev` was a proxy from `data/eod2` = today's F&O stocks).
- **Sector and index performance:** `EXT/nse_index_closes.csv`, 181 indices, daily open/high/low/close, P/E, P/B, yield, turnover. Banks, IT, auto, FMCG, metal, pharma, realty, energy, PSU bank, private bank, media, infrastructure, financial services, Next 50, Midcap 50, Nifty 100/200/500 from 2018; Oil & Gas and Consumer Durables from 2020-01-27; Healthcare from 2020-11-19; 'NIFTY Midcap 100' and 'NIFTY Smallcap 100' exist under upper-case names (coverage dates not checked), as do Midcap 150 and Smallcap 250. No intraday sector data. Previous session only. Used before: no.
- **Constituents:** NIFTY 50 historical constituents are not stored; `data/eod2` (473 files, 1995-2026-11-13) and `data/sector_map.csv` (439 stocks) use today's list.

## 10. News sentiment; scheduled events

- **GDELT:** `g1_research/data/external/gdelt/timelinetone_YYYY.json` and `timelinevolraw_YYYY.json`, 2021-09-01 to 2026-11-07, one value a day for the query (Nifty OR Sensex OR "Indian stocks"): average tone and article count. 1,850 days; gaps: 2025 has 348 of 365 days, 2026 has 285 of 311, 2023 has 364 of 365. It is a global machine score with no article times; day D is complete only after the UTC day ends (05:30 IST of D+1), so only the previous day is usable. Used before: against G1 spot follow-through (`g1_research/EXTERNAL_RESULT.md`, `g1_external.py`), not in `context_dataset.csv`.
- **Timestamped news: none.**
- **Scheduled events:** `scanner/s3_buy4.py` lines 44-52: RBI 13 dates (2024-10-09 to 2026-10-07), Budget 2 (2025-02-01, 2026-02-01), FOMC 16 US statement dates (2024-11-07 to 2026-09-16; the Oct and Dec 2026 meetings are missing), US election 1 (2024-11-06). No CPI, GDP, India election results, MSCI/index-rebalance or expiry-type events. The date is known in advance; the outcome is not (RBI at 10:00 IST and the Budget at 11:00 IST fall inside the entry window; FOMC acts on the next Indian session). Used before: `event_window`.
- `data/events.sqlite` (32,049 rows; types ban, block_deal, bulk_deal, results, results_date, insider, rating, order_win, capacity, analyst_view; 2023-01 to 2026-11) is stock-level; 0 index-level rows.

## 11. Trade records (for the alignment key)

- G1 and G1-F: `g1_research/results/g1_live_replay_trades.csv`, 259 trades (154 with g1f=1), 2024-10-01 to 2026-10-23. G1-C: `g1_research/data/g1c_opt_trades.csv`, 240 rows (235 priced), 2024-10-03 to 2026-10-27. XP: `g1_research/data/xp_history_minute.csv`, 108 rows (107 priced), 2024-10-03 to 2026-10-19. Feature table: `index_context_research/results/context_dataset.csv`, 755 rows, 495 trade dates, NaN counts: us_prev_ret 20, gift 10 each, fut and fii_fut 6 each, pcr_oi 12.
- All trade dates exist in the NIFTY minute store and in repaired VIX. All dates are inside the first-pass GIFT range (from 2023-07-03).
- Other option-trade files: SENSEX max-up studies (`sensex_maxup_free_trades.csv` 263, `calls_sensex_maxup_free_trades.csv` 226) and NIFTY calls (235), without net P&L. No BANKNIFTY option trade records. Live ledgers are on the VM (not read).
- The prospective window (after 2026-11-13 17:48 IST) is not in any of these files and was not opened.

## 12. Still missing (final)

FII/DII cash before 2025-12-01 and for September 2026; GIFT 09:00 level and any GIFT intraday history (also near-month OI); timestamped news; NIFTY 50 historical constituents; BANKNIFTY option minutes and trade records; SENSEX daily file; NIFTY futures intraday history before Nov 2026; index options after 2026-10-28 (only the 1-second recorder, which is inside the holdout); minute spot after 2026-10-29; participant OI after 2026-11-06; India macro-event dates beyond the typed lists; a Yahoo intraday series for Asia; Indian-session USD/INR change.
