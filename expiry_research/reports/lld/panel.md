# LLD: leak-free daily panels

Written 2026-11-04, before the code. Module = `scripts/build_panel.py`, `tests/test_panel_leakage.py`.

## Purpose
One row per full trading session t and underlying, holding (1) what was known at a stated time on t (features),
(2) what happened on t itself (outcomes), (3) what happens on the next full session t+1 (labels). Research modules
read only these panels, so the column prefix must tell them when a value became known.

## Inputs (read-only, `INDEX_STORE`; plus the calendar stage outputs)
| Input | Used for |
|---|---|
| `spot_1m/{NIFTY50,NIFTYBANK,SENSEX}` | daily OHLC (from 2021-10-20), minute outcomes, f1515 features |
| `spot_1m/INDIAVIX` | f1515 VIX (minute close of 15:14), fallback VIX close |
| `index_close_daily.parquet` | daily OHLC before 2021-10-20 and on bad minute days; reconcile |
| `vix_daily.parquet` | VIX close (main source) and its trailing history from 2008 |
| `options_daily/{NIFTY,BANKNIFTY}` | futures (IDF) and options (IDO) end-of-day features |
| `data/sessions_<UL>.csv`, `data/special_sessions.csv` | session list and calendar tags (known in advance) |

## Row set
- NIFTY, BANKNIFTY: the calendar's sessions 2018-01-01 → 2026-10-29 with `is_special_session = False`.
  Diwali Muhurat (about one hour) is not a row; `cal_special_between` marks a t whose gap to t+1 spans one.
- SENSEX: the same NSE session list from 2021-10-20 (first SENSEX minute day). BSE shares the NSE holiday list
  in this span; a session with no SENSEX minute file is kept with blank prices and listed in the gap report.
- t+1 = the next row of the same panel. The last row (2026-10-29) has blank labels.

## Daily OHLC and its source (`src`)
- Minute bars are read in IST, bars 09:15..15:29 only (the 15:30 bar is dropped), duplicates removed.
- Minute day is good (`m_ok`) if it has >= 370 of the 375 bars, starts 09:15, ends 15:29, and is not on the audit's
  bad-day list (2021-11-04, 2021-11-10, 2022-03-07; DATA_AUDIT.md).
- Good minute day: open = 09:15 open, high/low = max/min of bars, close = 15:29 close, `src = spot_1m`.
- Otherwise `index_close_daily` if it has the day (`src = index_close_daily`), else the minute aggregate is used only
  if at least 300 bars exist (`src = spot_1m_short`), else blank (`src = none`). Nothing is filled.
- Minute-derived outcome columns are blank when `m_ok` is false.
- The close of a minute day is the last traded value, not NSE's official close (an average of the last 30 minutes);
  `px_close_official` keeps the official value where it exists, and the reconcile reports the gap.

## Column prefixes and availability codes
| Prefix | Meaning | Availability |
|---|---|---|
| `date`, `underlying`, `split`, `src`, `m_ok`, `px_*` | identifiers and the session's own prices | TCLOSE(t) |
| `f_` | known after the official close of t, including that evening's bhavcopy | TCLOSE(t) |
| `f1515_` | minute bars of t up to the 15:14 bar (its close is the 15:14:59 value) plus earlier days | T1515(t) |
| `o_` | outcomes of session t itself (gap, candle, minute path) | OUTCOME(t) = known at TCLOSE(t) |
| `cal_`, `cal_next_` | expiry calendar tags of t and of t+1 (schedule published in advance) | TCLOSE(t) |
| `y_` | labels describing session t+1 | NEXT(t+1) |

`o_X` and `y_X` share one function: a per-session outcome table is computed once, `o_X` is its value on t and
`y_X` its value on t+1 (shift -1). So a label and its feature twin always mean the same thing.

## Session outcome table (one value per session s, relative to the previous session s-1)
gap_pct = open(s)/close(s-1)-1; gap_dir up / down / flat (|gap| < 0.1 %); gap_sign (+1/-1/0, raw);
oc = close/open-1; cc = close/close(s-1)-1; high_vs_prevclose, low_vs_prevclose; range_pct = (high-low)/close(s-1);
max_exc = max(high/close(s-1)-1, 1-low/close(s-1)); big_cc = |cc| >= 1 %; big_exc = max_exc >= 1 %;
gap_filled (gap up: low <= close(s-1); gap down: high >= close(s-1); blank when gap is exactly 0);
gap_fill_min (minutes after 09:15 of the first bar that reached close(s-1); minute days only);
ret15/30/60 = close of the 09:29 / 09:44 / 10:14 bar over the 09:15 open, minus 1 (minute days only);
last_hour = close 15:29 / close 14:29 - 1; rv = sqrt(sum of squared 1-minute log returns, first bar open->close
included); high_min / low_min = minutes after 09:15 of the first bar making the day high / low.
All in percent except flags and minutes.

## f_ features (TCLOSE(t))
- Candle of t: body fraction |c-o|/(h-l), upper and lower wick fractions, close position (c-l)/(h-l).
- Streaks: consecutive up (+) / down (-) closes ending at t; same for gaps (sign of gap; 0 resets).
- Momentum 1/3/5/10/20 sessions: close(t)/close(t-k)-1.
- Distance of close(t) to the high / low of the 20 and 55 sessions ending at t.
- HV10 / HV20: std of daily log returns over the last 10 / 20 sessions x sqrt(252), percent.
- ATR14 % = mean true range of the last 14 sessions / close(t).
- VIX: close (vix_daily; fallback index_close_daily, then the clean minute 15:29 close from 2023-08-23), `vix_src`,
  1d and 5d percent change on panel sessions, percentile of the close among the previous 252 VIX closes (needs 200).
- Futures (bhavcopy of t): front contract = smallest XpryDt > t; settle, close, basis = close/px_close-1, days to
  its expiry, its OI, OI change, volume; all-contract OI and OI change; ratio of OI, volume, all-OI to the mean of
  the previous 20 sessions (t-20..t-1, needs 15).
- Options (bhavcopy of t) for two expiries chosen from what is listed on t: `near` = smallest option XpryDt > t
  (the nearest expiry on or after t+1); `mon` = smallest option XpryDt > t that also has a future (a monthly).
  Per expiry: listed expiry date and calendar days to it, n_strikes (rows with CE or PE), n_strikes_oi, CE / PE OI,
  CE / PE OI change, CE / PE volume, PCR(OI), PCR(volume), max-pain strike and its distance to px_close %,
  top-3 strike OI share (CE+PE per strike), call wall (max CE OI strike above close) and put wall (max PE OI strike
  below close) distance %, ATM strike (strike nearest close among those with CE and PE settle > 0), ATM straddle
  settle % of close, its 1d change on the same expiry (blank if that expiry was not listed on t-1), ATM CE / PE
  volume. Settle <= 0 is treated as missing for the straddle. Nothing is filled across strikes or days.
- Cross panel (NIFTY and BANKNIFTY panels): BANKNIFTY minus NIFTY 1d and 5d return, same date only.
- The expiry date is used exactly as listed on t; a contract the exchange re-dated later keeps its old date here.

## f1515_ features (T1515(t))
ret_to_1514 = close(15:14)/close(t-1)-1; ret_open_to_1514; pos_in_range (of the 09:15..15:14 range); range_pct;
rv to 15:14; vix_1514 (minute VIX close at 15:14, unit-fixed against the previous VIX close: ratio > 20 -> /100,
< 0.05 -> x100) and its change vs the previous VIX close. Blank unless >= 355 of the 360 bars to 15:14 exist and
the day is not on the bad-day list.

## Calendar tags
From `sessions_<UL>.csv`: cal_is_expiry, cal_kind (weekly / monthly / none), cal_is_quarterly, cal_sessions_to_expiry,
cal_sessions_to_weekly, cal_sessions_to_monthly, cal_sessions_since_expiry, cal_days_to_expiry, cal_next_expiry_kind,
cal_gap, cal_dow; and the same for t+1 as cal_next_*, plus cal_days_to_next_session and cal_special_between.
These use the final dates; a late holiday re-dating is known from its announcement only (see EXPIRY_CALENDAR_ANALYSIS).

## Split
discovery (t <= 2022-12-31), validation (2023-01-01 .. 2024-06-30), final (t >= 2024-07-01), by the date of t.
`split_edge` = True where t+1 falls in a later split (the label belongs to the next period).

## Outputs
`data/panel_{NIFTY,BANKNIFTY,SENSEX}.parquet`, `data/panel_dictionary.csv` (column, group, definition, availability),
`results/panel_summary.csv` (per panel x split row counts and NaN share per column), `results/panel_reconcile.csv`
(minute vs official daily OHLC and the gap-label agreement), `results/panel_gaps.csv` (sessions with missing inputs),
`results/panel_stdout.txt`, `reports/PANEL.md`.

## Tests (`tests/test_panel_leakage.py`)
a. For sampled dates t (each split, both expiry and non-expiry days), cut every raw input at TCLOSE(t) (rows with date
   <= t; minute bars <= 15:29 of t), rebuild, and require every f_, o_, cal_ value of row t to equal the full build.
   For f1515_: cut at T1515(t) (no daily, VIX or bhavcopy rows of t; minute bars of t <= 15:14) and require equality.
b. For sampled t, recompute every y_ value directly from the raw minute bars / daily rows of t+1 and close(t) with
   separate test code, and require equality with the panel.
c. Every panel column has a dictionary entry, every prefix maps to the right availability code, no unknown prefix.

## Change 2026-11-05: final period sealed, calendar known-from rule (verifier issues, written before the code change)
1. **Sealed final period.** `build_panel.py` still builds all rows (features need history), but writes:
   - `data/panel_<UL>.parquet` = discovery + validation rows only (t <= 2024-06-30). On the validation edge row
     (2024-06-28, t+1 = 2024-07-01 is a final session) every `y_` value except `y_date` is blanked.
   - `data/sealed/panel_<UL>_final.parquet` = final rows (t >= 2024-07-01) plus the unblanked edge row. Only the
     coordinator opens it, once (PREREGISTRATION).
   - `scripts/panel_io.py` is the shared loader: `load_panel(ul)` reads the open file and refuses any final row;
     `load_sealed_final(ul, coordinator=True)` must be called with the flag; `sealed_feature_columns(ul, cols)` reads
     only id / `f_` / `f1515_` / `cal_` columns of the sealed file (for the leakage test, never `o_` / `y_` / `px_`).
   - Build diagnostics use discovery + validation only: `panel_summary.csv` gives NaN shares for discovery,
     validation and open (= both); the final split row has only its row count and span. `panel_reconcile.csv` uses
     days <= 2024-06-30. `panel_gaps.csv` covers open rows; the final rows' input gaps (from src / n_bars / f_ columns
     only) go to `data/sealed/panel_gaps_final.csv`.
2. **Calendar known-from.** `cal_*` tags of t come from `sessions_<UL>.csv`, which now counts only to expiries known on
   t (see lld/audit_calendar.md). For `cal_next_*` (tags of t+1, used at t), a tag is blanked when its pointer's
   `known_from` is after t: `next_expiry_known_from` > t blanks cal_next_ sessions_to_expiry, days_to_expiry,
   upcoming_kind (and is_expiry, kind, is_quarterly when t+1 is itself that expiry); `next_weekly_known_from` > t
   blanks cal_next_sessions_to_weekly; `next_monthly_known_from` > t blanks cal_next_sessions_to_monthly.
3. Tests: all tests read the open panel through `panel_io`; test a also checks f_ / f1515_ / cal_ of final sample
   dates through `sealed_feature_columns`; new test e checks the seal (no final row or final label in the open file,
   sealed file holds exactly the final rows + edge row) and that no `cal_next_` count uses an expiry unknown on t.
