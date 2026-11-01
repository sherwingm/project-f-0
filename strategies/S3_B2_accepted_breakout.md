# S3 B2 · NIFTY opening-range breakout that holds ("accepted"), long ATM option

Pre-registered 2026-11-01, **before any B2 number was computed**. Buy only. Rules: DECISIONS.md "S3 · index options"
and "S3 · buy-only, tested on 2024 → today". Engine `scanner/s3_engine.py`. Idea (the user, 2026-11-01): find the edge
in Breakout + volume (B1) and take more trades.

## Why B2, and what is not independent
The B1 deep dive (`data/results/S3_B1_deep_dive_2026-11-01.md`, af902d48) found:
- NIFTY closed back inside the opening range on 435 of 488 breakout days, typically 5 minutes after the signal;
- the 2x volume test hardly filtered (495 → 488 trades);
- the 25 % trail armed on any profit and acted as a second stop (228 of 299 trail exits were losses).

B2 answers those three points: it waits for the breakout to hold, drops the volume test, and exits when the breakout
fails instead of on a trailing stop. **B2 was designed after seeing B1's results on 2024-10 → 2026-10**, so an option
test on that window is not out-of-sample. That is why stage A uses NIFTY spot from a window B1/P4 never used, and stage C
is forward.

## Signal on session d (all stages)
- **Opening range:** NIFTY 50 spot high and low of the 1-minute bars 09:15-09:29 (15 minutes).
- **Breakout:** a 1-minute spot close above the range high (→ call) or below the range low (→ put), 09:30 → 13:00.
- **Acceptance:** the next **15** one-minute closes all stay beyond that edge (≥ high for a call, ≤ low for a put).
  The breakout is then *accepted*; the signal minute is the 15th close.
- If a close comes back inside the range first, that breakout is void and the scan goes on (a later close beyond
  either edge starts a new breakout; one already accepted → no more scanning). The 15 closes may run past 13:00; an
  acceptance after 13:15 does not trade.
- No volume test. No VIX or weekday filter. One trade a day at most.

## Trade
- **Entry:** the minute after the signal minute. 1 lot of the ATM option (strike nearest the spot close at the signal
  minute), side as above; expiry as B1 (nearest weekly with at least one session left after d).
- **Exit**, the first of:
  1. **Breakout fails:** a 1-minute spot close back inside the range (below the high for a call, above the low for a
     put). Exit at the next minute's option close.
  2. **Stop:** option value −25 % of the premium paid (stage B / C only).
  3. **Time:** 15:15.
- No trailing stop and no target. Costs and lot as every S3 pod (slippage 0.5 %, 1 % before 09:30, from 15:00 or 2+
  strikes out; `server/charges.py`).

## Stage A · spot check, NIFTY 50, 2022-01-03 → 2024-09-30 (no option prices exist there)
Measure per trade: NIFTY's move in the trade's direction, entry-minute close → exit-minute close, in % (exits 1 and 3
only; the option stop cannot be priced on spot).

**Cost hurdle, fixed now:** on B1's 488 trades a 1 % NIFTY move in the trade's direction was worth about +81 % of the
premium, and the costs and time decay needed about +0.05 % to +0.06 % of NIFTY to break even (least squares of net %
on the spot move and hours held, computed 2026-11-01 from S3_B1_trades.csv). The hurdle is set at **+0.10 % a trade** to cover 2x
costs with margin.

**Stage A passes only if all hold:**
- at least 150 trades;
- mean directional move ≥ +0.10 %, and its t ≥ 2;
- each half positive (2022-01-03 → 2023-05-31, 2023-06-01 → 2024-09-30);
- both neighbours on acceptance (10 and 20 minutes) have mean > 0.

Also reported (no effect on the verdict): the same measure for B1's breakout (first breakout, no acceptance) on the
same days, so the effect of acceptance is visible; trades per year; calls vs puts; exits by reason.

**If stage A fails, B2 is closed** and stages B and C do not run.

## Stage B · option test, 2024-10-01 → 2026-10-28 (only if A passes; in-sample for the idea, labelled so)
The unchanged S3 gate on net % of the premium: ≥ 30 trades, mean > 0 and > 0 at 2x costs, t ≥ 2, each half positive,
worst trade smaller than the average month (₹), neighbours net positive.
**Neighbours (fixed):** acceptance 10 and 20 minutes; opening range 12 and 18 minutes; stop 20 % and 30 %.
A pass here is not a pass for B2: it only allows stage C.

## Stage C · forward, sessions from 2026-11-02 (only if A and B pass)
The same rules on each new session as the nightly recorder stores its option minutes; research only, run from this
repo, nothing on the live server. Verdict once **30 trades** exist, on the stage B gate (halves: first and second 15
trades). Only a stage C pass can be proposed to the user as a paper strategy; nothing is enabled automatically.

## Look-ahead
The range, the breakout and the acceptance use closes up to the signal minute; the fill is the next minute's close.
The failure exit uses the close of minute t and fills at t + 1. No parameter is picked from B2's results.

## Run order changed (the user, 2026-11-01, before any B2 number was computed)
The user: run the option test first, 2024-10 → 2025-09, then 2025-10 → present, then the 2022-24 spot check. So:
1. **Stage B runs first**, on 2024-10-01 → 2026-10-28; its two halves are exactly those two periods and are reported
   one after the other.
2. **Stage A runs after it, whatever B shows**, with its rules and hurdle unchanged. It stays the only window the idea
   has not seen.
3. **Verdict unchanged:** B2 goes to stage C only if both A and B pass. Nothing else in the rules changes.
