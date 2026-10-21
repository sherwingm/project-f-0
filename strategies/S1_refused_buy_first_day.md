# S1 · refused cheap options: buy on the contract's first trading day, sell 7 / 10 sessions before expiry (backtest)

**Pre-registered 2026-10-21**, before any number is computed. The user: on the results day options like UJJIVANSFB
66 PE and UNIONBANK 180 PE are under the ₹2 floor and cannot be bought; "if the contract's first-day price is below
₹10 (or ₹7), buy it that day and sell it 7 (or 10) trading days before expiry". **Nothing live changes.**

## Read this first
The contract (stock, put or call, strike) is only known **after** the results: the fade picks put or call from the
numbers and the strike from the results-day price. Buying it on its first trading day, weeks earlier, uses that
later knowledge. So this test answers "would those exact contracts have paid from their first day?", not "is this
tradable as a rule". A rule would have to choose the contract before the results.

## Contracts
The 146 refused examples of `data/results/S1_refused_below_floor_all.xlsx` (140 fade-backtest sub-₹2 signals 2022–26,
6 live refusals Oct 2026). The 27 Oct 2026 contracts have not reached their exit day yet and are reported as open.

## Prices (NSE daily F&O bhavcopy, the local cache `data/cache/fo_bhavcopy_*.csv`: closes and volumes)
- **First trading day** = the first session on which the contract traded (volume > 0).
- **Buy** = that day's close + 1 tick (the cache has no opening price; a listing day's first print is thin and stale).
- **Sell** = the close − 1 tick on the session **7** (variant: **10**) sessions before expiry (expiry day = 0). No trade
  that day → the last close before it. Sell day on or before the buy day → excluded and counted.
- One lot, real charges (`server.charges`). Tick ₹0.05 before 2025-11-03, ₹0.01 from it.

## Rules tested
- Buy only if the first-day price is **< ₹10**, or **< ₹7**; sell at **7** or **10** sessions before expiry (4 rules).
- Each also with one lot ≤ ₹8,000 at the buy price (the live cost cap).

## Reported
Per rule: N, win %, mean and median net % of premium, total ₹, date-clustered t, by year; and how many buys the
threshold skipped. Descriptive: no pass test (because of the look-ahead above), nothing is chosen from it.
