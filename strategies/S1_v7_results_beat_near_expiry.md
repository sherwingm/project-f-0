# S1 v7 · Results-beat continuation, long calls, near-expiry calls allowed, 5-session decay exit + 50 % stop — CLOSED

**Status: closed, failed the gate** (`DECISIONS.md`, 2026-10-13). Primary variant: arm A 258 trades, mean −17.3 %, t −1.52; arm B 84 trades, mean +31.8 %, t 1.07, N < 200. Near-expiry trades lost most (A −37.3 %, B −12.1 %); the 50 % stop closed 87–95 % of them within about 2 sessions. Report: `data/results/S1_v7_backtest_report.md`; per-trade sheet: `data/results/S1_v7_trade_sheet.xlsx`.

S1, version 7, under the gate in `DECISIONS.md`. **Pre-registered**: every choice is fixed here before any v7 run.
Long options only: every trade is a bought call; maximum loss = the premium paid.
Test window **2021-01-01 to 2024-12-31**; 2025-01-01 onward is the holdout, untouched unless the gate passes.
Backtest: `python -m scanner.backtest_s1_v7`.

**Read this first.** 2021-2024 has now been looked at for S1 v2-v6 and for what-ifs on v6's trades (a 50 % stop,
holding to T-2, the option's path after the exit). v7's choices were made after seeing those. A gate pass on the test
window is therefore only a first filter; the 2025+ holdout, run once, is the real test.

**What changes from v6:** the expiry, the strike for near-expiry trades, and the exits; the signal is v4's.
- v6 skipped the current monthly expiry when fewer than 10 sessions remained and bought next month's (dearer) call.
  v7 keeps the current monthly down to **3 sessions left**, with cheap lots (₹600–3,000) and a liquid strike
  (≥ 500 contracts on day +1).
- v6 sold after 3 sessions without a new closing high, at T-2 at the latest, no stop. v7 sells after **5** sessions
  without a new closing high, at **T-1** at the latest, and on a **50 % stop**.

## Signal (as v4 / v6)
- A results filing (event store, type `results`, with its filing time). **Day 0** = the first full session after
  the filing timestamp (the filing day if filed before 09:15 on a session day, otherwise the next session).
- **P0** = the close of the session before day 0. **AR0** = the stock's return P0 → day-0 close minus the
  leave-one-out equal-weight sector's return that session (the other stocks of its sector in
  `data/sector_map.csv`, ≥ 3 per day; a stock without a sector: minus NIFTY 500). Beat: **AR0 ≥ +2 %**.
- Skip if the day-0 raw move is **≥ +10 %**; skip if the stock is in the F&O ban list for day +1.
- One signal per stock and day 0; stocks with option contracts in day 0's bhavcopy only.
- **Arm A:** all beats. **Arm B:** beats where, at the P0 close, the leave-one-out sector's 21- and 63-session
  returns exceed NIFTY 500's and its level is above its 50-session average (no sector: not in B).
- One position per stock (per arm and variant); 10-session cooldown after an exit. No cap on positions open at once.
- **Holdout guard:** a signal is taken only if day +1 + 20 sessions and its expiry's T-1 session both fall on or
  before 2024-12-31, so no trade reads a holdout price.

## Expiry
n = sessions after day 0 up to and including the current monthly expiry (the last listed expiry of the month;
`scanner/backtest_cheap_options.sessions_to`).

| n | Expiry | Trade type |
|---|---|---|
| ≥ 10 | current monthly | normal |
| 3–9 | current monthly | **near-expiry** |
| < 3 | next monthly | normal |

## Strike walk and entry (day +1)
Start at the listed call strike nearest day 0's underlying close (a tie: the lower) and walk **upward**, one listed
strike of that expiry at a time. Take the **first** strike where, on day +1:

| | Normal trade (as v6) | Near-expiry trade |
|---|---|---|
| Contracts traded on day +1 (1 contract = 1 lot) | ≥ 50 | **≥ 500** |
| One lot (fill × lot size) | ₹600–8,000 | **₹600–3,000** |

and the fill is ≥ ₹2 per share (`ALLOW_LOTTERY=false`). Entry fill = the engine fill: the day's premium VWAP
(NSE notional turnover ÷ (contracts × lot) − strike) or, if unavailable, the close; + 1 tick (₹0.05).
Too thin or above the band: next strike up. Lot below ₹600 or fill below ₹2: stop, no trade (the strikes above are
cheaper still). No strike left: no trade. **Size: 1 lot.**

## Exits (each close from day +1, in this order)
1. **Stop:** the close ≤ 50 % of the entry fill → exit at that close.
2. **Decay:** best = the entry fill. At each close: if the close > best, best = the close and the stall count resets
   to 0; otherwise the stall count goes up by 1. Stall count = **5** → exit at that close.
3. **T-1:** the session before expiry (1 session to expiry) → exit at that close. Stock options are physically
   settled; nothing is held into expiry day.

Exit fill: the call's close − 1 tick (not below 0). A gap through the stop exits at the (lower) close.

## Costs (as v6)
- Slippage per side, % of premium, by AMFI category point in time: large 1 %, mid 2 %, small 3 % (not found 3 %).
- Charges: `server/charges.py`, post-2026-04-01 schedule, on both orders.
- Net = (exit − entry) × quantity − charges − slippage; % of premium = net ÷ (entry × quantity).
- Corporate actions: a trade whose call leaves the bhavcopy, or whose future moves > 3 % differently from eod2's
  adjusted close, is excluded and counted.

## Variants (each with its own positions)
| Variant | Change from primary | Role |
|---|---|---|
| `primary` | — | **the gate** |
| `near_c50` | near-expiry strikes need ≥ 50 contracts (not 500) | side report (liquidity) |
| `no_stop` | no 50 % stop | side report |
| `old_expiry` | v6's expiry rule (current monthly only if ≥ 10 sessions), so no near-expiry trades | side report: isolates the expiry change |

## Diagnostic alongside (not a trade)
The same signals as a 1-lot stock future bought at the day +1 close and held 20 (and 5) sessions, as v4 / v6.

## Report (`data/results/S1_v7_backtest_report.md`, trades `S1_v7_trades.csv`), test window only
v6's sections (header; futures diagnostic; main tables per arm × variant, overall and 2021-22 / 2023-24, with
exit-reason shares and the filter funnel; breakdowns; slippage sensitivity; equity curve; the gate per arm on
`primary`), plus a breakdown **near-expiry vs normal** trades. Per-trade sheet: `data/results/S1_v7_trade_sheet.xlsx`.
Numbers only.

## Gate
`DECISIONS.md`, unchanged, on `primary`, per arm: net mean > 0 after costs; date-clustered t ≥ 2; positive in both
2021-22 and 2023-24; N ≥ 200. Pass → the holdout once. Fail → closed, recorded, not re-tuned.

## Known limits
- Sector membership and industry are today's lists applied to all dates (constituent-history bias).
- The strike walk reads day +1's whole-day volume and VWAP, as the engine's liquidity check always has.
- Stop, decay and T-1 use daily closes; there is no intraday option history.
- The live paper engine still exits at T-2 and uses the ≥ 10-session expiry rule; it changes only if v7 passes the
  gate and the holdout.
