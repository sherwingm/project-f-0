# Forward test: NIFTY expiry-day ATM straddle (pre-registered 2026-11-05, before any forward expiry)

**Why.** The study (`reports/FINAL_RESEARCH_REPORT.md`) found no direction edge and no profitable size signal. Its one
open question is the expiry-day swing. A same-day NIFTY ATM straddle reached +100 % at some minute on 22 of 107
expiry days (mean max up +53 %, median +27 %). Held to 15:15 it averaged −7.2 % net. With a +20 % target it won on
63 % of days but still averaged −8.1 %.

The user, 2026-11-05: "Test do it", then "Both" (commit the research, and start the forward test).

This is a **log, not a strategy**:
- No order is sent anywhere.
- It has its own ledger, `data/xp_ledger.json`, on the live server.
- S1, G1 and NT are not touched.

## Rules (fixed now; no open parameters)
- **Days:** every NSE session that is a NIFTY options expiry day, meaning a NIFTY contract expires today in Upstox's
  instrument list.
- **Strike:** the ATM strike (50-point steps) nearest NIFTY 50's first print at or after 09:15:00.
- **Entry:** buy 1 lot of the CE and 1 lot of the PE of **today's expiry** at the **last best ask of each leg in the
  09:16 minute**. If a leg has no ask in that minute, the day is listed as skipped. Nothing is filled by guess.
- **Primary exit (+20 % target):** sell both legs at their best bids the first second the two bids together reach
  ≥ 1.20 × the two asks paid. Otherwise sell both at their best bids at the first quote from 15:15:00.
- **Shadow exit (hold to 15:15):** the same position valued at the bids at the first quote from 15:15:00, logged
  side by side.
- **Also logged:**
  - max up: the highest bid sum during the day against the price paid;
  - the time of max up;
  - VIX at 09:16;
  - the opening gap;
  - each leg's spread at entry.
- **Costs:** real bid / ask (no extra slippage) plus `server/charges.py` per leg. A research-style version is also
  logged: last prices with 1 % slippage per leg (2 % before 09:30), for comparison with the backtest.

## Gate, judged once 40 forward expiry days are logged
1. The primary (+20 %) exit's mean net % of premium is > 0.
2. One-sided t-test p < 0.05.
3. The primary exit beats hold-to-15:15: paired mean difference > 0.

A pass is reported to the user as a candidate for paper trading. Nothing is enabled automatically. A fail closes the
expiry-straddle question. The rules are not re-tuned (target level, entry minute, strike).

NIFTY expires weekly, so 40 expiry days is about 9-10 months.
