# GIFT overnight, same-contract definition: ADDENDUM (Agent 3b, 17 Nov 2026)

Requested by the coordinator. Same-contract return = open of the near-month contract on D / settlement of the SAME expiry on the previous GIFT trade date - 1 (`gift_samecontract.py`). Thresholds unchanged (+/-0.3 %; indicated vs actual +/-0.2 points). Statistics, bootstrap (resample days, 5000, seed 20261117), raw p-values as in `GIFT_REGIME_DRAFT.md`. Outputs: `gift_labels_samecontract.csv`, `gift_tables_samecontract.csv`, `gift_tests_samecontract.csv`, `gift_consistency_samecontract.csv`, `gift_halfyear_samecontract.csv`, `gift_triple_status_samecontract.csv`, `gift_vs_actual_descriptive_samecontract.csv`, `gift_samecontract_checks.txt`. In these files R1/R2 are the prev_settle-column version.
Missing: 1 of 867 GIFT days has no same-expiry row on the previous date; 6 trade rows missing (G1-F 2, G1 2, G1-C 2, XP 0). Nothing else changed; H12 (Asia) is identical to the earlier run.

## Three versions side by side (nothing chosen by looking at returns)
| version | definition | corr with actual NIFTY gap, 823 days | corr, 505 trade-window days | G1-F days |
|---|---|---|---|---|
| A. prev_settle column (first run) | open / row `prev_settle` - 1 | 0.50 | 0.50 | 0.22 |
| B. previous-row settlement | open / previous row's settlement (near-month of that row) - 1; carry-contaminated on 23 roll days | 0.73 | 0.73 | 0.62 (G1-F, see earlier) |
| C. same-contract (faithful to Amendment 1) | open / settlement of the same expiry on the previous trade date - 1 | **0.75** | **0.75** | **0.64** |
The coordinator treats **C as primary** (faithful implementation of the amendment text); A and B stay visible. (The 823 days are those with a NIFTY eod open; the coordinator's 825 differs by 2 days with a missing value.) C differs from B on only 40 days (roll days).

## Class sizes with C
All trades: G1-F gap-down 28 / flat 111 / gap-up 13 (152); G1 43 / 165 / 49; G1-C 33 / 149 / 51; XP 18 / 72 / 17. G1-F GIFT gap-down (28): actual open flat 16, gap-down 12. G1-F GIFT gap-up (13): actual open flat 13 (none can be gap-up by construction). So 13 G1-F trades had a GIFT gap-up with a flat actual open.

## G1-F, whole sample (explanatory)
| class | n | win % | mean net % [95 % CI] | median % | total Rs | max up mean % | top-5 % share |
|---|---|---|---|---|---|---|---|
| H10 GIFT gap-down | 28 | 39 | 26.7 [-13, 74] | -34.8 | 87,769 | 118 | 78 |
| H10 flat | 111 | 41 | 19.4 [2, 38] | -17.3 | 155,621 | 103 | 71 |
| H10 gap-up | 13 | 46 | 17.5 [-26, 72] | -11.7 | 10,958 | 102 | 208 |
| H11 weaker | 26 | 58 | 39.5 [2, 87] | 6.4 | 52,230 | 124 | 69 |
| H11 in line | 102 | 34 | 8.0 [-9, 26] | -34.4 | 60,122 | 91 | 176 |
| H11 stronger | 24 | 54 | 53.5 [8, 107] | 19.7 | 141,995 | 148 | 48 |
p-values (raw): H10 Kruskal-Wallis 0.947; gap-down minus gap-up +9.1 pp (Welch p 0.80); flat minus rest -4.4 pp (p 0.83). H11 Kruskal-Wallis **0.077**; in line minus the rest **-38.1 pp (Welch p 0.048)**; weaker minus stronger -14.0 pp (p 0.68). H12 unchanged (0.583).
Combinations: direction3 x GIFT KW p 0.743 (cells with n >= 10: bearish|gap-down 13 +5.4 %, bearish|flat 54 +11.0 %, sideways|gap-down 10 +6.4 %, sideways|flat 46 +19.3 %, bullish|flat 11 +61.1 %; other cells <= 6). VIX x GIFT KW p 0.164 (normal|flat 29 +30.7 % [4, 59] vs low|flat 82 +15.4 %). Triple: insufficient for all strategies (G1-F 4 of 27 cells reach 10).

## G1-F, predictive (class minus rest, discovery / second half)
- H10: gap-down +13.7 / +1.0 (same sign, both near zero, CI wide); flat +7.6 / -15.8 (flips); gap-up not testable (4 discovery). KW p 0.57 / 0.40.
- H11: in line **-40.6 / -33.7 (same sign, same size)**, Welch p 0.145 in discovery (46 vs 28) and 0.205 in the second half (56 vs 22); weaker +32.9 / +18.5 (same sign, discovery n 10); stronger +31.0 / not testable (second half 6). KW p 0.556 discovery, 0.033 second half (2 classes).
- Half-years, 'in line' vs all trades: 2024H2 +1.5 vs +32.6; 2025H1 +17.8 vs +40.3; 2025H2 +4.5 vs +3.5; 2026H1 +45.8 vs +64.1; 2026H2 -10.6 vs -5.6: below the half-year mean in 4 of 5. GIFT flat tracks the half-year mean (nearly all trades). Half-year swings are not explained by overnight class.

## Other strategies (C, whole sample)
- G1: gap-up (49) vs flat; consistency H10 gap-up -34.5 / -5.9 same sign; H11 in line -26.1 / -5.1 same sign. No raw p below 0.1.
- G1-C: H11 Kruskal-Wallis p 0.039 (nominal), stronger (38) vs weaker (50): weaker minus stronger +31.2 pp (Welch p 0.064); stronger -43.7 in the second half, -0.5 vs rest in discovery. In line same sign both periods (-10.9 / -3.4). Not significant after any correction of a 15-hypothesis family.
- XP: nothing below p 0.1; gap classes mostly too few.

## Reading
Under the faithful definition H10 (GIFT gap class) shows nothing for G1-F (p 0.95). H11 (indicated vs actual) now carries the pattern previously seen only in the robustness variant: G1-F days when the cash open was in line with GIFT did worse (+8.0 % vs +39.5 % weaker and +53.5 % stronger), nominal p 0.048 (Welch) / 0.077 (Kruskal-Wallis), same sign and size in discovery and second half (-40.6 / -33.7 pp) but not individually significant in either (0.145 / 0.205). The pre-registered first-run version (A) shows no such pattern, and A is the least faithful and the noisiest reference. The H11 raw p (0.077 Kruskal-Wallis) would have to pass Benjamini-Hochberg over 15 hypotheses per strategy (first threshold 0.0067 at 10 %), which it does not; and it is a statement about days of a divergence between GIFT and the cash open, not a tradable rule (the cash open is known before entry, so no look-ahead, but nothing here is a rule change). Both versions A and B remain in the first draft and in the files.
