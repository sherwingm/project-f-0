# Holding-pattern search, pre-registered 2026-11-07 (before any feature statistic was computed)

**Question (the user):** is there a strong pattern in which G1 / G1-F trades keep going up after entry, so that we know
which ones are worth holding? Measure: **max up** (no exit, no stop) as the default: share reaching +100 %, mean and
median, then the booked result as a side line.

## Data and split
- The 259 G1 history trades (`data/results/S3_G1_datasheet.csv`) joined with `g1_research/data/g1_hold_days_trades.csv`
  (peaks and booked results by hold length). G1-F is a subset (the three skip filters).
- **Discovery:** entry day before 2025-10-01 (about 128 trades). **Validation:** from 2025-10-01 (about 131). All
  thresholds come from discovery only. No other data is used; there is no untouched third period, so a rule that passes
  is "passed validation", not "validated", and the forward paper run is the real test.

## Target (fixed)
`reach` = the put's highest later minute close through the close of day h = min(days to expiry, 3) after entry is
**≥ +100 %** above the price paid (peak with no stop, no exit). Shown alongside: mean and median of that peak.

## Decision times (a feature is used only if known by then; only trades still alive, i.e. not stopped yet, count)
| Time | Features (all from the datasheet / hold file) |
|---|---|
| D1 entry | days to expiry, minutes after 09:30, OR width %, breakout depth %, day-1 gap %, day-1 open → entry %, previous day return %, previous 5-day return %, close vs EMA20 %, VIX at signal, VIX change since open, premium % of spot |
| D2 next 09:16 (adds) | day-1 entry → 15:15 %, day-1 15:15 vs OR low %, next-day gap %, the put's booked % at next 09:16 |
| D3 next close (adds) | the put's booked % at the next close, next-day open → 15:15 % |

## Rules (fixed): one feature at a time, no combinations
For each feature, two buckets: **high** = at or above the discovery 67th percentile, **low** = at or below the discovery
33rd percentile. A bucket is a rule. One family: every rule of every decision time (about 36).

## Procedure
1. Discovery: for each rule, reach rate in the bucket vs outside it (Fisher exact, two-sided); Benjamini-Hochberg at FDR
   10 % across the whole family. A candidate needs q ≤ 0.10, at least 25 trades in the bucket and a higher reach rate.
2. Freeze the candidates (file written before validation is touched).
3. Validation, once: same direction, one-sided Fisher p < 0.05, at least 20 trades, and an effect at least half the
   discovery effect.
4. Robustness of any rule that passes: by year, and the G1-F subset.
5. Nothing is re-tuned after seeing validation. A rule that fails is Rejected.

## Labels
Observed / Suggestive (BH-significant in discovery) / Passed validation / Rejected / Untestable (n too small).

## Amendment 1, written 2026-11-07 after the first run and before the corrected one (honest record)
The first run (`g1_hold_pattern.py`) froze 4 candidates; 3 of them passed validation. They are all **circular**: for the
next-09:16 and next-close decisions, the target ("peak through day h from entry reaches +100 %") already contains the gain
made BEFORE the decision, so "the put is already up" predicts it mechanically (examples: the put's booked % at 09:16,
NIFTY's move after entry that day). The one rule known at entry (shallow breakout depth) failed validation (p 0.14).
Those 3 passes are not evidence of a holding pattern and are labelled **Rejected (circular target)**.

**Corrected target = the follow-up:** after the decision time, the put's highest later minute close through the close of
day h = min(days to expiry, 3) is **≥ +50 % above the put's price at the decision time** (so only the gain still to come
counts). Decisions: D1 entry (the target is unchanged, no overlap), D2 next 09:16, D3 next close (needs days to expiry
≥ 2, otherwise there is no time left). Same split, features, buckets, FDR 10 % (one family over all three targets),
candidate and validation rules as above, nothing else changed. A result of "no pattern" is a valid result.
