# S1 v2 · Weak-sector results-miss put debit spread

Strategy 1 under the gate in `DECISIONS.md`. **Pre-registered**: every choice is fixed here before any v2
backtest is run; nothing is tuned after one. v1 (naked put, 1-month-low exit, 2.5x target) is superseded.
Backtest: `python -m scanner.backtest_s1` (diagnostic first, then the three arms; output in `data/results/`).

## Universe
- Stocks with option contracts in that day's NSE F&O bhavcopy (point in time).
- Excluded: any stock in the F&O ban list for the **entry day** (NSE publishes it the evening before).
- Each stock has one **sector**, from `data/sector_map.csv` (`python -m scanner.sectors`): membership of NIFTY
  PSU BANK, then PRIVATE BANK, then BANK, then PHARMA; otherwise the NIFTY 500 list's industry mapped to a
  sector (see `scanner/sectors.py`). Other industries and stocks outside NIFTY 500: no sector, never traded.

## Sector filter (at the close of the signal day t, leave-one-out)
- The sector's return is the **equal-weight** average daily return of the other stocks in the same sector of
  `data/sector_map.csv` (eod2 adjusted closes), **excluding the candidate stock**; a day with fewer than 3 other
  stocks with a return has no sector return. Sector level = the compounded daily returns.
- All three must hold (NIFTY 500 = the eod2 index close):
  1. sector 21-session return − NIFTY 500 21-session return < 0;
  2. sector 63-session return − NIFTY 500 63-session return < 0;
  3. sector level at t < its 50-session average (t−49 … t).
- Any missing sector return in t−62 … t: the filter fails.

## Trigger (results only)
- A results filing (event store, type `results`, with its filing time) whose **day 0** abnormal return is ≤ −2 %:
  day-0 stock return (close day−1 → close day 0) minus the leave-one-out sector's day-0 return.
- **Day 0** = the first full session after the filing timestamp: the filing day itself if filed before 09:15 on a
  session day; otherwise the next session (no time recorded: the next session).
- Signal day t = day 0. Several filings with the same day 0: one signal.
- One position per stock; a signal while a position is open or pending is ignored; **10-session cooldown**: a
  signal on the exit session or the 10 sessions after it is ignored (an excluded trade counts as an exit).

## Instrument (S1 v2, primary): put debit spread, same expiry, 1 lot
- Expiry: the first listed stock-option expiry with ≥ 25 sessions after t (expiry day included).
- Long: the listed strike nearest to spot (a tie: the higher). Spot = t's underlying close (UDiFF `UndrlygPric`;
  before 2024-07-05, the nearest stock future's close).
- Short: a listed strike in [0.93 × spot, 0.95 × spot] (5–7 % below spot) and below the long strike; several: the
  one nearest 0.94 × spot (a tie: the higher). None: no trade.
- Lot size: the bhavcopy's `NewBrdLotQty`; old-format files (before 2024-07-05) have none, so the lot is the
  greatest common divisor of the stock's non-zero open interests that day (open interest is whole lots).
- Net debit per lot at the entry fill must be between ₹2,000 and ₹8,000; otherwise no trade.

## Entry
- Day t+1 opening price + 1 tick (₹0.05) for the long leg, − 1 tick for the short leg (no historical depth).
- No opening trade (open = 0) in either leg: no trade.

## Exits (checked on each session's close from the entry day, in this order of precedence)
Spread value = long close − short close (per share); entry debit = long fill − short fill.
1. value ≤ 0.5 × entry debit → exit (stop);
2. 5 sessions or fewer before expiry → exit;
3. 20 sessions elapsed since the entry session → exit;
4. once the value has closed ≥ 2 × entry debit at any point since entry, exit on a close < 0.75 × the highest
   close since entry (trailing).

No 1-month-low rule, no fixed target, no stock-chart exits. Exit fills: long close − 1 tick (not below 0),
short close + 1 tick.

## Costs
- Charges: `server/charges.py`, the post-2026-04-01 schedule, on all four orders (STT 0.15 % of premium on sells,
  ₹35.53 per lakh of premium exchange charge per side, ₹20 brokerage per order, 18 % GST, plus SEBI fee and
  stamp duty as that file sets them).
- Slippage s = 2 % of premium per leg per side (primary), 1 % and 3 % as sensitivities.
- Net ₹ = (exit value − entry debit at the fills) × quantity − charges − slippage. Risked = entry debit × quantity.

## Pre-registered subgroup
Signals where the sector's 63-session relative return (filter 2) is below −15 %: reported separately.

## S1-alt (comparison): same signal, naked put
Same universe, sector filter, trigger, entry, costs and exits 1–4, with value = the put's close. Instrument: the
long put at the highest listed strike in [0.97 × spot, spot], the second expiry after t (next month), 1 lot.
Refused as the paper engine refuses: opening premium < ₹2 (`ALLOW_LOTTERY=false`).

## Secondary arm (report only, not a gate)
The technical trigger in place of results: close < its 20-session average and a 21-session return worse than
the leave-one-out sector's 21-session return (with the sector filter), run through the S1 v2 spread rules.

## Diagnostic (run and printed before any option backtest)
For every results-miss signal passing the sector filter (one per stock and day 0; no ban / position filters),
and every technical signal onset (trigger and filter true on t, not on t−1): the stock's 10- and 20-session
return (close t → close t+h) minus the leave-one-out sector's; N, mean, median, share negative, date-clustered t.

## Report
For each of S1 v2, S1-alt and the secondary arm, overall and by 2021-22 / 2023-24 / 2025-26 (entry date):
N, hit rate (net > 0), mean and median net return per trade (% of debit and ₹), net P&L per ₹1,000 risked,
date-clustered t (clustered on entry date), worst 5 % (5th percentile of net %), share of exits by reason
(1/2/3/4), and the extreme-drawdown subgroup. Trades whose contract is adjusted for a corporate action while
open (a leg disappears from the bhavcopy, or the future moves > 3 % differently from eod2's adjusted close)
are excluded and counted.

## Known limits
- **Constituent-history bias**: sector membership and NSE industry are today's lists, applied to all dates.
- Results and ban events come from the event store: 2021-22 back-filled on the point-in-time universe, 2023
  onward on the universe at the time of that back-fill.
- The 09:20 fill is the session's opening price (no historical order book).
