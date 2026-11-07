# LLD: review_pricepath (Agent 5b, skeptical review of module pricepath)

Written 2026-11-05 before the review code. Code `scripts/review_pricepath_checks.py`; outputs `results/review_pricepath/`.
Reads: `panel_io.load_panel` (NIFTY, BANKNIFTY), and pricepath's own `results/pricepath/*.csv` and scripts (review
exception). Never reads `data/sealed/`, `results/verify/`, other agents' results, or S1/S2/S3 material. Writes nothing
outside `results/review_pricepath/`, this LLD and the script. pricepath files are not edited.

## Scope
Every pricepath candidate labelled Suggestive (36) or Passed-validation (23: 22 rules + event PPC009), plus spot
checks of Rejected PPC007 (BANKNIFTY weekly D0 persistence), PPC146 (NIFTY NR4 W0), PPC059 (NIFTY T1515 rule).

## Checks
1. **Leakage.** Recompute every input of the passed rules from `px_*` / `f_vix_close` / `f_fut_vol` with my own code
   (f_mom5, f_dist_low20, f_fut_vol_r20, f_vix_chg1, f_streak_close, o_cc, o_range_pct, o_gap_pct) and confirm they
   use rows <= t; confirm `y_max_exc` of t equals `o_max_exc` of t+1 and that no condition column is `y_`, `o_` at T1515
   or `cal_` of a re-dated expiry. Thresholds: recompute discovery quantiles; confirm no validation row enters them.
2. **Recompute.** My own masks / contexts (`cal_next_kind`) / usable rows (drop `split_edge`, `cal_special_between`) /
   target (`y_max_exc >= 1`), discovery n, rate, base, effect, two-sided binomial p; validation the same with the
   one-sided binomial p; pass rule as written (same sign, p1 < 0.05, |effect| >= half discovery, n >= 10).
   PPC009: my own calendar shuffle (one non-monthly week per month, 2,000 draws) and a Welch test vs matched weeks.
3. **Freeze order.** File times, sha256 recorded by validation, LLD text on when the n < 10 rule was added.
4. **Family.** Count tests the discovery script performs vs rows in `hypotheses.csv`; list analyses run but not
   counted (robustness neighbours, extras, the pair-selection step).
5. **Robustness.** Per year, excluding 2020, excluding the top 1 % of `y_max_exc`, VIX tercile, neighbouring
   thresholds (discovery quantile +- 0.05 / 0.10). PPC009: drop 2020-03-23 / March 2020, median, sign test.
6. **Known effect restated?** (a) Tradeable target: excursion >= 1 % measured from the t+1 OPEN (the earliest TCLOSE
   entry), `max(high/open - 1, 1 - low/open)`, from `y_high_vs_prevclose`, `y_low_vs_prevclose`, `y_gap_pct`.
   (b) Volatility-adjusted test: a logistic model `y ~ log VIX + log ATR14` fitted on all usable discovery rows (no
   signal); observed hits on signal rows vs the model's expected hits (normal approx. to the Poisson-binomial), in
   discovery and validation (validation: model refitted on validation rows, to absorb the level shift; both shown).
   A rule that adds nothing beyond VIX / ATR is volatility clustering restated, and VIX is what options already price.

Verdicts: holds / weaker-than-claimed / refuted / leak. These review tests are not new candidates; nothing is re-tuned.
