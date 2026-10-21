# S1 fade · wider stops, a 1-minute wait, trailing stops and re-entry (backtest, realistic entry)

**Pre-registered 2026-10-21**, before any of these numbers is computed. The user saw a live trade stopped at −20 % that
later went to +83 %. In the realistic-entry backtest, 54 of 294 stopped trades later rose ≥ 50 % above entry. The user:
"check by keeping the stop loss at each percentage like 25 %, 28 %, 30 %; if hit, wait 30 s to 1 min; keep a trailing
stop to sell, starting after +20 % or from the start; include any other idea". **Nothing live changes.**

## Data
- The 409 trades of `S1_fade_realistic_entry.md`: entry **B** = the 09:16 candle open + 1 tick, 1-minute option
  candles to 15:19 (`S1_v10_bandv10_*.csv`). Tick ₹0.05 before 2025-11-03, ₹0.01 from it. Real charges
  (`server.charges`), no extra slippage. Default exit: the 15:19 close − 1 tick.
- **Train** = day 0 before 2025-11-03 (189 trades). **Test** = from 2025-11-03 (220 trades).

## Exit mechanics (1-minute candles; candles are walked from the stop start to 15:19)
- **Touch stop** (as v11): the first candle whose low ≤ entry × (1 − S) sells at min(stop, that candle's open) − 1 tick.
- **1-minute wait** (the user's "wait 30 s to 1 min"; finer data does not exist): a candle must **close** ≤ the
  stop; then sell at the **next** candle's open − 1 tick. A dip that recovers within its minute does not sell.
- **Trailing stop (A, D):** active once a candle's high ≥ entry × (1 + A) (A = 0 means from the start). Peak = the
  highest high of the candles **before** the current one since activation (the activating candle's high counts from
  the next candle). Sell when a candle's low ≤ peak × (1 − D), at min(that level, the candle's open) − 1 tick.
  Within a candle the stop is checked before the trail.
- **Re-entry:** after a v11 stop, buy again once a candle closes ≥ the original entry, at the next candle's open + 1
  tick (once per day, only before 15:00). The new position has its own −20 % touch stop, else 15:19. Net = both
  round trips with charges, as % of the first premium.

## Variants (all reported)
1. **Stop width:** S = 20, 25, 28, 30, 35, 40, 50 %, plus no stop; × touch / 1-minute wait; × stop start 09:17, 09:30,
   10:00 (43 variants). v11 = S 20, touch, 09:17.
2. **Trailing:** base stop = none, 20 % touch, or 30 % touch (from 09:17); × A = 0, 20, 50 %; × D = 15, 20, 30 % (27).
3. **Re-entry:** v11 + re-entry (1).

## The test (fixed now)
- On **train**, pick the variant with the highest mean net % of premium (ties: the simpler one, i.e. fewer rules).
- It **passes** only if on **test**: its mean net % > 0, AND the per-trade difference to v11 (variant − v11, % of
  premium) has mean > 0 with date-clustered **t ≥ 2**.
- The best variant of each family on train is also shown on test (descriptive; not a pass).
- With about 70 variants tried, a train winner is expected to look good by luck; only the test half counts. A pass
  would only justify a paper shadow tag (the user's decision), never a live change from this data alone.
- Hindsight peaks (the highest price after the stop) are not a strategy and are not reported as one.
