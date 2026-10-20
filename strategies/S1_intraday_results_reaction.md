# S1 · results filed during market hours: does the stock fade or keep going? (step 1, stock only)

**Pre-registered 2026-10-20**, before any case list is built, any candle is fetched or any number is computed. The
user's request: check "whether trying to take the trade near the time of result knowing", and whether it explains
"how some of them is loss". This is descriptive. **Nothing live changes.** An option trade is tested only in step 2,
and only if step 1 passes. Step 2 gets its own pre-registration.

## Cases
- A results filing (`type = results`, event store) of a stock that is in that day's F&O bhavcopy.
- Filed on an NSE session day between **09:15 and 14:50 IST** (inclusive), so at least 15 minutes remain after the
  first 15 minutes before 15:20.
- **t0** = the earliest announcement time stored for that stock that day (NSE or BSE source).
- One case per stock and day (the earliest filing).
- Filings before 09:15 (the fade's own day-0 cases) and after 14:50 are out.
- Window: filing days 2022-01-01 → 2026-09-25.

## Data
- Stock 1-minute candles of each case day: Kotak historical data (`nse_cm|<token>`, `1min`), fetched on GitHub.
- NIFTY 50 1-minute: branch `index-data`, `spot_1m/NIFTY50/<YYYY-MM>.parquet`.
- Candle time = the minute's start. "The close at T" = the close of the minute starting at T.
- A case without candles covering both t0 − 1 min and 15:20 is excluded and counted per year.

## Measures (% moves on 1-minute closes)
- `pre` = the close of the last minute before t0's minute.
- **R15** = pre → the close of the minute at t0 + 15 min: the first reaction.
- **RA** = the close at t0 + 15 → the close of the 15:20 minute: what comes after. **This is the test.**
- `B15` = the close at t0 − 16 → pre: a timing check, the move in the 15 minutes **before** the announcement.
- **Primary:** each move minus NIFTY 50's move over the same minutes (market-adjusted). Raw moves are reported too.

## Splits and report
- R15 buckets (adjusted): ≤ −3 %, −3 to −1 %, −1 to +1 %, +1 to +3 %, ≥ +3 %.
- Per bucket, for 2022-24, 2025-26 and pooled:
  - N, mean and median RA, the share continuing (RA with the same sign as R15), date-clustered t of RA
    (`scanner.stats.clustered_t`).
- The same table by the fade's numbers class (strong / weak / neither: `scanner.event_screens.strong(q, 10)` /
  `weak`, from `data/financials.json`) and by year.
- The timing check: mean |B15| against mean |R15|. A large B15 means the stored time is later than the news.
- **The loss question** (descriptive): the backtest fade trades (`S1_v10_trades*.csv`, entry = open) whose filing was
  in market hours the session before day 0. Their R15 and RA show whether the day-0 trade came after the move was
  done.

## Pass to step 2 (fixed now)
A bucket with |R15| ≥ 1 % (the four outer buckets) passes when **all** hold:
1. Mean RA has the **same sign** in 2022-24 and in 2025-26.
2. |mean RA| ≥ **0.5 %** in each window (about the least a ₹600–8,000 option needs to beat its spread and charges).
3. Pooled date-clustered **|t| ≥ 3** (four buckets are tested).

The sign of a passing bucket fixes step 2's trade:
- **continuation:** buy in the direction of R15;
- **fade:** buy against it.

No passing bucket: step 1 closes with its numbers, and no option test follows.

## Limits
- The stored announcement time is when the exchange published it. A leak or an earlier BSE/press release shows in
  B15.
- Stock moves only: an option trade adds spread, charges and theta (step 2).
- 1-minute closes, not quotes.

## Addendum 2026-10-20 · the path after an entry at the announcement (descriptive only)
Written before it is computed. The user asked how the stock moves if the entry is taken on seeing the announcement.
- **Same 644 cases with usable minutes.**
- **Entry** = the close of the minute after the announcement's minute (t0 + 1), the earliest realistic fill. The
  move missed by that minute is reported: `pre` → entry.
- **Moves from the entry**, market-adjusted (minus NIFTY 50) and raw:
  - at +5, +15, +30 and +60 minutes, and at 15:20;
  - the next session's open and close (stock: eod2 daily; NIFTY: its 1-minute file, 09:15 open and the last close).
  - A horizon after 15:20 on the day is cut at 15:20.
- **Groups:** the result's numbers class (strong / weak / neither, as above), and the direction of the missed jump
  (up / down).
- **Report per group and horizon:** N, mean, median, share up, date-clustered t; for 2022-24, 2025-26 and pooled.
- **No pass test.** This is a look at the path. Any trade from it needs its own pre-registration.
