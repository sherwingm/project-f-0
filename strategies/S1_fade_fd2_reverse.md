# S1 fade · the reverse trade on the fd2 days: buy a call instead of the losing put (backtest)

**Pre-registered 2026-10-20**, before any call price for these days is read. The user's idea: "if we got this we
will do the reverse and get our profit too". The puts whose market-hours filing day already fell ≥ 2 % lost −28 % a
trade (24 trades, `data/results/S1_fade_filing_day_skip.md`), so: buy a **call** on those days instead.
**Nothing live changes.**

**Read this first:** the 24 days were picked *because* the puts lost. A put losing does not mean a call wins. Both
pay the spread, the charges and the day's time decay, and a flat stock makes both lose. So this test is biased in
favour of the idea, and a pass would still need fresh live data.

## Trades
- The same 24 put signals: the v10 backtest's put trades with entry = open whose results were filed 09:15–14:50 on
  the session before day 0, where D ≤ −2 %. D is the stock's filing-day move from the minute before the filing to
  15:29, minus NIFTY's; the list is in `data/results/S1_fade_filing_day_skip_trades.csv`, SKIP group, side PE.
- **The reverse:** a **call**, everything else as v10 (`scanner/backtest_s1_v10.py`):
  - expiry by `fade_live.choose_expiry` on the call chain;
  - spot = the previous session's underlying close;
  - walk upward from the strike nearest the spot (a tie: the lower);
  - the first strike with ≥ 50 contracts, a fill ≥ ₹2 and one lot ₹600–8,000;
  - fill = day 0's open + 1 tick;
  - sold at day 0's close − 1 tick (E1), with the same charges and % slippage.
- Reported beside it, not tested: the 13 call skips reversed to a **put** the same way (too few).
- Minute data for these calls is not fetched, so v11's stop is not applied. Daily data only.

## Pass test (fixed now; all needed)
1. At least 20 reversed call trades.
2. Pooled mean net % > 0 with date-clustered **t ≥ 2**.
3. Mean net % > 0 in **both** 2022-24 and 2025-26.

A pass would only justify a paper shadow track (the user's decision), never a live rule from this data alone.
