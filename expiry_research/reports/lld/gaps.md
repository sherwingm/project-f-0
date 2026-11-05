# LLD: gaps module (Agent 1, expiry gap and reversal patterns)

Written 2026-11-05, before the code. Scripts `scripts/gaps_common.py`, `scripts/gaps_specs.py`,
`scripts/gaps_discovery.py`, `scripts/gaps_freeze.py`, `scripts/gaps_validate.py`, `scripts/gaps_robust.py`,
`scripts/gaps_behaviour.py`; tests `tests/test_gaps.py`; outputs `results/gaps/`; reports
`reports/GAP_TRANSITION_ANALYSIS.md` and Section 2 of `reports/EXPIRY_CALENDAR_ANALYSIS.md`.

## Inputs
- Panels via `panel_io.load_panel(ul)` only (NIFTY, BANKNIFTY; SENSEX is used only to state what is untestable).
- `spot_1m/{NIFTY50,NIFTYBANK}` monthly files with month <= 2024-06, rows filtered to date <= 2024-06-30 at load.
  Used for one thing: returns measured from the close of the 09:15 bar (the first price at which a trader who saw
  the opening gap can act), so a gap signal is never credited with the open print itself.
- Not used: data/sealed/, results/verify/, anything of S1/S2/S3, other agents' folders.

## Row set and tags (gaps_common.prepare)
- Row = session t with label session t+1. Dropped: `split_edge`, `cal_special_between` (gap spans a Muhurat
  session), rows with blank `y_gap_pct`.
- Context of the target session t+1 (calendar, known in advance):
  `k = cal_next_sessions_to_expiry` (0 = D0 expiry day, 1 = D-1, ... 4 = D-4, 5+), `dplus1 = cal_next_sessions_since_expiry == 1`
  and not an expiry day. In a 5-session weekly week D+1 and D-4 are the same session; tests use the overlapping
  tags as defined, and tables say so.
- Kind: D0 uses `cal_next_kind`; D-k uses `cal_next_upcoming_kind`; D+1 uses `cal_kind` of t (the expiry just past).
- Weekday regime of t+1 (by date of t+1): NIFTY `N18_monthly_only` (< 2019-02-11), `N_thu_weekly`;
  BANKNIFTY `B_thu` (< 2023-09-01), `B_wed_weekly_thu_monthly` (2023-09-01 .. 2024-02-29), `B_wed` (2024-03-01 ..).
- Gap direction: panel `y_gap_dir` / `o_gap_dir` (flat if |gap| < 0.1 %). Signed buckets of |gap|:
  flat < 0.1, 0.1-0.3, 0.3-0.5, 0.5-1.0, >= 1.0.
- Own gap streak `g_streak` from `o_gap_dir`: consecutive non-flat same-direction gaps ending at t (+n up, -n down,
  flat resets). (`f_streak_gap` resets only on an exactly zero gap, so tiny gaps keep it alive; not used.)
- VIX terciles: cut points from discovery `f_vix_close` per underlying, applied unchanged to validation.
- Minute targets (t+1, `m_ok` days, 2021-10-20 → only): `e_ret15/30/60` = close of 09:29/09:44/10:14 bar / close of
  09:15 bar - 1; `e_oc` = 15:29 close / 09:15 bar close - 1; `e_fill` = a later bar (09:16 →) touched the previous
  close. Signed by the gap direction: continuation > 0.

## Decision times used
| Code | Inputs | Typical target |
|---|---|---|
| T1515(t) | gaps of t and earlier (o_gap_* known at t 09:15), calendar | y_gap direction (entry 15:15-15:29 of t) |
| TCLOSE(t) | adds f_close_pos, o_cc, o_oc of t | y_oc / y_cc (entry t+1 open); y_gap is then informational only |
| OPEN(t+1) | adds y_gap_pct (the opening print of t+1) | continuation / reversal / fill after 09:16 |
OPEN(t+1) is later than TCLOSE: the rule waits for the opening print and enters at the 09:15 bar close at the
earliest. Daily `y_oc` (from the 09:15 open) is reported as the long-history proxy and marked optimistic.

## Hypothesis family (gaps_specs.py, one function per group; all on discovery, per underlying)
Each spec: id, ul, group, rule text, decision time, target, direction, kind, condition mask, comparison mask,
outcome, and a parameter that the robustness step moves to neighbouring values.
- kind `rate_vs_base`: k/n vs the unconditional rate of the same target over all rows of the same split and
  underlying; exact binomial (`binom_p`).
- kind `rate_2g`: rate in group A vs group B (`two_prop`).
- kind `mean_2g`: mean in A vs B, Welch t (scipy), CI by `mean_ci`.
- kind `trend`: Cochran-Armitage trend of a 0/1 outcome over k = 4..0 (scipy normal tail).
Groups: T transitions (up→down, down→up, |gap| >= 0.5 / 1 reversal, 3x3 chi-square), X reversal by context
(D0, D-1..D-4, D+1, trend), S streaks of 2 / 3 → next gap and next oc, C close position (f_close_pos, and the
T1515 twin f1515_pos_in_range) → next gap, L large gap → continuation of oc and fill vs all gaps, E expiry-day
(and D-1, D+1) gap >= 0.3 / 0.5 vs same-size gaps on other days (daily and minute targets), F gap-fill conditions
(direction, VIX tercile, context, prior 5-day trend) within |gap| 0.1-0.5 and >= 0.5, P first session after
expiry (next gap / next oc against the expiry-day move), B behaviour by expiry type (range, |cc|, |oc|, |gap|,
rv, high time, low time, big-move rates; D0 / D-1 / D+1 vs ordinary; monthly vs weekly D0; non-expiry Thursday
control in NIFTY 2018).
Fill-rate-by-size is printed as a table, not tested (mechanically true).
BH at FDR 10 % over every test of the family (both underlyings, all groups); family size stated in the report.
n < 30 tests are run and logged but flagged `thin` and cannot be frozen.

## Protocol
1. `gaps_discovery.py`: discovery rows only; writes `hypotheses.csv` (discovery columns) and the tables.
2. `gaps_freeze.py`: fixed rule: freeze every hypothesis with BH q < 0.10, n >= 30 in the conditional group,
   and a decision time that is not a label. Writes `candidates_frozen.csv` with the sha256 of `gaps_specs.py` and
   `gaps_common.py`. No validation number exists before this file.
3. `gaps_validate.py`: refuses to run if the hashes differ; evaluates only frozen ids on validation once.
   Pass: same sign, one-sided p < 0.05 vs the validation base (or comparison group), and |effect| >= half the
   discovery |effect|. Writes `validation.csv`; labels Passed-validation / Rejected.
4. `gaps_robust.py`: frozen ids on discovery + validation: drop the best 1 % of signed outcomes in the condition
   group, per year, per weekday regime, per VIX tercile, neighbouring thresholds (parameter ±1 step). Writes
   `robustness.csv`. Never changes a label to a pass; a re-tuned variant would be a new, unvalidated candidate.
5. `gaps_behaviour.py`: descriptive tables for Section 2 (discovery; validation shown only for frozen ids) and
   the minute-coverage count. Per-expiry CSV `per_expiry_D0.csv` (one row per expiry day: gap, oc, fill, signal).

## Tests (tests/test_gaps.py)
Transition counts sum to rows; context tags match calendar columns on hand-picked dates; own streak recomputed
by a loop; minute entry returns recomputed for 3 dates from raw files; no rule mask reads a y_ column except the
OPEN(t+1) gap; loader dates <= 2024-06-30; validation refuses on hash mismatch.
