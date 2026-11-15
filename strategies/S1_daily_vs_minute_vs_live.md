# S1 live strategies: does the daily-candle backtest of the OLD data (2022-24) give the same result as the same backtest on Oct 2024 to present, and what do 1-minute data and live say? (pre-registration, 15 Nov 2026, before any number of this comparison)

**Request (the user, 15 Nov):** check whether the daily-candle result of the old data and the result for Oct 2024 to present give about the same performance, using the strategies that are live. Clarified: "old backtest result refers to the old data".
**Already settled elsewhere (not re-run):** arms A / B daily vs minutes (`S1_armab_minutes.md`: A -24.4 %, B -19.1 %, entry 7.2 % dearer than the daily test), the fade on minutes (`S1_fade_minutes_retest.md`: v12 +2.86 %), the stress audit. **New here:** the same daily-candle code on the old period vs the recent period side by side, with the minute and live results on the recent dates, and a trade-by-trade match.
Descriptive only: no pass / fail, nothing tuned, nothing live changes.

## Strategies compared (only those that are live AND have old data; G1 / G1-F / G1-C / XP have no old minute data: their option history starts Oct 2024)
- **S1 fade (v10 rule, daily candles):** trade files `data/results/S1_v10_trades_2022_24.csv` (day0 2022-01-13 to 2024-11-27) and `S1_v10_trades.csv` (2025-01-10 to 2026-08-17). Entry day-0 open + tick on daily prices. Exits: e1 = sold the same day, e2 = the daily-candle stop path.
- **S1 arms A / B (daily candles):** the recent period is recomputed from `data/results/S1_v8_trades.csv` (live-rule variant, entry 2025-04-22 to 2026-08-12); the old period (2021-2024, v7 rules) has no trade file in the repo, so its numbers are **quoted** from DECISIONS.md and the v8 report and labelled as quoted, not recomputed.

## Periods
- **Old data:** day0 / entry before 2024-10-01 (fade: 2022-01-13 to 2024-09-30; arms: 2021-2024 as reported). **Recent:** from 2024-10-01 to the end of each source. Because the daily files start 2025-01, the fade's daily recent period is Jan 2025 to Aug 2026 (the daily file for Oct-Dec 2024 is inside the 2022-24 file: its rows from 2024-10-01 are counted as recent, not old).
- Then, for the recent period: the 1-minute re-test (`S1_fade_minutes_retest_trades.csv`, live-rule filter lot_ok and entry >= Rs 2, v12 and v10-hold) and the live paper record (`stress_audit/data/paper_ledger_snapshot_2026-11-09.json`, closed trades with `rule.strategy == "fade"`, 15 Oct to 9 Nov 2026; no date overlap with the other two, so distribution only).
- Matching key (symbol, day0) for daily vs minutes on the recent dates.

## Reported
1. Per source and period: n, win %, mean and median net % of premium, total Rs, date-clustered t; max up first where the source has it (minutes only).
2. Old vs recent (daily): the difference of means with its clustered t, and whether the sign flips.
3. Matched trades (daily ∩ minutes): share matched, minute entry / daily entry price ratio, per-trade net % difference (minute v10 - daily e1), correlation, share with the same sign.
4. A plain-words reading and the most likely reasons (entry price, strike, intraday path). No recommendation to change anything.
