# S1 fade · a trail that widens once the gain passes +40 % (backtest, realistic entry)

**Pre-registered 2026-10-21**, before any of these numbers is computed. The user, after the v12 worked example (sold
at +41.5 % by the 2 % trail while the option later reached +100 %): "trail on at +10 %, sells 5 % below the peak ...
why can't we increase this [the 5 %] as the profit went up more than 40 %". **Nothing live changes.**

## The exit (1-minute candles, as `scanner/fade_stop_trail.py` `walk`)
- Entry B = the 09:16 candle open + 1 tick; candles from 09:17 to 15:19; real charges; tick ₹0.05 before 2025-11-03,
  ₹0.01 from it.
- **Stop:** the first candle whose low ≤ 0.80 × entry sells at min(stop, that candle's open) − 1 tick (checked first).
- **Trail on** once a candle's high ≥ 1.10 × entry. Peak = the highest high of the candles **before** the current one
  since it switched on.
- **The gap widens:** gap = **G1** while the peak is below entry × (1 + 40 %); **G2** once the peak is at or above it.
  Level = peak × (1 − gap). The first candle whose low ≤ the level sells at min(level, that candle's open) − 1 tick.
- **Main version:** the level follows the gap as written (when the peak crosses +40 %, the level can step down to give
  the wider room at once). **Sensitivity:** a "ratchet" version where the level never moves down.
- Else the 15:19 close − 1 tick.

## Variants
- Main grid (threshold +40 %, as the user said): G1 ∈ {2 %, 5 %} × G2 ∈ {10 %, 15 %, 20 %} → 6 variants.
- Reported beside them (not chosen from): v12 (gap 2 % flat, live), gap 5 % flat (the shadow tag), v11 (stop only),
  v10 (no stop); thresholds +30 % and +60 %; the ratchet version.

## Trades
1. **The live fade set** (the test): the contracts of `data/results/S1_fade_cheap_dte_trades.csv` with entry B ≥ ₹2 and
   one lot ₹600–8,000 (339 trades, Oct 2024 – Aug 2026), 1 lot each.
2. Descriptive: the refused sub-₹2 signals with listing price ₹2–7 and ₹2–10
   (`data/results/S1_refused_listing_price_trades.csv`), as many lots as fit under ₹8,000.

## Test (fixed now), on set 1
Pick the main-grid variant with the highest mean net % on **train** (day 0 before 2025-11-03). It passes only if on
**test** (from 2025-11-03) its mean > 0 and its per-trade difference to v12 (gap 2 %) is > 0 with date-clustered t ≥ 2.
The test half has been looked at by earlier exit studies, so a pass is weaker than a clean one. A pass would only
justify a paper shadow tag (the user's decision).

Also reported: how each exit ended (stop, trail, 15:19), and on trades whose peak reached +40 %, the mean kept by each.
