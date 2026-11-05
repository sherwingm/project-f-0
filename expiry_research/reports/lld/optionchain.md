# LLD: option-chain and OI behaviour (module `optionchain`, Agent 3)

Written 2026-11-05, before the code. Scripts `scripts/optionchain_features.py`, `scripts/optionchain_discovery.py`,
`scripts/optionchain_validation.py`; tests `tests/test_optionchain.py`; outputs `results/optionchain/`;
report `reports/OPTIONS_CHAIN_ANALYSIS.md`. Independent of S1/S2/S3 and of the other research agents.

## Question
Does end-of-day option-chain / futures-OI information of session t (bhavcopy, known at TCLOSE(t)) predict the next
session (gap direction and size, first-30-minute return, open-to-close, range, big move, gap fill), overall and when
t+1 is an expiry (weekly / monthly), and from two sessions before an expiry (D-2)? Plus two structural questions:
does the index settle toward max pain on expiry, and is the expiry-day realised move larger or smaller than the ATM
straddle implied it would be?

## Inputs
- Panels only via `panel_io.load_panel(ul)` (NIFTY, BANKNIFTY; t <= 2024-06-28). SENSEX has no option history
  before 2024-09 and no BSE bhavcopy: every SENSEX question here is **Untestable** before the final stage.
- Raw bhavcopy `options_daily/<UL>/<YYYY-MM>.parquet` (files 2018-01 .. 2024-06 only, rows `TradDt <= 2024-06-30`
  filtered at load) for strike-wise detail: ATM-zone PCR and OI change, the D0 settlement value of the D-1 / D-2 ATM
  straddle, and quality statistics.
- Not used: data/sealed, results/verify, anything outside expiry_research (except the read-only store), other
  agents' folders.

## Bhavcopy quality handling
- `UndrlygPric` empty before 2024-07: the underlying is the panel `px_close` (minute close from 2021-10, official
  before) for features, and `px_close_official` for expiry settlement comparisons.
- Settle <= 0: such rows are excluded from any price use (straddle, settlement). OI and volume of those rows are kept
  (they are real OI numbers). Shares per year are reported.
- Strike sparsity: per year, the number of near-expiry strikes with OI > 0 inside +-5 % of close vs the full grid
  (NIFTY 50-point, BANKNIFTY 100-point) is reported; ATM-zone features need >= 3 strikes on each side or are blank.
- No IV column: the IV proxy is the ATM straddle time value, annualised:
  `iv_proxy = (straddle_pct - |K/S-1|*100) / 0.7979 / sqrt(n_sess) * sqrt(252)`, n_sess = weekday count from t+1 to
  the near expiry (holidays ignored; known in advance). 0.7979 = sqrt(2/pi) (ATM straddle ~ 0.8 sigma sqrt T).
- Bid-ask: not available historically (bhavcopy has trade / settle prices only). Settle prices are not executable
  fills; every straddle cost here is a settle price.

## Contexts (rows t), per underlying, never pooled
| ctx | rows | targets refer to |
|---|---|---|
| ALL | every row with a label | t+1 |
| NW | `cal_next_kind == weekly` (t = D-1 of a weekly) | t+1 = weekly expiry D0 |
| NM | `cal_next_kind == monthly` (t = D-1 of a monthly) | t+1 = monthly expiry D0 |
| D2 | `cal_next_sessions_to_expiry == 1` (t = D-2, any expiry) | t+2 = expiry D0 (taken from the next row's `y_`) |
`split_edge` rows are dropped. D2 rows whose t+1 row is missing are dropped.

## Signals (all TCLOSE(t)); directional (dir) or volatility (vol)
| id | signal | type | buckets |
|---|---|---|---|
| pcr_oi | f_opt_near_pcr_oi | dir | hi / lo tercile |
| pcr_vol | f_opt_near_pcr_vol | dir | hi / lo |
| pcr_oi_chg | pcr_oi(t) - pcr_oi(t-1), same near expiry | dir | hi / lo |
| net_oi_flow | (pe_oi_chg - ce_oi_chg) / (ce_oi + pe_oi), near | dir | hi / lo |
| mon_pcr_oi | f_opt_mon_pcr_oi | dir | hi / lo |
| atmz_pcr | PE OI / CE OI, near expiry, strikes within +-2 % of close (raw) | dir | hi / lo |
| atmz_flow | (PE OI chg - CE OI chg) / (CE+PE OI), strikes within +-2 % (raw) | dir | hi / lo |
| maxpain_dist | f_opt_near_maxpain_dist_pct | dir | hi / lo |
| wall_skew | callwall_dist + putwall_dist (near; > 0 = more room up) | dir | hi / lo |
| basis_ann | f_fut_basis_pct * 365 / f_fut_dte | dir | hi / lo |
| fut_build | sign(f_mom1) x sign(f_futall_oi_chg): LB (up, OI up), SB (down, OI up), SC (up, OI down), LU (down, OI down) | dir | 4 classes |
| opt_build | sign(f_mom1) x sign(pe_oi_chg - ce_oi_chg): UP_PW (up, puts added more), UP_CW, DN_PW, DN_CW | dir | 4 classes |
| iv | iv_proxy | vol | hi / lo |
| iv_chg | iv_proxy(t) - iv_proxy(t-1), same near expiry | vol | hi / lo |
| strad_chg | f_opt_near_straddle_chg1 | vol | hi / lo |
| iv_hv | iv_proxy - f_hv10 | vol | hi / lo |
| vol_surge | near CE+PE volume / median of the previous 5 rows with the same n_sess | vol | hi / lo |
| top3 | f_opt_near_top3_oi_share | vol | hi / lo |
| wall_width | callwall_dist - putwall_dist | vol | hi / lo |
| wall_near | min(callwall_dist, -putwall_dist) | vol | hi / lo |
| fut_oi_abs | abs(f_futall_oi_chg) / f_futall_oi | vol | hi / lo |
| mp_abs | abs(f_opt_near_maxpain_dist_pct) | vol | hi / lo |
Tercile cut points are computed on DISCOVERY rows of the same (underlying, context) only, and frozen.

## Targets (binary; continuous means are reported alongside)
dir: gap_up (gap > 0), oc_up, ret30_up (minute days only), cc_up (D2: close(t+2) / close(t) > 1).
vol: gap_big (|gap| > discovery median of that ul/ctx), range_big (range > discovery median), big_move
(`max_exc >= 1 %`), gap_fill. Direction of a bucket's effect is not assumed; the test is two-sided.

## Test (one row of `hypotheses.csv` each)
Bucket rows vs all rows of the same ul / ctx / split: n, k, rate, Wilson 95 % CI, base, effect = rate - base,
two-sided exact binomial p vs base. Flag n < 30. Structural tests (below) join the same family. BH at FDR 10 % over
the whole family; family size reported.

## Structural tests
- MP1 settles toward max pain: on D-1 rows, share where |maxpain - S(E)| < |maxpain - close(t)| (S(E) = official
  close of the expiry day), vs the same share on non-expiry-eve rows (two-proportion test); MP2 direction:
  sign(close(E) - close(t)) == sign(maxpain - close(t)) on rows with |dist| >= 0.25 %, vs the same on non-eve rows;
  MP3 = MP1 at D-2 with S(t+2).
- ST1 straddle: on D-1 rows, cost = ATM straddle settle (t), payoff = CE + PE final settlement on E at the same strike
  (raw bhavcopy; fallback |S(E) - K|). Statistic: mean (payoff - cost) / close(t) %, t-test and block bootstrap;
  also realised / implied ratio and share payoff > cost. ST2 = same from D-2. ST3: D0 range vs D-1 straddle (share of
  expiries where range_pct > straddle_pct). By weekly / monthly and underlying.

## Freezing rule (fixed now)
Frozen = every discovery test with BH q <= 0.10 and n >= 30. If fewer than 5, add the next best tests by p with
p < 0.01 and n >= 30 (marked `exploratory`) up to 10 in total. Written to `candidates_frozen.csv` by the discovery
script, which computes no validation statistic. The validation script refuses to run if that file is missing and
evaluates only those rows, once.

## Validation pass rule (fixed)
Same sign of effect, one-sided binomial p < 0.05 vs the validation base rate of the same rows, and |effect| >= half
the discovery |effect|. Continuous structural candidates: same sign, one-sided t p < 0.05, mean >= half.

## Robustness (discovery + validation, frozen candidates only; descriptive, not re-tuning)
Drop the 1 % of rows with the most favourable continuous outcome; per year; per weekday regime (NIFTY: monthly-only
2018 / Thursday weekly; BANKNIFTY: Thursday to 2023-08-31 / Wednesday weekly from 2023-09-01); per VIX tercile;
neighbouring thresholds (30 % and 40 % instead of 33 % tails).

## Outputs (`results/optionchain/`)
features_<UL>.parquet, bhavcopy_quality.csv, thresholds.csv, hypotheses.csv, structural.csv, candidates_frozen.csv,
validation.csv, robustness.csv, per-expiry prediction CSVs `pred_<cand>.csv`, stdout logs.

## Tests (`tests/test_optionchain.py`)
No feature row uses a raw row dated after t; no date > 2024-06-30 anywhere; thresholds come from discovery rows only
(recomputed); validation statistics absent from candidates_frozen.csv; D2 targets equal the next row's labels.

## Changes during the build (recorded after the code, before validation)
- Expiry-day settlement: the bhavcopy's expiring-option `SttlmPric` on the expiry day is the index final settlement
  value (0 on 2018-19 expiries); used directly, official close as fallback (they agree exactly).
- Added during discovery, before freezing: 96 conditional straddle P&L tests (signals iv, iv_hv, iv_chg, strad_chg,
  vol_surge, top3, wall_width, mp_abs; hi / lo; NW, NM, D2) in the same BH family.
- Output names as built: `structural_discovery.csv` (not structural.csv), `straddle_per_expiry_<UL>.csv`,
  `robustness_summary.csv`; shared code in `scripts/optionchain_common.py`.
