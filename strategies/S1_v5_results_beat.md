# S1 v5 · Results-beat continuation, long calls, ₹10,000–30,000 band

S1, version 5, under the gate in `DECISIONS.md`. **Pre-registered**: every choice is fixed here before any v5 run.
Long options only: every trade is a bought call; maximum loss = the premium paid.
Test window **2021-01-01 to 2024-12-31**; 2025-01-01 onward is the holdout, untouched unless the gate passes.
Signals whose day +1 + 20 sessions falls after 2024-12-31 are not taken, so no trade reads a holdout price.
Backtest: `python -m scanner.backtest_s1_v5`.

**What changes from v4:** only the sizing. v4's volatility budget clipped to ₹2,000–8,000 left 3 trades; v5 trades
**1 lot** when that lot's premium at the entry fill is **between ₹10,000 and ₹30,000** (`DECISIONS.md` budget
band; the paper cap is 6 % of ₹5,00,000 = ₹30,000). Everything else is v4's definition, restated here.

## Signal (as v4)
- A results filing (event store, type `results`, with its filing time). **Day 0** = the first full session after
  the filing timestamp (the filing day if filed before 09:15 on a session day, otherwise the next session).
- **P0** = the close of the session before day 0. **AR0** = the stock's return P0 → day-0 close minus the
  leave-one-out equal-weight sector's return that session (the other stocks of its sector in
  `data/sector_map.csv`, ≥ 3 per day; a stock without a sector: minus NIFTY 500). Beat: **AR0 ≥ +2 %**.
- Skip if the day-0 raw move is **≥ +10 %**; skip if the stock is in the F&O ban list for day +1.
- One signal per stock and day 0; stocks with option contracts in day 0's bhavcopy only.
- **Arm A:** all beats. **Arm B:** beats where, at the P0 close, the leave-one-out sector's 21- and 63-session
  returns exceed NIFTY 500's and its level is above its 50-session average (no sector: not in B).
- One position per stock (per arm and exit variant); 10-session cooldown after an exit. No cap on the number of
  positions open at once across stocks in the backtest (the paper account's 3-position limit is not simulated).

## Instrument and entry
- Naked long call, the listed strike nearest day 0's underlying close (a tie: the lower); expiry by the engine
  rule (`scanner/option_engine.py`): the current monthly expiry if ≥ 10 sessions remain after day 0, else the next.
- Entry on day +1 at the engine fill: the call's day +1 VWAP (notional turnover ÷ (contracts × lot) − strike) or,
  if unavailable, its close; + 1 tick. The call must have traded ≥ 50 contracts on day +1.
- Refused: fill < ₹2 (`ALLOW_LOTTERY=false`).
- **Size: 1 lot**, taken only if fill × lot is within **₹10,000–30,000**; otherwise no trade (counted:
  below the band / above the band).

## Exits (v2 rules; each close from day +1, in this order)
1. call close ≤ 0.5 × entry premium;
2. 5 sessions or fewer before expiry;
3. 20 sessions since entry (the 5-session variant is reported alongside, with its own positions);
4. after a close ≥ 2 × entry premium, a close < 0.75 × the highest close since entry.
Exit fill: the call's close − 1 tick (not below 0; nothing is sold at 0).

## Costs
- Slippage per side, % of premium, by AMFI category point in time: large 1 %, mid 2 %, small 3 % (not found 3 %).
- Charges: `server/charges.py`, post-2026-04-01 schedule, on both orders.
- Risked = entry premium × quantity; net = (exit − entry) × quantity − charges − slippage.
- Corporate actions: a trade whose call leaves the bhavcopy, or whose future moves > 3 % differently from eod2's
  adjusted close, is excluded and counted.

## Diagnostic alongside (not a trade)
The same signals as a 1-lot stock future bought at the day +1 close and held 20 (and 5) sessions, eod2 adjusted
closes, net of 0.1 % round trip, % of notional (identical in definition to v4's).

## Report (`data/results/S1_v5_backtest_report.md`, trades `S1_v5_trades.csv`), test window only
The S1 v2 report format: 1 header (the test / holdout split, the constituent-history bias), 2 diagnostic (the
futures diagnostic), 3 main tables (per arm × exit variant, overall and 2021-22 / 2023-24: N, hit rate, mean and
median net return in % of premium and ₹, net per ₹1,000 risked, date-clustered t, 10th / 90th percentile, worst
5 %, exit-reason shares) and signals removed by each filter, 4 breakdowns by AMFI category and 20-day volatility
tercile, 5 slippage sensitivity (flat 1 / 2 / 3 %), 6 equity curve by exit month (arm A, 20-session exits) with
the maximum drawdown, 7 the gate per `DECISIONS.md` for arms A and B with 20-session exits. Numbers only.

## Known limits
- Sector membership and industry are today's lists applied to all dates (constituent-history bias).
- The futures diagnostic uses eod2 adjusted stock closes, not futures prices.
