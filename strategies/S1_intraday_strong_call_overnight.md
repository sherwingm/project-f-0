# S1 · buy a call one minute after a strong market-hours result, sell at the next open (option backtest)

**Pre-registered 2026-10-20**, before any option candle for it is fetched or any number is computed. The user's
request: "pre-register and test an option trade: buy a call one minute after a strong market-hours result, sell at
the next open". This is a backtest. **Nothing live changes.** A pass becomes a candidate for the user's decision, as
its own version with a DECISIONS.md entry.

## Why
`data/results/S1_intraday_results_path.md` (descriptive): after a strong result filed in market hours, the stock is
flat for the rest of that day but **+0.79 % by the next open** (market-adjusted, t 4.0; 2022-24 +0.82 %, 2025-26
+0.76 %). That was found by looking, so only this test counts. It reuses the same cases, so it is not fresh; the
real check is paper trading later.

## Cases
- `data/results/S1_intraday_cases.csv`: a results filing of an F&O stock, 09:15–14:50 IST on a session day, one
  per stock and day, t0 = the earliest announcement time.
- **Strong only:** NP YoY > +10 %, NP QoQ > 0, revenue YoY > 0 (`scanner.event_screens.strong(q, 10)`, from
  `data/financials.json`).
- Days from **2024-10-01** (Upstox has expired stock-option minutes only from the Oct 2024 expiries) to 2026-09-25.
- The stock in the F&O ban that day: skipped.

## Trade (1 lot, a bought call)
- **Expiry:** the current monthly if ≥ 2 sessions remain after the filing day; else the next monthly.
- **Entry minute:** t0 + 1. **Spot** = the stock's close in that minute.
- **Strike walk:**
  - start at the listed call strike nearest that spot (a tie: the lower), walking upward;
  - take the first strike whose entry minute has a trade (volume > 0), with a price ≥ ₹2 and one lot at the entry
    price within ₹600–8,000;
  - at most 8 strikes.
  - A lot under ₹600 stops the walk; nothing found means no trade (counted).
- **Entry price** = that minute's close + 1 tick.
- **Exit** = the next session's **09:15 minute close − 1 tick**: the first settled price of the open. The 09:15 open
  print is not used, because single option prints can be wild.
- **Tick:** ₹0.05 before 2025-11-03, ₹0.01 from it.
- **Charges:** real (`server.charges.leg`), buy and sell.
- **Sensitivity** (reported, not the test): 2 ticks each side.

## Data
Upstox expired-instruments 1-minute candles for the candidate strikes (the nearest 8 strikes from the entry spot
upward, plus one below for a tie), for the filing day and the next session. Fetched on GitHub
(`fetch_band_minutes intra`). A trade without candles for its entry minute or for the next 09:15 is excluded and
counted.

## Report
- N, win rate, mean and median net % of premium, total ₹, date-clustered t.
- 2024-25 vs 2026; the same with 2 ticks.
- The stock's own move (entry → next 09:15 close), so a fail can be told apart: "the stock moved but the option did
  not" vs "the stock did not move".

## Pass test (fixed now; all needed)
1. At least 60 trades.
2. Mean net % > 0 with date-clustered **t ≥ 2** (1-tick costs).
3. Mean net % > 0 in **both** 2024-25 and 2026.

A pass makes it a candidate for paper trading, the user's decision. A fail closes it with its numbers.

## Limits
- 1-minute closes, not quotes: the real ask can be worse than the close + 1 tick.
- The overnight hold carries the gap risk both ways, and theta for one night.
- About 118 strong cases: a small sample.
