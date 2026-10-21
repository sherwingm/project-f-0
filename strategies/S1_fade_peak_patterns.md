# S1 fade · learn from 1-minute candles how the up-moves to the peak happen, then test an exit built on it

**Pre-registered 2026-10-21**, before any pattern is looked at. The user: "I like to capture the peak of the trade ...
learn the pattern of how the positive percentage is made in the up-movement ... go through the 1-min candles, find how
to make the profit by seeing the patterns." Winners peak at about +100 % on average but v12 keeps about a quarter.
**Nothing live changes.** This file fixes the **protocol**, so the patterns cannot be fitted to the data they are
judged on.

## Data
- Trades: the live fade set (entry B ≥ ₹2, one lot ₹600–8,000; `data/results/S1_fade_cheap_dte_trades.csv`, 1 lot) and
  the refused set (entry B < ₹2; `data/results/S1_refused_listing_price_trades.csv`, as many lots as fit under ₹8,000).
  Entry B = the 09:16 candle open + 1 tick. 1-minute option candles from the five minute sets; stock 1-minute candles
  from `data/cache/intraday/` where present (Kotak's history before Nov 2025 is known to be imperfect).
- **Train** = day 0 before 2025-11-03 (Oct 2024 – Oct 2025): 154 live + 130 refused = 284 trades.
- **Test** = from 2025-11-03 (Nov 2025 – Aug 2026): about 185 live + 144 refused. **Not opened in phases A and B**: the
  agents get a copy of the train trades and candles only.

## Phase A · patterns (train only, descriptive)
Paths to the peak (time, steps, pullbacks before the peak and their depth), what happens after the peak, volume, time
of day, early signs in the first minutes, the stock's own move. Findings are reported with counts on the train set.

## Phase B · exit rules (train only)
At most **5** candidate exit rules, each written as an exact algorithm on 1-minute candles that a live bot could run
(no future information: only candles up to the current one), with the −20 % stop kept unless a rule says otherwise.
Each is evaluated on train against v12 (−20 % stop, trail on at +10 %, 2 % gap); **one is chosen on train** (highest
train mean net %, live set) and **frozen in an addendum to this file before phase C**.

## Phase C · one test (test half, once)
The frozen rule vs v12 on the test half. **Pass:** on the live set, test mean > 0 and the per-trade difference to v12
> 0 with date-clustered t ≥ 2. The refused set is reported beside it (descriptive). Real charges; fills at the candle's
level or open − 1 tick as in `scanner/fade_stop_trail.py`. A pass would only justify a paper shadow tag (the user's
decision). Note: the test half has been seen by earlier exit studies (aggregate numbers only), so a pass is weaker than
a fully clean one.
