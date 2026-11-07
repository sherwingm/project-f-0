# LLD: final (coordinator's single final out-of-sample test)

Written 2026-11-05, before any final-period value is read. Follows `FINAL_TEST_PLAN.md` exactly; nothing in it
is changed. Script: `scripts/final_test.py` (one run). Outputs: `results/final/`.

## Inputs
- Open panels via `panel_io.load_panel(ul)`; sealed panels via `panel_io.load_sealed_final(ul, coordinator=True)`
  (opened once, in this script only). Combined panel per index = open rows except 2024-06-28 + all sealed rows
  (the sealed file carries the unblanked 2024-06-28 edge row, so rolling / shifted features continue across the
  split). Columns must be identical; the script asserts it.
- Frozen rules: `results/pricepath/candidates_frozen.csv` (PPC032, 062, 092, 098, 129),
  `results/optionchain/candidates_frozen.csv` + `thresholds.csv` (OC08, 13, 17, 21, 118),
  `results/model/candidates_frozen.csv` (M143, M218, M220; its SHA-256 is checked against the recorded one).
- Bhavcopy: only through `optionchain_features.build` (each row uses its own TradDt <= t). Its raw-file reader is
  limited to 2024-01 onwards (the only raw-derived columns, atmz_* and settle_index_near, are not used by any
  candidate; the 2024-01 start keeps the sample check of validation rows possible).

## Feature rebuild (each module's own code)
| Module | Code reused | How it is fed the final period |
|---|---|---|
| pricepath | `pricepath_common.build_features(ul, P)` | P = combined panel (the function takes P) |
| optionchain | `optionchain_features.build(ul)` | module globals patched: `load_panel` -> combined panel, `load_raw` -> files 2024-01..2026-10, `CUTOFF` -> last stored day |
| model | `model_common.build_frame(ul, "TCLOSE")` (calls `_derive`) | its source is executed with two literal edits: `load_panel` -> combined panel, the `< "2024-07-01"` filter -> `< "2099-01-01"`, and the `assert not final` line removed. Split is then discovery / validation / final by target date, by its own code |

Rule masks use the module's own functions: `pricepath_common.cond_mask` / `rate_test`, `optionchain_common.bucket_mask` /
`binary_target`, `model_common.apply_rule` + `model_validate.rows_for`.

## Code-path proof (before any final statistic)
1. Rebuilt features on validation rows equal the module's own stored or freshly built values exactly
   (pricepath: `build_features(load_panel)`; optionchain: `results/optionchain/features_<UL>.parquet`;
   model: `build_frame` unpatched). Columns: every rule feature and every target used.
2. Running the final-test evaluation code on the validation split reproduces each candidate's validation n, k
   (or mean), base and effect in the module's validation CSV. Any mismatch stops the script before final numbers.

## Final statistic per candidate (computed once)
Rows: final period, the module's own row rules (pricepath: usable, context ALL, label present; optionchain:
context ALL frame, split_edge dropped, signal and label present; model: label present, cal_special_between
dropped, rule features present). Final rows are those whose t+1 is >= 2024-07-01 (model / optionchain by target
date, pricepath by `split == final`).
- Base = the module's own base on final rows; rate / mean of flagged rows; effect = flagged - base.
- One-sided p: exact binomial vs base (binary), one-sample t vs base mean (model continuous), as in each module.
- Gate 1: same sign as discovery, p < 0.05, |effect| >= 0.5 x |discovery effect|.
- Gate 2: BH (stats_utils.bh, FDR 10 %) over the 13 one-sided p-values.
- Validated (size) = gate 1 and gate 2; otherwise Rejected. No re-run.

## Reported, not gating
- Beyond VIX: VIX-only model fitted on discovery + validation rows of the same frame and target
  (StandardScaler + LogisticRegression(C=0.1), as `model_vixbase.py`; for the continuous low_pc target, OLS on VIX).
  On final rows: observed minus VIX-predicted for flagged and for unflagged rows; difference of the two mean
  residuals, Welch one-sided p. Positive difference (in the rule's direction) = adds something beyond VIX.
- From open: the same target measured from the t+1 open: big_exc -> max(high/open-1, 1-low/open) >= 1 %;
  big move (optionchain) the same; low_pc -> low/open - 1; range_big unchanged (the range has no gap; reported
  as identical). Built from y_ columns: open = prev close x (1 + gap).
- Per-session flags: `results/final/flags_<UL>.csv`, one row per final session t with each candidate's flag,
  feature value and target.

## Observed cross-checks (not tests of any candidate)
(a) Expiry day (t+1 is an expiry, `cal_next_is_expiry`): gap up (y_gap_dir == up, 0.1 % flat band) and oc > 0
    rates, discovery vs final, NIFTY / BANKNIFTY; SENSEX final only (its calendar exists only in the final
    period), with all-session base rates. Wilson CI, two-proportion p. Discovery numbers are checked against
    `results/bias/ref_discovery.csv`.
(b) Gap transition P(y_gap_dir | o_gap_dir) in the final period, via `bias_discovery.transition` (chi-square).

## Not in this step
The tradeability straddle back-test of the plan runs only for Validated NIFTY rules and is reported as a
separate step; this script does not price options.

## Observed extras (added before running it, after the gate; changes no label)
`scripts/final_extras.py` reads only `results/final/flags_<UL>.csv`: distinct months with a flag, effect by
half-year and inside final-period VIX terciles (flags >= 5 per cell), and a circular-shift permutation p
(2000 shifts of >= 20 sessions) that keeps flag clustering. Outputs `extras_summary.csv`, `extras_groups.csv`.
