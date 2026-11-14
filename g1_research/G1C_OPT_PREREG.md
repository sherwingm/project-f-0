# G1-C optimization study: pre-registration (written 14 Nov 2026, before any number)

**Request:** the user, 14 Nov 2026: "Lets started optimizating the g1-c". Research only. **Nothing live changes**: G1-C keeps its rules, ledger and 30-trade gate
(`strategies/S3_G1C_call_overnight.md`). A pass here can only justify a **paper shadow tag** with the user's approval, never a rule change, never a real order.

## What was seen before this page (disclosed)
- The call mirror on the whole window 2024-10-01 to 2026-10-28, live rule (ATM, 50 % stop, next 15:29), 235 signals: **-10.8 % of premium a trade**, win 29 %, -Rs 1.6 lakh, -12.7 % at 2x costs; max up through the next close reached +100 % on 20 %, mean +65 %, median +35 % (`VERIFY_RESULT.md`). Every strike lost; ITM about +2 to +3 points better, t below 1.
- Max-up-only call summaries (`results/calls_nifty_maxup_free_summary.csv`), the minimum-break-size test for calls (`DEPTH_RESULT.md`: no threshold helps), the same-day vs overnight comparison for puts (same-day exits lose for puts).
- Four up-break days of 2-6 Nov 2026 and G1-C's first live trade (13 Nov, stopped -50.75 %).
- So the whole window has been looked at for calls. This study is **not independent**; the discovery / validation split below is chronological inside it and is weaker than a fresh sample. Prior expectation: nothing passes.

## Data and trades
- Signals: `scanner.s3_b2.signal(day, 15, None)` side CE (first 1-minute close above the 09:15-09:29 range, 09:30-13:00), the same code path as `verify_strikes.py`. Option prices: NIFTY 1-minute (`INDEX_STORE`), engine fills and charges (`scanner/s3_engine.py`, dated STT), 1 lot, 1x and 2x costs.
- Window 2024-10-01 to 2026-10-28. **Discovery:** signal day before 2025-10-01. **Validation:** 2025-10-01 to 2026-10-28. Live G1-C trades are not used.

## The family (21 candidate cells plus the baseline, fixed now; no cell may be added after a number is seen)
Baseline B = live rule: ATM call, 50 % stop on the minute close, sold at the next session's 15:29.
- **Exits (ATM, 5 cells):** X1 same day 15:15 with 50 % stop; X2 next session 09:16; X3 two sessions later 15:29 (needs expiry on or after that day, else the expiry close); X4 live exit with a 35 % stop; X5 live exit with no stop.
- **Strike (live exit, 2 cells):** K1 one strike in the money; K2 two strikes in the money.
- **Skip filters (live exit, ATM, 14 cells):** for each of 7 features known at the signal minute, skip the trade when the feature is above (or below) the **discovery-half median**: day-1 gap %, opening-range width %, VIX at signal, minutes after 09:30 of the signal, previous-5-day NIFTY return, previous close vs 20-day EMA %, breakout depth at the signal %. Each feature gives two cells (skip high, skip low).
- A cell with fewer than 30 trades in discovery is reported "too few" and is not tested.
- The family is 21 candidate cells (5 + 2 + 14); B is the reference, reported beside them, not a candidate.

## Reporting order (house rule)
For every cell and half: **max up first** (share reaching +50 / +100 / +200 %, mean, median), then the booked result (trades, win %, mean net % of premium, median, total Rs, date-clustered t), at 1x and 2x costs.

## Selection and pass rules
1. **Discovery:** for each tested cell, one-sided date-clustered t-test that mean net % > 0. Benjamini-Hochberg at FDR 10 % across all tested cells. Survivors are frozen (written to `results/g1c_opt_candidates_frozen.csv`) before the validation half is opened.
2. **Validation (opened once):** a frozen candidate passes only if ALL hold: mean net % > 0; date-clustered t >= 1.5; mean > 0 at 2x costs; mean > 0 without its 3 best trades; trade count >= 30.
3. **Reading:** a pass means "candidate for a paper shadow tag on live G1-C trades, judged at 30 trades", nothing more. If no cell survives discovery, or none passes validation, the verdict is **no candidate**, G1-C stays as is, and nothing is rescued by loosening a threshold, adding cells or switching windows.
4. Cells are also compared with B by a paired difference (descriptive only).
5. Trial count: this run adds 21 cells to the registry (`docs/research/experiments.csv`, one row for the run).

## Sensitivity and amendments
- Amendments are allowed only if written and committed before the by-cell results are printed, and must say what had been seen. Any threshold chosen after seeing a number is disclosed.
- Output: `g1_research/scripts/g1c_opt.py` -> `results/g1c_opt_*.csv`, `G1C_OPT_RESULT.md`. Commit of this page recorded in the result.

## Amendment 1 (14 Nov 2026, written while the `build` stage runs; no by-cell number had been printed or read)
**Source:** the user's pasted notes on 14 Nov (r/IndiaAlgoTrading "11.5-year NIFTY gap" case study, Zerodha Varsity, forums). Reddit cannot be opened by our tools, so the claims are taken as written in the notes, as leads only.
The earlier verification (`VERIFY_RESULT.md`, Test 5) checked only that post's exit rules (30 % stop, trail after +20 %), not its two gap claims. They are added here as two extra cells in the same family, tested on the same G1-C call trades (live exit, ATM):
- **GAP075 (gap and go):** keep a call only when the day opened at least +0.75 % above the previous session's close (follow the gap). Expected to give few trades; reported "too few" if under 30 in discovery, never loosened.
- **SKIPEXT (the "87 % losing" setup):** skip a call when the day's gap is between +0.2 % and +0.5 % AND the previous close was at least 2.5 % above its 20-day **simple** moving average of daily closes. The notes give the gap size without a sign; we use the gap in the trade's direction (up, for calls). The 20-day SMA is computed from daily closes up to the previous session only.
The family becomes 23 candidate cells; the Benjamini-Hochberg pass at 10 % runs over all tested cells including these two.
**Not added (outside the project's rules or already tested):** short straddles / strangles before events (option selling; the user's buy-only decision of 30 Oct; a long event straddle, E1, lost -6.2 %); bull call / bear put spreads (need a sold leg; buy-only rule; would need the user's decision first); 50 / 200 SMA crosses (the notes themselves say they fail); "gap >= 0.5 % confirmed, follow the gap" was already tested as S3 G1-gap (closed, -4.3 %, t -0.54; the calls-only hint failed on 2022-24 spot).
