# Minimum breakout size: result (2026-11-12). Plan: DEPTH_PREREG.md (+ Amendment 1). Script: scripts/verify_depth.py. Data: data/verify_depth_trades.csv, results/verify_depth_summary.csv
Variant A: take the trade only if the signal close is at least X % beyond the range edge (kept = a clean subset of today's trades; live exit, ATM, engine fills and charges, Oct 2024 - Oct 2026).

**Depth is tiny: median 0.017 % beyond the range edge** (10th 0.003 %, 75th 0.031 %, 90th 0.050 %). The first thresholds (0.05-0.20 %) keep 27 / 4 / 0 of 259 puts, so thresholds 0.01 / 0.02 / 0.03 % were added (Amendment 1).

**Verdict: a minimum size does NOT help. 0 of 12 tests passed.**
G1 puts (259), by minimum depth: kept trades vs dropped trades (booked average per trade; max up reaching +100 % in brackets):
| Minimum | Kept | Kept avg (+100 %) | Dropped avg (+100 %) | Kept - dropped (t) | Both halves | 2x costs |
|---|---|---|---|---|---|---|
| 0.01 % | 177 | -6.3 % (28 %) | +30.9 % (45 %) | -37.1 (-2.71) | -36.9 / -38.5 | -2.72 |
| 0.02 % | 117 | -4.8 % (30 %) | +14.0 % (37 %) | -18.8 (-1.62) | -20.3 / -18.2 | -1.64 |
| 0.03 % | 68 | +11.3 % (35 %) | +3.4 % (33 %) | +7.8 (0.56) | +9.5 / +6.4 | 0.52 |
| 0.05 % | 27 | -11.3 % (30 %) | +7.4 % (34 %) | -18.7 (-1.65) | -42.6 / +3.8 | -1.78 |
- G1-F puts: the same shape (0.01 %: kept +5.5 % vs dropped +50.1 %, t -2.33; 0.03 %: +26.4 % vs +17.3 %, t 0.49).
- Call mirror (235): no effect at any threshold (kept - dropped between -6 and +3 points, t within +/- 0.5); the calls lose at every size.
- Max up agrees with the booked result: the tiniest breaks (under 0.01 %) reached +100 % MORE often (45 % vs 28 %), not less.

**Reading:** a bigger break is not a better one. If anything the opposite for puts: breaks under 0.01 % did best (t -2.71 for "kept worse than dropped"). With 12 tries that is suggestive only (about p 0.007 unadjusted, 0.08 after 12 tries) and it is the reverse of the rule asked about; it is NOT adopted. Nothing live changes; G1 / G1-F / G1-C keep "any close outside the range".
