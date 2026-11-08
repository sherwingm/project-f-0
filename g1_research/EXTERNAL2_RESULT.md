# Drift-free FII / DII positions: result (2026-11-08). Plan: EXTERNAL2_PREREG.md. Script: scripts/g1_external2.py
Each position compared with its own recent past (z-score over 60 sessions, rank over 250, one-day change scaled). 16 features, 32 rules, 528 of 638 signals have every feature (the first year lacks the 250-session history).

**Result: one candidate, and it did not hold. Nothing passed.**
- Candidate: FII index-futures one-day change, falling (FII cutting longs / adding shorts): discovery 41 % vs 22 % reached >= 1 ATR (q 0.08).
- Validation: 35 % vs 28 % (p 0.28, fails the bar of 0.05 and half the effect). Confirmation: 37 % vs 37 % (no effect).
- The mirror rule (FII adding longs) did worse in discovery and was not a candidate. Every other rule: q >= 0.18.
- Together with `EXTERNAL_RESULT.md`: no FII / DII positioning form, raw or drift-free, predicts G1 follow-through. Last FII / DII form tried here.
