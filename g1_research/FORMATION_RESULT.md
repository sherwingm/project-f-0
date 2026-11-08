# Formation patterns, one at a time: result (2026-11-08). Plan: FORMATION_PREREG.md. Script: scripts/g1_formation.py
28 price-shape facts (opening range, the stretch before the break, the breakout candle, yesterday's candle), 53 rules, each alone.
Outcome: max up through the next close >= +100 %. 259 signals (128 discovery, 131 validation).

**Result: no formation pattern. 0 candidates** (best discovery q = 0.67; the FDR bar was 0.10).
- Strongest in discovery: OR width small vs the last 5 days' range (51 % vs 28 % reached +100 %, p 0.019, q 0.67); a calm breakout candle (49 % vs 29 %).
- Information only: on validation those fall to 32 % vs 31 % and 30 % vs 32 %, so they were noise.
- With 53 rules, a handful of p < 0.05 is what chance gives.
