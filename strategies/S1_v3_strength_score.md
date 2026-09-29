# S1 v3 · Strength score, one trade a day

S1, version 3, under the gate in `DECISIONS.md`. **Pre-registered**: every choice is fixed here before any v3 run.
Test window **2021-01-01 to 2024-12-31**; 2025-01-01 onward is the holdout, untouched unless the gate passes.
Backtest: `python -m scanner.backtest_s1_v3` (diagnostic first; the option backtest only if the diagnostic clears).

## Universe (each session t)
Stocks with option contracts in t's F&O bhavcopy, not in the F&O ban list for the entry day (t+1; NSE publishes
it the evening before).

## Score at the close of t: 0–8 points per direction (long, short)
1. **Model, 3 points.** The walk-forward model (`scanner/model.py`: 3-class down / flat / up, 3-session label
   net of NIFTY 50, ±1 %) scored out of sample: each calendar quarter is predicted by a model trained only on
   earlier rows, **purged** of every training row whose 3-session label reaches into the predicted quarter, so
   the model never sees a test day. Long: p_up in the top decile of t's rows (p_up ≥ the day's 90th percentile);
   short: p_down in the top decile. Days without an out-of-sample probability (the first quarter of the data,
   2021 Q1, which has no earlier training rows) give 0 model points.
2. **Sector relative strength, 2 / 1 points.** Leave-one-out equal-weight sector (as S1 v2: the other stocks of the
   same sector in `data/sector_map.csv`, ≥ 3 per day), 21- and 63-session return minus NIFTY 500's. Long: 2 points
   if both > 0, 1 if one; short: 2 if both < 0, 1 if one. A stock without a sector gets 0.
3. **Tier-1 event in the direction within the last 5 sessions, 2 points.** An event counts on t if its session
   `a` satisfies t−4 ≤ a ≤ t:
   - results with |day-0 abnormal return| ≥ 2 % (day 0 = first full session after the filing time, as S1 v2;
     abnormal = stock − leave-one-out sector, or − NIFTY 500 for a stock without a sector); direction = its
     sign; a = day 0;
   - major order win (event store `order_win` with materiality bucket `major`), long;
   - rating action by a registered CRA (`rating` upgrade → long, downgrade → short);
   - fund block deal (`block_deal` fund_buy → long, fund_sell → short). The store does not identify promoter
     block deals (they fall under other_buy / other_sell), so they do not count.
   For order wins, ratings and deals, a = the event's session if filed before 15:30 on a session day, or if it
   has no time (the end-of-day deal files); otherwise the next session.
4. **Volume and open interest, 1 point.** Volume ratio (t's volume ÷ the mean of the 20 sessions before t,
   eod2) > 1.5 **and** all-expiry stock-futures OI up on t: long if the stock closed up on t (long buildup),
   short if it closed down (short buildup).
5. **Liquidity pass, required.** The current monthly expiry's (first monthly expiry after t) ATM option of the
   direction's type (call for long, put for short; strike nearest spot, a tie: the higher) traded ≥ 100
   contracts and had OI ≥ 50 lots on t. No pass → score 0.

**Direction** = the direction with the higher total (before the liquidity check); a tie → no trade. **Score** =
that total, or 0 without a liquidity pass.

## Selection
Each session: among eligible stocks (in the universe, no open or pending position, not cooling down) with
score ≥ 1, the top score; all stocks tied at the top, up to 3 per day (more than 3 tied: the higher model
probability in the direction, then symbol). One open position per stock; a 10-session cooldown after an exit
(signals on the exit session or the 10 after it are ignored).

## Diagnostic first (stock returns, no options), test window only
For the stocks selected 2021-01-01 to 2024-12-31: the 5- and 20-session return (close t → close t+h) of the
stock minus the leave-one-out sector (NIFTY 500 for a stock without a sector), **signed by direction** (short:
negated). N, mean, median, share positive, date-clustered t; overall, by score level (8, 7, 6, …), by direction,
and by 2021-22 / 2023-24. In the diagnostic a selected stock is treated as held for the 20-session maximum from
t+1, then cooling down 10 sessions (not selectable again before t+32).
**Stop rule:** if the overall 20-session date-clustered t < 1.5, print the diagnostic and stop; no option backtest.

## Option backtest (only if the diagnostic clears), test window only
- **Instrument:** debit spread in the direction, same expiry, per `scanner/option_engine.py`:
  - expiry: the current monthly expiry if ≥ 10 sessions remain after t, else the next monthly;
  - long: the strike nearest spot (a tie: the higher for puts, the lower for calls);
  - short: puts in [0.93, 0.95] × spot, calls in [1.05, 1.07] × spot, nearest 0.94 / 1.06 × spot (a tie: the
    one nearer the long strike); none: no trade.
- **Sizing:** budget = ₹5,000 × (median 20-day realised vol of t's universe ÷ the stock's), clipped to
  ₹2,000–8,000; lots = the largest whole number whose net debit fits the budget; 0 lots: no trade. Vol = std
  (ddof 1) of the last 20 daily log returns.
- **Entry (engine fill):** on t+1, each leg at its VWAP (turnover ÷ (contracts × lot) − strike, NSE turnover being
  notional) or, if unavailable, its close; + 1 tick on the long leg, − 1 tick on the short leg. Each leg must
  have traded ≥ 50 contracts on t+1, otherwise no trade. The trade's first mark is t+1's close.
- **Exits** (each close from t+1, in this order; value = long close − short close):
  1. value ≤ 0.5 × entry debit;
  2. 5 sessions or fewer before expiry;
  3. 20 sessions since entry;
  4. after a close ≥ 2 × entry debit, a close < 0.75 × the highest close since entry.
  Exit fills: long close − 1 tick, short close + 1 tick.
- **Costs:** slippage per leg per side by AMFI category (point in time, `scanner/amfi.py`): large 1 %, mid 2 %,
  small 3 % (unknown 3 %) of premium; charges `server/charges.py` (post-2026-04-01) on all four orders.
- **Corporate actions:** a trade whose leg leaves the bhavcopy, or whose future moves > 3 % differently from
  eod2's adjusted close, is excluded and counted.

## Report
`data/results/S1_v3_backtest_report.md` and `S1_v3_trades.csv`: the S1 v2 report's sections (header with the
test / holdout split and the constituent-history bias, diagnostic, main tables, breakdowns by AMFI category and
volatility tercile, slippage sensitivity, equity curve, gate) plus the diagnostic by score level; test window
only. Numbers only.

## Known limits
- Sector membership and industry are today's lists applied to all dates (constituent-history bias).
- The model's first out-of-sample quarter is 2021 Q2.
