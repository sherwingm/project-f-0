# LLD: data audit + historical expiry calendar

Written 2026-11-04, before the code. Module = `scripts/audit_data.py`, `scripts/build_calendar.py`,
`tests/test_calendar.py`.

## Purpose
1. Know exactly what the read-only store holds: span, sessions, gaps, duplicates, bad prices, unit errors, how far
   two sources of the same thing agree. Later experiments must cite this audit for what they can and cannot use.
2. Build a historical expiry calendar (one row per underlying and expiry date) and per-session expiry tags that
   later modules join on.

## Inputs (read-only, `INDEX_STORE`)
| Set | Read as |
|---|---|
| `options_daily/{NIFTY,BANKNIFTY}/YYYY-MM.parquet` | bhavcopy rows (IDF futures, IDO options) |
| `index_close_daily.parquet` | daily OHLC for NIFTY50, NIFTYBANK, INDIAVIX |
| `spot_1m/{NIFTY50,NIFTYBANK,SENSEX,INDIAVIX}/YYYY-MM.parquet` | 1-minute OHLC, IST timestamps |
| `vix_daily.parquet` | India VIX daily OHLC |
| `options_1m/{NIFTY,SENSEX}/<expiry>/<day>.parquet` | option minute bars, folder = expiry, file = trading day |
| `nifty_1s/<day>.parquet`, `chain_eod/<yyyymmdd>.parquet`, `instruments/<yyyymmdd>.parquet` | small extras, checked for span and columns only |
| `expiries.parquet` | currently listed future expiries (not history); used only for expiries after the last stored session |

No S1/S2/S3 code or output is read.

## Outputs
`results/audit/`:
| File | One row per | Key columns |
|---|---|---|
| `dataset_summary.csv` | dataset | dataset, resolution, first, last, n_sessions, n_rows, n_dup, n_nan_price, n_nonpos_price, n_ohlc_bad |
| `session_presence.csv` | union session date | date, weekday, one 0/1 column per dataset, n_present, n_expected (in-span datasets), flag |
| `session_mismatches.csv` | (date, dataset) where an in-span dataset lacks a union session or has a weekend day | date, dataset, issue |
| `spot1m_bars_per_day.csv` | (index, date) | n_bars, first_time, last_time, short (<370), late_start, early_end, n_dup_ts |
| `vix_unit_issues.csv` | (source, date) with any minute or daily value off by x100 or /100 | n_minutes_x100, n_minutes_div100, daily ref |
| `reconcile_daily_vs_1m.csv` | (index, date) in overlap | official OHLC, 1m OHLC, pct diffs |
| `reconcile_summary.csv` | index x field | n, median abs pct diff, p99, n over 0.1 %, n over 0.5 % |
| `bhavcopy_monthly_coverage.csv` | (underlying, month) | sessions, rows, fut rows, opt rows, strikes per day (median), distinct strikes, option expiries listed (median per day), expiries in month |
| `options_1m_coverage.csv` | (underlying, expiry folder) | n_day_files, first_day, last_day, last_day==expiry, rows, median tokens per day, median minutes per day, columns |
| `price_issues_bhavcopy.csv` | (underlying, month) | rows with NaN / zero close, zero settle, OHLC inconsistent (traded rows only) |

`data/expiry_calendar.csv` (one row per underlying, expiry_date):
underlying, expiry_date, weekday, kind (weekly / monthly), is_quarterly (monthly in Mar/Jun/Sep/Dec),
status (expired / future_listed), source (bhavcopy / options_1m / expiries_parquet), has_futures,
first_listed_seen, last_traded, n_sessions_traded, usual_weekday (official regime), shifted (weekday differs from the
regime), shift_reason (holiday: regime day was not a session / regime_change / unexplained), relabelled_from
(older XpryDt values whose contracts were re-dated into this expiry).
`data/expiry_relabels.csv`: ghost XpryDt values (contracts later re-dated by the exchange) with the date they moved to.
`data/sessions_<UL>.csv` for NIFTY, BANKNIFTY, SENSEX: date, weekday, next_expiry, sessions_to_next_expiry,
next_weekly, sessions_to_next_weekly, next_monthly, sessions_to_next_monthly, last_expiry,
sessions_since_last_expiry, is_expiry_any, is_expiry_weekly, is_expiry_monthly.

## Rules
- Session calendar = union of trading days seen in bhavcopy, spot_1m, index_close_daily, vix_daily, options_1m day
  files (weekends kept only if the data shows them, e.g. special or Muhurat sessions; flagged).
- Expiry is real (status expired) if contracts with that XpryDt traded and the max TradDt for that XpryDt equals the
  XpryDt. An XpryDt whose last TradDt is earlier than itself and before the last stored session is a ghost: the
  exchange re-dated those contracts (holiday or schedule change); it is linked to the real expiry within 7 days
  that the contracts continued under.
- SENSEX expiries come from `options_1m/SENSEX` folder names; real if the last day file equals the folder date.
  SENSEX history before the first folder is not stored, so SENSEX tags start there.
- kind = monthly if it is the last real expiry in its calendar month for that underlying, else weekly. Cross-check:
  NIFTY/BANKNIFTY futures exist only on monthly expiries.
- Decision time: the expiry calendar is published by the exchange weeks in advance, so the session tags are known
  before every session and are legitimate features. One caveat: re-dated expiries (holiday shifts, regime changes)
  were known only from the circular date; the calendar uses the final dates. Sessions counts are computed from the
  session calendar (which embeds holidays, themselves announced in advance each year).
- Sessions after the last stored session cannot be counted; tags needing them are left blank, never guessed.
- Missing data is listed, never filled.

## Tests (`tests/test_calendar.py`)
- NIFTY 2018-01-25 is a monthly Thursday expiry.
- Every expired expiry is a session in the session calendar.
- No two monthlies in one (underlying, month); every NIFTY/BANKNIFTY monthly has futures and no weekly has futures.
- Weekly gaps: consecutive expiries of an underlying are 1-14 calendar days apart while weeklies exist.
- BANKNIFTY has no weekly after 2024-11-13; NIFTY weeklies are Tuesday-based from 2025-09.
- sessions tags: is_expiry_* rows have sessions_to_next_* == 0.

## Changes made during build (2026-11-04, recorded after first run)
- **kind rule changed.** "Last expiry of the calendar month" mislabels 3 months: BANKNIFTY 2024-01 (weekly 31-Jan
  after monthly 25-Jan), BANKNIFTY 2024-04 and NIFTY 2025-04 (weekly pulled back to 30-Apr for the 1-May holiday).
  New rule: monthly = the expiry on the holiday-adjusted last official monthly weekday of the month (window
  [target - 6 d, target]). It matches futures presence on every NSE expiry. `last_in_month` is kept as a column.
- **Special sessions.** Data-detected short sessions (Diwali Muhurat): NIFTY option volume < 30 % of the 21-session
  median and < 200 NIFTY50 minute bars. They stay in the session list but are not counted as sessions for the
  `sessions_*` tags (tags blank on those rows) and a regime day falling on one explains a shifted expiry.
  Output `data/special_sessions.csv`.
- **Single-dataset days dropped.** A date seen in only one dataset is not a session (2023-12-23 spot SENSEX,
  2025-04-26 option minutes). Output `results/audit/sessions_dropped.csv`.
- **Status `expired_unverified`** for a SENSEX folder whose expiry-day file is missing (2026-10-29).
- **Missing expiries.** Official regime days with no stored expiry within [-4 d, +2 d] go to
  `data/expiry_missing.csv`; session tags around them are blanked and `calendar_gap = True`.
- **Ghost links** follow chains (an XpryDt re-dated twice) to `final_expiry`.
- Session tags have `is_special_session`, `calendar_gap`, `cal_days_to_next_expiry`, `next_expiry_kind`.

## Change 2026-11-05: count only to expiries known on the day (verifier issue, written before the code change)
Problem: the tags pointed to every live expiry, listed or not. NIFTY rows 2018-01-01 → 2019-02-08 counted down to
2019-02-14, the first NIFTY weekly, which was first listed on 2019-02-11 (look-ahead of up to 277 sessions).
- New column `known_from` in `data/expiry_calendar.csv`: the first day the expiry is known.
  - Bhavcopy expiries: `first_listed_seen`. For a re-dated expiry, the earliest `old_first_seen` of the ghost dates
    linked to it, if earlier (the contract existed under its old date; the re-dating itself is the documented caveat).
  - SENSEX (options_1m folders) and expiries.parquet rows: blank. A folder's first day is when collection started, not
    the listing day, so it cannot be used. SENSEX tags start 2024-10-04, long after the SENSEX weekly launch (2023-05).
  - No launch announcement date is used: the NIFTY weekly launch circular was not read, so its listing day
    (2019-02-11) is the earliest date it counts as known. Nothing is inferred.
- Session tags: on day d, `next_expiry`, `next_weekly`, `next_monthly` (and their counts, `cal_days_to_next_expiry`,
  `next_expiry_kind`) use only expiries with `known_from <= d` or blank `known_from`. `last_expiry` and `is_expiry_*`
  are unchanged (past or same-day facts).
- New columns in `sessions_<UL>.csv`: `next_expiry_known_from`, `next_weekly_known_from`, `next_monthly_known_from`
  (the `known_from` of each pointer). The panel uses them to blank `cal_next_*` tags of t+1 that were not known on t.
- Tests: no pointer has `known_from` later than its row date; NIFTY weekly tags blank before 2019-02-11; NIFTY
  2019-02-01 → 02-08 point to 2019-02-28 (monthly).
