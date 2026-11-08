# Drift-free FII / DII positions: pre-registered 2026-11-08 (before any normalised feature was computed)

**Why:** `EXTERNAL_RESULT.md` found no candidate, but raw position levels drift over the years, so cut-points set on the first two
years put most later days in one bucket. Here every position is compared with its OWN recent past, using only earlier sessions.
Same 638 signals, same outcome (`reach` = NIFTY kept falling >= 1 ATR5 from entry to the next close), same three periods and the same
rules and tests as `UNDERLYING_PREREG.md` / `EXTERNAL_PREREG.md`. Record-only; no live change.

## Features (16; each alone; computed from sessions BEFORE the signal day only)
Base series from the participant file (previous session close): FII index-futures net (long - short), FII index-futures long ratio,
FII option bearish net (put net - call net), DII index-futures net, Client index-futures net, Pro index-futures net.
- **z60** of each of the 6: (today's value - mean of the previous 60 sessions) / their standard deviation. (6)
- **pct250** of each of the 6: share of the previous 250 sessions with a lower value. (6)
- **Change z** (one-session change divided by the standard deviation of one-session changes over the previous 60 sessions) for FII futures net,
  FII option bearish net, DII futures net, Client futures net. (4)

## Rules and tests
Continuous: "high" >= discovery P67, "low" <= discovery P33 (the cut-points are in the normalised unit, so they do not drift).
One family of 32 rules; Benjamini-Hochberg 10 %; Fisher two-sided on `reach`. Candidate: q <= 0.10, bucket >= 25.
Validation (127): same direction, one-sided p < 0.05, bucket >= 20, effect >= half. Confirmation (263): same direction, one-sided p < 0.05.
**Passed = all three.** A pass gets: by-year and without-largest-3 %-of-F checks. Nothing is re-tuned. This is the last FII / DII form tried here.
