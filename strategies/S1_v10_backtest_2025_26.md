# S1 v10 fade · descriptive backtest 2025-2026, same-day exit against the carried-trade exit rule

**Pre-registered 2026-10-17**, before any data is fetched and before any number is computed. Numbers only. Code:
`python -m scanner.backtest_s1_v10` → `data/results/S1_v10_backtest_report.md`, `S1_v10_trades.csv`.
The user asked (2026-10-17) for the whole S1 v10 fade over 2025-01-01 → 2026-09-25, comparing the same-day 15:20 exit
with the carried-trade rule (addendum in `strategies/S1_v10_results_day_fade_paper.md`), "descriptive only".

## What this is not
- **Not a gate and not a test.** No pass/fail, no promotion, no rule change follows from the result. S1 v10 stays a
  paper run with its own review (30 closed trades or 6 weeks); the live paper trades remain the only fresh evidence.
- **Not out of sample.** 2025-01-01 onward is the holdout S1 v8 already used (DECISIONS.md), and the pattern v10 trades
  (stocks move against the results headline on the results day) was seen in S1 v9 on 2021-2026, which includes this
  window. The carried-trade exit was chosen after the eight carried trades were seen.

## Signals (the v10 rule, unchanged)
- Every results filing in the event store (type `results`, with its filing time) whose **day 0** (the first full
  session after the filing; `day0_index`) falls in 2025-01-01 … 2026-09-25. One signal per stock and day 0.
- The quarter's numbers as filed (`data/financials.json`, `result_quality`):
  - **strong**: net profit YoY > +10 % and QoQ > 0 and revenue YoY > 0 → buy a **put**;
  - **weak**: net profit YoY < −10 % and QoQ < 0 → buy a **call**;
  - anything else, or numbers missing: no trade, counted in the funnel.
- Only stocks with option contracts in the previous session's bhavcopy. No ban-list filter and no quiet-day filter (v10
  has neither). Signals removed are counted in order.

## The option (v10's walk, with historical stand-ins)
- Expiry: the current monthly if ≥ 2 sessions remain after day 0, else the next monthly (`fade_live.choose_expiry`).
- Start strike: the listed strike nearest the **previous session's close** (`UndrlygPric`; v10 uses the live price at
  the poll). Walk away from the money (down for puts, up for calls; a tie: the lower strike for calls, the higher for
  puts), at most 15 strikes. Take the first with: **≥ 50 contracts on day 0** (stand-in for v10's two-sided quote and
  ≤ 10 % spread, which history cannot show), fill ≥ ₹2, and one lot at the fill within ₹600–8,000. Fill < ₹2 or lot
  < ₹600: stop, no trade.
- **Entry (primary): day 0's open + 1 tick (₹0.05)**, as the S1 v9 measure (`open_prices`). v10 buys at the live ask at
  the first poll that fits, minutes after 09:15, so the real fill is later and dearer than this. Side report: day 0's
  premium VWAP + 1 tick.
- 1 lot.

## Exits, both run on the same trades
- **E1 · same day (v10 as written):** sold at day 0's close − 1 tick (v10 sells at the 15:20 bid; the close is the
  stand-in).
- **E2 · carried-trade rule:** on each close from day 0, in this order: close ≤ 0.80 × entry (stop) → sell; close ≤
  0.75 × the highest close since entry, the entry price counting as the first value (trail) → sell; the close is the
  session before expiry (T-1) → sell. Sold at that close − 1 tick (not below 0). No fixed profit target.
- A contract that leaves the bhavcopy, or whose future moves > 3 % differently from the stock's adjusted close while
  held (corporate action), is excluded and counted. An E2 trade with no exit inside the data is excluded and counted.

## Costs
Charges `server/charges.py` (post-2026-04-01 schedule) on both orders; slippage per side as % of premium by AMFI
category, point in time: large 1 %, mid 2 %, small 3 % (not found 3 %) (`backtest_s1_v4.net_of`).

## Report (numbers only)
For E1 and E2, pooled and separately for puts and calls, and by calendar half-year (2025 H1, 2025 H2, 2026 H1, 2026
Q3): N, hit rate (net > 0), mean and median net % of premium, total ₹, average lot ₹, 10th / 90th percentile, date-
clustered t (`stats.clustered_t`), E2 exit-reason shares (stop / trail / T-1), average sessions held. Also: the
same-signal stock move open → close on day 0 (the S1 v9 measure) beside the option result; the funnel of signals
removed; the VWAP-entry side report. The report states the caveats above at its top.

## Known limits
- No order book in the data: the walk's liquidity test is a contract count, the fill is the open or VWAP plus a tick.
- Sector, industry and AMFI category are today's lists / point-in-time AMFI as the other S1 backtests.
- `financials.json` covers only stocks whose results were fetched; the share of filings without numbers is reported.

## Addendum 2026-10-18 · the same backtest on 2022-01-01 → 2024-12-31 (user's request)
Written before any 2022-24 number is computed. Every rule above is unchanged; only the window differs. Run:
`python -m scanner.backtest_s1_v10 --start 2022-01-01 --end 2024-12-31 --tag _2022_24` → `S1_v10_backtest_report_2022_24.md`,
`S1_v10_trades_2022_24.csv`. Periods are half-years (2022 H1 … 2024 H2).
- Descriptive only, like the 2025-26 run. 2021-2024 is S1's test window, already used by v2-v7 and v9 (which saw the fade
  pattern on 2021-2026), so this is not out of sample either.
- 2022's results filings are back-filled from NSE for this run (the event-store seed on this PC starts in 2023). If the
  back-fill fails, the window starts 2023-01-01 and the report says so.
- Option files before 2024-07-05 are NSE's old bhavcopy format: the lot is the greatest common divisor of the day's open
  interests and the spot is the nearest future's close (as in every earlier S1 backtest).

## Addendum 2026-10-19 · premium-floor sweep (user's request)
Written before any number from this sweep is read. Prompted by UJJIVANSFB on 19 Oct: its nearest put asked ~₹1.40,
under v10's ₹2 floor, so the live trader did not buy it. The user wants to see a lower floor before changing the live
rule. **The live v10 rule stays at ₹2 until the user decides after reading this; any change goes into DECISIONS.md.**
- The same 2025-01-01 → 2026-09-25 backtest with only the floor changed: ₹2 (v10, a check against the original
  report), ₹1, ₹0.50, ₹0.25 and ₹0.05 (one tick, i.e. no floor). Run:
  `python -m scanner.backtest_s1_v10 --min-premium <f> --tag _floor<f>` (dot written as `p`) →
  `S1_v10_backtest_report_floor<f>.md`, `S1_v10_trades_floor<f>.csv`.
- Every other rule is unchanged, including the ₹600–8,000 lot band. A lower floor matters only where a lot still costs
  ≥ ₹600, so it mostly adds stocks with large lots and low prices.
- Reported side by side: N, hit rate, mean / median net %, total ₹, t for E1 (v10's same-day exit), and **the trades
  each lower floor adds** (the ones with a fill under ₹2) on their own. Pooled means hide that group.
- Caveats: the not-out-of-sample caveats above apply. At low premiums the +1 tick fill and the % slippage are large
  relative to the price, and history has no order book, so cheap options are where this backtest is least reliable.
  Five floors on one window is a choice among five, so the best of the five is expected to look better than it is.
