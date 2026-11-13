# Amendments to stress_audit/PREREG.md (each written before the run it concerns)

A1 (13 Nov 2026, before any stress number). Section 3, "order-conservative" for S1. Writing the simulator showed that the "high first, then low" ordering
inside a candle is NOT uniformly the worse one: in a candle that touches both the -20 % stop and +10 %, high-first sells at the trail level (better than the
stop), while in a candle that only makes a new high and then dips, high-first sells earlier than the baseline. So the report shows three lines, all
labelled: order H (high first, as pre-registered), the per-trade WORST of baseline and order H, and the per-trade BEST of the two. The worst/best lines are
bounds chosen by outcome, shown to size the ambiguity; they are never a baseline, never a recommendation, and never used for a verdict. Trades whose result
differs between the two orderings are counted as "ambiguous candle" trades.

A2 (13 Nov 2026, before any stress number). S1 slippage scenario C2 also reports "S1 daily-test slippage" by market-cap category (large 1 %, mid 2 %, small
3 % per side, `scanner/backtest_s1_v4.py` SLIPPAGE; category from `S1_v10_trades.csv`, "unknown" 3 %). In every slippage scenario the stop and trail levels
are computed from the price actually paid (including slippage), because that is what a live stop references.

A3 (13 Nov 2026, before any stress number). Extra informational S1 scenarios, run in addition to the list: C5s STT by trade date (the baseline charges the
2026 STT on every date), S3t trail sold at the next candle's open (the late-fill twin of S3).

A4 (13 Nov 2026, before any stress number). One bounded interpretation: for G1 "exposure" is hours from entry to exit per trade and the share of trading
sessions with an open position; for S1 it is minutes from the entry candle to the exit candle and the share of trading sessions with a trade.
