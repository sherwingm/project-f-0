# Score methods search: result (2026-11-08). Plan: SCORE_METHODS_PREREG.md. Script: scripts/g1_score_methods.py. Data: results/g1_score_methods.csv
10 methods, fitted on discovery (128 signals), read once on validation (131). Outcome: max up through the next close, no stop.

## Verdict: NONE passes. No score method here ranks max up in a way we can trust.
| Method | Validation rho | one-sided p | Walk-forward rho |
|---|---|---|---|
| M1 old checklist | +0.09 | 0.16 | +0.05 |
| M2 checklist, learned direction (A) | +0.16 | 0.034 | -0.04 |
| M3 same on set B (12 items) | +0.11 | 0.11 | +0.03 |
| M4 without EMA20 | +0.12 | 0.09 | 0.00 |
| M5 terciles | +0.11 | 0.10 | +0.04 |
| M6 rank average (A) | +0.11 | 0.11 | +0.05 |
| M7 rank average (B) | +0.07 | 0.23 | +0.07 |
| M8 rank, weighted | +0.07 | 0.22 | +0.05 |
| M9 logistic (B) | +0.13 | 0.07 | +0.08 |
| M10 random forest (B) | +0.10 | 0.12 | +0.10 |
The bar was p < 0.005 (10 methods) AND top third reaching +100 % more often than the bottom third. Nothing is close.

- Best method (M2) has p 0.034 on its own, but with 10 tries the chance of a best this big from pure noise is **0.126** (permutation).
- Walk-forward (fit on the past, score the next signal, 199 signals) is about zero for every method (-0.04 to +0.10).
- The random forest fits discovery very well (rho 0.53 in-sample) and gives 0.10 on validation: it memorised.
- Top third vs bottom third reaching +100 %: about equal for all methods (30-36 % vs 25-36 %).
- One thing leans the same way everywhere: the top third of the score has a higher median max up (about +56..70 % vs +33..44 %) and a better booked average (+5..+34 % vs -1..-23 %). It is consistent but small, not significant, and not a tested claim.
- M2 hiding checks: same sign in 2025 (+0.21) and 2026 (+0.18), G1-F +0.16, but without the 10 largest max-ups it falls to +0.09.

## What it means
With 259 history trades and about 10 entry-time facts, nothing separates big moves from small ones. The score stays a record. The live signals are the only clean test; a new score would need its own pre-registration, and a lead (like M2's direction) must repeat on live data first.
