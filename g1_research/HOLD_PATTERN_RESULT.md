# Holding-pattern search: result (2026-11-07)
Rules: `HOLD_PATTERN_PREREG.md` (with Amendment 1). Scripts: `scripts/g1_hold_pattern.py` (first run, circular target),
`scripts/g1_hold_followup.py`, `scripts/g1_hold_pattern2.py` (corrected follow-up target). History only, in-sample.

- First run: 4 candidates, 3 "passed" validation, but all three use the gain made before the decision (circular):
  **Rejected (circular target)**. The only rule known at entry (shallow breakout depth) failed validation (p 0.14).
- Corrected run (the gain AFTER the decision, 92 rules, FDR 10 %): **0 candidates**. Best rules (q 0.14): a shallow
  breakout at entry (more follow-up) and high VIX (less follow-up); neither survives the correction.
- **Conclusion: no holding pattern found.** No feature known at entry, next 09:16 or next close separates the trades that
  keep rising from those that do not, once the already-made gain is removed from the target.

## Addendum: IV crush (Amendment 2, the user's remark)
- India VIX (proxy for implied volatility) matters a lot for where the put stands at the decision: with NIFTY lower than at
  entry, the put is +23 % (median +9 %) at next 09:16 if VIX fell, against +89 % (median +75 %) if VIX rose (G1-F).
- It does NOT predict the follow-up: VIX change entry → 09:16 and entry → close, high / low buckets, 4 rules in a family of
  96: q 0.70-1.00, no candidate. IV crush explains the gain already made, not the gain still to come.
- Scripts `g1_ivcrush_check.py`, `g1_ivcrush_rules.py`; data `data/g1_ivcrush_trades.csv`; results `results/g1_ivcrush_*.csv`.
