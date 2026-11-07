# Data audit (2026-11-04)

Scripts: `scripts/audit_data.py` (writes `results/audit/*.csv`, stdout in `results/audit/audit_stdout.txt`) and
`scripts/build_calendar.py` (session calendar, special sessions). Store: `../fo-index-data/data/index`, read-only.
Every number below comes from the CSV named next to it.

## 1. What exists (`dataset_summary.csv`)
| Dataset | Resolution | First | Last | Sessions | Rows |
|---|---|---|---|---|---|
| options_daily/NIFTY | daily bhavcopy | 2018-01-01 | 2026-10-29 | 2,177 | 4,635,778 |
| options_daily/BANKNIFTY | daily bhavcopy | 2018-01-01 | 2026-10-29 | 2,177 | 3,073,898 |
| index_close_daily (NIFTY50, NIFTYBANK, INDIAVIX) | daily | 2018-01-01 | 2025-09-30 | 1,913 each | 1,913 each |
| vix_daily | daily | 2008-03-03 | 2026-10-23 | 4,567 | 4,567 |
| spot_1m NIFTY50 / NIFTYBANK / SENSEX | 1 min | 2021-10-20 | 2026-10-29 | 1,241 | ~466k each |
| spot_1m INDIAVIX | 1 min | 2021-10-20 | 2026-10-29 | 1,242 | 466,351 |
| options_1m/NIFTY | 1 min per option | 2024-08-02 | 2026-10-28 | 555 days, 111 expiries | 119.5 M |
| options_1m/SENSEX | 1 min per option | 2024-09-06 | 2026-10-28 | 528 days, 109 expiries | 65.0 M |
| nifty_1s | 1 s, with bid/ask | 2026-11-02 | 2026-11-04 | 3 | 5.8 M |
| chain_eod | EOD chain snapshot | 2026-10-16 | 2026-10-29 | 9 | 6,264 |
| instruments | daily contract master | 2026-10-16 | 2026-10-29 | 10 | 124,294 |
| expiries.parquet | listed expiries | 2026-10-19 | 2031-06-26 | – | 49 |

Notes:
- The bhavcopy holds only NIFTY and BANKNIFTY index futures (IDF, 6,531 rows each) and options (IDO).
- The union session calendar (`session_presence.csv`) has 2,183 dates from 2018; 2 are dropped as untrusted
  (seen in one dataset only, `sessions_dropped.csv`), leaving 2,181 (`data/sessions_NIFTY.csv`).
- The last stored session is 2026-10-29. nifty_1s days (2-4 Nov 2026) are not used for the calendar because
  30 Oct 2026 is in no dataset, so sessions after 29 Oct cannot be counted.

## 2. Missing sessions (`session_mismatches.csv`, `session_presence.csv`)
A day is "missing" in a dataset when it lies inside that dataset's span and other datasets have it.

| Dataset | Missing days | Which |
|---|---|---|
| bhavcopy NIFTY and BANKNIFTY | 4 real | 2021-03-30 (normal Tuesday), 2024-01-20 (Sat special full session), 2025-02-01 (Sat, Budget), 2026-02-01 (Sun, Budget) |
| index_close_daily (all 3) | 2 real | 2024-01-20, 2025-02-01 |
| vix_daily | 21 real | 13 in 2019-2021 (e.g. 2019-02-13, 2021-05-05), plus 2022-12-26, 2024-01-01, 2024-01-20, 2024-02-19, 2025-01-01, 2025-02-01, 2026-01-01, 2026-02-01 |
| spot_1m NIFTY50, NIFTYBANK | 3 | Muhurat sessions 2022-10-24, 2024-11-01, 2025-10-21 |
| spot_1m SENSEX | 4 | the same 3 Muhurat days + 2021-11-04 |
| spot_1m INDIAVIX | 2 | 2024-11-01, 2025-10-21 |
| options_1m SENSEX | 4 | 2024-09-09 → 2024-09-12 |

Untrusted single-dataset days (counted in the table above against every other dataset, but not sessions):
2023-12-23 (Saturday, 16 SENSEX minute bars only) and 2025-04-26 (Saturday, one SENSEX option-minute file).

Weekend sessions kept: 2024-01-20, 2025-02-01, 2026-02-01 (present in 4-6 datasets).
Special short sessions found in the data (`data/special_sessions.csv`): 2018-11-07, 2021-11-04, 2022-10-24,
2024-11-01, 2025-10-21, all Diwali Muhurat days (NIFTY option volume 8-27 % of normal, few or no minute bars).
Weekend Muhurat sessions (2019, 2020, 2023) are in no dataset.

## 3. Quality issues
| Issue | Size | File |
|---|---|---|
| Duplicate rows, bhavcopy / daily files / spot_1m | 0 | `dataset_summary.csv` |
| Duplicate (timestamp, token) rows, options_1m | NIFTY 279,435 (all in expiry 2026-10-19); SENSEX 328,775 (all in 2026-10-22) | `options_1m_coverage.csv` |
| Option close ≤ 0, options_1m SENSEX | 24,937 rows | `dataset_summary.csv` |
| Bhavcopy settle price ≤ 0 | NIFTY 109,244 rows, BANKNIFTY 29,144 (mostly 2018-19) | `price_issues_bhavcopy.csv` |
| Bhavcopy untraded rows (volume 0) | about 40-90 % of option rows per year | `price_issues_bhavcopy.csv` |
| Bhavcopy UndrlygPric empty | every row before 2024-07-05 | `price_issues_bhavcopy.csv` |
| Bhavcopy OHLC inconsistent on traded rows | 0 | `dataset_summary.csv` |
| index_close INDIAVIX with no OHLC (close only) | 2021-02-12, 2021-03-30 | `dataset_summary.csv` |
| vix_daily last row has no close | 2026-10-23 | `dataset_summary.csv` |
| spot_1m bad days | 2021-11-04 (42 flat bars at 14:48-15:30: Muhurat at wrong clock), 2021-11-10 (358 bars), 2022-03-07 (high +1.4 % / +2.6 % vs official), 2022-10-24 VIX only (85 bars) | `spot1m_bars_per_day.csv`, `reconcile_daily_vs_1m.csv` |

**VIX unit problem (`vix_unit_issues.csv`).** In spot_1m INDIAVIX, 455 days from 2021-10-20 to 2023-08-22 carry
minute values stored x100 (76,741 minutes) or /100 (92,476 minutes); each OHLC field can be off on its own. The
audit rescales each field by 0.01 or 100 when it is > 20x or < 0.05x that day's vix_daily close. 13 days have no
vix_daily close to compare with (listed in the file), so they cannot be repaired this way; 4 of them sit in the
overlap with index_close_daily and still show 100x errors after the fix. vix_daily and index_close_daily VIX
values are all inside 5-100.

## 4. Reconciliation, index_close_daily vs spot_1m daily OHLC (`reconcile_summary.csv`, 974 days, 2021-10 → 2025-09)
| Index | Field | Median abs diff | Days > 0.5 % |
|---|---|---|---|
| NIFTY50 | open | 0.000 % | 1 |
| NIFTY50 | high / low | 0.002 % / 0.003 % | 2 / 0 |
| NIFTY50 | close | 0.048 % | 2 |
| NIFTYBANK | close | 0.064 % | 2 |
| INDIAVIX (after unit fix) | close | 0.386 % | 363 |

The official close is a 30-minute average (index close rule), the last minute bar is not, so a close gap of a few
basis points is expected. The four > 0.5 % NIFTY/BANK days are 2021-11-04 (bad minute data), 2022-03-07 (bad
minute high), 2022-04-19 and 2024-06-04 (close only; fast closing moves). VIX minute close differs from the
official close by 0.39 % on a typical day: use vix_daily for the daily VIX value, not the last minute.
vix_daily vs index_close_daily VIX agree to 0.05 % (3 close days differ > 0.5 %).

## 5. Bhavcopy coverage (`bhavcopy_monthly_coverage.csv`)
No month has fewer than 15 sessions. Median per day:
| Year | NIFTY strikes (traded) | NIFTY expiries listed | BANKNIFTY strikes (traded) | BANKNIFTY expiries listed |
|---|---|---|---|---|
| 2018 | 143 (71) | 14 | 60 (51) | 10 |
| 2020 | 145 (99) | 21 | 111 (92) | 10 |
| 2022 | 152 (123) | 21 | 142 (130) | 10 |
| 2024 | 126 (116) | 18 | 124 (120) | 10 |
| 2025 | 121 (116) | 18 | 155 (153) | 6 |
| 2026 | 146 (144) | 18 | 174 (159) | 6 |

## 6. Option minutes (`options_1m_coverage.csv`)
- NIFTY: every real NIFTY expiry from 2024-10-03 to 2026-10-19 has a folder; no folder is a non-expiry
  (`calendar_checks.csv`). Median 20 day files and 113 contracts per day per expiry, 375 minutes per day.
  The 2026-10-27 folder ends 2026-10-23 (no 26-27 Oct files). The 2024-12-26 folder holds 2 contracts only.
- SENSEX: 109 folders, 2024-10-04 → 2026-11-05; median 64 contracts per day (about 180 on expiry day).
  Missing: expiry 2024-10-25 (weekly + monthly) has no folder; days 2024-09-09 → 09-12 absent; 2026-10-29 has no
  expiry-day file. Several 2024-25 folders hold under 30 contracts per day.
- Columns: open, high, low, close, volume, oi, token, symbol, strike, type, source. **No bid/ask or depth
  column**, so fills can only be modelled from trade prices plus an assumed spread.
- Bid/ask exists only in nifty_1s (3 days, 2026-11-02 → 04, ~96 % of rows have bid and ask) and chain_eod
  (9 days, 44 % of rows have bid/ask). That is enough to estimate a typical spread, not to backtest with quotes.

## 7. What each later experiment can and cannot use
| Question | Usable data | Limit |
|---|---|---|
| Daily index behaviour before expiry (returns, ranges, gaps) | index_close_daily 2018-01 → 2025-09; bhavcopy futures 2018 → 2026-10 | index daily stops 2025-09; after that use futures OHLC or spot_1m |
| Intraday behaviour (T1515 features, minute paths) | spot_1m 2021-10 → 2026-10 | discovery part only 2021-10 → 2022-12; drop bad days listed in section 3; VIX minutes need the unit fix |
| VIX level / change | vix_daily 2008 → 2026-10-23 | 21 missing days; last row has no close |
| OI, volume, settle, option prices at EOD | bhavcopy 2018 → 2026-10 | 4 missing days; UndrlygPric empty before 2024-07; untraded rows carry stale prices |
| Executable option entry/exit prices | options_1m NIFTY 2024-10 →, SENSEX 2024-10 → | final out-of-sample period only; trade prices, no quotes |
| Spreads / slippage | nifty_1s (3 days), chain_eod (9 days) | too short for a backtest; a spread assumption only |
| SENSEX expiry behaviour | spot_1m SENSEX 2021-10 →; SENSEX expiries 2024-10 → | no SENSEX option history before 2024-09, no BSE bhavcopy |
| Stock options | none | **Untestable** |
| Market breadth, sectors, global markets, FII/DII flows, news | none stored | **Untestable** unless data is added |
