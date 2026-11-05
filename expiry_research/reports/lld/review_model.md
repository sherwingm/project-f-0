# LLD: review_model (Agent 5b, skeptical review of module `model`)

Written before the review code. Reads only scripts/panel_io.load_panel (NIFTY, BANKNIFTY; t <= 2024-06-30) plus
the `model` module's own files (scripts/model_*.py, results/model/*) for review. Writes only results/review_model/.

Script: scripts/review_model_check.py (single run, deterministic seed 20261105).

1. Independent rebuild (no import of model_common): target session s = y_date; split by y_date
   (discovery <= 2022-12-31, validation 2023-01-01..2024-06-30); rows with cal_special_between dropped;
   D2 features = previous panel row (checked that the previous row is the previous trading session);
   T1515 rows need f1515_ret_to_1514. Derived d_opt_near_straddle_daily = f_opt_near_straddle_pct / sqrt(max(dte,1)).
2. For every frozen candidate labelled Passed-validation or Suggestive: recompute discovery and validation n, rate,
   base (same rows, rule features present), effect, p (binomial / t, as written), and the pass rule.
3. Leakage checks: feature availability by prefix vs cutoff; D0 context at D2 (was s already the listed near
   expiry in the bhavcopy of t-1?); thresholds equal discovery quantiles (no validation data).
4. Freeze checks: SHA-256 of candidates_frozen.csv vs recorded; mtimes frozen < validation; 241 ids identical.
5. Family: hypotheses.csv counts vs tests the scripts run.
6. Serial-correlation check: circular-shift permutation p in validation (shift rule mask vs outcomes, 2000 draws,
   min shift 20 sessions) and number of distinct calendar months among validation hits.
7. Restatement check: VIX-matched rule (VIX at the same cutoff >= its discovery quantile that fires as often as the
   candidate in discovery). Validation effect of the VIX twin vs the candidate. For low_pc / high_pc rules also the
   opposite excursion and |cc| (is it just a smaller range?), and the calm-only / PCR-only components.
8. Robustness: drop the largest 1 % favourable outcomes, per year, per weekday regime, drop the 2024-06 election week.
9. Spot checks of 2 non-passed claims: CTX-D0 (expiry day not different, discovery) and one Rejected rule.
Outputs: results/review_model/recompute.csv, checks.csv, spot_checks.csv, stdout.txt.
