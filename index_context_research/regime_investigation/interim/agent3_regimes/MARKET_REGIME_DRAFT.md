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


---
# Part A. EXPLANATORY (whole sample, 2024-10-01 to 2026-10-23, entries). Descriptive tables

Units: net % = net rupees after slippage and all charges / rupees of premium paid; Rs = net rupees (separate). CI = bootstrap 95 % of the mean net %, resampling trading days, 5000 draws, seed 20261117. 'top-5 % share' = rupees of the best ceil(5 % n) trades / total rupees (blank = total not positive; above 100 means the rest lost money). maxup = best option price through the next close, % over price paid. Cells n < 10 are shown as 'too few' with no numbers.


## G1-F

Tests (whole sample; Kruskal-Wallis on net % across classes with n>=10; Benjamini-Hochberg 10 % over H1-H9 for this strategy):

| hyp | cells with n>=10 | Kruskal-Wallis p | named Welch diff (pp) | Welch p | BH 10% |
|---|---|---|---|---|---|
| H1 | 4 | 0.511 | bearish minus bullish: -47.8 | 0.150 | no |
| H2 | 2 | 0.020 | - | - | no |
| H3 | 3 | 0.946 | falling minus rising: 14.7 | 0.485 | no |
| H4 | 1 | - | - | - | no |
| H5 | 2 | 0.630 | gap-down minus flat: -15.4 | 0.468 | no |
| H6 | 3 | 0.304 | down minus up: -8.3 | 0.694 | no |
| H7 | 5 | 0.209 | - | - | no |
| H8 | 4 | 0.770 | - | - | no |
| H9 | 3 | 0.039 | - | - | no |


**H1 direction (ret20 quintiles 1=strongly bearish ... 5=strongly bullish)**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 36 | 47 | 18.8 [-4, 45] | -3.2 | 56,384 | 101 | 50 | 63 |
| 2 | 39 | 41 | 5.2 [-19, 33] | -31.9 | 34,290 | 99 | 44 | 134 |
| 3 | 60 | 33 | 16.9 [-10, 47] | -32.6 | 63,606 | 91 | 28 | 96 |
| 4 | 13 | 31 | 18.1 [-36, 86] | -51.2 | 13,639 | 131 | 46 | 129 |
| 5 | 6 | too few | too few | | | | | |


**H2 VIX level**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| low | 108 | 34 | 11.8 [-6, 31] | -37.6 | 64,172 | 101 | 37 | 176 |
| normal | 46 | 57 | 38.1 [11, 69] | 7.4 | 182,874 | 113 | 50 | 49 |


**H3 VIX direction (5 sessions)**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| falling | 50 | 42 | 27.8 [-2, 61] | -17.7 | 85,648 | 103 | 40 | 73 |
| flat | 72 | 39 | 16.9 [-5, 41] | -27.5 | 122,678 | 100 | 35 | 88 |
| rising | 32 | 44 | 13.1 [-11, 39] | -10.1 | 38,720 | 116 | 56 | 83 |


**H4 sudden VIX expansion at signal**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| no | 152 | 41 | 20.3 [5, 37] | -18.2 | 250,322 | 105 | 41 | 76 |
| yes | 2 | too few | too few | | | | | |


**H5 actual NIFTY opening gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| gap-down | 21 | 33 | 6.4 [-26, 45] | -51.0 | 3,732 | 71 | 29 | 786 |
| flat | 133 | 42 | 21.8 [5, 40] | -17.3 | 243,314 | 110 | 43 | 71 |


**H6 S&P 500 previous session**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| down | 51 | 35 | 19.8 [-9, 52] | -36.2 | 80,013 | 103 | 33 | 107 |
| flat | 48 | 35 | 8.0 [-17, 35] | -46.8 | 56,683 | 101 | 42 | 110 |
| up | 52 | 48 | 28.1 [2, 56] | -5.9 | 92,743 | 110 | 46 | 58 |


**H7 direction3 x VIX level**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | low | 48 | 33 | -2.9 [-22, 17] | -32.2 | -18,402 | 97 | 42 | - |
| bearish | normal | 27 | 63 | 37.8 [7, 72] | 7.9 | 109,076 | 104 | 56 | 42 |
| sideways | low | 46 | 30 | 17.6 [-14, 55] | -51.1 | 39,994 | 96 | 30 | 149 |
| sideways | normal | 14 | 43 | 14.6 [-22, 56] | -4.9 | 23,612 | 74 | 21 | 73 |
| bullish | low | 14 | 50 | 43.3 [-12, 107] | 11.6 | 42,579 | 129 | 43 | 41 |
| bullish | normal | 5 | too few | too few | | | | | |


**H8 direction3 x gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | gap-down | 8 | too few | too few | | | | | |
| bearish | flat | 67 | 48 | 15.3 [-3, 35] | -6.4 | 101,445 | 106 | 49 | 83 |
| sideways | gap-down | 11 | 36 | 6.1 [-40, 67] | -51.2 | 680 | 69 | 18 | 2375 |
| sideways | flat | 49 | 33 | 19.3 [-10, 54] | -29.0 | 62,926 | 96 | 31 | 97 |
| bullish | gap-down | 2 | too few | too few | | | | | |
| bullish | flat | 17 | 47 | 53.9 [-5, 123] | -12.6 | 78,943 | 166 | 53 | 56 |


**H9 VIX level x gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| low | gap-down | 15 | 33 | 5.6 [-31, 54] | -18.5 | 5,928 | 75 | 27 | 273 |
| low | flat | 93 | 34 | 12.8 [-7, 35] | -39.0 | 58,244 | 105 | 39 | 166 |
| normal | gap-down | 6 | too few | too few | | | | | |
| normal | flat | 40 | 60 | 42.5 [12, 76] | 8.4 | 185,070 | 121 | 52 | 37 |


**R1 robustness: ret5 quintiles**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 24 | 42 | 13.0 [-14, 43] | -4.2 | 31,621 | 88 | 46 | 112 |
| 2 | 55 | 33 | 7.4 [-19, 38] | -51.2 | 26,793 | 111 | 38 | 274 |
| 3 | 41 | 61 | 55.0 [23, 89] | 22.7 | 169,470 | 118 | 41 | 37 |
| 4 | 18 | 39 | 22.2 [-22, 70] | -41.4 | 38,395 | 92 | 44 | 61 |
| 5 | 16 | 19 | -21.5 [-41, 2] | -40.1 | -19,233 | 87 | 38 | - |


**R2 robustness: ret10 quintiles**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 39 | 33 | -2.8 [-24, 20] | -30.3 | -6,713 | 89 | 41 | - |
| 2 | 43 | 49 | 30.5 [1, 62] | -2.0 | 115,033 | 121 | 49 | 57 |
| 3 | 29 | 34 | -4.6 [-31, 28] | -51.4 | -6,864 | 65 | 24 | - |
| 4 | 30 | 47 | 58.2 [11, 111] | -6.1 | 115,613 | 141 | 47 | 58 |
| 5 | 13 | 38 | 16.3 [-22, 60] | -12.6 | 29,978 | 99 | 38 | 57 |


**R3 robustness: MA structure**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bear | 26 | 46 | 27.1 [-6, 67] | -3.2 | 64,066 | 118 | 50 | 68 |
| mixed | 77 | 39 | 12.4 [-7, 35] | -47.6 | 97,924 | 104 | 42 | 102 |
| bull | 51 | 41 | 26.8 [-2, 59] | -11.7 | 85,056 | 99 | 35 | 75 |


## G1

Tests (whole sample; Kruskal-Wallis on net % across classes with n>=10; Benjamini-Hochberg 10 % over H1-H9 for this strategy):

| hyp | cells with n>=10 | Kruskal-Wallis p | named Welch diff (pp) | Welch p | BH 10% |
|---|---|---|---|---|---|
| H1 | 5 | 0.284 | bearish minus bullish: -23.5 | 0.240 | no |
| H2 | 3 | 0.810 | low minus high: 33.3 | 0.203 | no |
| H3 | 3 | 0.824 | falling minus rising: 16.8 | 0.274 | no |
| H4 | 1 | - | - | - | no |
| H5 | 3 | 0.584 | gap-down minus flat: -9.7 | 0.521 | no |
| H6 | 3 | 0.203 | down minus up: 5.1 | 0.739 | no |
| H7 | 7 | 0.944 | - | - | no |
| H8 | 7 | 0.942 | - | - | no |
| H9 | 6 | 0.663 | - | - | no |


**H1 direction (ret20 quintiles 1=strongly bearish ... 5=strongly bullish)**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 82 | 35 | 6.2 [-12, 27] | -39.4 | 3,359 | 91 | 39 | 3255 |
| 2 | 66 | 33 | -9.6 [-25, 8] | -51.5 | -32,313 | 80 | 33 | - |
| 3 | 75 | 31 | 9.8 [-14, 36] | -50.7 | 11,760 | 86 | 25 | 654 |
| 4 | 20 | 30 | 4.2 [-33, 52] | -51.2 | -3,404 | 102 | 35 | - |
| 5 | 16 | 56 | 45.7 [-6, 106] | 31.6 | 61,045 | 130 | 44 | 73 |


**H2 VIX level**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| low | 132 | 35 | 11.2 [-5, 30] | -40.7 | 60,878 | 99 | 37 | 211 |
| normal | 117 | 35 | 1.4 [-14, 19] | -51.1 | 15,143 | 84 | 31 | 1040 |
| high | 10 | 20 | -22.1 [-56, 25] | -50.9 | -35,572 | 48 | 20 | - |


**H3 VIX direction (5 sessions)**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| falling | 81 | 38 | 16.5 [-7, 42] | -38.8 | 24,078 | 99 | 36 | 409 |
| flat | 109 | 32 | 1.0 [-15, 19] | -51.1 | -1,629 | 84 | 28 | - |
| rising | 69 | 33 | -0.3 [-17, 17] | -40.0 | 17,999 | 91 | 39 | 505 |


**H4 sudden VIX expansion at signal**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| no | 253 | 35 | 6.1 [-5, 18] | -50.9 | 65,030 | 89 | 33 | 459 |
| yes | 6 | too few | too few | | | | | |


**H5 actual NIFTY opening gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| gap-down | 42 | 33 | 1.8 [-21, 28] | -51.1 | -10,622 | 86 | 36 | - |
| flat | 165 | 37 | 11.5 [-3, 27] | -32.5 | 166,905 | 99 | 38 | 128 |
| gap-up | 52 | 27 | -10.6 [-32, 17] | -51.2 | -115,835 | 65 | 17 | - |


**H6 S&P 500 previous session**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| down | 73 | 34 | 12.5 [-10, 38] | -51.0 | 78,822 | 94 | 33 | 152 |
| flat | 81 | 28 | -2.9 [-22, 18] | -51.3 | -18,634 | 85 | 31 | - |
| up | 99 | 38 | 7.4 [-10, 25] | -38.7 | -24,948 | 92 | 34 | - |


**H7 direction3 x VIX level**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | low | 65 | 34 | -0.9 [-18, 18] | -32.5 | -15,670 | 97 | 43 | - |
| bearish | normal | 73 | 37 | 2.1 [-16, 24] | -51.1 | 22,289 | 82 | 33 | 418 |
| bearish | high | 10 | 20 | -22.1 [-56, 25] | -50.9 | -35,572 | 48 | 20 | - |
| sideways | low | 53 | 32 | 17.5 [-13, 51] | -51.2 | 33,969 | 94 | 28 | 176 |
| sideways | normal | 22 | 27 | -8.9 [-34, 22] | -43.7 | -22,209 | 68 | 18 | - |
| bullish | low | 14 | 50 | 43.3 [-12, 107] | 11.6 | 42,579 | 129 | 43 | 41 |
| bullish | normal | 22 | 36 | 9.5 [-29, 59] | -51.2 | 15,062 | 105 | 36 | 407 |


**H8 direction3 x gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | gap-down | 24 | 25 | -6.6 [-36, 27] | -51.1 | -20,038 | 81 | 38 | - |
| bearish | flat | 86 | 40 | 4.1 [-11, 21] | -31.1 | 64,142 | 96 | 43 | 167 |
| bearish | gap-up | 38 | 29 | -8.5 [-33, 24] | -51.1 | -73,057 | 68 | 21 | - |
| sideways | gap-down | 13 | 31 | -3.1 [-42, 49] | -51.6 | -12,350 | 84 | 23 | - |
| sideways | flat | 51 | 31 | 16.6 [-13, 49] | -36.2 | 50,634 | 92 | 29 | 120 |
| sideways | gap-up | 11 | 27 | -6.7 [-50, 61] | -51.2 | -26,524 | 61 | 9 | - |
| bullish | gap-down | 5 | too few | too few | | | | | |
| bullish | flat | 28 | 39 | 24.9 [-15, 72] | -45.0 | 52,129 | 122 | 39 | 119 |
| bullish | gap-up | 3 | too few | too few | | | | | |


**H9 VIX level x gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| low | gap-down | 19 | 37 | 9.5 [-24, 51] | -18.5 | 11,470 | 98 | 42 | 141 |
| low | flat | 96 | 33 | 10.7 [-9, 32] | -45.0 | 46,835 | 102 | 38 | 206 |
| low | gap-up | 17 | 41 | 15.9 [-24, 67] | -18.2 | 2,573 | 82 | 29 | 463 |
| normal | gap-down | 19 | 32 | -5.8 [-38, 31] | -51.9 | -21,649 | 73 | 26 | - |
| normal | flat | 69 | 42 | 12.7 [-7, 35] | -21.4 | 120,070 | 95 | 39 | 94 |
| normal | gap-up | 29 | 21 | -20.5 [-44, 18] | -51.2 | -83,278 | 64 | 14 | - |
| high | gap-down | 4 | too few | too few | | | | | |
| high | gap-up | 6 | too few | too few | | | | | |


**R1 robustness: ret5 quintiles**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 57 | 35 | -1.2 [-19, 18] | -27.7 | 27,126 | 75 | 33 | 273 |
| 2 | 79 | 25 | -5.4 [-26, 17] | -51.3 | -93,087 | 96 | 33 | - |
| 3 | 66 | 50 | 37.5 [12, 66] | 1.7 | 149,346 | 112 | 39 | 53 |
| 4 | 30 | 33 | 0.4 [-28, 35] | -51.0 | -4,062 | 74 | 30 | - |
| 5 | 27 | 22 | -21.1 [-38, -2] | -51.2 | -38,874 | 70 | 26 | - |


**R2 robustness: ret10 quintiles**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 79 | 28 | -12.5 [-27, 3] | -51.0 | -89,195 | 73 | 32 | - |
| 2 | 75 | 39 | 14.0 [-8, 39] | -50.7 | 57,135 | 113 | 43 | 143 |
| 3 | 41 | 32 | -3.6 [-28, 25] | -51.4 | -28,145 | 65 | 22 | - |
| 4 | 41 | 46 | 42.0 [7, 83] | -10.4 | 107,757 | 117 | 39 | 80 |
| 5 | 23 | 26 | -9.4 [-34, 19] | -51.2 | -7,104 | 72 | 22 | - |


**R3 robustness: MA structure**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bear | 71 | 35 | 5.7 [-14, 29] | -50.8 | 10,738 | 94 | 37 | 913 |
| mixed | 115 | 33 | -0.4 [-15, 17] | -51.2 | -860 | 89 | 33 | - |
| bull | 73 | 36 | 14.5 [-8, 39] | -39.0 | 30,570 | 89 | 32 | 263 |


## G1-C

Tests (whole sample; Kruskal-Wallis on net % across classes with n>=10; Benjamini-Hochberg 10 % over H1-H9 for this strategy):

| hyp | cells with n>=10 | Kruskal-Wallis p | named Welch diff (pp) | Welch p | BH 10% |
|---|---|---|---|---|---|
| H1 | 5 | 0.255 | bearish minus bullish: 30.9 | 0.005 | no |
| H2 | 3 | 0.610 | low minus high: -4.3 | 0.867 | no |
| H3 | 3 | 0.895 | falling minus rising: 14.1 | 0.319 | no |
| H4 | 1 | - | - | - | no |
| H5 | 3 | 0.748 | gap-down minus flat: -1.8 | 0.889 | no |
| H6 | 3 | 0.181 | down minus up: 10.9 | 0.407 | no |
| H7 | 7 | 0.457 | - | - | no |
| H8 | 5 | 0.455 | - | - | no |
| H9 | 6 | 0.540 | - | - | no |


**H1 direction (ret20 quintiles 1=strongly bearish ... 5=strongly bullish)**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 75 | 27 | -12.1 [-29, 7] | -51.4 | -100,603 | 68 | 21 | - |
| 2 | 55 | 40 | 4.4 [-15, 25] | -34.3 | 73,456 | 72 | 24 | 77 |
| 3 | 64 | 34 | -6.1 [-22, 12] | -51.2 | 3,050 | 55 | 17 | 2387 |
| 4 | 29 | 14 | -33.2 [-50, -9] | -51.4 | -78,176 | 70 | 14 | - |
| 5 | 12 | 8 | -42.8 [-55, -29] | -51.6 | -56,507 | 59 | 17 | - |


**H2 VIX level**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| low | 117 | 28 | -13.5 [-25, -1] | -51.4 | -99,314 | 55 | 21 | - |
| normal | 105 | 30 | -7.9 [-22, 8] | -51.2 | -65,556 | 77 | 18 | - |
| high | 13 | 31 | -9.2 [-51, 40] | -50.9 | 6,089 | 67 | 23 | 836 |


**H3 VIX direction (5 sessions)**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| falling | 61 | 36 | 0.6 [-19, 23] | -51.6 | 63,144 | 62 | 18 | 163 |
| flat | 107 | 26 | -15.6 [-28, -3] | -51.3 | -120,970 | 62 | 21 | - |
| rising | 67 | 28 | -13.5 [-30, 4] | -51.1 | -100,955 | 72 | 18 | - |


**H4 sudden VIX expansion at signal**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| no | 231 | 29 | -11.1 [-20, -1] | -51.3 | -170,962 | 63 | 19 | - |
| yes | 4 | too few | too few | | | | | |


**H5 actual NIFTY opening gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| gap-down | 43 | 26 | -11.2 [-31, 13] | -51.4 | 5,306 | 57 | 16 | 1718 |
| flat | 155 | 31 | -9.4 [-21, 3] | -51.2 | -118,481 | 69 | 21 | - |
| gap-up | 37 | 27 | -16.1 [-37, 9] | -51.4 | -45,606 | 59 | 16 | - |


**H6 S&P 500 previous session**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| down | 64 | 31 | -3.0 [-22, 19] | -50.9 | 2,289 | 75 | 22 | 4360 |
| flat | 76 | 33 | -13.3 [-27, 1] | -51.1 | -77,386 | 66 | 16 | - |
| up | 87 | 25 | -13.9 [-29, 3] | -51.7 | -70,036 | 56 | 21 | - |


**H7 direction3 x VIX level**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | low | 55 | 33 | -7.3 [-25, 11] | -51.3 | -16,237 | 65 | 27 | - |
| bearish | normal | 63 | 32 | -2.5 [-22, 20] | -51.1 | -18,810 | 76 | 19 | - |
| bearish | high | 12 | 33 | -8.7 [-53, 46] | -51.0 | 7,900 | 56 | 17 | 644 |
| sideways | low | 45 | 31 | -8.7 [-28, 12] | -51.3 | -5,343 | 49 | 16 | - |
| sideways | normal | 19 | 42 | 0.1 [-31, 40] | -50.9 | 8,392 | 69 | 21 | 224 |
| bullish | low | 17 | 6 | -46.2 [-55, -35] | -51.9 | -77,734 | 36 | 12 | - |
| bullish | normal | 23 | 17 | -29.4 [-50, -0] | -51.4 | -55,138 | 84 | 13 | - |
| bullish | high | 1 | too few | too few | | | | | |


**H8 direction3 x gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | gap-down | 28 | 32 | 3.2 [-26, 35] | -42.6 | 53,145 | 70 | 21 | 142 |
| bearish | flat | 76 | 36 | -1.9 [-19, 17] | -51.2 | -39,665 | 76 | 26 | - |
| bearish | gap-up | 26 | 23 | -23.5 [-44, -2] | -51.5 | -40,628 | 49 | 12 | - |
| sideways | gap-down | 8 | too few | too few | | | | | |
| sideways | flat | 51 | 35 | -7.3 [-25, 12] | -51.3 | 4,516 | 56 | 18 | 1173 |
| sideways | gap-up | 5 | too few | too few | | | | | |
| bullish | gap-down | 7 | too few | too few | | | | | |
| bullish | flat | 28 | 11 | -33.6 [-50, -8] | -51.4 | -83,332 | 73 | 14 | - |
| bullish | gap-up | 6 | too few | too few | | | | | |


**H9 VIX level x gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| low | gap-down | 17 | 6 | -43.5 [-53, -32] | -51.9 | -63,783 | 41 | 12 | - |
| low | flat | 84 | 32 | -7.2 [-22, 9] | -51.2 | -24,754 | 60 | 23 | - |
| low | gap-up | 16 | 31 | -15.0 [-42, 15] | -51.6 | -10,777 | 43 | 19 | - |
| normal | gap-down | 22 | 36 | 2.5 [-29, 39] | -51.0 | 19,623 | 65 | 18 | 205 |
| normal | flat | 69 | 30 | -10.3 [-28, 10] | -51.2 | -72,669 | 81 | 19 | - |
| normal | gap-up | 14 | 21 | -12.4 [-45, 38] | -51.5 | -12,510 | 76 | 14 | - |
| high | gap-down | 4 | too few | too few | | | | | |
| high | flat | 2 | too few | too few | | | | | |
| high | gap-up | 7 | too few | too few | | | | | |


**R1 robustness: ret5 quintiles**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 61 | 28 | -7.5 [-27, 15] | -51.1 | -30,852 | 69 | 21 | - |
| 2 | 66 | 32 | -12.6 [-27, 3] | -51.2 | -48,460 | 64 | 21 | - |
| 3 | 42 | 29 | -13.0 [-33, 11] | -51.3 | -45,152 | 64 | 21 | - |
| 4 | 43 | 28 | -13.5 [-32, 8] | -51.7 | -52,561 | 69 | 19 | - |
| 5 | 23 | 30 | -5.3 [-37, 34] | -51.6 | 18,244 | 51 | 9 | 375 |


**R2 robustness: ret10 quintiles**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 61 | 26 | -7.2 [-27, 16] | -51.2 | -19,973 | 74 | 21 | - |
| 2 | 77 | 31 | -11.7 [-26, 4] | -51.2 | -52,051 | 70 | 18 | - |
| 3 | 34 | 26 | -20.4 [-38, -2] | -51.4 | -39,532 | 59 | 21 | - |
| 4 | 37 | 35 | -8.8 [-29, 12] | -51.2 | -24,616 | 44 | 16 | - |
| 5 | 26 | 27 | -6.6 [-37, 30] | -51.3 | -22,609 | 69 | 23 | - |


**R3 robustness: MA structure**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bear | 72 | 25 | -10.3 [-29, 10] | -51.3 | -91,358 | 73 | 28 | - |
| mixed | 100 | 34 | -11.1 [-23, 2] | -45.0 | -30,663 | 53 | 11 | - |
| bull | 63 | 27 | -10.8 [-28, 9] | -51.5 | -36,759 | 75 | 24 | - |


## XP

Tests (whole sample; Kruskal-Wallis on net % across classes with n>=10; Benjamini-Hochberg 10 % over H1-H9 for this strategy):

| hyp | cells with n>=10 | Kruskal-Wallis p | named Welch diff (pp) | Welch p | BH 10% |
|---|---|---|---|---|---|
| H1 | 4 | 0.918 | bearish minus bullish: -9.5 | 0.756 | no |
| H2 | 2 | 0.625 | - | - | no |
| H3 | 3 | 0.011 | falling minus rising: 52.1 | 0.015 | SURVIVES |
| H4 | 1 | - | - | - | no |
| H5 | 3 | 0.702 | gap-down minus flat: -5.8 | 0.799 | no |
| H6 | 3 | 0.670 | down minus up: 13.8 | 0.537 | no |
| H7 | 5 | 0.705 | - | - | no |
| H8 | 4 | 0.843 | - | - | no |
| H9 | 2 | 0.948 | - | - | no |


**H1 direction (ret20 quintiles 1=strongly bearish ... 5=strongly bullish)**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 33 | 27 | -11.5 [-32, 12] | -19.9 | -35,026 | 48 | 18 | - |
| 2 | 25 | 44 | 4.9 [-24, 35] | -7.4 | -6,868 | 63 | 36 | - |
| 3 | 33 | 33 | -12.0 [-33, 11] | -28.0 | -46,003 | 48 | 18 | - |
| 4 | 10 | 30 | 8.6 [-50, 93] | -23.3 | 5,105 | 61 | 10 | 511 |
| 5 | 6 | too few | too few | | | | | |


**H2 VIX level**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| low | 51 | 35 | -4.8 [-23, 14] | -13.6 | -28,664 | 52 | 22 | - |
| normal | 50 | 32 | -3.2 [-26, 22] | -30.9 | -20,336 | 58 | 24 | - |
| high | 6 | too few | too few | | | | | |


**H3 VIX direction (5 sessions)**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| falling | 30 | 53 | 32.7 [2, 69] | 8.0 | 70,351 | 79 | 37 | 65 |
| flat | 43 | 26 | -20.8 [-38, -1] | -39.1 | -88,188 | 41 | 14 | - |
| rising | 34 | 26 | -19.3 [-39, 4] | -40.6 | -61,798 | 46 | 18 | - |


**H4 sudden VIX expansion at signal**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| no | 105 | 33 | -4.8 [-19, 10] | -24.2 | -70,607 | 54 | 22 | - |
| yes | 2 | too few | too few | | | | | |


**H5 actual NIFTY opening gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| gap-down | 15 | 33 | -8.2 [-45, 32] | -26.5 | -25,475 | 58 | 27 | - |
| flat | 78 | 36 | -2.4 [-19, 15] | -22.6 | -15,754 | 52 | 19 | - |
| gap-up | 14 | 21 | -18.5 [-51, 22] | -34.2 | -38,406 | 56 | 29 | - |


**H6 S&P 500 previous session**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| down | 26 | 31 | -2.7 [-38, 41] | -36.7 | -29,885 | 60 | 23 | - |
| flat | 33 | 36 | 1.5 [-24, 29] | -16.2 | 10,661 | 61 | 30 | 323 |
| up | 45 | 31 | -16.4 [-30, -2] | -24.2 | -78,240 | 42 | 11 | - |


**H7 direction3 x VIX level**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | low | 23 | 35 | 5.8 [-20, 35] | -7.4 | 9,667 | 66 | 35 | 258 |
| bearish | normal | 29 | 34 | -7.7 [-33, 20] | -39.2 | -20,926 | 50 | 24 | - |
| bearish | high | 6 | too few | too few | | | | | |
| sideways | low | 23 | 35 | -13.5 [-40, 15] | -40.1 | -33,513 | 41 | 13 | - |
| sideways | normal | 10 | 30 | -8.5 [-39, 28] | -24.8 | -12,490 | 63 | 30 | - |
| bullish | low | 5 | too few | too few | | | | | |
| bullish | normal | 11 | 27 | 13.6 [-51, 101] | -39.1 | 13,080 | 74 | 18 | 199 |


**H8 direction3 x gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | gap-down | 9 | too few | too few | | | | | |
| bearish | flat | 37 | 35 | -5.4 [-26, 16] | -16.2 | -9,848 | 48 | 22 | - |
| bearish | gap-up | 12 | 25 | -16.7 [-55, 31] | -34.2 | -33,310 | 56 | 33 | - |
| sideways | gap-down | 4 | too few | too few | | | | | |
| sideways | flat | 27 | 37 | -8.5 [-31, 17] | -25.4 | -23,856 | 49 | 19 | - |
| sideways | gap-up | 2 | too few | too few | | | | | |
| bullish | gap-down | 2 | too few | too few | | | | | |
| bullish | flat | 14 | 36 | 17.1 [-33, 83] | -23.3 | 17,950 | 70 | 14 | 145 |


**H9 VIX level x gap**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| low | gap-down | 5 | too few | too few | | | | | |
| low | flat | 41 | 37 | -7.4 [-26, 12] | -13.6 | -28,702 | 45 | 15 | - |
| low | gap-up | 5 | too few | too few | | | | | |
| normal | gap-down | 7 | too few | too few | | | | | |
| normal | flat | 37 | 35 | 3.1 [-23, 35] | -28.9 | 12,948 | 60 | 24 | 351 |
| normal | gap-up | 6 | too few | too few | | | | | |
| high | gap-down | 3 | too few | too few | | | | | |
| high | gap-up | 3 | too few | too few | | | | | |


**R1 robustness: ret5 quintiles**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 27 | 19 | -24.3 [-50, 4] | -55.2 | -63,632 | 43 | 19 | - |
| 2 | 32 | 31 | -12.2 [-31, 9] | -22.7 | -51,092 | 49 | 19 | - |
| 3 | 23 | 35 | -12.2 [-32, 9] | -13.6 | -23,459 | 47 | 17 | - |
| 4 | 13 | 46 | 20.2 [-23, 68] | -12.4 | 21,133 | 65 | 31 | 92 |
| 5 | 12 | 58 | 41.2 [-19, 113] | 17.4 | 37,416 | 91 | 33 | 70 |


**R2 robustness: ret10 quintiles**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| 1 | 32 | 25 | -14.2 [-36, 11] | -29.6 | -53,159 | 42 | 12 | - |
| 2 | 29 | 28 | -7.9 [-37, 28] | -21.0 | -21,799 | 64 | 31 | - |
| 3 | 17 | 41 | 7.3 [-30, 48] | -28.0 | 3,715 | 59 | 24 | 523 |
| 4 | 19 | 42 | -10.9 [-37, 17] | -24.2 | -23,686 | 46 | 16 | - |
| 5 | 10 | 50 | 19.6 [-16, 59] | 2.3 | 15,295 | 66 | 30 | 53 |


**R3 robustness: MA structure**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bear | 33 | 24 | -20.7 [-40, 2] | -28.9 | -74,415 | 39 | 15 | - |
| mixed | 45 | 40 | 0.4 [-19, 21] | -12.4 | -9,447 | 59 | 27 | - |
| bull | 29 | 34 | 3.3 [-28, 40] | -40.1 | 4,227 | 62 | 21 | 1076 |


## Cross-strategy: direction3 (collapsed ret20 classes) under the same regimes


**G1-F**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | 75 | 44 | 11.7 [-5, 30] | -17.3 | 90,674 | 100 | 47 | 93 |
| sideways | 60 | 33 | 16.9 [-10, 47] | -32.6 | 63,606 | 91 | 28 | 96 |
| bullish | 19 | 53 | 59.5 [5, 120] | 35.8 | 92,766 | 167 | 58 | 48 |


**G1**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | 148 | 34 | -0.8 [-13, 13] | -51.0 | -28,953 | 86 | 36 | - |
| sideways | 75 | 31 | 9.8 [-14, 36] | -50.7 | 11,760 | 86 | 25 | 654 |
| bullish | 36 | 42 | 22.6 [-11, 61] | -45.0 | 57,642 | 115 | 39 | 108 |


**G1-C**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | 130 | 32 | -5.1 [-19, 10] | -51.2 | -27,148 | 70 | 22 | - |
| sideways | 64 | 34 | -6.1 [-22, 12] | -51.2 | 3,050 | 55 | 17 | 2387 |
| bullish | 41 | 12 | -36.0 [-49, -18] | -51.4 | -134,683 | 67 | 15 | - |


**XP**

| regime | n | win% | mean net % [95% CI] | median % | total Rs | maxup mean % | maxup>=100% share | top-5% share of Rs |
|---|---|---|---|---|---|---|---|---|
| bearish | 58 | 34 | -4.4 [-22, 14] | -14.7 | -41,894 | 55 | 26 | - |
| sideways | 33 | 33 | -12.0 [-33, 11] | -28.0 | -46,003 | 48 | 18 | - |
| bullish | 16 | 31 | 5.1 [-41, 65] | -36.1 | 8,261 | 61 | 12 | 316 |


## Triple (direction3 x VIX level x gap)

| strategy | cells | smallest cell | cells >= 10 | status |
|---|---|---|---|---|
| G1-F | 27 | 0 | 6 | insufficient (some cells < 10) |
| G1 | 27 | 0 | 10 | insufficient (some cells < 10) |
| G1-C | 27 | 0 | 8 | insufficient (some cells < 10) |
| XP | 27 | 0 | 3 | insufficient (some cells < 10) |

## Supplementary (not in the 9-hypothesis family): days to expiry

| strategy | dte | n | win% | mean net % [95% CI] | total Rs |
|---|---|---|---|---|---|
| G1-F | 1 | 34 | 24 | 15.4 [-26, 65] | 23,028 |
| G1-F | 2+ | 120 | 46 | 20.9 [6, 37] | 224,018 |
| G1 | 1 | 57 | 21 | 2.4 [-26, 35] | -17,015 |
| G1 | 2+ | 202 | 38 | 6.4 [-5, 19] | 57,463 |
| G1-C | 1 | 49 | 12 | -27.5 [-48, -2] | -77,933 |
| G1-C | 2+ | 186 | 34 | -6.4 [-16, 4] | -80,847 |
| XP | 0 | 107 | 34 | -5.3 [-19, 9] | -79,635 |

---
# Part B. PREDICTIVE: rules fixed in advance, discovery = entries to 2025-09-30, then consistency in 2025-10-01 to 2026-10-28

The second half was already seen descriptively (yearly/quarterly tables, one frozen validation): this is a consistency check, not a pristine holdout. Consistency = class mean minus mean of the other trades, same sign in both periods, computed only when the class and the rest both have n >= 10 in that period.


## G1-F

Discovery tests (BH 10 % over H1-H9):

| hyp | cells with n>=10 | Kruskal-Wallis p | named Welch diff (pp) | Welch p | BH 10% |
|---|---|---|---|---|---|
| H1 | 3 | 0.584 | bearish minus bullish: -41.9 | 0.344 | no |
| H2 | 2 | 0.474 | - | - | no |
| H3 | 3 | 0.854 | falling minus rising: 27.5 | 0.388 | no |
| H4 | 1 | - | - | - | no |
| H5 | 1 | - | - | - | no |
| H6 | 3 | 0.221 | down minus up: -10.0 | 0.757 | no |
| H7 | 4 | 0.322 | - | - | no |
| H8 | 3 | 0.978 | - | - | no |
| H9 | 2 | 0.193 | - | - | no |


Class difference vs the rest of the trades (pp of net %), discovery vs second half:

| hyp | class | n disc | diff disc | n second | diff second | same sign |
|---|---|---|---|---|---|---|
| H1 | bearish | 38 | -32.4 | 37 | -0.1 | True |
| H1 | sideways | 25 | 17.8 | 35 | -21.3 | False |
| H1 | bullish | 12 | 30.8 | 7 | - | not testable |
| H2 | low | 37 | -5.4 | 71 | - | not testable |
| H2 | normal | 38 | 5.4 | 8 | - | not testable |
| H2 | high | 0 | - | 0 | - | not testable |
| H3 | falling | 25 | 13.2 | 25 | 10.5 | True |
| H3 | flat | 36 | 2.2 | 36 | -12.6 | False |
| H3 | rising | 14 | -23.0 | 18 | 4.9 | False |
| H4 | no | 75 | - | 77 | - | not testable |
| H4 | yes | 0 | - | 2 | - | not testable |
| H5 | gap-down | 9 | - | 12 | -29.6 | not testable |
| H5 | flat | 66 | - | 67 | 29.6 | not testable |
| H5 | gap-up | 0 | - | 0 | - | not testable |
| H6 | down | 23 | 6.6 | 28 | -4.2 | False |
| H6 | flat | 24 | -31.4 | 24 | -3.2 | True |
| H6 | up | 28 | 23.2 | 24 | 0.2 | True |

By half-year (cells with n >= 10 only):

| half-year | class | n | mean net % in class | mean net % all trades that half-year |
|---|---|---|---|---|
| 2024H2 | dir3=bearish | 14 | 10.1 | 32.6 |
| 2025H1 | dir3=bearish | 11 | 40.2 | 40.3 |
| 2025H2 | dir3=bearish | 19 | -9.4 | 3.5 |
| 2025H2 | vix_level=low | 49 | 0.3 | 3.5 |
| 2025H2 | vix_dir=rising | 11 | -3.0 | 3.5 |
| 2026H1 | dir3=bearish | 10 | 29.4 | 64.1 |
| 2026H1 | vix_level=low | 16 | 57.5 | 64.1 |
| 2026H2 | dir3=bearish | 21 | 8.7 | -5.6 |
| 2026H2 | vix_level=low | 33 | -11.2 | -5.6 |

## G1

Discovery tests (BH 10 % over H1-H9):

| hyp | cells with n>=10 | Kruskal-Wallis p | named Welch diff (pp) | Welch p | BH 10% |
|---|---|---|---|---|---|
| H1 | 4 | 0.290 | bearish minus bullish: -17.6 | 0.511 | no |
| H2 | 2 | 0.533 | - | - | no |
| H3 | 3 | 0.329 | falling minus rising: 39.2 | 0.084 | no |
| H4 | 1 | - | - | - | no |
| H5 | 3 | 0.929 | gap-down minus flat: 2.3 | 0.941 | no |
| H6 | 3 | 0.024 | down minus up: -3.4 | 0.886 | no |
| H7 | 5 | 0.428 | - | - | no |
| H8 | 4 | 0.799 | - | - | no |
| H9 | 3 | 0.968 | - | - | no |


Class difference vs the rest of the trades (pp of net %), discovery vs second half:

| hyp | class | n disc | diff disc | n second | diff second | same sign |
|---|---|---|---|---|---|---|
| H1 | bearish | 74 | -18.3 | 74 | -11.5 | True |
| H1 | sideways | 32 | 14.8 | 43 | -0.2 | False |
| H1 | bullish | 22 | 12.0 | 14 | 30.0 | True |
| H2 | low | 48 | 16.5 | 84 | 11.7 | True |
| H2 | normal | 79 | -14.3 | 38 | -6.0 | True |
| H2 | high | 1 | - | 9 | - | not testable |
| H3 | falling | 40 | 25.1 | 41 | 7.1 | True |
| H3 | flat | 58 | -1.0 | 51 | -15.5 | True |
| H3 | rising | 30 | -28.7 | 39 | 10.3 | False |
| H4 | no | 128 | - | 125 | - | not testable |
| H4 | yes | 0 | - | 6 | - | not testable |
| H5 | gap-down | 13 | 5.3 | 29 | -7.7 | False |
| H5 | flat | 87 | 7.8 | 78 | 23.6 | True |
| H5 | gap-up | 28 | -12.8 | 24 | -29.1 | True |
| H6 | down | 31 | 6.7 | 42 | 13.3 | True |
| H6 | flat | 45 | -20.5 | 36 | -4.0 | True |
| H6 | up | 52 | 14.3 | 47 | -8.9 | False |

By half-year (cells with n >= 10 only):

| half-year | class | n | mean net % in class | mean net % all trades that half-year |
|---|---|---|---|---|
| 2024H2 | dir3=bearish | 24 | 19.5 | 30.0 |
| 2025H1 | dir3=bearish | 31 | -2.6 | 1.5 |
| 2025H1 | dir3=bullish | 17 | 16.7 | 1.5 |
| 2025H1 | vix_dir=rising | 18 | -12.1 | 1.5 |
| 2025H2 | dir3=bearish | 25 | -11.6 | 3.0 |
| 2025H2 | vix_level=low | 60 | 0.4 | 3.0 |
| 2025H2 | vix_dir=rising | 12 | -8.6 | 3.0 |
| 2026H1 | dir3=bearish | 38 | -7.6 | 8.5 |
| 2026H1 | vix_level=low | 21 | 37.9 | 8.5 |
| 2026H1 | vix_dir=rising | 23 | 13.5 | 8.5 |
| 2026H1 | gap_cls=gap-down | 17 | -9.3 | 8.5 |
| 2026H2 | dir3=bearish | 30 | 2.2 | -7.1 |
| 2026H2 | vix_level=low | 37 | -6.1 | -7.1 |

## G1-C

Discovery tests (BH 10 % over H1-H9):

| hyp | cells with n>=10 | Kruskal-Wallis p | named Welch diff (pp) | Welch p | BH 10% |
|---|---|---|---|---|---|
| H1 | 4 | 0.234 | bearish minus bullish: 32.3 | 0.102 | no |
| H2 | 2 | 0.619 | - | - | no |
| H3 | 3 | 0.666 | falling minus rising: 35.4 | 0.144 | no |
| H4 | 1 | - | - | - | no |
| H5 | 3 | 0.826 | gap-down minus flat: -13.0 | 0.446 | no |
| H6 | 3 | 0.462 | down minus up: 11.8 | 0.564 | no |
| H7 | 5 | 0.177 | - | - | no |
| H8 | 4 | 0.210 | - | - | no |
| H9 | 3 | 0.659 | - | - | no |


Class difference vs the rest of the trades (pp of net %), discovery vs second half:

| hyp | class | n disc | diff disc | n second | diff second | same sign |
|---|---|---|---|---|---|---|
| H1 | bearish | 63 | 10.3 | 67 | 14.4 | True |
| H1 | sideways | 30 | 11.1 | 34 | 2.5 | True |
| H1 | bullish | 19 | -33.4 | 22 | -27.7 | True |
| H2 | low | 44 | -3.1 | 73 | -3.2 | True |
| H2 | normal | 65 | -2.2 | 40 | 6.5 | False |
| H2 | high | 3 | - | 10 | -9.0 | not testable |
| H3 | falling | 29 | 36.2 | 32 | -3.5 | False |
| H3 | flat | 51 | -18.1 | 56 | -0.3 | True |
| H3 | rising | 32 | -12.1 | 35 | 3.7 | False |
| H4 | no | 111 | - | 120 | - | not testable |
| H4 | yes | 1 | - | 3 | - | not testable |
| H5 | gap-down | 22 | -16.3 | 21 | 14.5 | False |
| H5 | flat | 75 | -0.4 | 80 | 7.6 | False |
| H5 | gap-up | 15 | 23.0 | 22 | -25.7 | False |
| H6 | down | 34 | 10.5 | 30 | 9.1 | True |
| H6 | flat | 34 | -2.3 | 42 | -3.9 | True |
| H6 | up | 44 | -7.3 | 43 | -3.9 | True |

By half-year (cells with n >= 10 only):

| half-year | class | n | mean net % in class | mean net % all trades that half-year |
|---|---|---|---|---|
| 2024H2 | dir3=bearish | 20 | -9.0 | -17.7 |
| 2025H1 | dir3=bearish | 29 | 20.3 | 12.0 |
| 2025H1 | dir3=bullish | 16 | -28.3 | 12.0 |
| 2025H1 | vix_dir=rising | 19 | -20.3 | 12.0 |
| 2025H1 | gap_cls=gap-down | 13 | -9.3 | 12.0 |
| 2025H2 | dir3=bearish | 24 | 2.0 | -11.2 |
| 2025H2 | vix_level=low | 62 | -11.2 | -11.2 |
| 2025H2 | vix_dir=rising | 10 | 0.1 | -11.2 |
| 2026H1 | dir3=bearish | 38 | -13.8 | -19.7 |
| 2026H1 | vix_level=low | 17 | -21.1 | -19.7 |
| 2026H1 | vix_dir=rising | 19 | -29.1 | -19.7 |
| 2026H1 | gap_cls=gap-down | 13 | 19.0 | -19.7 |
| 2026H2 | dir3=bearish | 19 | -31.4 | -29.6 |
| 2026H2 | vix_level=low | 23 | -43.3 | -29.6 |
| 2026H2 | vix_dir=rising | 11 | -10.6 | -29.6 |

## XP

Discovery tests (BH 10 % over H1-H9):

| hyp | cells with n>=10 | Kruskal-Wallis p | named Welch diff (pp) | Welch p | BH 10% |
|---|---|---|---|---|---|
| H1 | 3 | 0.257 | bearish minus bullish: -43.6 | 0.355 | no |
| H2 | 2 | 0.239 | - | - | no |
| H3 | 3 | 0.000 | falling minus rising: 120.1 | 0.001 | SURVIVES |
| H4 | 1 | - | - | - | no |
| H5 | 1 | - | - | - | no |
| H6 | 3 | 0.526 | down minus up: 10.7 | 0.789 | no |
| H7 | 2 | 0.338 | - | - | no |
| H8 | 2 | 0.342 | - | - | no |
| H9 | 2 | 0.544 | - | - | no |


Class difference vs the rest of the trades (pp of net %), discovery vs second half:

| hyp | class | n disc | diff disc | n second | diff second | same sign |
|---|---|---|---|---|---|---|
| H1 | bearish | 29 | -37.9 | 29 | 38.7 | False |
| H1 | sideways | 13 | 22.2 | 20 | -31.6 | False |
| H1 | bullish | 10 | 33.3 | 6 | - | not testable |
| H2 | low | 20 | 12.3 | 31 | -5.4 | False |
| H2 | normal | 31 | -4.1 | 19 | 6.5 | False |
| H2 | high | 1 | - | 5 | - | not testable |
| H3 | falling | 14 | 112.7 | 16 | -0.4 | False |
| H3 | flat | 22 | -43.3 | 21 | -10.0 | True |
| H3 | rising | 16 | -54.5 | 18 | 11.1 | False |
| H4 | no | 52 | - | 53 | - | not testable |
| H4 | yes | 0 | - | 2 | - | not testable |
| H5 | gap-down | 7 | - | 8 | - | not testable |
| H5 | flat | 39 | 37.2 | 39 | -13.1 | False |
| H5 | gap-up | 6 | - | 8 | - | not testable |
| H6 | down | 12 | 13.1 | 14 | -4.3 | False |
| H6 | flat | 17 | -9.3 | 16 | 28.2 | False |
| H6 | up | 23 | -1.1 | 22 | -37.7 | True |

By half-year (cells with n >= 10 only):

| half-year | class | n | mean net % in class | mean net % all trades that half-year |
|---|---|---|---|---|
| 2025H1 | dir3=bearish | 13 | -23.4 | 10.4 |
| 2025H2 | dir3=bearish | 11 | -14.2 | -24.4 |
| 2025H2 | vix_level=low | 27 | -24.4 | -24.4 |
| 2026H1 | dir3=bearish | 16 | 3.4 | -6.4 |
| 2026H1 | vix_dir=rising | 10 | -10.5 | -6.4 |
| 2026H2 | dir3=bearish | 10 | 19.0 | 2.6 |
| 2026H2 | vix_level=low | 12 | -7.6 | 2.6 |

---
Files: boundaries.json, regime_labels.csv, regime_tables.csv (all sections), regime_tests.csv, regime_consistency.csv, regime_halfyear.csv, triple_status.csv, supp_*.csv, hashes.txt; scripts regimes.py, regime_tables.py, build_draft.py.