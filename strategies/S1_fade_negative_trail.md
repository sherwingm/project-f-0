# S1 fade · "negative trailing" stops: step the stop down at −20 %, then trail or reset (backtest, realistic entry)

**Pre-registered 2026-10-21**, before these numbers are computed. The user: "trail in the opposite side: if it hits
−20 % then move the stop to −25 %", and chose to test all three versions offered. **Nothing live changes.**

## Data and mechanics
As `S1_fade_stop_trail_study.md`: the 409 realistic-entry trades (entry = 09:16 open + 1 tick), 1-minute candles from
09:17 to 15:19, real charges, train = before 2025-11-03 (189), test = from it (220). A stop or trail level hit in a
candle sells at min(level, the candle's open) − 1 tick; else the 15:19 close − 1 tick. "Peak" = the highest high of
the candles **before** the current one since the step-down candle.

## Variants
1. **Step down, then trail up (N1):** nothing sells above −20 %. The first candle whose low ≤ 0.80 × entry steps the
   stop to 0.75 × entry. From the next candle the level is max(0.75 × entry, 0.95 × peak).
2. **Ladder to a floor (N2-30, N2-35, N2-40):** each −5 % step moves the stop 5 % lower until the floor, where it sells.
   This equals a plain stop at the floor; reported so the three ideas sit side by side.
3. **Step down, reset at the buy price:** stop to 0.75 × entry at the −20 % touch; once a later candle's high ≥ entry,
   the stop moves to the entry price (break-even), and
   - **N3a:** then holds to 15:19 (stop stays at break-even);
   - **N3b:** then trails at max(entry, 0.95 × the highest high since).

## Test (fixed now)
Pick the variant with the highest train mean net % of premium; it passes only if on test its mean > 0 and its
per-trade difference to v11 is > 0 with date-clustered t ≥ 2. All six are reported with v11 and v10. The test half has
been looked at by two earlier exit studies, so a pass is weaker than a clean one.
