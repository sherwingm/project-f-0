# Overnight / GIFT regimes: DRAFT (Agent 3b, 17 Nov 2026)

Definitions are the fixed ones of Amendment 1 (`PREREG_REGIME.md`), unchanged; direction3 and VIX level are the labels of agent 3 (`regime_labels.csv`, `boundaries.json`). Original recorded trade results only (`context_dataset.csv`: G1-F 154, G1 259, G1-C 235, XP 107; entries 2024-10-01 to 2026-10-23). Nothing re-simulated; MAE not computed (coordinator merges). No download, no network, no VM, no holdout or sealed data. Raw p-values only: the coordinator applies the final Benjamini-Hochberg over the enlarged family.

## Method notes (read first)
- GIFT near-month = earliest NIFTY futures expiry not yet expired on that date (`FUTIDXNIFTY...`; 867 days, 2023-07-03 to 2026-11-17, no zero opens).
- H10 GIFT overnight % = GIFT first trade of the trade date (`open`, 06:30 IST) / `prev_settle` of the same row - 1 (the file's previous-settlement field). Classes: gap-up >= +0.3, gap-down <= -0.3, flat.
- H11 = actual NIFTY opening gap (`gap_pct`, 09:15 open vs previous close, from the context dataset) minus H10 return: stronger >= +0.2, weaker <= -0.2, in line between.
- H12 Asia = mean of Nikkei and Hang Seng opening gaps (open / previous close of that market, local dates); up / down +/-0.3. Where one market was closed the other alone is used (87 of 755 rows); 7 rows have neither. Reported only as an overnight descriptor.
- Combinations: C1 direction3 x GIFT class, C2 VIX level x GIFT class (VIX 'high' has no GIFT trades with n >= 10), C3 triple: **insufficient for all four strategies** (smallest cell 0; at most 3 to 7 of 27 cells reach 10; `gift_triple_status.csv` lists the counts).
- Missing: 6 trade rows have no GIFT value (all excluded from GIFT tables).
- Cells with n < 10 are marked 'too few' in `gift_tables.csv` (numbers are kept there only for audit) and carry no conclusion. Bootstrap = resample trading days, 5000 draws, seed 20261117. Net % = net rupees / premium paid; rupees separate.
- Robustness (outside the family, labelled R1/R2): the same classes using the PREVIOUS ROW's `settlement` instead of this row's `prev_settle`.

## Important data limitation found (affects how much weight H10 / H11 can carry)
- Against the actual NIFTY opening gap (NIFTY eod open / previous close, all 505 days of the trade window), the pre-registered GIFT measure (open / `prev_settle`) has correlation **0.50**; the previous-row variant has **0.73** (0.75 excluding the 23 monthly roll days; `gift_diagnostics.txt`). So `prev_settle` is a noisier overnight reference than the previous session's last settlement. The previous-row variant has its own flaw: on roll days it compares the new contract with the expiring one, adding about +0.56 points of carry. Neither is the true 09:00 pre-open level (not available). The pre-registered definition was kept; the weaker agreement means H11 'stronger / weaker' classes partly capture reference noise.
- Trade-window GIFT class counts (all days): gap-down 32, gap-up 60, flat 413. On trade days the GIFT gap classes are small: G1-F 8 / 134 / 10.

## What GIFT adds on the trade days (descriptive; `gift_vs_actual_descriptive.csv`)
G1-F: correlation GIFT return vs actual gap only 0.22 on its 152 days (G1 0.36, G1-C 0.62, XP 0.48), because G1-F's filter removes gap-ups and compresses the actual gap.
- GIFT gap-down (8): mean GIFT -0.40 %, mean actual gap -0.26 %; actual gap-down 3, flat 5, gap-up 0.
- GIFT flat (134): actual gap-down 17, flat 117, gap-up 0.
- GIFT gap-up (10): mean GIFT +0.43 %, mean actual gap +0.05 %; actual gap-down 1, flat 9, gap-up 0 (G1-F cannot contain an actual gap-up). **So 10 G1-F trades had a GIFT gap-up with a flat/down actual open (9 flat, 1 down)**: GIFT pointed up, the cash market did not follow; these are exactly the trades the actual-gap filter let through.
Other strategies: GIFT gap-up is followed by an actual gap-up in about half the cases (G1 14 of 28, G1-C 13 of 30, XP 4 of 8); GIFT gap-down by an actual gap-down in half or more (G1 7 of 14, G1-C 9 of 17, XP 6 of 9).

# Part A. EXPLANATORY (whole sample)

## G1-F (primary, 152 trades with GIFT and with Asia)
Tests: H10 Kruskal-Wallis uses only the 2 classes with n >= 10 (flat and gap-up); gap-down (8) is too few. Welch gap-down vs gap-up: not testable (n 8 / 10). Flat minus rest -4.1 pp, Welch p 0.89.

| class | n | win % | mean net % [95 % CI] | median % | total Rs | max up mean % | share max up >= 100 % | top-5 % share of Rs |
|---|---|---|---|---|---|---|---|---|
| H10 GIFT gap-down (n 8, too few) | 8 | 50 | 52.0 [-31, 165] | -15.4 | 50,109 | 135 | 38 | 89 |
| H10 GIFT flat | 134 | 41 | 20.1 [4, 37] | -15.6 | 192,289 | 107 | 43 | 76 |
| H10 GIFT gap-up | 10 | 40 | 1.9 [-46, 61] | -41.8 | 11,950 | 70 | 30 | 144 |
| H11 weaker | 41 | 46 | 23.6 [-4, 56] | -8.3 | 58,363 | 80 | 27 | 92 |
| H11 in line | 88 | 38 | 16.0 [-4, 38] | -28.2 | 101,794 | 109 | 43 | 105 |
| H11 stronger | 23 | 48 | 32.8 [-10, 82] | -2.0 | 94,191 | 141 | 61 | 68 |
| H12 Asia down | 41 | 39 | 19.7 [-11, 56] | -50.8 | 71,427 | 105 | 39 | 108 |
| H12 Asia flat | 64 | 44 | 17.9 [-4, 42] | -16.1 | 104,064 | 97 | 39 | 78 |
| H12 Asia up | 47 | 40 | 25.0 [-2, 55] | -11.7 | 78,856 | 118 | 47 | 82 |

p-values (raw): H10 KW 0.609 (flat vs gap-up only); H11 KW 0.628, in line minus rest -10.9 pp (p 0.52), weaker minus stronger -9.2 pp (p 0.75); H12 KW 0.583, down minus up -5.4 pp (p 0.82). Nothing separates the classes.
Combinations (n >= 10 cells only): C1 bearish|flat 64 (+14.7 %), sideways|flat 54 (+21.2 %), bullish|flat 16 (+38.1 %); every gap-up / gap-down cell has n <= 5, so GIFT cannot be examined inside direction classes. KW p 0.787. C2: low|flat 98 (+13.7 %), normal|flat 36 (+37.5 % [11, 66], win 58 %); KW p 0.020, which is the known normal-VIX effect of agent 3 (H2 / H9) and not a GIFT effect: all GIFT gap cells are n <= 5. Triple: insufficient.
Robustness (outside the family): prev-row GIFT class (gap-down 28 / flat 109 / gap-up 15): KW 0.685, nothing. Prev-row indicated-vs-actual: weaker 28 (+43.6 % [7, 89]), in line 100 (+6.3 % [-10, 24]), stronger 24 (+53.5 % [8, 107]); KW 0.031; in line minus rest -41.9 pp (Welch p 0.027). Mean |actual gap - GIFT| is 0.09 points when 'in line' and 0.34 to 0.40 otherwise: the better days are days on which the cash open differed from GIFT in either direction. This is a lead from a noisy robustness variant, nominal, not in the family; under the pre-registered measure H11 shows no such pattern (in line -10.9 pp, p 0.52).

## Other strategies, one line each (whole sample, mean net %)
- G1 puts: GIFT gap-down (14) +7.8, flat (215) +9.9, gap-up (28) -25.1 [-45, 0] (win 25 %, Rs -56,428); KW 0.160; gap-down minus gap-up +32.9 pp (p 0.37). H11 and H12 flat (KW 0.93 / 0.67). Nothing near significance.
- G1-C calls: GIFT gap-down (17) -32.7 [-49, -13], win 12 %, flat -8.7, gap-up -8.7; KW 0.930 (only 2 classes with n >= 10 differ little), gap-down minus gap-up -24.1 pp (p 0.16); H11 stronger (60) -20.4 vs weaker -4.2 (KW 0.19); Asia up -16.2 vs flat -4.3 (KW 0.37). Nothing significant. Prev-row ivsa KW 0.046 nominal.
- XP expiry-day straddle: GIFT flat (90) -0.7 vs the 17 non-flat days (flat minus rest +29.2 pp, Welch p 0.071, nominal); gap-down (9, too few) -35.2, gap-up (8, too few) -23.8; H11 stronger (21) -26.3 (win 10 %) vs in line +0.7, KW 0.33; Asia up (35) -19.6 vs flat +2.5, KW 0.74. Nothing significant.

# Part B. PREDICTIVE (discovery = entries to 2025-09-30; second half 2025-10-01 to 2026-10-28, already seen descriptively, consistency check only)

## G1-F
- H10: 134 flat trades are the only class testable in discovery (58) and the second half (76); gap-down 8 (all discovery) and gap-up 10 (8 discovery, 2 second half) are never testable in both periods. **No consistency check is possible.**
- H11 (class mean minus rest, discovery / second half): weaker +18.1 / -6.3 (different sign); in line -27.7 / +5.0 (different sign); stronger +23.6 / +0.9 (same sign, second-half n 10, essentially zero). KW p 0.880 discovery, 0.529 second half.
- H12 Asia: down +40.5 / -24.4; flat -44.9 / +33.6; up +23.9 / -8.9: signs flip, none consistent. KW p 0.208 / 0.316.
- Prev-row variant (robustness only): 'in line' minus rest -47.7 pp in discovery (n 44 vs 30) and -33.7 pp in the second half (n 56 vs 22): same sign and same order of size in both periods. It is the only same-sign pattern in this study; it is a robustness-variant finding with a noisy reference, so it is a lead, not a result.
- By half-year (n >= 10 cells; mean of class vs all trades that half-year): GIFT flat tracks the whole half-year (e.g. 2025H2 +7.8 vs +3.5; 2026H1 +70.1 vs +64.1; 2026H2 -5.9 vs -5.6) because it is nearly all trades. 'In line' under the pre-registered measure: 2024H2 +7.7 vs +32.6, 2025H1 +28.1 vs +40.3, 2025H2 +10.5 vs +3.5, 2026H1 +62.1 vs +64.1, 2026H2 -12.3 vs -5.6: below the half-year mean in 4 of 5. Asia down / up: 2025H2 -6.0 / +2.3 vs +3.5; 2026H2 -6.9 / +5.1 vs -5.6: no stable pattern. Large half-year swings (e.g. 2026H1 +64 %, 2026H2 -5.6 %) are not explained by overnight class.

## Secondary strategies (consistency, same-sign yes / no)
- G1: H10 flat (n 98 / 117) +13.8 / +49.6 same sign (flat is nearly all trades; the rest is only 29 / 13 trades, so little information); H11 weaker same sign (+9.1 / +1.8), in line and stronger flip; H12 up same sign (-8.5 / -22.7), others flip.
- G1-C: H10 gap-down 17 trades (9 / 8) never testable in a period; H11 weaker same sign small (+13.7 / +1.6); stronger +12.8 / -30.8 flips; H12 up -4.7 / -10.5 and flat +9.1 / +9.3 same sign small.
- XP: H10 not testable; H11 stronger -22.0 in the second half only (discovery n 9); H12 up -16.4 / -23.7, down +5.7 / +8.2, flat +9.4 / +16.6 same sign across periods, intervals include zero, whole-sample KW 0.74.

# Conclusion for the coordinator
For G1-F none of H10, H11, H12 or the GIFT combinations shows an effect (all raw p >= 0.52 except the VIX-driven C2 0.020). GIFT classes are almost empty for G1-F (8 gap-down, 10 gap-up of 152), so the question cannot be answered for the tails. The only same-sign pattern in both periods is a robustness-variant one (previous-row GIFT reference, 'cash open in line with GIFT' worse than days when it differed), not part of the pre-registered family and resting on a reference that is carry-contaminated on roll days. No rule change is suggested; this is absence of evidence in small cells.
