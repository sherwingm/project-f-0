# FII / DII positions vs NIFTY's next-day direction and size, all sessions: pre-registered 2026-11-09 (before any outcome was joined)

**Why:** `EXTERNAL_RESULT.md` and `EXTERNAL2_RESULT.md` tested positions only on G1 breakout days (638 signals) and found no pattern; the
one faint, shrinking lead was the FII index-futures one-day change. This asks the wider question on EVERY session (about 1,240):
do FII / DII / Client / Pro positions at one close say anything about NIFTY's next day? Not G1-specific; record-only research.

## Rows and outcomes (fixed)
One row per session t from 2021-11 on: features = positions at the close of t (participant file of t); outcomes are for session t+1
(close of t to close of t+1; t+1 is the next date with spot bars), so everything is known before t+1 opens.
- **Direction:** `up` = NIFTY close(t+1) > close(t).
- **Size:** `big` = |close(t+1)/close(t) - 1| in the top third of discovery (cut from discovery; applied unchanged later). Shown with the mean |move|.

## Features: the 16 drift-free ones of `EXTERNAL2_PREREG.md`, computed from sessions up to and including t only
z60, pct250 and the change-z forms of FII futures net, FII long ratio, FII option bearish net, DII futures net, Client futures net,
Pro futures net (change-z for four of them).

## Periods (chronological)
Discovery 2021-11 to 2023-09-30; validation 2023-10-01 to 2024-09-30; confirmation 2024-10-01 to 2026-10-28.

## Rules and tests
Continuous: "high" >= discovery P67, "low" <= discovery P33, so 32 rules per outcome; one family of 64 (two outcomes), Benjamini-Hochberg 10 %
over all 64, Fisher exact two-sided in discovery. Candidate: q <= 0.10, bucket >= 40 sessions, either direction. Validation: same
direction, one-sided p < 0.05, bucket >= 30, effect (in points of probability) >= half. Confirmation: same direction, one-sided p < 0.05.
**Passed = all three.** A pass gets by-year checks and the same test on the 638 G1 days. Nothing is re-tuned; "no FII / DII link" is a valid answer and is
the last FII / DII question tried in this chat unless a pass appears.
