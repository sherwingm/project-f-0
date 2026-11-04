# S3 N1 · NIFTY near-expiry opening-range breakout, option 2 strikes out, sold the same day (pre-registered 2026-11-05)

**Why:** the user, 2026-11-04: "let use built to trade on the near expiry ... it is the plan to capture the trade more
than 100%", then "leave my own code rules only for this strategy" and "Yes, write the page". Buy only, 1 lot. Strategy
name in the code: **`near_expiry`** (the one name `NEAR_EXPIRY_STRATEGIES` exempts from `ALLOW_LOTTERY`; DECISIONS.md
2026-11-04). Nothing here changes S1, S2, G1 or the live server.

**What was seen before this page (disclosed):**
- `data/results/near_expiry_maxup.md` (0349396a), NIFTY 2024-10 → 2026-10, buys at 09:20 with no direction rule:
  options 0-1 sessions from expiry touch +100 % on 31-43 % of trades, but held to expiry the median is −100 %; selling
  at +100 % is worse than holding (it caps the +500 % tail); selling at 15:15 the same day is the least bad exit
  (calls −4 to −20 %, puts −5 to −9 % on sessions 0-1). Conclusion there: time to expiry alone has no edge, a
  direction signal is needed. That is why this page has a breakout signal, no target and a same-day exit.
- The breakout signal is B2's / G1's (`scanner.s3_b2.signal`). B2 on every day (both directions) was in-sample
  flat to negative (`S3 B2` rows, best +3.4 %, every second half negative). **N1's subset (expiry day and the day
  before, 2 strikes out, same-day exit) has not been run on any data.**
- No unseen option history is left (option minutes start 2024-10; the user said on 2026-11-03 not to use 2022-24
  again), so **the verdict is forward only**. One in-sample run on 2024-10 → 2026-10 is allowed after this page is
  committed, as a description only (§ History run): it cannot pass or fail N1 and no rule may change after it.

## Rules (no open parameters)
- **Days:** the NIFTY weekly expiry day (0 sessions left) and the session before it (1 session left), by
  `index_data.load.expiries("NIFTY")` and the NSE holiday list. Any other day has no trade.
- **Opening range:** NIFTY 50 high and low of the 1-minute bars 09:15-09:29.
- **Signal:** the first 1-minute close outside the range, 09:30 → 13:00 (`scanner.s3_b2.signal(day, 15, None)`, no
  acceptance). Close above the high → **call**; below the low → **put**. One trade a day; no re-entry after an exit.
- **Option:** the nearest weekly expiry (the one 0 or 1 session away), strike **2 steps (100 points) out of the
  money** from NIFTY's close of the signal minute rounded to 50: call = ATM + 100, put = ATM − 100.
- **Entry:** the minute after the signal minute, at the ask.
- **Stop:** the option's bid ≤ 50 % of the price paid, checked every second (every minute in the history), sold at
  the bid.
- **Exit:** if the stop has not acted, **sell at 15:15** the same day at the bid. **No target** (the max-up study
  found a +100 % target lowers the mean). Never held overnight, never held to expiry.
- **Size:** 1 lot (the lot at entry, 65 now). The per-trade risk cap and the position counts of `server/risk.py`
  still apply; only `ALLOW_LOTTERY` is lifted for this strategy.

## Forward stage (the test)
- **Sessions:** from 2026-11-06 (the session before the 2026-11-09 expiry) on, as `index_data.pull_1s` brings each day's 1-second file from
  the live recorder (`<store>/nifty_1s/<day>.parquet`). Research only, run from this repo; nothing is ordered.
- **Prices:** NIFTY 50 1-second last prices → 1-minute bars for the signal; the option bought at the ask (last quote
  of the entry minute) and sold at the bid (the stop's second, or the last quote of the 15:15 minute). No added
  slippage: the spread is the real one. Charges from `server/charges.py`.
- A day with no quote for the option within 60 seconds of the needed minute is listed as skipped with the reason,
  never filled by guess. The recorder covers ATM ± 10 strikes of 2 expiries, so the 2-out strike is in it.
- Also reported (no effect on the verdict): max up while held and to 15:29; the calls and puts apart; the expiry day
  and the day before apart; the same trades on minute closes + the engine's slippage, to compare the fills.

## History run (description only, once, after this page is committed)
`scanner/s3_n1.py` on 2024-10-01 → 2026-10-28 option minutes (`options_1m`), the rules above with minute closes +
the S3 slippage (0.5 %; 1 % for 2+ strikes out, before 09:30 or after 15:00) and charges. Reports the same numbers as
the forward stage. It is in-sample for the signal family (B2) and the exit choice (the max-up study), so it is shown
beside the forward result, never pooled with it.

## Gate, judged once the 30th forward trade is booked (the S3 buy gate)
1. 30 trades.
2. Mean net % of the premium > 0.
3. At 2× charges (the real spread kept once) the mean is still > 0.
4. t ≥ 2.
5. Both halves positive (trades 1-15 and 16-30).
6. The worst trade's ₹ loss is smaller than the average month's ₹ result.

About 2 eligible days a week, nearly all with a breakout: roughly 8 trades a month, so 30 trades take about four
months. Thirty trades are few for an option that often goes to zero; a fail closes N1 and is not rescued by changing
the strike, the stop, the days or the exit minute.

## After the verdict
- **Pass:** a proposal to the user to run N1 as a paper strategy on the website (like G1), and only after that, a
  separate decision on real orders through Kotak Neo (static IP, limit orders only; Kotak allows NIFTY strikes within
  15 % of the index, far wider than 100 points). Nothing is enabled automatically.
- **Fail:** the near-expiry ORB lead is closed. The result goes to DECISIONS.md either way.
