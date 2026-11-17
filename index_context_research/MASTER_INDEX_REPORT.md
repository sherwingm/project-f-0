# Master index report: when should the existing index strategies trade? (16 Nov 2026)

Plan `PREREG_CONTEXT.md`; data and limits `DATA_LIMITATIONS.md`; per-topic files in this folder; registry `HYPOTHESIS_REGISTRY.md`. Research only: no existing strategy, paper system, server or recorder was touched; **nothing was committed**.
Sets: G1 puts (259), G1-F (154), G1-C calls (235), XP expiry-day straddles (107): NIFTY option replays, Oct 2024 to Oct 2026, 1 lot, engine fills and dated charges.
Method: 17 pre-entry features x 4 sets = 67 cells; split at the discovery median; discovery = entries to 2025-09-30, Benjamini-Hochberg 10 %; validation (from 2025-10-01) opened once for frozen survivors.

## The answer
**No pre-entry factor produced a validated improvement.** 67 cells were tested. One survived the multiple-testing correction in discovery (XP: the 5-session VIX change) and **it reversed in validation** (the sign flipped, t +1.2). Nothing was promoted; combinations were not run because nothing passed. The strategies' good and bad periods cannot be predicted from what was available before entry in this data.

## Results A to L
- **A. Best individual factor:** none validated. The strongest discovery result was XP with the VIX change over the previous 5 sessions: after a VIX rise the straddle averaged -38 % (7.7 % of trades reached +100 %), after a fall +39 % (42 %), difference -77 points, t -3.7. In validation the pattern reversed (+22.8 points, t +1.2), so it is FAILED, not a finding.
- **B. Best combination:** not run (no validated factor; 25-60 trades per cell would be too few). The earlier combination study on index-futures proxies also found nothing.
- **C. Best index:** not answerable: only NIFTY has trade history for these rules. FINNIFTY / MIDCPNIFTY / BANKEX have no usable data here.
- **D. Best market conditions (descriptive, not predictive):** G1 did best in the middle VIX tercile (+25 %) and with a low or mid opening gap (+17 % / +8 %), worst in high VIX (-15 %) and with a big gap (-8 %), matching the stress audit. G1-F is positive in every year (+33 %, +16 %, +19 %); G1 is +30 %, +2 %, +2 %; G1-C is -18 %, 0 %, -23 %; XP -5 %, -7 %, -3 %. None of these splits survived correction.
- **E. Worst conditions:** G1-C in 2026 (-23 %, profit factor 0.48) and XP in every year; G1 and G1-C after a VIX rise (nominal, p 0.06 / 0.055).
- **F. No-trade conditions:** none validated. The event window (RBI / Budget / FOMC) looks worse for G1 (-11 % vs +11 %, 15 trades) and G1-F (-5 % vs +30 %, 10 trades) but is far from significant (p 0.15-0.22).
- **G. News advantage:** not answered: no timestamped news source beyond scheduled dates (see `NEWS_IMPACT_ANALYSIS.md`).
- **H. Pre-market advantage (GIFT):** no evidence. The settlement-based proxies are not the pre-open gap; XP's nominal result (GIFT previous-session change, t +2.1) did not survive correction. The real question remains untestable with daily settlements.
- **I. Institutional advantage:** none. FII futures long share and its change: all p between 0.2 and 0.9 (nothing close); futures price / OI changes: only XP's price change is nominal (p 0.04), and it did not survive correction.
- **J. Volatility advantage:** no validated one. VIX level, percentile and 5-day change: the XP result above failed validation; the others are nominal at best (p 0.055-0.12).
- **K. Options advantage:** the closest to a lead, still not a finding. ATM implied volatility at entry: G1 puts did better when IV was low (+30 % vs -13 %, t -2.5, p 0.012) and G1-C calls better when IV was high (+12 % vs -20 %, t +2.1); the put-call OI ratio for G1-C (+16 % vs -25 %, t +2.7, p 0.007). They have opposite signs between puts and calls and do not survive the correction for 67 tests, so they are hypotheses for the live record, not rules.
- **L. Yearly stability:** only the G1-F positive result repeats in all three calendar periods (in-sample filters). Every conditional effect found in 2024-25 weakened or reversed later (XP's VIX effect, G1-C's 2026 loss).

## Honest reading
- With 107-259 trades per set, 67 cells and about 420 earlier looks at the same data, a feature must be very strong to stand out; none was. The two near-misses are in the options data (IV, put-call OI), which also have the noisiest inputs (last-trade prices, no bid / ask).
- Profit concentration: for G1 the top 5 % of trades earned more (Rs 298k) than the set's whole total (Rs 40k); for G1-F they earned Rs 190k of Rs 247k.
- What this changes: nothing in any rule. What would help: the live paper record accumulating, a bid / ask recorder at entry, and (if wanted) real GIFT pre-open data from a vendor.

## Index of files
`YEARLY_INDEX_PERFORMANCE.md`, `NEWS_IMPACT_ANALYSIS.md`, `GIFT_NIFTY_ANALYSIS.md`, `FII_DII_ANALYSIS.md`, `INDEX_FUTURES_ANALYSIS.md`, `VIX_VOLATILITY_ANALYSIS.md`, `INDEX_BREADTH_ANALYSIS.md`, `INDEX_OPTIONS_ANALYSIS.md`, `EXECUTION_DISCIPLINE_ANALYSIS.md`, `INDIVIDUAL_FACTOR_RESULTS.md`, `COMBINATION_ANALYSIS.md`, `OUT_OF_SAMPLE_VALIDATION.md`, `DATA_LIMITATIONS.md`, `HYPOTHESIS_REGISTRY.md`, `EXPERIMENT_MANIFEST.json`; code in `scripts/`, datasets in `results/` (`context_dataset.csv`, `ctx_*.csv`); raw GIFT files in `data/gift/` (git-ignored).
