# S1 v8 · Any result in a strong sector, long calls (with the live rules as reference), on recent data

S1, version 8. **Pre-registered**: every choice is fixed here before any v8 run. Long options only.
Backtest: `python -m scanner.backtest_s1_v8`.

**Read this first: the window is the holdout.** DECISIONS.md kept 2025-01-01 onward untouched, to be evaluated once
for a version that passed the 2021-24 gate. On 2026-10-14 the user chose to run this version, and the current live
rules beside it, on **2025-04-01 → the last available session (Oct 2026)** instead, because 2021-24 has been looked
at for v2-v7 and their what-ifs. This run is that one look. After it, the only unseen evidence is the live paper
account from 2026-10-14.

**Why v8.** A stock-level check on 2021-24 (not a trade) found that in a **strong sector** the stock rose over the
next 20 sessions after **both** good results (beats: +3.7 %, t 4.2, N 139) and bad results (misses: +3.3 %, t 5.7,
N 192), while puts on misses would have lost. Taking calls on any result in a strong sector roughly doubles arm B's
signals, which is what arm B's low t needed. This idea was found on 2021-24; the recent window is its test.

## Signal
- A results filing (event store, type `results`, with its filing time). **Day 0** = the first full session after
  the filing timestamp (the filing day if filed before 09:15 on a session day, otherwise the next session).
- **AR0** = the stock's return P0 → day-0 close minus the leave-one-out equal-weight sector's return that session
  (`data/sector_map.csv`, ≥ 3 others per day; a stock without a sector: minus NIFTY 500).
- **Beat:** AR0 ≥ +2 % and the raw day-0 move < +10 %. **Miss:** AR0 ≤ −2 % and the raw day-0 move > −10 %.
- **Strong sector** (arm B's test, at the P0 close): the leave-one-out sector's 21- and 63-session returns exceed
  NIFTY 500's and its level is above its 50-session average. No sector: not strong.
- Not in the F&O ban list on day +1. One signal per stock and day 0; stocks with option contracts on day 0.
- One position per stock and arm; 10-session cooldown after an exit.

## Arms (each with its own positions)
| Arm | Signals | Role |
|---|---|---|
| `S` | beats **and misses** in a strong sector | **v8 primary** |
| `S_miss` | misses in a strong sector | side report: does the miss half carry its weight? |
| `A` | all beats | reference: the live paper rules, arm A |
| `B` | beats in a strong sector | reference: the live paper rules, arm B |

## Trade (every arm: the live paper rules, S1 v7 `old_expiry`)
- Expiry: the current monthly if ≥ 10 sessions remain after day 0, else the next monthly.
- Strike: from the call strike nearest day 0's underlying close (a tie: the lower) upward, the first with
  **≥ 50 contracts** on day +1, fill ≥ Rs 2 and **one lot at Rs 600-8,000**. Fill = the day's premium VWAP (else the
  close) + 1 tick. Size: 1 lot.
- Exits on each close from day +1, in order: **50 % stop** (close ≤ half the fill), **5 sessions without a new
  closing high**, **T-1**. Exit fill = close − 1 tick.
- Costs: slippage 1 / 2 / 3 % per side by AMFI category, `server/charges.py` charges on both orders; corporate-action
  check (call leaves the bhavcopy, or the future moves > 3 % differently from the stock): excluded and counted.

## Window
Day 0 from **2025-04-01**; a signal is taken only if day +1 + 20 sessions and its expiry's T-1 session fall on or
before the last session with stock closes, so every trade completes inside the data.

## Report (`data/results/S1_v8_backtest_report.md`, trades `S1_v8_trades.csv`, sheet `S1_v8_trade_sheet.xlsx`)
Per arm: N, hit rate, mean and median net % of premium and ₹, date-clustered t, 10th / 90th percentile, exit-reason
shares, and the two halves (2025 / 2026 by entry date); signals removed by each filter; breakdowns by strike distance
and sessions held; the futures diagnostic (the same signals as a stock position for 20 sessions, net of 0.1 %).
The DECISIONS.md gate (mean > 0, t ≥ 2, both halves positive, N ≥ 200) is shown per arm.

## What follows
- `S` passes → it becomes the candidate for the live paper account (the paper test is then the deciding evidence).
- `S` fails → closed and recorded; the live rules' reference numbers are recorded beside it.

## Known limits
- Sector membership and industry are today's lists applied to all dates.
- The strike walk reads day +1's whole-day volume and VWAP; exits use daily closes.
- F&O ban lists are back-filled from NSE's archive where the store had gaps (Nov 2025 – Aug 2026).
