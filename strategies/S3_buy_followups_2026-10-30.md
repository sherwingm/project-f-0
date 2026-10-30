# S3 buy pods · follow-ups after the 2026-10-30 run (data fix re-run, SENSEX replication, gap-up check, max up)

Pre-registered 2026-10-30, **after the first E1 / Q1 / B1 / G1 results (all FAIL, DECISIONS 6a314203) and before any
number below is computed**. Buy only (DECISIONS "S3 · buy-only"). The user: "Do all the things" (after the four
results), "don't ask any of the permission". Nothing here can enable a strategy in the live system; a pass only opens a
paper-trading proposal for the user to decide.

## Why
1. **The spot store was wrong** at 09:15 and missed the two Budget sessions (`data/results/s3_spot_repair_2026-10-30.md`,
   data commit 62a23257). The four pods and P4 (the closed opening-range pod) read the 09:15 bar or those sessions.
2. **One market only.** Every NIFTY result can be checked on SENSEX, which has its own option chain in the store
   (2024-10 → 2026-11 expiries), as R1 did for the expiry pods.
3. **G1's side split** (seen after the run): calls +12.0 %, puts −13.8 % of the premium (about 17 trades each). It is
   a hint, not a result. It needs data G1 never saw.
4. **Max up** is how the user reads trades (memory: "max up is the real measure"): how high each bought option went.

## F1 · Data-fix re-run (NIFTY, rules and code unchanged)
- `scanner/s3_buy4.py` at 36fbbfc6 (the code that produced the first results), the four pre-registered pages
  unchanged, the same window, halves and gate, on store 62a23257. The reports and trade files are overwritten; the
  first numbers stay in git (e96073da) and in DECISIONS.
- **P4** (`scanner/s3_p4.py`, its page and its test window 2024-10 → 2025-09 only) is re-run the same way.
- **Verdict rule:** the S3 gate as before. A pod that now passes is **not** promoted: its holdout is used up, so it
  would only go to the user as a paper-trading proposal. Old → new numbers for every pod go to DECISIONS.
- Expected change: E1 gains the two Budget events (2025-02-01, 2026-02-01) → up to 31 trades; G1 89 gaps instead of
  90; B1 / P4 opening ranges widen on most days.

## F2 · R2, the SENSEX replication of E1 / Q1 / B1 / G1
Each pod exactly as its page, with these substitutions only:
- **Underlying:** SENSEX options (`options_1m/SENSEX`), SENSEX spot (`spot_1m/SENSEX`) for the ATM strike, the daily
  bars (`s3_regime.daily("SENSEX")`), the gap, the opening range and the session list. Strike step 100.
- **Expiries:** the SENSEX expiries in the store, chosen by the same rules (E1 / Q1: the nearest expiry strictly
  after the exit session with chain files on the entry and exit sessions; B1 / G1: the nearest expiry with at least
  one session left after d, on an expiry day the next one).
- **Lot:** fixed at 20, as R1 (the store has no SENSEX lot history; % of the premium is lot-free apart from fixed
  fees). Fees from `server/charges.py` as for NIFTY (BSE's own exchange fee differs slightly; noted, not modelled).
- **Unchanged:** event dates (RBI, Budget, FOMC → next session, US election), India VIX for Q1's low-VIX rule and the
  reported VIX, the window 2024-10-01 → 2026-10-28, halves, neighbours, baselines, the gate.
- **Reading:** a SENSEX pass of a pod that failed on NIFTY is "SENSEX only, not confirmed" (NIFTY and SENSEX move
  together, so a real effect should show on both). Expected: all four fail.
- Count before the run (spot only): SENSEX has 102 sessions with |gap| ≥ 0.5 % in the window, 38 confirmed (21 up,
  17 down); 109 SENSEX expiries 2024-10-04 → 2026-11-05.

## F3 · The gap-up hint (G1 calls only), checked where G1 never looked
**F3a · NIFTY spot, 2022-01-03 → 2024-09-30** (no option minutes exist then; the repaired store has NSE's official
opens from 2022-01). G1's primary signal (gap ≥ 0.5 % vs the previous session's last close, confirmed by the 09:29
close, entry minute 09:30). For each signal, in % of the spot and signed in the gap's direction, from the 09:30 close:
- **follow-through** to the 15:15 close (G1's time exit);
- the **max favourable** and **max adverse** moves 09:31-15:15 (bar highs / lows).
Baseline: every session's 09:30 → 15:15 move in the same window (unsigned drift, used as the long-side baseline).
Count before the run: 74 confirmed signals, **45 up**, 29 down (163 gaps ≥ 0.5 %).
**The hint is supported only if all hold:**
1. up-gap follow-through mean > 0 with t ≥ 2;
2. it beats the all-session 09:30 → 15:15 mean (Welch t ≥ 2) — so it is not just the 2022-24 uptrend;
3. it beats the down-gap follow-through mean (Welch t ≥ 2);
4. positive in both halves (2022-01-03 → 2023-05-31, 2023-06-01 → 2024-09-30).
Spot moves cannot price an option (premium, decay, costs), so even a pass is not a trading rule: it would only make a
forward paper test worth proposing to the user.
**F3b · SENSEX options, the R2 G1 primary trades on up gaps only** (calls). Descriptive (about 21 trades, below the
30 the gate needs): mean, median, win rate, t.

## F4 · Max up (descriptive, no verdict)
For every primary trade of the F1 re-run (E1, Q1, B1, G1 on NIFTY): the highest combined value of the bought legs
after entry, as % above the entry fill paid (gross, no exit costs):
- **while held:** minutes after the entry minute up to the exit minute;
- **any time:** up to 15:29 of the exit session (what was there to take, had the exit been different).
Marks as the engine: each leg's last traded 1-minute close carried forward; a minute where any leg's mark is older than
the engine's stale limit is not counted. Reported like the results page's Max up panel: trades reaching +10 / +20 /
+50 / +100 %, the median, and the booked result next to it. A finding here cannot change a verdict; picking an exit
from it would be fitting on seen data.

## Look-ahead
F1 and F2 reuse the pages' look-ahead rules. F3a uses bars up to 09:29 for the signal, the 09:30 close as entry and
later bars only for outcomes. F4 is descriptive. No parameter is chosen from any result.
