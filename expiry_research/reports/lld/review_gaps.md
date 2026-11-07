# LLD: review_gaps (Agent 5b, skeptical review of module `gaps`)

Written 2026-11-05, before the code. Script `scripts/review_gaps_check.py`; outputs `results/review_gaps/`.
Reads the gaps module's scripts and `results/gaps/*` for review only; edits none of them. Does not import any
`gaps_*` code: every number is rebuilt from `panel_io.load_panel(ul)` (and, for one minute check, raw
`spot_1m` files with month <= 2024-06 and rows <= 2024-06-30).

## What is checked
1. **Frozen candidates** (`results/gaps/candidates_frozen.csv`: N_Fa_dir, N_BD0_low_min, N_BDp1_low_min,
   B_BDm1_abs_gap). For each: own tags (D0 = cal_next_is_expiry, D-1 = cal_next_sessions_to_expiry == 1,
   D+1 = cal_next_sessions_since_expiry == 1 and not expiry, ordinary = none of these), same row filter
   (drop split_edge, cal_special_between, blank y_gap_pct), recompute discovery and validation n / mean or rate /
   comparison / effect / two-sided and one-sided p (Welch t, pooled two-proportion z) and the pass rule
   (same sign, one-sided p < 0.05, |effect| >= half discovery).
2. **Leakage**: list the inputs of each rule and their availability (dictionary); confirm no y_ column other than
   the OPEN(t+1) gap enters a condition.
3. **Freeze order**: sha256 of gaps_specs.py + gaps_common.py + gaps_eval.py vs the frozen hash; file mtimes;
   recompute BH over hypotheses.csv d_p and confirm the frozen set is exactly {q <= 0.10, not thin}.
4. **Family**: count specs per underlying vs hypotheses.csv rows; list tests reported with a p-value that are not
   in the family (neighbour thresholds, regime slices, descriptive tables).
5. **Confounds**: weekday-matched comparisons (D0 Thursday vs Tuesday only; D-1 Wednesday vs Tuesday only;
   by weekday of t+1 means of y_low_min and y_abs_gap), per year, drop the top 1 % of the outcome.
6. **Other-direction spot checks** (discovery only; their validation stays unopened because they were not
   frozen): N_ED0m_se_ret15 (expiry-day 15-minute fade from the 09:15 bar close, from raw minutes) and
   B_EDm1_05_fill (BANKNIFTY D-1 large-gap fill). Also confirm their BH q from the full family.

## Outputs
`results/review_gaps/recompute.csv` (frozen ids, disc + val, theirs vs mine), `confounds.csv`, `family.csv`,
`spotchecks.csv`, `hypotheses.csv` (every check run here, with p and BH over this review's own family),
`review_stdout.txt`.
