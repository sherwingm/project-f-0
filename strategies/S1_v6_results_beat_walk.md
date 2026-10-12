# S1 v6 · Results-beat continuation, long calls, ₹600–8,000 per lot, strike walk, decay exit

S1, version 6, under the gate in `DECISIONS.md`. **Pre-registered**: every choice is fixed here before any v6 run.
Long options only: every trade is a bought call; maximum loss = the premium paid.
Test window **2021-01-01 to 2024-12-31**; 2025-01-01 onward is the holdout, untouched unless the gate passes.
Backtest: `python -m scanner.backtest_s1_v6`.

**What changes from v5:** the strike, the size and the exits; the signal is v4's.
- v4 bought the at-the-money call inside ₹2,000–8,000 and kept 3 trades; v5 bought it inside ₹10,000–30,000 and
  kept 57. v6 keeps **one lot at ₹600–8,000** and, when the at-the-money call is too expensive or too thin,
  **walks up to the next strike**.
- No stop-loss, no 20-session limit, no trailing exit: the call is held while it keeps making new highs and sold
  when it **decays** (no new high for 3 sessions), or at T-2 at the latest.

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
- One position per stock (per arm and variant); 10-session cooldown after an exit. No cap on the number of
  positions open at once across stocks (the paper account's 3-position limit is not simulated).
- **Holdout guard:** a signal is taken only if day +1 + 20 sessions and its expiry's T-2 session both fall on or
  before 2024-12-31, so no trade reads a holdout price.

## Expiry
The engine rule (`scanner/option_engine.py`): the current monthly expiry if ≥ 10 sessions remain after day 0, else
the next monthly.

## Strike walk and entry (day +1)
Start at the listed call strike nearest day 0's underlying close (a tie: the lower) and walk **upward**, one listed
strike of that expiry at a time. Take the **first** strike where, on day +1:
1. the call traded **≥ 50 contracts** (1 contract = 1 lot). Entry fill = the engine fill: the day's premium VWAP
   (NSE notional turnover ÷ (contracts × lot) − strike) or, if unavailable, the close; + 1 tick (₹0.05);
2. the fill is **≥ ₹2** per share (`ALLOW_LOTTERY=false`);
3. fill × lot is **within ₹600–8,000**.

A strike that trades < 50 contracts or costs more than ₹8,000 per lot: go to the next strike up. A strike whose
lot costs less than ₹600 or whose fill is below ₹2: stop, no trade (the strikes above are cheaper still). No
strike left: no trade. There is no cap on how far above spot the walk may go; the report shows the distance.

**Size: 1 lot.**

## Exits (each close from day +1, in this order)
1. **Decay:** best = the entry fill. At each close: if the close > best, best = the close and the stall count
   resets to 0; otherwise the stall count goes up by 1. Stall count = **3** → exit at that close.
2. **T-2:** the second session before expiry (2 sessions to expiry) → exit at that close. Stock options are
   physically settled; the paper engine never holds to expiry either (`server/paper.py`).

Exit fill: the call's close − 1 tick (not below 0; nothing is sold at 0).

## Costs
- Slippage per side, % of premium, by AMFI category point in time: large 1 %, mid 2 %, small 3 % (not found 3 %).
- Charges: `server/charges.py`, post-2026-04-01 schedule, on both orders.
- Risked = entry premium × quantity; net = (exit − entry) × quantity − charges − slippage.
- Corporate actions: a trade whose call leaves the bhavcopy, or whose future moves > 3 % differently from eod2's
  adjusted close, is excluded and counted.

## Variants (each with its own positions)
| Variant | Decay sessions | Min contracts on day +1 | Role |
|---|---|---|---|
| `d3_c50` | 3 | 50 | **primary: the gate** |
| `d5_c50` | 5 | 50 | side report |
| `d3_c20` | 3 | 20 | side report (liquidity) |

## Diagnostic alongside (not a trade)
The same signals as a 1-lot stock future bought at the day +1 close and held 20 (and 5) sessions, eod2 adjusted
closes, net of 0.1 % round trip, % of notional (identical in definition to v4's).

## Report (`data/results/S1_v6_backtest_report.md`, trades `S1_v6_trades.csv`), test window only
1 header (the test / holdout split, the constituent-history bias); 2 the futures diagnostic; 3 main tables per arm ×
variant, overall and 2021-22 / 2023-24 (N, hit rate, mean and median net return in % of premium and ₹, net per
₹1,000 risked, date-clustered t, 10th / 90th percentile, worst 5 %, exit-reason shares) and signals removed by
each filter; 4 breakdowns by AMFI category, 20-day volatility tercile, strike distance above spot (0–2 %, 2–5 %,
5–10 %, > 10 %) and sessions held; 5 slippage sensitivity (flat 1 / 2 / 3 %); 6 equity curve by exit month (arm A,
primary) with the maximum drawdown; 7 the gate per `DECISIONS.md` for arms A and B on the primary variant.
Numbers only.

## Known limits
- Sector membership and industry are today's lists applied to all dates (constituent-history bias).
- The strike walk reads day +1's whole-day volume and VWAP, as the engine's liquidity check always has.
- The futures diagnostic uses eod2 adjusted stock closes, not futures prices.
