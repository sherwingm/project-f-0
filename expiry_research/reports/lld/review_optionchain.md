# LLD: review_optionchain (Agent 5b, skeptical review of module optionchain)

Goal: try to refute every Passed-validation candidate of module optionchain; spot-check two Rejected/Observed claims.

Inputs: panels via scripts/panel_io.load_panel (t <= 2024-06-30) only; their results/optionchain/*.csv for
comparison only. No sealed data, no raw files after 2024-06-30.

Script: scripts/review_optionchain_checks.py (one run, writes results/review_optionchain/).
1. Rebuild the signals (iv_proxy, wall_width, wall_near, mp_abs, strad_chg, iv_chg, vol_surge) from panel columns with
   my own code, compare to their features parquet (max abs diff).
2. Rebuild contexts (ALL, NW), discovery tercile cut points, discovery target medians; recompute discovery and
   validation n / rate / base / effect / p for each passer (recompute.csv).
3. Leakage checks (leak_checks.csv): causal rolling windows, same-expiry diffs, near expiry vs calendar, thresholds
   equal discovery quantiles, frozen-file order.
4. Vol-clustering control (incremental.csv): logistic baseline fit on DISCOVERY rows only with TCLOSE-known inputs
   (log VIX, log hv10, log range of t, |mom1|, t+1 is expiry, sessions to expiry, weekday of t+1); excess of the
   bucket over the baseline prediction (sum(y - p)) in discovery and validation, z-test; plus a logistic fit with
   the signal added, per period.
5. Robustness (robust.csv): drop top 1 % / 5 % of target outcomes, per year, per weekday regime, VIX terciles,
   thresholds at the 60/70/75/80 % discovery quantiles.
6. Spot-checks: OBS-MP (expiry closes toward max pain) and OC128 (BANKNIFTY D-2 straddle).
Everything here is a review statistic; nothing is a new candidate.
