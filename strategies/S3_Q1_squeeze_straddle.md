# S3 Q1 · NIFTY long ATM straddle after a quiet spell (squeeze)

Pre-registered 2026-10-30, **before any Q1 option return was computed**. Buy only. Rules: DECISIONS.md "S3 · index
options" and "S3 · buy-only, tested on 2024 → today". Engine: `scanner/s3_engine.py`; runner `scanner/s3_buy4.py`.
Idea (the user, 2026-10-30): buy a straddle after several very quiet days (narrow range, low VIX), when options are
cheap, because calm spells tend to end in a sharp move.

## Window
2024-10-01 → 2026-10-28. Halves: 2024-10-01 → 2025-09-30 and 2025-10-01 → 2026-10-28.

## Signal on session d (known by 14:45 on d)
Daily bars come from the 1-minute NIFTY 50 spot (`scanner/s3_regime.daily`, sessions with ≥ 60 bars).
- **Range %** of a session = (high − low) ÷ close × 100.
- **Quiet:** the mean range % of the **5** sessions ending at d − 1 is at or below the **20th percentile** of that same
  5-session mean over the 250 sessions ending at d − 2 (at least 200 needed).
- **Low VIX:** India VIX's last 1-minute close at or before 14:44 on d is at or below the median of the 60 previous
  sessions' VIX closes (d − 60 … d − 1).
- Both must hold.

## Trade (primary)
- **Entry:** 14:45 on d. Buy 1 lot each of the ATM call and put (strike nearest the 14:45 spot).
- **Expiry:** the nearest NIFTY expiry strictly after the exit session, with chain files on the entry and exit
  sessions.
- **Exit:** 14:45 on the **3rd** session after d. No stop, no target.
- **One position at a time:** a signal before the exit session is ignored; the next trade can start on a session
  after the exit session.
- Costs and lot as in every S3 pod (engine fills, `server/charges.py`, bhavcopy lot).

**Count before the run** (spot and VIX only, no option prices): 124 quiet sessions in the window; 105 with the VIX
rule; about 42 non-overlapping 3-session trades.

## Gate (unchanged S3 gate)
At least 30 trades; net mean % of the premium paid > 0 and > 0 at 2× costs; t ≥ 2; positive in each half; worst trade
smaller than the average month (₹); neighbours net positive.

**Neighbours (fixed):** percentile 16 and 24 (20 ± 20 %); lookback 4 and 6 sessions; hold 2 and 4 sessions.

## Also reported (no effect on the verdict)
- **Baseline:** the same 3-session straddle entered every 4th session with no filter (back-to-back, non-overlapping).
- Every trade, and the skipped signals with the reason.

## Look-ahead
The range rule uses sessions up to d − 1; the percentile uses sessions up to d − 2; VIX uses d's own minutes up to
14:44 and earlier sessions' closes; entry is at 14:45. No parameter is picked from Q1's results.
