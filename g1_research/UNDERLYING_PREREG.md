# G1 follow-through on NIFTY's own move, five years of signals: pre-registered 2026-11-08 (before any outcome was computed)

**Why:** 259 option trades are too few (the score, formation and hold-pattern searches all found nothing). NIFTY 1-minute spot exists
from 2021-10-20 (about 1,240 sessions; correction to my "8 years": it is 5 years), so the same G1 breakout can be found on about
2.5x as many days. The put's max up is mostly the underlying's move; so test the move first, then confirm on the option trades.
Record-only research; nothing changes live.

## Signal (the G1 rule, on spot only)
Opening range 09:15-09:29; the first 1-minute close outside it from 09:30 to 13:00; only a close BELOW the low counts
(`scanner.s3_b2.signal(day, 15, None)`). Entry = the close of the minute after the signal minute (G1's entry minute), at NIFTY spot.

## Outcomes (fixed)
Unit: ATR5 = mean (high - low) of the 5 sessions before the signal day, in index points.
- **F (primary)** = (entry spot - lowest low from the entry minute to the next session's 15:29) / ATR5: how far NIFTY kept falling, the
  spot twin of a put's max up. `reach` = **F >= 1.0**. Also shown: share F >= 0.5 / 1.0 / 2.0, mean and median F.
- **N (booked-like)** = (entry spot - next session's 15:29 close) / ATR5, positive = the put side gained.
- The next session = the next date that has spot bars. A signal with no next session is dropped.

## Q0: is there follow-through at all? (before any pattern)
Mean N of the signals vs the mean N of the SAME entry minute-of-day on all sessions (the drift baseline); two-sided Welch t and a
permutation check. Also F of the signals vs F of the baseline. Reported for the whole 5 years and each year. A plain
"G1 has no follow-through beyond drift" is a valid answer.

## Periods (chronological, three, none overlapping)
- **Discovery:** signal day 2021-10-20 -> 2023-09-30 (cut-points, rule choice).
- **Validation:** 2023-10-01 -> 2024-09-30 (read once).
- **Confirmation:** 2024-10-01 -> 2026-10-28 (the 259 G1 option trades; used for nothing before this step except being the data of
  the earlier searches, never for choosing a rule here). Read once, with F and also the put's max up >= +100 %.

## Features (each alone, no combinations; 40)
- The 28 formation facts of `FORMATION_PREREG.md` (computed on the same definitions).
- 10 entry facts: breakout depth, minutes after 09:30, OR width, day-1 gap, VIX at the signal, VIX change since open, prev-day return,
  prev 5-day return, close vs EMA20, ADX14 of the prior day.
- 2 regime facts: VIX at the signal vs its 250-session range (percentile), and ATR5 / ATR20 (is range expanding).

## Rules and tests (fixed)
Continuous: "high" >= discovery P67, "low" <= discovery P33; 0/1: "= 1". One family, Benjamini-Hochberg 10 % over all rules, Fisher
exact two-sided on `reach` (F >= 1) in discovery. Candidate: q <= 0.10, bucket >= 25 signals, either direction.
Validation: same direction, one-sided p < 0.05, bucket >= 20, effect >= half the discovery effect. Confirmation: same direction,
one-sided p < 0.05 on F-reach (and the put's max up >= +100 % shown). **Passed = all three.** Hiding checks on a pass: by year,
without the largest 3 % of F, G1-F days only.
No re-tuning. Nothing passing = "no pattern even with five years".
