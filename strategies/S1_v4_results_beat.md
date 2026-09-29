# S1 v4 · Results-beat continuation, long calls only

S1, version 4, under the gate in `DECISIONS.md`. **Pre-registered**: every choice is fixed here before any v4 run.
Long options only (`DECISIONS.md`): every trade is a bought call; maximum loss = the premium paid.
Test window **2021-01-01 to 2024-12-31**; 2025-01-01 onward is the holdout, untouched unless the gate passes.
Backtest: `python -m scanner.backtest_s1_v4`.

## Signal
- A results filing (event store, type `results`, with its filing time). **Day 0** = the first full session after
  the filing timestamp: the filing day itself if filed before 09:15 on a session day, otherwise the next session.
- **P0** = the close of the session before day 0. **AR0** = the stock's return P0 → day-0 close minus the
  leave-one-out sector's return over the same session (equal-weight, the other stocks of the same sector in
  `data/sector_map.csv`, ≥ 3 per day; a stock without a sector: minus NIFTY 500). Beat: **AR0 ≥ +2 %**.
- Skip if the day-0 raw move (P0 → day-0 close) is **≥ +10 %**.
- Skip if the stock is in the F&O ban list for the entry day (day +1).
- Several filings with the same day 0: one signal. Stocks with option contracts in day 0's bhavcopy only.
- **Arm A:** all beats. **Arm B:** beats where, at the P0 close, the leave-one-out sector's 21- and 63-session
  returns exceed NIFTY 500's and its level is above its 50-session average (a stock without a sector: not in B).
- One position per stock (per arm and variant); a 10-session cooldown after an exit (signals on the exit
  session or the 10 after it are ignored).

## Instrument: naked long call (the only tradable expression)
- Strike: the listed call strike nearest day 0's underlying close (UDiFF `UndrlygPric`; before 2024-07-05 the
  nearest stock future's close); a tie: the lower.
- Expiry (engine rule, `scanner/option_engine.py`): the current monthly expiry if ≥ 10 sessions remain after
  day 0, else the next monthly.
- Lot: the bhavcopy's lot size (old files: the greatest common divisor of the stock's open interests).

## Entry (day +1, engine fill rule)
- Fill = the call's day +1 VWAP (NSE notional turnover ÷ (contracts × lot) − strike) or, if unavailable, its
  day +1 close; + 1 tick (₹0.05).
- Liquidity gate: the call traded ≥ 50 contracts on day +1, otherwise no trade.
- Refused as the paper engine refuses: fill premium < ₹2 (`ALLOW_LOTTERY=false`).
- Sizing: budget = ₹5,000 × (median 20-day realised vol of day 0's universe ÷ the stock's), clipped to
  ₹2,000–8,000 (vol = std, ddof 1, of the last 20 daily log returns, eod2 adjusted closes); lots =
  floor(budget ÷ (fill × lot)); 0 lots: no trade.

## Exits (checked on each close from day +1, in this order)
1. call close ≤ 0.5 × entry premium (stop);
2. 5 sessions or fewer before expiry;
3. 20 sessions since entry (**variant: 5 sessions**, reported alongside with its own positions);
4. after a close ≥ 2 × entry premium, a close < 0.75 × the highest close since entry (trailing).
Exit fill: the call's close − 1 tick (not below 0; nothing is sold at 0).

## Costs
- Slippage per side, % of premium, by AMFI category point in time (`scanner/amfi.py`): large 1 %, mid 2 %,
  small 3 % (not found: 3 %).
- Charges: `server/charges.py`, post-2026-04-01 schedule, on both orders.
- Risked = entry premium × quantity. Net = (exit − entry) × quantity − charges − slippage.
- Corporate actions: a trade whose call leaves the bhavcopy, or whose future moves > 3 % differently from eod2's
  adjusted close, is excluded and counted.

## Diagnostic (not a trade)
The same signals (after the signal filters: beat, the +10 % cap, ban; one per stock and day 0; no position,
cooldown or option filters) as a 1-lot stock future bought at the day +1 close and held 20 sessions (and 5),
priced on eod2 adjusted closes, net of 0.1 % round-trip cost, as % of notional. Reported per arm × horizon:
N, hit rate, mean, median, 10th / 90th percentile, worst 5 %, date-clustered t.

## Report (`data/results/S1_v4_backtest_report.md`, trades `S1_v4_trades.csv`), test window only
Per arm (A, B) × exit variant (20, 5 sessions), overall and by 2021-22 / 2023-24: N, hit rate (net > 0), mean
and median net return (% of premium and ₹), net per ₹1,000 risked, date-clustered t (entry date), 10th / 90th
percentile and worst 5 % (5th percentile) of net %, exit-reason shares (1/2/3/4), and the signals removed by
each filter in order (not a beat, raw ≥ +10 %, ban, position / cooldown, no strike or expiry, < 50 contracts
on day +1, lottery, budget below one lot). The gate per `DECISIONS.md` for each arm with the 20-session exits.
Numbers only.

## Known limits
- Sector membership and industry are today's lists applied to all dates (constituent-history bias).
- The futures diagnostic uses eod2 adjusted stock closes, not futures prices.
