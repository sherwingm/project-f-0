# S1 arms A / B · the fade's −20 % stop applied to the live call arms (descriptive study)

**Pre-registered 2026-10-20**, before any A / B minute candle is fetched or any number of this study is computed. The
user's request: "also check the backtest for the arm a and arm b as used in the fade compare prev and new". This is
a descriptive comparison. **The live arms A / B are not changed**; any change needs the user's decision and its own
pre-registered version, as S1 v11 had.

## Trades
- The live rules' trades as the S1 v8 run makes them (`scanner.backtest_s1_v8`, "live rules" = S1 v7 `old_expiry`
  through `backtest_s1_v7.simulate`):
  - day 0 2025-04-01 → 2026-09-25;
  - arm A = every results beat, arm B = beats in a strong sector;
  - one call lot (₹600–8,000), entered the session after day 0 (d1) at the day's VWAP + 1 tick.
- Re-run on this PC because the 2026-10-14 output is not stored. Its totals are checked against DECISIONS.md (arm A
  172 trades, −3.3 %; arm B 74, −14.5 %) before anything else is read. A mismatch is reported, not hidden.
- Minute candles start at the Oct 2024 expiries (Upstox), so the whole window is covered.

## Prev (the live exit, S1 v7)
On each close from d1: 50 % stop, 5 sessions without a new closing high, T-1. Sold at that close − 1 tick, with the
backtest's charges and % slippage (`backtest_s1_v4.net_of`). The backtest's own `net` is used as is.

## New (the fade's v11 stop added)
- **Same entry price** (d1's VWAP + 1 tick, i.e. the live "close" arm's 15:20 buy).
- On d1 itself, only the close is checked, as in prev (the VWAP entry has no intraday entry time).
- From the next session on, from **09:16 to 15:29** each session, on 1-minute candles:
  - the first minute whose low ≤ 0.80 × entry sells at **min(0.80 × entry, that minute's open) − 1 tick**;
  - a tick is ₹0.05 before 2025-11-03 and ₹0.01 from it;
  - a minute without candles (no trade) cannot fire the stop.
- If the stop did not fire that day, the day's close goes through the prev rules (decay, T-1, and the 50 % stop,
  which the −20 % stop pre-empts). The same close and price as prev, so a trade the stop never touches has exactly
  prev's result.
- Costs: the same `net_of` (charges + % slippage by AMFI category) on the new exit price.
- Minute data is needed only for the sessions from d1 + 1 up to prev's exit day: the stop can only end a trade
  earlier.

## Report (per arm, prev vs new)
- N, win rate, mean and median net % of premium, total net ₹, date-clustered t of the per-trade difference
  (new − prev), by calendar year.
- The stop's firing rate and its day (d1 + 1, d1 + 2, …).
- For stopped trades: how far the option rose after the stop before prev's exit (the fade question), and how many
  would have ended better under prev.
- A trade whose minute candles are missing for a needed day is excluded from both columns and counted.

## Reading it (fixed now)
The new exit "helps" an arm only if, on the same trades, the new total net ₹ > prev's and the mean per-trade difference
> 0 with t ≥ 2. Even then it is descriptive: this window is the holdout already used by S1 v8, and the stop level was
chosen on the fade, not on these arms.
