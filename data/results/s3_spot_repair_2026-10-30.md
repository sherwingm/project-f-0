# Index spot / VIX 1-minute store: repair from Upstox (2026-10-30)

Code `index_data/fill_spot_upstox.py` (tests `tests/test_fill_spot_upstox.py`); data commit **62a23257** on
`index-data` (on top of the 2026-10-29 recorder commit ad801cfa). From now on the nightly recorder runs the same repair
for the latest months (`index_data/daily_extras.py`, step `spot_upstox_repair`).

## Why
While filling the two Budget sessions that E1 was missing, Upstox's public 1-minute candles (no login) were compared
with the Kotak rows already in the store, and both with NSE's official daily open / high / low
(`index_close_daily.parquet`, 2022-01 → 2025-09):

| Check | Kotak store before | After the repair |
|---|---|---|
| NIFTY 50 day open = NSE official (± 0.05 pt), 923 sessions | 34.7 % | **100.0 %** |
| NIFTY 50 day high within 0.02 % of NSE | 89.8 % | 96.3 % |
| NIFTY 50 day low within 0.02 % of NSE | 93.6 % | 97.2 % |
| Nifty Bank day open = NSE | 42.1 % | **100.0 %** |
| Nifty Bank day high / low within 0.02 % | 85.6 % / 86.7 % | 93.7 % / 93.1 % |
| India VIX day open = NSE | 99.8 % | 100.0 % |

(India VIX's official high / low agree on only ~35 % of days with either vendor: NSE computes VIX's daily high / low
differently from the 1-minute bars. No S3 rule uses VIX's high or low.)

What was wrong:
1. **The 09:15 bar.** Kotak's first bar of the day has the wrong open before 2025-09 (e.g. 2024-10-07: 25,099.75 vs
   NSE's 25,084.10) and a high / low that miss part of the minute on most days (e.g. 2026-03-19: Kotak's 15-minute
   opening range 162.65 points, the true one 197.75). Upstox's 09:15 open, high and low equal NSE's official ones on
   every day checked.
2. **Every later minute agrees.** Closes 09:16-15:29 on 4 check days × 4 series: median difference 0.00-0.02 %, 99th
   percentile ≤ 0.15 %; highs / lows to 0.01 % (13 more NIFTY days); same minute labels (a 1-minute shift never fits
   better).
3. **Missing regular sessions:** the Budget sessions Sat 2025-02-01 and Sun 2026-02-01, 2022-06-16, and the special
   full Saturday session 2024-01-20 (SENSEX also 2022-07-29 and 2022-12-27).
4. **Fake full days for short special sessions:** the DR-drill Saturday 2024-05-18 (two short sessions; stored as
   373 rows, 69 % flat) and the Muhurat session 2025-10-21 (13:45-14:44 only; stored as 376 rows, 81 % flat filler at
   the previous close, first bar with open above high), the 2022-10-24 Muhurat (80 flat rows) and a one-bar Saturday
   2025-08-23.

## What was changed (every series, 2022-01 → 2026-10; Upstox has no minutes before 2022)

| Series | 09:15 bars replaced (changed) | Minutes added | Sessions added | Sessions dropped |
|---|---|---|---|---|
| NIFTY50 | 1,186 (1,145) | 859 | 2022-06-16, 2024-01-20, 2025-02-01, 2026-02-01 | 2022-10-24, 2024-05-18, 2025-08-23, 2025-10-21 |
| NIFTYBANK | 1,186 (1,144) | 1,225 | same 4 | same 4 |
| SENSEX | 1,184 (1,115) | 1,632 | + 2022-07-29, 2022-12-27 | 2024-05-18, 2025-10-21 |
| INDIAVIX | 1,186 (548) | 448 | same 4 | 2024-05-18, 2025-08-23, 2025-10-21 |

Rules: a session with ≥ 300 Upstox minutes is regular (09:15 bar replaced, missing 09:15-15:29 minutes added; the
store's own later minutes and its 15:30 bar are kept). A stored day is dropped only when Upstox has fewer minutes **and**
≥ 50 % of the stored bars are flat filler, or Upstox has none and ≥ 90 % are filler. Changed rows carry
`source="upstox"`. Running the repair again changes nothing.

**Not changed:** 2021-10 → 2021-12 (Upstox has no minutes; Kotak's 09:15 opens there are still off by up to ~16
points), the 2021-11-04 Muhurat (43 flat rows; < 60 bars, so `s3_regime.daily` already skips it), SENSEX 2023-12-23
(16 rows, kept, skipped by the 60-bar rule) and India VIX 2022-10-24 (Kotak rows, not flat). Remaining day high / low
differences against NSE are concentrated in 2021-2023-H1 (a few points; three bad Kotak ticks of 0.2-1.4 % on
2022-03-07, 2022-09-07, 2022-11-28 for NIFTY); from 2023-H2 at most 2 sessions per half-year differ, none by 0.2 %.

## What it affects
- **G1** (gap = the 09:15 open vs the previous close), **B1** and **P4** (the opening range includes the 09:15 bar's
  high / low), **Q1** (daily range; the dropped special sessions; the added sessions), **E1** (the two Budget events
  become tradable; session lists). The 14:30-15:25 expiry pods (P1-P3, P5-P7, R1) take the spot only at their entry
  minute and are unaffected.
- Their re-runs on the repaired store are pre-registered in `strategies/S3_buy_followups_2026-10-30.md`.
