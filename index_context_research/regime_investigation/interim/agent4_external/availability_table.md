# Availability table (agent 4): what was known before the entry, and how it was aligned

Rule: entries are at 09:16 or 09:30-13:00 IST. Anything published after the entry minute is never a predictor. "T" = the trade date (Indian session). "P" = the previous Indian session on the NSE calendar (Nifty 50 rows of `nse_index_closes.csv` plus the two Budget weekend sessions 2025-02-01 and 2026-02-01, which are missing from that file; their market data therefore stay missing for the next trading day, 2025-02-03 and 2026-02-02). Paths are relative to `index_context_research/regime_investigation/external_data/` (E) or the repo root.

## Used as pre-entry predictors

| Variable | Source | Coverage | Published (IST) | Known before entry? | Alignment to T |
|---|---|---|---|---|---|
| Nikkei opening gap | E/yahoo/N225_1d.csv | 2018-01-04 to 2026-11-17; 13 closes and 12 opens missing | open 05:30 on T (09:00 JST) | Yes | local date = timestamp_utc + local_offset_s; gap = open of row dated T / close of previous row - 1. Japan holiday = missing |
| Hang Seng opening gap | E/yahoo/HSI_1d.csv | 2018-01-02 to 2026-11-17; 1 close missing | open 07:00 on T (09:30 HKT) | Yes | same; HK holiday = missing |
| Asia pre-entry (average of the two) | derived | needs both markets | by 07:00 on T | Yes | up / down at +/-0.3 %, else flat; if either market is closed it is missing (not filled from one market): 21 of 154 G1-F trades missing |
| US overnight (S&P 500) | E/yahoo/GSPC_1d.csv | 2018-01-02 to 2026-11-17; no missing close | US close 16:00 ET = 01:30 / 02:30 IST next calendar day | Yes | last row dated before T vs the row before it. Matches the project's earlier `us_prev_ret` on 733 of 735 trades; the 2 differing trades are both on 2026-09-29, where the older file (ends 2026-09-25) most likely carried a stale value |
| Global risk-on / off | derived | needs US and Asia | by 07:00 on T | Yes | risk-on = US up and Asia up/flat; risk-off = US down and Asia down/flat; else mixed |
| USD/INR, previous Indian session | E/yahoo/USDINR_60m.csv (hourly) | 2024-11-18 to 2026-11-17 only; trades before that are missing | hourly bars; the 09:00 UTC bar ends at 15:30 IST | Yes | change from the open of the 03:00 UTC bar (08:30 IST) to the close of the 09:00 UTC bar (15:30 IST) on P; +/-0.2 %. **The Yahoo DAILY USD/INR file is not usable: its close equals its open on 100 % of days in 2023-24, 92 % in 2025, 73 % in 2026 (daily-vs-hourly correlation 0.04), so it was rejected.** The approximate hourly session window is a stated approximation of "Indian session" |
| Brent previous-day change | E/yahoo/BRENT_1d.csv | 2018-01-02 to 2026-11-17 | futures settle about 14:30 ET = about 00:00 IST next day | Yes | last row before T vs the row before; +/-1 %. **Quality-limited:** daily vs 14:00-ET hourly (older file in data/parents, ends 2026-10-16) differ by more than 2 % on 27 of 527 days (max 13 %). Those days are flagged `brent_suspect` (3 G1-F trades) and a robustness run excludes them |
| US VIX spike | E/yahoo/VIX_US_1d.csv | 82 closes missing | 16:15 ET = about 02:45 IST next day | Yes | previous-session rise >= +10 % = spike |
| Dollar index direction (extra) | E/yahoo/DXY_1d.csv | 463 weekend-dated all-empty rows dropped; 3 weekday closes missing | Yahoo daily bar done before 05:30 IST on T | Yes | up / down vs previous weekday close; descriptive |
| US 10-year yield direction (extra) | E/yahoo/US10Y_1d.csv | no missing close; contains outliers (largest step 49.9 %) | US bond close 17:00 ET | Yes | sign of change; descriptive |
| Breadth (advance share) | E/nse_breadth_daily.csv | 2021-10-01 to 2026-11-17; the Budget Sat / Sun sessions absent | NSE full bhavcopy, evening of that session | Yes (previous session only) | row of P; advances / (advances + declines); low <= 36.55 %, high >= 61.47 % (25th / 75th percentile of 780 sessions 2021-10-01..2024-09-30) |
| Sector leadership | E/nse_index_closes.csv | 2018-2026 (Nifty Bank, Nifty 50) | index close 15:30 on P, file in the evening | Yes | (Bank return on P) - (Nifty 50 return on P) from consecutive closes; +/-0.3 points. NSE's own change_pct column disagrees with consecutive closes only around special sessions, so closes were used |
| FII / DII cash (third party) | E/fii_dii_cash_stockezee.csv | 2025-12-01 to 2026-11-17; **September 2026 absent at source**; 218 rows | NSE provisional flows are published in the evening of the session | Yes (previous session only) | row of P; sign of FII net and DII net: diverge (opposite), both buying, both selling. 79 of 154 G1-F trades are in the window and 59 have a row. Verified against NSE on one day only: descriptive, third party |
| FII / DII index-futures long share (level and 1-session change) | g1_research/data/external/participant_oi/*.csv | 1280 files, 2021-09-01 to 2026-11-06; header dates all match file names; 60 weekdays have no file and are not in the project's holiday list (the list was fetched in 2026-10 and may omit older holidays; not verified) | NSE participant-wise OI archive, evening of the session | Yes (previous session) | file of P (and of the session before P for the change); share = long / (long + short). Level terciles from session days 2024-10-01..2025-09-30 (return-independent): FII 16.80 / 29.98, DII 54.00 / 66.50 |
| FII index-options stance | same files | same | same | Yes | (net long puts - net long calls) / total option OI of FII; terciles 0.026 / 0.076; 1-session change sign (up = more put-heavy) |
| GDELT tone | g1_research/data/external/gdelt/timelinetone_*.json | 2021-09-01 to 2026-11-07; 44 calendar days missing | UTC day complete at 05:30 IST on the next day | Yes, but retrieved later (possible revision; cannot be proven point-in-time) | value dated T-1 (UTC calendar day) vs median of the 250 prior daily values. A global machine score for the query "Nifty OR Sensex OR Indian stocks", not a news event list |
| Scheduled events | scanner/s3_buy4.py (RBI 13, FOMC 16, Budget 2, US election 1: 2024-11-05) | 2024-10 to 2026-10 | announced long in advance | Yes (schedule; the outcome is not) | day_before / event_day / day_after relative to the entry session. FOMC and US election map to the first Indian session after the US date. RBI statements come at 10:00, so entries before 10:00 on RBI days precede the outcome |

## Not used, because published after the entry (POST-ENTRY) or outside the family
- Same-day Nikkei / Hang Seng / Shanghai close; the same-day S&P 500 and futures after 09:15 IST (POST-ENTRY).
- Same-day FII / DII cash, same-day participant OI, same-day breadth (published in the evening, POST-ENTRY).
- ES / NQ futures hourly bars (2 years): the move between the US close and 09:15 IST is pre-entry information but is not part of the fixed Amendment-1 family, so it was not added.
- The `nifty_close`, `india_vix` columns of the third-party FII / DII file (differ from NSE; not to be used), and its FII derivative columns (the participant OI files are used instead).
- Shanghai, KOSPI, Taiwan, ASX200, Nasdaq, gold, WTI: downloaded but outside the fixed family; no test run.
- GIFT NIFTY (06:30 open, previous settlement): not in this agent's brief.

## What cannot be established
- The 09:00 GIFT level and any intraday pre-open data; timestamped news events; CPI, GDP, geopolitical events, any Indian election: no local source. No event other than the US 2024 election, RBI, Budget and FOMC exists, and none was invented.
- FII / DII cash before 2025-12 and in 2026-09; participants' positions for the two Budget weekend sessions.
- USD/INR before 2024-11-18; the daily USD/INR bar is unusable.
- Exact publication clock times for the evening files (stated limitation: all are many hours before the next entry).
- Muhurat (Diwali evening) sessions (e.g. 2024-11-01, 2025-10-21; low volume) appear in the index file and count as the "previous session" for the next day; not adjusted.
