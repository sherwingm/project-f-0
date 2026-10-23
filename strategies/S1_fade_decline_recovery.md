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

## Addendum (24 Oct 2026, written after the first pass, BEFORE the measures below were computed)
The first pass (the definitions above) was run first. The user's brief of 24 Oct adds these measures; each is fixed
here before it is calculated.

**Per trade:** entry price; the actual v12 exit time and reason; the candle high and low over the held minutes
(09:17 through the exit minute).

**For each decline threshold x (5, 10, 15, 20 %):**
- *Reached*: the decline minute as defined above.
- *Sufficient observations for a window of N minutes*: at least N candles left after the decline minute up to 15:19.
  Each window's denominator is these trades, not all that fell.
- *Before the exit / after the exit*: a recovery candle at or before the v12 exit minute counts as **before exit**
  (the trade was still held); one after the exit minute counts as **after exit** (hypothetical, never realised P&L).
  A decline that happened after the exit is counted separately as a "post-exit decline".
- *Recovery relative to entry*: a later candle high ≥ entry.
- *Recovery from the threshold*: a later candle high ≥ the decline low × 1.10 (a 10 % bounce from where it fell),
  reported next to the recovery to entry.
- *Later best and worst*: the highest high and lowest low after the decline minute, as % of entry.
- *Realised net*: v12's net ₹ as booked by the backtest. Any post-exit recovery is shown in a separate column and is
  never added to it.
- Split by v12 exit reason (stop / trail) and by half.
- *Same-candle ambiguity*: trades whose decline and v12 exit fall in the same minute, and those whose held high and
  low share one candle, are counted and flagged.

**Data-quality exclusions:**
- Historical backtest exits are all same day by construction (none on the next session). The 8 next-session paper
  exits of 16–19 Oct are excluded from any paper-trade comparison.
- The 11 rows with impossible strike distances (strike / stock open of 1.9–9.5, consistent with stock prices adjusted
  for later splits or bonuses; not verified against an outside source) are excluded from every strike-distance
  statement.

**Entry-price check (paper trades):** for each of the 23 paper positions, the contract's 1-minute candle of the entry
minute from Kotak's history (read-only, run on the server with its own key). The fill is labelled:
- *consistent*: inside the candle's low–high;
- *outside the traded range*: unconfirmed;
- *unresolved*: no candle returned.
ADANIENSOL 23 Oct is also checked against the second-by-second entry probe. A fill inside the range is still not proof
the ask was there.

**Entry quality:** only entry-time features with valid data (premium; strike distance on the 328 valid rows; sessions
to expiry; the opening gap). Spread and the stock's price at 09:16 have no historical source and are reported as
missing.
