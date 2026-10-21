# S1 v12 fade · the −20 % stop plus a 2 % trailing stop (live paper rule from 2026-10-22)

**Decided 2026-10-21 by the user:** "make the Trail (−20 % stop, trail on at +10 %, gap 2 %) as v12 and make it live".
Paper only, 1 lot each, as before. **Only the exit changes**; the entry is v10's (unchanged).

## The rule
- **Entry:** unchanged (strategies/S1_v10_results_day_fade_paper.md): from 09:15, the walk's strike at the live ask.
- **Exit, on the entry day, on the best bid at each poll (about every 30 s):**
  1. **Stop:** from 09:16, the first bid ≤ 0.80 × entry sells at that bid (as v11).
  2. **Trail:** from 09:16, the first bid ≥ 1.10 × entry switches the trail on; peak = the highest bid since. Once on,
     the first bid ≤ 0.98 × peak sells at that bid (`fade_trail`). (Once on, the trail level ≥ 1.078 × entry is above
     the stop, so the trail always acts first.)
  3. Else the first poll from 15:20, at the best bid (as v10 / v11).
- Applies to fade positions bought from the deploy on 2026-10-21 evening (first trades 2026-10-22). Positions are
  tagged `rule.version = "v12"`.

## Shadows kept on every v12 trade (no orders)
- `shadow_v11`: the −20 % stop alone (else 15:20). Same as real unless the trail sold; then tracked after the sale on
  the same bids (its stop, else the 15:20 bid).
- `shadow_v10`: held to 15:20 (for a trade sold early, the 15:20 bid).
- `shadow_trail`: the 5 % gap version (strategies/S1_v11_trail_shadow_track.md), tracked after a 2 % trail sale the
  same way.

## Evidence and its limits (stated at the decision)
- Backtest, realistic entry, Jan 2025 – Aug 2026, 362 trades: v12 +3.25 % a trade (t 2.18, win 56.9 %, +₹83,687) vs v11
  +0.23 % (t 0.10) and v10 +1.31 % (t 0.39). In both 2025 and 2026 it was the best of the three.
- **Not proven better than v11** (difference +3.0 points, t 1.55). The 2 % gap was chosen after seeing results on part
  of the same data. The backtest sells on 1-minute traded prices; live sells at the bid every ~30 s, and the bid–ask
  spread of cheap options is often 2–5 %, so live results may be clearly worse than the backtest.

## Review
At 30 closed v12 trades: real v12 vs shadow v11 and shadow v10 (closed, wins, mean net %, total ₹, t of the
difference). If v12 is not ahead of v11, the user decides whether to go back.
