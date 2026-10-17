# S1 v10 fade · intraday timeline and stop-loss study 2025-2026 (descriptive)

**Pre-registered 2026-10-17**, before any minute data is fetched and before any number is computed. Numbers only. Code:
`python -m scanner.fade_timeline` → `data/results/S1_v10_stoploss_study.md`, `S1_v10_stoploss_study.xlsx`.
The user asked (2026-10-17) to study, on the 2025-2026 fade trades, *when* each trade peaks, dips and is sold, and how a
stop-loss could be kept without becoming a burden. The 16 Oct live trades (8, one day) suggested early peaks followed by
deep falls, and a −20 % stop touched early on most trades.

## What this is not
- **Not a test and not a rule change.** No rule follows from it automatically; any exit idea it suggests goes to paper first,
  as a new pre-registered version. S1 v10's live rule (same-day 15:20 exit, no stop) is unchanged.
- **Not out of sample** (2025-26 is the S1 v8 holdout and where the fade was seen), and **many exits are compared**, so the
  best of them will look better than it is by chance.
- **Not real option minute prices.** NSE's free files have only the day's open / high / low / close per option, and Kotak's
  history cannot look up expired option contracts. The option path is a proxy built from the stock's minute path (below).

## Trades
The 434 trades of `strategies/S1_v10_backtest_2025_26.md` with a valid same-day exit (entry: the option's day-0 open + 1
tick; `data/results/S1_v10_trades.csv`, entry `open`). A trade whose stock has no 1-minute history for day 0 is excluded and
counted.

## Data
- Stock: 1-minute candles of day 0 from Kotak's historical API, fetched through the live server's `/api/history` (the key
  stays on the server), cached under `data/cache/intraday/`.
- Option: day 0's open / high / low / close from the NSE bhavcopy price file (`data/cache/fo_prices_YYYYMMDD.csv`).

## The proxy option path (fixed before any run)
For each minute t from 09:15: **P(t) = O + b × (S(t) − S₀)**, floored at ₹0.05, where O = the option's day open, S₀ = the
stock's 09:15 open, S(t) the stock's price in that minute, and **b = s × (option high − option low) ÷ (stock high − stock
low)**, s = −1 for puts and +1 for calls (the option's day range mapped onto the stock's). A minute's proxy high / low use
the stock's low / high (puts) or high / low (calls). Stock range zero: the trade is excluded and counted.
**Calibration reported:** the proxy's 15:20 value against the option's real day close, and the proxy's day high / low
against the real ones (median absolute error, % of the entry).

## Timeline (per trade)
Time of the proxy peak and of the proxy dip after entry, which came first, the first minute touching −20 %, +30 % and
+50 % of the entry, and the value at 15:20. Reported as distributions: by half-hour of the day, and the share of trades
whose peak came before the dip.

## Exits compared (every one on the same proxy paths)
A stop or target sells at its level in the first minute that touches it (optimistic: a fast fall fills worse); otherwise
the trade is sold at the 15:20 proxy value. Charges and slippage as the backtest (`net_of`).
1. Same day 15:20, no stop (the live rule). Also shown with the real day close − 1 tick, as in the backtest.
2. Stop −20 %; stop −30 %; stop −40 %.
3. Target +30 %; target +50 %; target +100 %.
4. Stop −20 % + target +30 %; stop −20 % + target +50 %; stop −30 % + target +50 %.
5. Trail: sell 25 % below the highest proxy value since entry, once above the entry.
6. Stop −20 % armed only from 09:45 (the first 30 minutes are left alone).
Per exit: N, mean and median net % of premium, hit rate, date-clustered t, total ₹, by side (puts, calls) and by
half-year.

## Known limits
- The proxy assumes the option moves with the stock in a straight line within the day (no change in implied volatility,
  no time decay inside the day); the calibration lines show how far that is from the real day range and close.
- Touch-at-level fills overstate stops and targets in fast markets.
- Kotak symbols are today's; a renamed stock may have no history and is excluded and counted.

## Addendum 2026-10-17 (before any exit result): a second proxy, B
Written after the calibration of proxy A was seen on the first 38 trades fetched (median error: 15:20 value vs the real close
≈ 32 % of the entry, day high / low ≈ 20 %), and **before** any exit result was computed. Proxy A stays the pre-registered
proxy and is reported unchanged. Proxy B is added beside it:
- **B (range-anchored):** P(t) = option low + (option high − option low) × f(t), f = (stock high − S(t)) ÷ (stock high −
  stock low) for puts, (S(t) − stock low) ÷ (stock high − stock low) for calls. It matches the option's real day high and
  low exactly (at the times of the stock's low and high); its calibration is reported as the error of its 09:15 value
  against the real open and of its 15:20 value against the real close.
- The timeline (times of the peak and the dip, which came first) is the same under A and B: both follow the stock's own
  low and high. Only the price levels, and so the stop / target results, differ.
- All twelve exits are reported for both proxies. Conclusions about stop levels are read only where A and B agree.

## Addendum 2026-10-18 · the same study on the 2022-24 trades
Written before any 2022-24 number is computed. The trades of the 2022-24 fade backtest (addendum in
`strategies/S1_v10_backtest_2025_26.md`), the same day-0 1-minute stock candles through `/api/history`, the same proxies
A and B, the same twelve exits, and the exact single stop / target check on real prices. Run:
`python -m scanner.fade_timeline --tag _2022_24` (with `--fetch` first) → `S1_v10_stoploss_study_2022_24.md` / `.xlsx`.
