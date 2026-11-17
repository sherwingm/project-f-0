# Market regime analysis: DRAFT (Agent 3, 17 Nov 2026)

Pre-registered regimes and tests from `PREREG_REGIME.md`, implemented unchanged. Original recorded trade results only (`context_dataset.csv`: G1-F 154, G1 259, G1-C 235, XP 107; entries 2024-10-01 to 2026-10-23); nothing re-simulated; MAE not computed (coordinator merges it). No holdout, sealed data, VM or network touched.

## Method notes (read first)
- Boundaries (boundaries.json) come only from NIFTY daily closes (`data/eod2/nifty 50.csv`, checked equal to the store's index_close_daily where both exist) and India VIX daily closes (`vix_daily.parquet`, repaired) for 2018-01-01 to 2024-09-30. ret20 quintile edges: -1.88 %, +0.52 %, +2.57 %, +4.71 %. VIX 25th / 75th percentile: 13.51 / 19.94. ret5 and ret10 edges are in the file.
- Every label uses the previous NIFTY / VIX session close (strictly before the trade date), the actual 09:15 NIFTY open vs previous close (labelled "actual NIFTY opening gap"), the VIX at the signal minute (sudden expansion only) and the S&P 500 return of the last US session before the trade date (20 trades after the data end 2026-09-25 stay missing). True GIFT pre-open data does not exist and is NOT tested; no GIFT proxy is used in any hypothesis.
- Percent = net rupees after slippage and charges / premium paid in rupees; rupees are reported separately. The replay used the undated 2026 STT table (disclosed, not changed).
- Hypothesis p-value for the Benjamini-Hochberg step (10 %, 9 hypotheses, per strategy) = Kruskal-Wallis p across the classes with n >= 10. Named Welch pair differences are reported next to it. This choice was fixed in the script before any result was read; it makes the correction conservative for two-group contrasts.
- Cells with n < 10 are shown "too few" and carry no conclusion. In several cells the best 5 % of trades exceed 100 % of the total rupee profit (the rest lost money).

## Structural limits of this sample
- G1-F has no gap-up trades (its own filter) and NO high-VIX trades (all previous-close VIX below 19.94: 108 low, 46 normal, 0 high); only 2 sudden-expansion trades; only 19 bullish-direction trades (6 in the strongest quintile, too few). H4 and the high-VIX / gap-up halves of H2, H5, H9 cannot be tested for G1-F.
- Two years, one market phase. In the second half 71 of 79 G1-F trades are low-VIX, so the VIX-level result cannot be checked there.

## Main findings, G1-F (154 trades, explanatory = whole sample); none survives the correction
- H1 direction: bearish (Q1-Q2, n 75) mean +11.7 % [CI -5, +30]; sideways (60) +16.9 % [-10, +47]; bullish (19) +59.5 % [+5, +120] (6 of them in Q5, too few). Kruskal-Wallis p 0.51: no evidence of a direction effect; bullish looks better but is small and wide.
- H2 VIX level: low (108) mean +11.8 %, win 34 %, total Rs 64,172; normal (46) +38.1 % [+11, +69], win 57 %, total Rs 182,874. KW p 0.020 (nominal, best of the family, fails BH whose first threshold is 0.011). Welch low vs normal (not a pre-registered pair) p 0.14. High VIX: none.
- H3 VIX direction: falling +27.8 %, flat +16.9 %, rising +13.1 %; p 0.95.
- H4 sudden expansion: untestable (2 trades).
- H5 opening gap: gap-down (21) +6.4 % vs flat (133) +21.8 %; Welch p 0.47. Gap-up empty by construction.
- H6 S&P previous session: down +19.8 %, flat +8.0 %, up +28.1 %; p 0.30.
- H7-H9: only H9 (VIX level x gap) has nominal p 0.039 (normal-VIX flat-gap +42.5 % [+12, +76], n 40, vs low-VIX flat +12.8 %); the same signal as H2, not independent. Triple: insufficient (smallest cell 0).
- Robustness (not in the family): ret5 quintile KW p 0.015 (middle quintile best +55 %, strongest-up quintile -21.5 %); ret10 and MA structure nothing.

## Other strategies, one line each
- G1 puts (259): nothing near significance (smallest KW p 0.20). Puts did NOT do better in bearish regimes: bearish -0.8 %, sideways +9.8 %, bullish +22.6 % (all intervals include zero).
- G1-C calls (235): calls do worse after bullish run-ups: bullish (41) -36.0 % [-49, -18], win 12 %, vs bearish (130) -5.1 %; bearish minus bullish +30.9 pp, Welch p 0.005 whole sample (0.10 discovery, 0.012 second half; same sign both halves). Omnibus KW p 0.255, so it does not pass the pre-registered BH step; a lead, unconfirmed. Calls did not do better in bullish regimes; the reverse.
- XP expiry-day straddle (107, all on expiry day): H3 VIX direction survives BH in the whole sample (KW p 0.011) and in discovery (p 0.00016; falling +83 % n 14, rising -37 %) but fails the second half (falling -11.2 % n 16, rising -3.5 %; class difference vs rest -0.4 pp). Reversal, as in the earlier context study. Expiry weekday: Tuesday (55) -11.0 %, Thursday (45) +5.0 %, intervals include zero.

## What survives
- BH 10 % per strategy: only XP H3 (whole sample and discovery). Nothing for G1-F, G1, G1-C.
- Second-half consistency: XP H3 fails. G1-F: 8 class contrasts testable, 4 same sign (bearish, VIX falling, S&P flat, S&P up) with second-half sizes close to zero (bearish -0.1 pp). The G1-F VIX-level result cannot be checked (8 normal-VIX trades in the second half). G1-C bullish-vs-rest is consistent in sign and size in both halves (-33.4 / -27.7 pp) but did not clear the correction.
- By half-year G1-F swings widely whatever the regime (bearish class 2025H2 -9.4 % vs 2026H1 +29.4 %); the regime labels explain little of it.

## Bottom line
In these two years none of the pre-registered market-regime conditions explains G1-F's good and poor periods with statistical support. The one lead (normal vs low VIX) is nominal, has no high-VIX data and cannot be checked in the second half. This is absence of evidence in a small, single-phase sample, not evidence that regimes do not matter. No rule change is suggested.
