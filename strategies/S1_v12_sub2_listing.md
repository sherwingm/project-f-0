# S1 v12 fade · below-Rs 2 rule: buy refused signals whose listing-day price was Rs 2-7 (live paper from 2026-10-23)

**Decided 2026-10-22 by the user:** "keep that 2-7 to the live", exit v12, real paper trades. Paper only.

## The rule
- Applies only to a fade signal the normal walk refuses because of the Rs 2 floor ("premium below Rs 2" or "never fits").
- At that poll, on the same walk path (nearest strike, away from the money): the **first strike with a two-sided quote
  and a spread <= 10 % of the ask**.
- Bought at its ask **if** that contract's listing-day price (its close on its first session with volume, from
  `data/listing/<expiry>.csv`, built by `scanner/listing_prices.py` and updated nightly) is **Rs 2 to under Rs 7**;
  with **as many lots as cost <= Rs 8,000** (at least one must fit). Otherwise refused as before, with the reason kept.
- Exit, shadows and the 1-second checks: exactly v12 (`strategies/S1_v12_fade_trail2.md`). Positions carry `rule.sub2`.

## Evidence and its limits
Backtest (realistic 09:16 entry, Oct 2024 - Aug 2026, 109 refused trades with listing Rs 2-7, max lots, v12): +2.3 % a
trade (+Rs 22,250), win 49.5 %; best share of trades reaching +20/+50/+100 % peaks (71/45/20 %). Not proven: t 0.55,
-1.2 % in Oct 2024 - Oct 2025 and +5.6 % since; the Rs 2 lower limit was chosen after seeing the data. Contracts that
listed under Rs 2 lost with every exit. Reports: `data/results/S1_refused_listing_price.md`, `.xlsx`.
