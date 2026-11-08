# Score methods search, pre-registered 2026-11-08 (before any method was computed)

**Question (the user):** "try the various methods of calculating the score and find which one shows a result related to it."
Record-only score; nothing here changes a live rule. Same 259 history signals, same split as before:
discovery = entry day before 2025-10-01 (128), validation = from 2025-10-01 (131). Everything is fitted / chosen on
discovery only; validation is read once.

**Outcome:** max up through the next close, no stop (`peak_k1`). Primary measure: Spearman(score, peak_k1). Also shown:
share reaching +100 % in the top third vs the bottom third of the score (thirds cut at discovery cut-points), mean and
median max up per third, then the booked result.

## Feature sets (all known at entry)
- **A (7, the old checklist items):** depth, minutes after 09:30, OR width, day-1 gap, VIX, prev 5-day return, close vs EMA20.
- **B (12):** A + days to expiry, day-1 open to entry %, prev day return %, VIX change since open, premium % of spot.

## Methods (the whole family: 10; no method is added after the numbers)
| # | Method | Fitted on discovery |
|---|---|---|
| M1 | Old checklist (logic directions, medians), set A | thresholds only |
| M2 | Checklist, direction learned: sign of the discovery Spearman of each item with max up, median cut, set A | direction + cut |
| M3 | Same as M2 on set B | direction + cut |
| M4 | Checklist M2 with the overlap removed (drop EMA20, keeps prev 5-day), set A minus 1 | direction + cut |
| M5 | Terciles: +1 if item in its best discovery third, 0 middle, -1 worst third (direction learned), set A | direction + cuts |
| M6 | Percentile-rank average: each item ranked against the discovery spread (direction learned), mean rank, set A | direction + ranks |
| M7 | Same as M6 on set B | direction + ranks |
| M8 | Rank-weighted: M6 with weights = discovery |Spearman| of each item, set A | direction + weights |
| M9 | Logistic regression (L2, C=0.1, standardised) on "max up >= +100 %", set B; score = predicted probability | model |
| M10 | Random forest (200 trees, depth 3, min leaf 10) on "max up >= +100 %", set B | model |

## Judging
1. **Works** = validation Spearman > 0 with one-sided p < 0.05 / 10 = **0.005** (Bonferroni over the 10 methods), AND top-third
   reach rate above bottom-third in validation. Anything else is not a proven score. A method that is only "best on validation" is
   a selection, not a finding.
2. **Selection check:** the best validation rho of the 10 is compared with a permutation null (shuffle the validation max-up
   values 5,000 times, take the best rho of the 10 methods each time): p = the share of shuffles whose best is >= the observed best.
3. **Walk-forward:** for the model methods (M9, M10) and the learned-direction ones, also fit on all earlier signals and score each
   later signal in time order (from the 60th signal on), and report the Spearman over all those out-of-time scores.
4. **Hiding checks** on any method that passes: by year, G1-F only, without the 10 largest max-ups.
5. No re-tuning after the numbers. If nothing passes, the answer is "no score method here ranks max up"; the score stays a record.
