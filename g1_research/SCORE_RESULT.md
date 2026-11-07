# Breakout score 0-7: history check (2026-11-07). Plan: SCORE_PREREG.md. Script: scripts/g1_score.py. Data: results/g1_score_history.csv
Max up = the put's highest later minute close through the next close, no stop. 259 history signals (128 discovery, 131 validation).

## Does it work? No. Label: Rejected as a predictor (it stays a record).
| Band (validation) | n | >=+100 % | mean | median |
|---|---|---|---|---|
| low 0-2 | 21 | 19 % | +64 % | +25 % |
| mid 3-4 | 71 | 35 % | +94 % | +65 % |
| high 5-7 | 39 | 31 % | +95 % | +42 % |
- Spearman score vs max up: discovery +0.06 (p 0.53), validation +0.09 (p 0.32). High vs low band on >=+100 %: +11.7 points, one-sided p 0.25 (needs < 0.05).
- The shape is a hump, not a ladder: 3-4 points does best, 5-7 is no better. A higher score does not mean a bigger move.
- G1-F only: rho -0.03 (no link). By year: 2024 +0.03, 2025 -0.06, 2026 +0.20 (unstable).

## What was hiding
- Prev 5-day return and Prev close vs EMA20 overlap (correlation 0.59): that is one idea counted twice. Also width and VIX overlap (0.29). So it is about 5-6 views, not 7.
- Two items point the wrong way on max up (validation): prev 5-day (a falling market before gave a LOWER median max up, +36 % vs +67 %) and minutes after 09:30 (an early break did worse, 24 % vs 38 % reach +100 %). Only gap (gap down, p 0.04 in validation alone) and VIX < 17 lean the expected way; with 7 items one p of 0.04 is not evidence.
- Dropping prev 5-day lifts the validation rho to +0.16, but doing that now would be tuning after the result: NOT done. It is logged as a lead for the live data.
- Without the 10 biggest max-up trades the picture is the same (rho +0.08).
- No look-ahead: all 7 items are known at entry. Expanding percentile vs full-history percentile agree (rho 0.96).
- Score 7 never appeared in validation (3 times in discovery); the top of the scale is nearly empty.

## What it means
The score is a clean, honest RECORD of how strong the break looked, but on 259 history trades it does not rank the max up. So: record only (as chosen), no filter, no size. Judge again at 30 live signals, max up first, by band. A rule change needs its own pre-registration.
