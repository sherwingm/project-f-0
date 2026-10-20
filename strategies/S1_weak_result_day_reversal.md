# S1 fade · weak results filed in market hours: does an "already corrected" filing day predict the next day's call?

**Pre-registered 2026-10-20**, before any number of this study is computed. The user's idea: "without taking trade in
there, can we use that to watch the momentum on that day so that the loss of the trade can be neglected... reversal
for the bad result, check these only for the bad results". In plain terms:
- a weak result filed during market hours;
- the stock **already falls** on the filing day ("already corrected");
- the next day it should **bounce**, so the fade's call (bought at the next open) wins.

This is a descriptive test. **Nothing live changes.** A pass becomes a candidate filter for the user's decision, with
its own version and a DECISIONS.md entry.

## Cases
- **Weak** results (net profit YoY < −10 % and QoQ < 0; `scanner.event_screens.weak`, from `data/financials.json`).
- Filed 09:15–14:50 IST on a session day by an F&O stock, one per stock and day (`data/results/S1_intraday_cases.csv`).
- Usable 1-minute candles (`data/results/S1_intraday_minutes.csv`; the 66 weak cases of
  `S1_intraday_results_path_cases.csv`).
- Window 2022-01 → 2026-09.

## The filing-day watch (known by the close, before the fade's trade)
- **D** = the stock's move from the close of the minute before the announcement to its 15:29 minute close.
  Market-adjusted: minus NIFTY 50's move over the same minutes (branch `index-data`, `spot_1m/NIFTY50`).
  D_raw is reported too.
- **Already corrected** = D ≤ **−2 %** (the primary split). Not corrected = D > −2 %.
- Also reported in buckets: ≤ −3 %, −3 to −1 %, −1 to +1 %, > +1 %.

## Next day (the fade's day 0)
- **Stock** (eod2 daily, adjusted; NIFTY 50 from its 1-minute file), all market-adjusted:
  - gap = the filing day's close → the next open;
  - day = the next open → the next close (the window the fade's call is held in).
- **The fade's real call trades:** the v10 backtest's call trades with entry = open and E1 (15:20 exit), whose filing
  is one of these cases (`S1_v10_trades_2022_24.csv`, `S1_v10_trades.csv`, matched on symbol and filing date).
  Net % of premium after charges.
- **v11 exit** (−20 % stop from 09:16, minutes, Oct 2024 →) for the same calls, where minute candles exist:
  descriptive only.

## Report
For corrected / not corrected and the buckets, for 2022-24, 2025-26 and pooled:
- the stock: N, mean and median gap and day, and the share up;
- the fade's call: N, win rate, mean and median net %, total ₹;
- date-clustered t (`scanner.stats.clustered_t`) on the means.

## Pass test (fixed now; all needed)
1. At least **20** corrected call trades, pooled.
2. The corrected calls' mean net % is **> 0 in 2022-24 and in 2025-26**.
3. Corrected minus not corrected mean net % is **> 0 in both windows**.
4. The pooled corrected-call mean net % has a date-clustered **t ≥ 2**.

If all hold, the candidate is: for a market-hours weak filing, take the fade's call only when the filing day already
corrected ≥ 2 %. Otherwise nothing changes.

## Limits
- Small sample: about 66 weak cases, and fewer matched calls.
- Weak filings outside market hours (after the close or before the open) have no filing-day move, so they are not
  in this test.
- 2022-26 has been looked at before for the fade, so this is not fresh data.
