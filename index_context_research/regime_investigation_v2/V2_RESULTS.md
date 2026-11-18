# Deduplicated, higher-power re-test of G1-F's conditions: results (18 Nov 2026)

Plan: `PREREG_V2_POWER.md` (commit 12ca29fa1, before any number). Script: `scripts/v2_power_retest.py`; raw output `results/run_output.txt`, tables in `results/`. Data, missing-bar handling and quote filters untouched (stored labels read as they are). Year 1 = entries to 2025-09-30 (75 trades); Year 2 = after (79), read-only at the end.

**Pipeline found:** `interim/agent5_integrity/audit_06_multiple_comparisons.py` (36 G1-F "main" tests, Kruskal-Wallis p on the whole 154 trades, Benjamini-Hochberg 10 %). It was a rank test, not a raw-mean t-test. That script and its output were not edited; the new study is a separate script.

## Step 1: redundancy
- 36 tests; 1 dropped (FII/DII cash, A4:H15): the data starts Dec 2025, so there are no Year-1 trades. 35 usable.
- 22 pairs have |Spearman r| >= 0.70 in Year 1. Average-linkage clusters (cut 0.30) give **effective N = 23** (from 36).
- Clusters (representative = most Year-1 observations, never by p):
  - 5 tests: direction (H1), direction x VIX (H7), direction x gap (H8), direction x GIFT (both versions). Rep H1.
  - 4 tests: VIX level (H2), VIX x gap (H9), VIX x GIFT (both versions). Rep H2.
  - 4 tests: S&P overnight (H6, X01), US VIX spike (X04), risk-on/off (H13). Rep H6.
  - 2 each: Asia (two builds), FII futures level + FII options level. Reps A3b:H12, X08.
  - 13 singles stay alone.
- Full mapping: `results/cluster_map.csv`; correlation matrix: `results/year1_spearman_matrix.csv`.

## Step 2 and 3: before vs after (Benjamini-Hochberg, q < 0.10 to pass, unchanged)
- **Before** (original, whole sample, 36 tests, Kruskal-Wallis): 4 with p < 0.05, smallest p 0.020, smallest q 0.367, survivors 0.
- **Year 1 only, 35 tests, Kruskal-Wallis, no dedup:** 1 with p < 0.05, smallest p 0.043, smallest q 0.845.
- **After, N = 23, Year 1 only** (smallest p / smallest q / survivors):
  - Permutation F on winsorised returns (primary): 0.012 / 0.285 / 0
  - Winsorised Welch t (lowest vs highest class): 0.291 / 0.984 / 0
  - Mann-Whitney U (same pair): 0.206 / 0.960 / 0
  - Permutation of the mean difference (same pair): 0.236 / 0.975 / 0
  - Spearman rank, full Year-1 sample: 0.220 / 0.990 / 0
  - Kruskal-Wallis: 0.043 / 0.906 / 0
- **Sibling pooling:** G1 puts share G1-F's entry logic (G1-F is a subset); G1-C is the opposite side and was not pooled. Permutation within half-years on 128 G1 Year-1 trades: smallest p 0.109, q 0.90, survivors 0.

## Surviving signals (q < 0.10 in Year 1)
**None, under any method.** Year 2 was therefore not needed to judge anything. For information only (these are NOT survivors), the three lowest-q representatives in Year 2:
- Direction (H1): the strongest-direction class has 4 trades in Year 1 (mean +190 %) and 2 in Year 2 (+67 %); Year-2 edge small and thin.
- VIX level (H2): normal minus low is +5 points in Year 1, +80 in Year 2 (8 normal-VIX trades); this is the known pattern that appears only later in time.
- Cash open vs GIFT, same-contract (H11): stronger minus weaker -5 points in Year 1, +35 in Year 2: the sign flipped.

## Honest reading
- The statistics changed as asked, the answer did not: the best corrected q improved from 0.37 to 0.29 on the primary method, still far from 0.10; every other method is worse.
- The single low p (direction, p 0.012) is produced by a class of 4 trades with a mean of +190 %; my rule allowed classes of 3 or more, so tiny cells can dominate the F statistic. The rule was fixed before the numbers; I report it rather than change it. Spearman on the same signal (rho 0.10, p 0.40) shows nothing across all 75 trades.
- Winsorising and rank tests removed the extra variance from big winners, and the results moved toward "nothing", which supports the earlier reading that a few trades drive the means.
- Power: with about 75 trades split in groups, differences under about 60 points are invisible. "No evidence", not "no effect".
- Limits: neither year is blind (the whole-sample and discovery results existed before this study); FII/DII cash could not be tested in Year 1; the 3-trade minimum for a class is generous.
- Decision: no condition passes; nothing here supports changing G1-F or any filter.
