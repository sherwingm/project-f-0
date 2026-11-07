# Breakout score for G1 signals, pre-registered 2026-11-07 (before any score or outcome statistic was computed)

**Purpose (the user):** every G1 signal gets a score at entry. **Record only: the score changes no rule** (no filter, no
size). It is judged later by **max up** (no exit, no stop) split by score band, then the booked result.

## The score (0 to 7)
One point per item, all known at the entry minute (no look-ahead). Direction of each item is fixed here by market
logic, NOT by looking at outcomes. Thresholds = the median of the discovery period (entry day before 2025-10-01),
frozen in `g1_research/results/score_thresholds.csv` the first time the script runs and never re-fitted.

| # | Item | Point if | Why (logic) |
|---|---|---|---|
| 1 | Breakout depth at signal % | >= median | a clear break, not a touch |
| 2 | Minutes after 09:30 | <= median | an early break has the whole day |
| 3 | OR width % | <= median | a narrow range is a coiled range |
| 4 | Day-1 gap % | <= median | gap down agrees with a put |
| 5 | VIX at signal | < 17 | the G1-F rule: puts not already dear |
| 6 | Prev 5-day return % | <= median | a falling market before the break |
| 7 | Prev close vs EMA20 % | <= median | below its trend |

- **Score %** = points / 7 x 100.
- **Percentile** = the share of earlier signals with a lower score (ties count half). In history it uses only signals
  BEFORE the day (expanding, no look-ahead); live it uses all history plus the live signals so far (it keeps accumulating).
- **Accumulating %** = the running average of score % over all signals so far (shown next to each new one).
- Every signal is scored, including those G1-F skips. Missing input = that item scores 0 and is flagged.

## Check on the 259 history signals (this document is the plan; nothing is changed after seeing it)
Outcome (primary): **max up through the next close** (`peak_k1`: the put's highest later minute close, no stop), report
the share >= +50 / +100 / +200 %, mean, median, then the booked result (next-close exit, 50 % stop).
Bands: low 0-2, mid 3-4, high 5-7 (fixed now).
1. **Does it work?** Spearman score vs max up, in discovery and in validation (from 2025-10-01); high vs low band, one-sided
   Fisher on "max up >= +100 %" in validation; works only if validation shows the same direction, p < 0.05 and at least
   half of the discovery gap. Labels: Observed / Passed validation / Rejected. A "does not predict" result is valid.
2. **Is anything hiding?**
   a. Each item on its own (drop-one score) and each item's own link to max up: does one item do all the work or
      work against the rest.
   b. Items overlapping (correlation matrix): is it really 7 views or 3.
   c. By year, and the G1-F subset only.
   d. Without the 10 biggest max-up trades.
   e. Circularity: no item may use data after entry (checked by listing each column's time).
   f. Expanding percentile vs full-history percentile give the same bands (no look-ahead leak).
3. No re-tuning after seeing results. A weak or empty result stays as is; the score stays a record.
