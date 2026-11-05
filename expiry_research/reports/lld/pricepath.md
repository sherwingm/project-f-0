# LLD: pricepath (Agent 2: previous-day price action, candles, pre-expiry sequences)

Written 2026-11-05, before any pricepath code or statistic. Report: `reports/PRE_EXPIRY_PATTERN_ANALYSIS.md`.
Outputs: `results/pricepath/`. Code: `scripts/pricepath_*.py`. Tests: `tests/test_pricepath.py`.

## Inputs
Only `panel_io.load_panel(ul)` for NIFTY and BANKNIFTY (discovery 2018-01-01 → 2022-12-31, validation 2023-01-01 →
2024-06-30). No raw data, no sealed data, no S1/S2/S3 material. SENSEX: the open SENSEX panel has no expiry tags
(SENSEX expiries start 2024-10, sealed period) so every SENSEX expiry question is **Untestable** here.

Rows dropped from every test: `split_edge` (label in the next period) and `cal_special_between` (gap spans a Muhurat
session). NIFTY and BANKNIFTY are always reported separately.

## Derived features (all known at TCLOSE(t); only rows <= t are used)
Built in `scripts/pricepath_common.py` from `px_*`, `f_*`, `o_*`, `cal_*`:
- `atr_prev` = `f_atr14_pct` of t-1 (normaliser for outcomes of t, so years with different volatility compare).
- `abs_cc` = |o_cc|; `cc_n` = |o_cc| / atr_prev; `range_n` = o_range_pct / atr_prev; `gap_n` = |o_gap_pct| / atr_prev.
- `persist` = 1 if sign(o_cc of t) = sign(o_cc of t-1) (blank if either is 0 / missing).
- `nr4`, `nr7`: high-low of t is the smallest of the last 4 / 7 sessions (t included).
- `hv_ratio` = f_hv10 / f_hv20 (falling HV when low).
- `rng3_pct` = (max high - min low over t-2..t) / close(t), %.
- `up3` = number of up closes among t-2..t; `dn3` = number of down closes.
- `fbu3` = number of failed upside breakouts in t-2..t (high > previous high and close < previous high);
  `fbd3` mirror (low < previous low and close > previous low).
- `round_dist_pct` = distance from close(t) to the nearest multiple of 500 (NIFTY) / 1000 (BANKNIFTY), % of close.
- `wd_regime`: expiry weekday regime by date: NIFTY `thu_monthly_only` (< 2019-02-11), `thu_weekly`;
  BANKNIFTY `thu` (< 2023-09-01), `wed_weekly_thu_monthly` (2023-09-01 → 2024-02-29), `wed` (2024-03-01 →).

Thresholds are discovery quantiles per underlying (q80 means the 80th percentile of the discovery values of that
feature for that underlying); the numeric value is written into the frozen file, so validation uses fixed numbers.

## Contexts (by t+1, from `cal_next_*`, known at TCLOSE(t))
`W0` t+1 is a weekly expiry; `M0` t+1 is a monthly expiry; `W1` / `M1` t+1 is the session before a weekly / monthly
expiry; `X` t+1 is not an expiry; `ALL` every row. The base rate of a test is the rate of the target over all rows of
the same context, underlying and split.

## Part A: event study (descriptive, discovery; tests enter the family)
Position of session t: weekly D-k = `cal_sessions_to_expiry == k` and `cal_upcoming_kind == weekly` (k = 0..5);
monthly D-k = `cal_sessions_to_monthly == k`; D+1 = the session after a weekly / monthly expiry.
Metrics of t: `o_cc` mean, up rate, `cc_n`, `range_n`, `gap_n`, `persist` rate, `o_rv` (minute days only).
Comparisons:
1. Weekly D-k vs every other discovery session (not weekly D-k). Confounded with weekday (all discovery weeklies are
   Thursday); the weekday check is the BANKNIFTY Wednesday regime in validation.
2. Weekly placebo: NIFTY 2018 had no weeklies, so its non-monthly Thursdays are fake weekly D0 (same weekday,
   non-expiry week) and the sessions before / after are fake D-k. BANKNIFTY has no non-expiry week in discovery:
   placebo Untestable there.
3. Monthly D-k vs matched days: the same k before the weekly expiry of non-monthly weeks (same weekday, no monthly).
4. Calendar-shuffled placebo for monthly: in each discovery month, one non-monthly week is drawn at random and its
   expiry-weekday session is the fake monthly D0 (fake D-k = k sessions before it); 2,000 draws; p = two-sided share
   of draws with a mean at least as far from the matched mean as the real one.
Tests: Welch t (means) or two-proportion z (rates) for 1-3; the shuffle p for 4.

## Part B: listed hypotheses as rules (discovery; pre-declared primary specification marked *)
| Id | Decision | Condition at TCLOSE(t) | Context (t+1) | Target (t+1) |
|---|---|---|---|---|
| H1 rise then fall | TCLOSE(t) | f_mom3 >= q80* (q70, q90) and up3 >= 2 | W1, M1, W0*, M0* | down rate (y_cc < 0)*, sharp-fall rate (y_cc <= -q80 of abs_cc) |
| H2 decline then recovery | TCLOSE(t) | f_mom3 <= q20* (q10, q30) and dn3 >= 2 | W1, M1, W0*, M0* | up rate*, sharp-rise rate |
| H3 sideways then big move | TCLOSE(t) | nr4*, nr7, hv_ratio <= q20, rng3_pct <= q20 | W0*, M0*, X, ALL | big-move rate (y_max_exc >= 1 %)*, wide rate (y_range_pct >= q80 of o_range_pct) |
| H4 big move then reversal | TCLOSE(t) | abs_cc >= q80* (q90) | W0*, M0*, W1, X, ALL | reversal rate (sign y_cc != sign o_cc)* , oc reversal (sign y_oc != sign o_cc) |
| H5 failed breakouts | TCLOSE(t) | fbu3 >= 2* -> down; fbd3 >= 2* -> up | W0*, M0*, X, ALL | down / up rate |
| H6 round numbers / highs-lows | TCLOSE(t) | round_dist_pct <= 0.5 * -> quiet (y_range_pct <= q20) ; f_dist_high20 >= -0.5 -> up; f_dist_low20 <= 0.5 -> down | W0*, M0*, X, ALL | as listed |

## Part C: previous-day candle features (discovery)
Features (TCLOSE): f_body_frac, f_upper_wick_frac, f_lower_wick_frac, f_close_pos, o_range_pct, o_cc, o_gap_pct,
o_last_hour, f_streak_close, f_mom5, f_dist_high20, f_dist_low20, f_hv10, hv_ratio, f_atr14_pct, f_vix_close,
f_vix_chg1, f_futall_oi_r20, f_fut_vol_r20. Tails: <= q20 and >= q80 (streak: <= -3, >= +3).
T1515 features (only for the gap target, which a TCLOSE signal cannot trade): f1515_pos_in_range,
f1515_ret_open_to_1514, f1515_ret_to_1514, f1515_range_pct, f1515_vix_chg (minute era 2021-10 →).
Targets: gap-up rate (y_gap_pct > 0, zero gaps dropped), oc-up rate (y_oc > 0), ret30-up rate (y_ret30 > 0, minute
days only), big-move rate (y_big_move_exc). Contexts: ALL, X, W0, M0.
Interactions: for each (underlying, target, context) the single tails with raw p < 0.05 (at most 4, smallest p) are
paired with AND; at most 2 conditions per rule in this stage (3-condition rules not searched, to keep the family small).

## Statistics
Rates: n, k, rate, Wilson 95 % CI, base rate of the same context rows, effect = rate - base, exact binomial p vs base.
Means: Welch t vs comparison. Every test goes into `results/pricepath/hypotheses.csv`; BH at FDR 10 % over the whole
family (Parts A-C together); family size stated. n < 30 flagged and never frozen.

## Freezing (before any validation statistic)
`results/pricepath/candidates_frozen.csv` holds: every BH-significant discovery test with n >= 30 (Suggestive), plus
the primary (*) specification of H1-H6 for each underlying and context W0 / M0 (frozen even when not significant, so
the listed hypotheses get a verdict). Columns: id, ul, rule text, condition (machine form, numeric thresholds),
decision time, context, target, direction, discovery n / rate / base / effect / p / q.

## Validation (one pass, `scripts/pricepath_validate.py`)
Reads only the frozen file. Pass: same sign as discovery, one-sided binomial p < 0.05 vs the validation base rate of
the same context, and effect >= half the discovery effect. Only Suggestive candidates can become Passed-validation; a
non-significant primary that "passes" stays Observed. Event-study candidates: same rule with the matched comparison
(weekly: D-k vs other sessions; monthly: vs matched non-monthly weeks; shuffle: 2,000 draws over validation months,
one-sided share of draws at least as extreme). Added 2026-11-05 after the discovery run and before any validation
statistic: a candidate with validation n < 10 is not judged (Suggestive stays Suggestive, a primary stays Observed),
and a Suggestive candidate that fails the pass rule is Rejected; a primary that fails is Rejected.

## Robustness (discovery + validation, frozen candidates)
Drop the 1 % most favourable outcomes among signal rows (largest |y_cc| in the predicted direction / largest
outcome); per year; per weekday regime; per VIX tercile (terciles of f_vix_close over disc+val); neighbouring
thresholds (quantile level +- 0.05 / 0.10 from discovery quantiles; nr4 <-> nr7).

## Outputs
`features_<UL>.parquet` (derived, open period), `eventstudy.csv`, `placebo_shuffle.csv`, `hypotheses.csv`,
`candidates_frozen.csv`, `validation.csv`, `robustness.csv`, `predictions_frozen.csv` (one row per candidate x
context row: date, t+1, split, signal, outcome), stdout logs.
