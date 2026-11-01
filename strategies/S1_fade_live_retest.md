# S1 fade · past studies re-run on the live websocket data (research only)

Written before any number. Nothing live changes.

## Why
Every fade study so far used vendor 1-minute candles (last-trade prices). The server now records the Upstox websocket
(1-second candles of last price, best bid, ask) for every contract its loops watch: `data/candles_1s/<date>.jsonl` on the
VM, 26 – 30 Oct 2026. The user asked for the past tests to be done again on this live data.

## Data
- **Trades:** every live fade trade in `paper-state:data/paper_ledger.json` (`rule = rule_fade`) whose day has a 1-second
  file: 27 – 30 Oct (26 Oct had no fade trade; 15 – 23 Oct have no 1-second file). About 23 trades on 4 days.
- **Option prices:** the websocket 1-second candles (last price o/h/l/c, bid o/h/l/c, ask at the close, volume change).
  1-minute candles for the indicators are built from them (a minute with no tick repeats the last close, volume 0).
- **Stock, Nifty 50, India VIX 1-minute candles:** Upstox historical API (the stream does not record them). Cached in
  `data/cache/intraday/` like the earlier studies.
- **Later days** for the "overall" max up: the contract's Upstox 1-minute candles on each later session up to 30 Oct.

## Tests (the same questions as before, live prices)
1. **Live vs replay:** the v12 exit replayed on the websocket bid from the live fill must match the ledger's sale. Any gap is
   reported (it tests the replay, not the rule).
2. **Stops:** −20 % (v12), −25, −30, −40 %, none, everything else v12, on the 1-second bid, from the live fill.
3. **Max up / max dip:** from the live fill; while held, after the sale (rest of day 0, then later sessions to 30 Oct),
   overall; on the bid and on the last price.
4. **Market pattern:** each day's Nifty previous-day move and 09:15 gap; fail % and mean on "Nifty up yesterday + gap down"
   days vs the rest.
5. **Indicator entries:** all 15,061 rules of `scanner.fade_pattern_entry_more` (same 47 signs) on these trades; buy at the
   ask at the first second of the first traded minute after the sign, v12 exit on the bid; baseline = the 09:16 ask.
   The rules picked earlier (RSI back above 30 + EMA 50; range high + Nifty RSI + after 12:30; EMA 9 + Supertrend 7×2 turned
   up + crossed VWAP; Supertrend 7×2 turned up + stock past VWAP) are the pre-named ones. Out-of-sample check: does a
   rule's backtest mean (Oct 2024 – Aug 2026) predict its live mean (Spearman across rules)?
6. **Models:** the three models of `scanner.fade_ml` trained on the 335 backtest trades with the market-only inputs known at
   09:16 (`scanner.fade_market_pattern` set A), scored on the live trades (AUC).

## Limits stated now
About 23 trades on 4 days, one of them a pattern day: no rule can pass or fail on this. The value is a reality check
(do live prices agree with the backtest's picture?), not a new verdict. The trades were chosen by the live v12 system,
not by the backtest's contract list.
