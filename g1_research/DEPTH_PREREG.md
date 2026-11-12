# Minimum breakout size: pre-registered 2026-11-12 (before any number was computed)

**Question (the user, 12 Nov):** G1 buys on the first 1-minute close outside the 09:15-09:29 range, however small the break. "Check with that":
what if the breakout candle must close at least some percentage beyond the range?

**Depth** = how far the signal candle's close is beyond the range edge, as a % of the edge: puts (below the low) (low - close) / low x 100; calls
(above the high) (close - high) / high x 100. Today's rule has no minimum (median put depth about 0.02 %).

## Test (fixed now; nothing added after the numbers)
- **Variant A, the one tested:** the day is decided exactly as now (the first close outside the range, 09:30-13:00, buy the next minute). The trade
  is TAKEN only if the depth is at least X. A skipped day stays skipped (no waiting for a bigger break). So a threshold only removes trades,
  and the kept trades are a clean subset of today's trades: same entry, strike, stop and exit (next session's close, 50 % stop), no new fills.
  (A "wait for the first close at least X % beyond" variant would change entry times; it is NOT tested here.)
- **Thresholds X:** 0.05 %, 0.10 %, 0.15 %, 0.20 % (and X = 0 = today's rule as the baseline).
- **Trades:** the 259 G1 put signals, G1-F (the subset passing its three filters) and the 235 call-mirror signals, Oct 2024 to Oct 2026, ATM, the
  engine's fills and charges from `g1_research/data/verify_strikes_trades.csv` (1x and 2x costs). Depth computed from the NIFTY 1-minute spot.
- **Measures, max up first:** for kept and for dropped trades: share reaching +100 % (peak through the next close, no stop), mean and median max up;
  then win %, average and median net % of premium, total Rs for 1 lot, the number of trades.
- **Decision rule:** a threshold HELPS only if (1) the kept trades' average net % exceeds the dropped trades' (Welch t >= 2.0), (2) the kept average
  is above the baseline average and the kept total Rs does not fall by more than the dropped trades' losses justify (reported), (3) the kept-minus-dropped
  difference has the same sign in both halves (Oct 2024-Sep 2025, Oct 2025-Oct 2026), and (4) it holds at 2x costs. Otherwise: "no evidence
  a minimum size helps". With four thresholds and three sets, one pass would be reported with the number of tries.
- Read in-sample (G1-F's filters were chosen on this same period). A pass would still need its own forward paper run; no live rule changes.
