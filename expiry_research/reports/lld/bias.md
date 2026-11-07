# LLD: bias module (Agent 5a, independent validation and bias detection)

Written 2026-11-05, before the code. Scripts `scripts/bias_*.py`, tests `tests/test_bias.py`, outputs
`results/bias/`, report `reports/BIAS_AND_VALIDITY.md`. This module searches for no trading pattern. It builds the
project's controls: base rates, a false-discovery yardstick, regime checks, a leakage scan and a validity checklist.

## Inputs (read-only)
- Panels only through `panel_io.load_panel(ul)` (NIFTY, BANKNIFTY; t <= 2024-06-28). `data/sealed/` and
  `results/verify/` are never opened. SENSEX expiry questions are Untestable (calendar tags blank in the open panel).
- `data/expiry_calendar.csv`, `data/sessions_<UL>.csv`, `data/expiry_relabels.csv`, `data/special_sessions.csv`
  (calendar facts, rows <= 2024-06-30 only).
- Raw store only for one look-ahead cross-check: `vix_daily.parquet`, filtered to date <= 2024-06-30 on load.
- Nothing from S1/S2/S3, `scripts/` of other agents, `server/`, `data/results/` or other agents' result folders.

## Row tags (computed once in `bias_common.py`)
Row t describes session t+1 (labels `y_`). Tags use only `cal_next_*` (known at TCLOSE(t)).
- `ctx` (exclusive): `D0` if `cal_next_sessions_to_expiry == 0`; else `D+1` if `cal_next_sessions_since_expiry == 1`;
  else `D-k` for k = 1..5, `D-6+` for k >= 6 (NIFTY 2018 monthly-only cycle); `unknown` if blank.
- `dk` (non-exclusive countdown): `D0`, `D-1` .. `D-5`, `D-6+` from `cal_next_sessions_to_expiry` only.
- `xkind`: `cal_next_upcoming_kind` (weekly / monthly cycle that t+1 counts down to; on D0 = kind of that expiry).
- `wd_regime` by the date of t+1 (open period only):
  NIFTY `N0` (< 2019-02-11, monthly Thursday only), `N1` (>= 2019-02-11, weekly + monthly Thursday).
  BANKNIFTY `B1` (<= 2023-09-01, Thursday weekly + monthly), `B2` (2023-09-04 .. 2024-02-29, Wednesday weekly,
  Thursday monthly), `B3` (2024-03-01 .., Wednesday weekly + monthly).
  Breaks 2024-11 (BANKNIFTY weeklies end), 2025-01, 2025-09 lie in the sealed period: Untestable here.
- `vix_terc`: tercile of `f_vix_close` (of t), cut points from discovery rows of that underlying, applied to all.
- `covid`: t+1 in 2020-02-20 .. 2020-06-30 (fixed here, before any number is seen).
- `gap_after`: `cal_days_to_next_session` 1 / 2-3 (weekend) / 4+ (long holiday).
- Rows with `split_edge` and rows with a blank label are dropped from every test (they are counted).

## Targets (binary, for every rate table and the mining null)
`gap_up` (y_gap_dir == up), `gap_down`, `oc_pos` (y_oc > 0), `cc_pos` (y_cc > 0), `big_cc` (|y_cc| >= 1 %),
`big_exc` (y_max_exc >= 1 %). Reference tables add `gap_flat` and the mean of `y_range_pct`, `y_oc`.

## Stage 1, discovery only (`bias_discovery.py`)
1. Reference tables, discovery: per UL, per tag (`all`, `ctx`, `dk`, `xkind` x `ctx` for D0/D-1, `wd_regime`,
   `cal_next_dow`, `gap_after`, previous gap dir `o_gap_dir`): n, k, rate, Wilson CI, base (all discovery rows of that
   UL), diff, binomial p vs base. Means with t interval and Welch p vs the complement. P(gap dir t+1 | gap dir t) is
   the `o_gap_dir` table (3 x 3 transition matrix plus chi-square).
2. Mining null (yardstick): 20 TCLOSE `f_` features with >= 95 % discovery coverage. Single conditions: feature
   <= its discovery 20th percentile, >= its 80th (40). Two-condition: each single condition AND one of 4 expiry
   contexts (t+1 is D0; D-1; D+1; t+1 in a monthly cycle) = 160. 200 rules x 6 targets per UL; rules with n < 30 are
   not tested (same set in real and null). Test: exact two-sided binomial vs the discovery base rate; BH over the
   UL's tests and over both ULs. Null: 200 permutations of whole ISO weeks of the 6-label matrix (labels move jointly,
   order inside a week kept; blocks concatenated). Sensitivity null: weeks shuffled only among weeks of the same
   length, so labels keep their weekday slot (calendar seasonality survives). Reported per run: tests with p < 0.05,
   with BH q < 0.10, min p, best |edge| (rate - base, pp), best |edge| among p < 0.05, per target and per n-bin
   (30-59, 60-119, 120-249, 250+). Summary: null mean, 95th and 99th percentile, real value, empirical
   p = (1 + #null >= real) / 201.
3. Leakage AUC: every numeric `f_` / `f1515_` feature, discovery rows: AUC for gap up vs down (flats out), for
   `oc_pos`, and (calibration only) `big_exc`. Mann-Whitney p. Flag |AUC - 0.5| > 0.15. Positive controls:
   `y_gap_pct` (must give AUC 1), a planted leak (`f_mom1` of t+1). Negative control: shuffled feature, 200 times
   (gives the chance spread of AUC at this n).
4. Regimes inside discovery: per year (2018-2022) rate and chi-square homogeneity; each year vs the rest (two_prop);
   COVID window vs the rest; VIX terciles; label-source break at 2021-10-20 (official close before, minute after).
5. Label checks, discovery minute era (2021-10-20 .. 2022-12-30): gap direction with `px_close_official(t)` instead
   of the minute close: agreement, confusion, base rates, transition matrix, and how many of the mining rules' gap
   conclusions (p < 0.05) flip; AUC change per feature. Flat-band sensitivity (0.05 / 0.10 / 0.15 / 0.20 %).
6. Integrity checks: recompute f_mom1, f_hv10, f_dist_high20, f_close_pos, y_gap_pct, y_oc from px columns;
   f_vix_close vs raw vix_daily same date vs date shifted; split edges, Muhurat rows, re-dated expiries
   (calendar next expiry vs `f_opt_near_expiry` as listed).

Every p-value goes to `results/bias/hypotheses.csv` (id, family, ul, split, test, n, effect, p).

## Stage 2, freeze (`bias_freeze.py`)
BH (FDR 10 %) over all discovery tests logged so far. Candidates = discovery reference tests of an expiry context
(`ctx`, `dk`, `xkind` rows) with n >= 30 and q < 0.10. They are base-rate facts, not trading rules; they are frozen in
`results/bias/candidates_frozen.csv` so the validation look is a single, fixed one. If none, the file has a header only.

## Stage 3, validation (`bias_validation.py`), after the freeze
- Reference tables again on validation rows (same tags, base = validation rate). Regime checks that need validation:
  BANKNIFTY B1 vs B2 vs B3, D0 vs Thursday-non-expiry (is the "expiry effect" a weekday effect?), year 2023 vs 2024H1.
- Frozen candidates: pass = same sign, one-sided exact binomial p < 0.05 vs the validation base, effect >= half the
  discovery effect. Evaluated once.
- Label check of the validation minute era (official vs minute gap labels).

## Stage 4, robustness (`bias_robustness.py`), discovery + validation
For every frozen candidate: drop the 1 % of all rows with the most extreme continuous outcome behind the target;
per year; per weekday regime; per VIX tercile; neighbouring thresholds (big move 0.8 / 1.2 %, flat band 0.05 / 0.15 %,
D-k +- 1). Final BH over the whole log (family size stated). Per-row CSV of candidate rows.

## Outputs (`results/bias/`)
`ref_discovery.csv`, `ref_validation.csv`, `gap_transition.csv`, `mining_real.csv`, `mining_null_runs.csv`,
`mining_null_summary.csv`, `mining_null_by_nbin.csv`, `auc_leakage.csv`, `auc_controls.csv`, `regimes.csv`,
`label_official_vs_minute.csv`, `flat_band.csv`, `integrity.csv`, `redated_rows.csv`, `candidates_frozen.csv`,
`candidates_validation.csv`, `robustness.csv`, `candidate_rows.csv`, `hypotheses.csv`, `*_stdout.txt`.

## Tests (`tests/test_bias.py`)
Vectorised exact binomial p equals `scipy.stats.binomtest`; week permutation keeps the label multiset and the order
inside each week; AUC equals the Mann-Whitney U / (n1 n2); context tags on known dates (e.g. NIFTY 2024-06-26 row ->
t+1 2024-06-27 monthly D0; BANKNIFTY 2024-06-25 row -> D0); load_panel returns no row >= 2024-07-01.
