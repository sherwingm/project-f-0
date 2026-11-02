# S1 fade · carry with a profit-target sell (pre-registration)

Written 2 Nov 2026, before any multi-day minute candle of these trades is fetched or looked at (user: "Yes,
pre-register it"). Research only: nothing live changes; a pass only justifies a paper shadow record, the user's call.

## Why
On the 339 v12 backtest trades, the option's best price after the buy is far above what v12 takes: median max up
+16 % while held (1-minute highs), +44 % by day 0's close, +58 % by expiry (daily closes after day 0). The carry rule
retired on 17 Oct 2026 (−20 % stop, 25 % trail, T-1) lost −10.8 % a trade (t −2.6): the stop sold the dips before
the later rise. Question: does a resting profit-target sell **without a stop**, held to T-1, capture the later rise?

**Caveat stated now:** the idea came from looking at this data's max up, and the v12 trail (start +10 %, 2 % gap)
was itself chosen in-sample. A pass here is weaker than a clean out-of-sample one.

## Trades (fixed)
The 339 trades of `data/results/S1_fade_entry_quality_audit_trades.csv`: v12 backtest, day 0 Oct 2024 – Aug 2026,
entry = 09:16 candle open + 1 tick (realistic entry B, ≥ ₹2, one lot ₹600 – 8,000), one lot. Halves = the file's
`half` (train before 2025-11-03: 154; test from it: 185).

## Data
1-minute candles of each contract from day 0 to its expiry, Upstox expired-instruments API (GitHub job
`stock-options-probe` → `fetch_band_minutes carry`; contracts file `data/results/S1_v10_bandcarry_contracts.csv`
with `from` = day 0, `to` = expiry). Day 0 candles are the same source as the earlier studies.
- **T-1** = the last session with candles before the expiry date; the exit is its 15:19 candle.
- **Coverage:** a trade is complete if it has candles on day 0 and on its T-1 session. Incomplete trades are listed
  and dropped from every rule alike; if fewer than 90 % are complete the report says so and the verdict is "no
  verdict (data)".

## Exits compared (same trades, real charges both legs)
- **v12** (base): −20 % stop on the low from 09:17, trail on at +10 %, sells at 2 % below the highest high since,
  else 15:19 close − 1 tick on day 0. Recomputed from the candles with the code of
  `scanner/fade_entry_quality.py`; must equal the file's `v12 net %` on ≥ 95 % of trades (else stop and report).
- **C50** (primary): a sell limit at entry × 1.50 rounded up to the tick, resting from 09:17 on day 0 to T-1. It fills
  at the limit on the first candle whose high ≥ limit + 1 tick (a print through the price). No stop. If never filled,
  sell at T-1's 15:19 close − 1 tick (floor 1 tick).
- **C100** (secondary): the same at entry × 2.00.
- **H50** (idea 2, blend): half the money by v12, half by C50: net % = (v12 % + C50 %) / 2. Live it needs 2 lots;
  only 17 % of these trades fit 2 lots in ₹8,000, so a pass would need a ₹16,000 cap per signal (stated in the report).

A target candle that opens above the limit after an overnight gap still fills at the limit (conservative).

## Report per rule
N, win %, mean and median net % of premium, total ₹ (one lot; H50 at one lot's premium), date-clustered t, both
halves, sessions held (median), fills at the target vs at T-1 (and the mean of each), worst trade. Paired against v12:
mean difference and its date-clustered t.

## Pass (fixed now), per rule
All of: mean net % > 0 with t ≥ 2; mean above v12's on the same trades with paired-difference t ≥ 2; mean > 0 and above
v12 in both halves. C50 is the primary test; C100 and H50 are secondary and reported, with "secondary" next to any pass.

## Files
`scanner/fade_target_carry.py` (new) → `data/results/S1_fade_target_carry.md`, `_trades.csv`.
