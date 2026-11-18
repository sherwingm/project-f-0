# Pre-registration: deduplicated, higher-power re-test of G1-F's 36 conditions (18 Nov 2026)

Written and committed BEFORE any number of this study is computed. Method change only: same 154 recorded G1-F trades, same condition labels, same q < 0.10. No data fetching, missing-bar handling or quote-warning filters are touched (labels are read as stored).

## Honest status of the data
- Year 1 = entries to 2025-09-30 (75 trades, the original "discovery"); Year 2 = 2025-10-01 to 2026-10-28 (79 trades). **Neither year is blind to the researcher or to the project: whole-sample and discovery-only p-values for these conditions already exist** (earlier result: 0 of 31 discovery tests below 0.05, smallest 0.070). Year 2 was also seen descriptively. The guardrail below limits what this study does, it cannot restore blindness.
- The earlier family used Kruskal-Wallis p on the whole 154 trades, not a t-test (reference only).

## Step 1: remove redundant tests (Year 1 only, return-blind)
- The 36 tests = every G1-F row of `interim/agent5_integrity/consolidated_tests.csv` with family "main" and a non-missing p.
- Each test gets one numeric / ordinal Year-1 signal (table in the script: the underlying continuous value where one exists, else the ordered class code; combinations = sum of their two ordinal codes; unordered classes (FII/DII, events, risk) coded in the stated order).
- Spearman correlation matrix on Year-1 trades (pairs need >= 25 common trades). Average-linkage hierarchical clustering on distance 1 - |r|, cut at 0.30 (so members of a cluster have mean |r| >= 0.70; average linkage avoids chaining).
- Representative of a cluster = the member with the most non-missing Year-1 values; ties go to the earlier hypothesis id in order A3, A3b, A4. **Never chosen by p-value or return.** Tests whose signal is constant in Year 1 are dropped and listed.
- New effective N = number of clusters (printed with the mapping).

## Step 2: tests, per representative, Year 1 only
- Returns = recorded net % per trade.
- (a) **Primary** (the p-value that enters the pre-declared FDR): permutation test of the between-class F statistic on winsorised returns (2 % each tail of the Year-1 sample of that test), 10,000 label shuffles, seed 20261118, over all classes with >= 3 trades.
- (b) Winsorised Welch t, (c) Mann-Whitney U, (d) permutation of the raw mean difference (10,000), all on the **extreme pair**: lowest vs highest ordinal class, each >= 5 trades; otherwise missing.
- (e) Spearman rank correlation of net % with the continuous / ordinal signal over all Year-1 trades (needs >= 8 distinct values; skipped for classes-only signals).
- (f) Reference: Kruskal-Wallis on Year 1 alone.
- Benjamini-Hochberg is run separately for each method over the N representatives; **pass = q < 0.10** (unchanged; no bucket cut-off may be changed).
- Sibling pooling: G1-F is a strict subset of G1 (same entry logic with filters); G1-C is the opposite side (calls), not pooled. Diagnostic only: permutation omnibus test on G1 Year-1 trades (labels shuffled within half-years) for each representative.

## Step 3: reporting
- Table: original 36 (whole-sample KW p, q) vs Year-1-only KW (36) vs the N-test methods.
- Survivors (q < 0.10 in Year 1 under any method) get their Year-1 edge and then, read-only, the same edge in Year 2 (sign and size). If there are none, the three lowest-q representatives are shown in Year 2 for information, labelled as not survivors. Year 2 is never used to choose anything.
- Power note: with about 75 trades, differences under about 60 points cannot be detected; a non-pass is "no evidence".
