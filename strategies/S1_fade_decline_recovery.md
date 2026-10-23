# S1 fade · early decline and recovery (descriptive, historical candles)

Written 24 Oct 2026, before any number. The user's decision: descriptive research on the history now, no ML. Nothing
live changes.

## Data
- The 339 live-set trades of `data/results/S1_fade_entry_quality_audit_trades.csv` (day 0 from 2024-10-17 to
  2026-08-17). Entry = 09:16 candle open + 1 tick.
- Option 1-minute candles of the results day, 09:17–15:19 (`S1_v10_*_minutes.csv`).
- **Measurement basis: 1-minute OHLC PROXY.** A candle low is not a bid we know we could have sold at, and a candle
  high is not a sellable price. Within one candle the order of high and low is unknown.

## Definitions (fixed now)
- **Decline of x %** (x = 5, 10, 15, 20): the first candle from 09:17 whose low is ≤ entry × (1 − x/100). This is the
  decline minute.
- **Recovery to entry within N minutes** (N = 1, 3, 5, 10, 15, and "by 15:19"): any candle **after** the decline
  candle, from the next minute up to N minutes later, whose high is ≥ entry. The decline candle itself is excluded,
  because its high could have come before its low.
- **Recovery to +10 %** (v12's trail start) by 15:19: the same, with high ≥ 1.10 × entry.
- **Closed above entry**: the 15:19 candle close is > entry.
- Every count is shown with its denominator (the trades that reached that decline) and split by half (train before
  2025-11-03, test from it).

## After the actual v12 stop
For the trades v12 stopped (on candles), from the minute after the stop: whether a candle later reached entry, +10 %
and +20 %, how many minutes that took, and whether 15:19 closed above entry. Plus the net P&L v10 (hold to 15:19) would
have made on those same trades, from the existing file.

## Reading rules
- Descriptive only: no threshold here becomes a rule. A recovery seen on candle highs may not have been sellable.
- "Recovered" does not mean "held profitably": a trade can touch entry and fall again.
- Groups under 20 trades are marked inconclusive.
- Live best-bid data (from 26 Oct) will answer the same questions on real bids; until then, these are estimates.
