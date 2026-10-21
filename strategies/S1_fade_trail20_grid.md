# S1 fade · the −20 % stop plus a trailing stop, gaps and start levels from 2 % (backtest, realistic entry)

**Pre-registered 2026-10-21**, before these numbers are computed. The user, after `S1_fade_stop_trail_study.md` failed:
"try the 20 % trailing stop loss with the gap in different start from 2 % trailing". Read as: keep v11's −20 % touch stop
from 09:17, and add a trailing stop whose **start** (A, the gain that switches it on) and **gap** (D, how far below the
peak it sells) each run from 2 %. **Nothing live changes.**

## Grid (20 variants + v11)
- A (start) = 2, 5, 10, 20 % above entry; D (gap) = 2, 5, 10, 15, 20 % below the peak.
- Mechanics exactly as `S1_fade_stop_trail_study.md` (`scanner/fade_stop_trail.py` `walk`): entry B = 09:16 open + 1 tick;
  stop checked before the trail inside a candle; peak = highest high of earlier candles since activation; trail sells at
  min(level, candle open) − 1 tick; else 15:19 close − 1 tick; real charges.
- With 1-minute candles a 2 % gap is often hit by the noise inside one minute; the result is reported as it comes.

## Test (fixed now)
- Pick the variant with the highest train mean (day 0 before 2025-11-03); it passes only if on test its mean > 0 and its
  per-trade difference to v11 is > 0 with date-clustered t ≥ 2.
- **Caveat stated now:** the test half is not fully fresh. The earlier study showed test results for trails with
  gaps 15 / 20 / 30 % (the best, "no stop + trail A0 D15", +3.9 % on test, t 0.84 vs v11). This grid overlaps that
  family, so a pass here is weaker evidence than a clean out-of-sample pass.
