# S1 v9 results-day screen and event screens (block deals, ex-dividend, QIP) — stock level

**Pre-registered** (2026-10-14): every choice is fixed here before any run. These are screens of the stock's own move
(and, for ex-dividend, of the put across the ex-date), not strategies; a cell that passes gets an option backtest
written separately. Run: `python -m scanner.event_screens`.

**Why.** The user asked for (a) a "must-win" S1 with few trades and result constraints that buys on the **results
day itself** (HCLTECH: results out the evening of 12 Oct, the stock +8.4 % on 13 Oct, our rule bought only on the
14th), and (b) tests of three ideas: stocks fall on **ex-dividend** days, **QIP** announcements, **block deals**.
Window: 2021-01-01 → 2026-09-25 (the last session with stock closes). Every year is judged on its own; there is no
holdout left for S1, so a pass is followed by live paper days.

## Common rules
- Universe: stocks with stock options in that day's F&O bhavcopy. Prices: eod2 daily open / close (adjusted).
- Returns are signed in the stated direction, net of **0.1 %**, entry and exits as stated per screen.
- Per cell: N, mean, median, hit rate, date-clustered t, mean per calendar year 2021 … 2026.
- **Pass (a cell):** N ≥ 100; date-clustered t ≥ 3; mean ≥ the screen's minimum; mean positive in ≥ 5 of the 6
  years including 2025 and 2026.

## 1. S1 v9 · results day (long on strong numbers)
- Event: a results filing (event store, with its filing time). **Day 0** = the first full session after the filing
  (the filing day itself if filed before 09:15). **Entry: day 0's open.** Exits: the close of day 0, +1, +3, +5.
- Numbers (`data/financials.json`, the quarter the filing reports, as filed): net profit YoY, net profit QoQ,
  revenue YoY (% change; a base ≤ 0 counts as not meeting the test).
- Strong cells (long): **NP YoY > +10 %** or **> +25 %**, each **AND NP QoQ > 0 AND revenue YoY > 0**; each with and
  without **day 0's opening gap ≤ +5 %** (open vs the previous close). Each for **arm A** (all) and **arm B**
  (strong sector: the leave-one-out sector's 21- and 63-session return above NIFTY 500's and above its 50-session
  average, at the close before day 0). 2 × 2 × 2 × 4 horizons = 32 cells. Minimum mean: **+1.0 %** (day 3, 5),
  **+0.6 %** (day 0, 1).
- Side report (short): NP YoY < −10 % AND NP QoQ < 0, arms A and B, 4 horizons.

## 2. Block deals
- Event: a block deal (event store, type block_deal, with its ₹ value); several deals in one stock on one day are one
  event (values summed). Deals are reported after the close: **entry at the next session's open**; exits at the
  close of that session (+0), +1, +3, +5.
- Cells: total value **≥ ₹100 / ≥ ₹500 / ≥ ₹1,000 crore** × the stock's move on the deal day (**up / down**) × 4
  horizons = 24 cells. Direction: both are reported; a cell passes in the direction of its mean. Minimum mean
  **+0.6 %**.

## 3. Ex-dividend
- Event: an ex-dividend date with a ₹ amount (NSE corporate actions, `scanner/corp_actions.py`). Yield = dividend ÷
  the close before the ex-date.
- Stock (short): from the close before the ex-date to the ex-date's open and close; also the **excess** move
  (return + yield: 0 means the price fell exactly by the dividend).
- **Put across the ex-date (the user's idea):** the put of the current monthly expiry nearest the close before the
  ex-date, bought at that close (bhavcopy close + 1 tick), sold at the ex-date close − 1 tick, net of charges and
  2 % slippage per side; % of premium.
- Cells: yield **< 1 % / 1–2 % / ≥ 2 %** × {stock to close, excess, put}. Minimum mean **+0.6 %** (stock),
  **> 0** (put).

## 4. QIP
- Event: the first QIP notice of an issue (NSE announcements, category "Qualified Institutional Placement",
  `scanner/qip.py`; notices of one stock within 45 days are one issue). Day 0 as in §1; **entry: day 0's open**;
  exits: close of day 0, +1, +3, +5; direction **short**. Minimum mean **+0.6 %**.

## What follows
Passing cells → an option backtest per cell (calls for longs, puts for shorts; ₹600–8,000 walk from the at-the-money
strike; entry at day 0's option open price, `fo_prices.OpnPric`; exit at the passing horizon), pre-registered then.
For the results-day screen, arm B is also run with the earlier methods the user named: v5 (ATM, ₹10,000–30,000,
20 sessions), v7 (walk ₹600–8,000, 50 % stop / 5 sessions without a new high / T-1), v4 (ATM, ₹2,000–8,000, 20
sessions).

## Known limits
- Daily data: "the open" is the day's official open; a live entry fills later at a worse price on gap days.
- Result numbers are as filed; restatements are not tracked. Block deals carry no buy/sell side in the store.
- Sector lists are today's, applied to all dates.

## Addendum (2026-10-14, before any option run): the S1 v9 option backtest, every strong cell
The user asked for the option result now, so the option step runs for **all four strong cells**, not only the cells
whose stock screen passes (`python -m scanner.backtest_s1_v9`). A smoke run of the stock screen on partial result
numbers (~45 % of filings) had been seen before this addendum; no option number had.
- Signal: §1's strong cells, arms A / B. Entry day = day 0. Expiry, strike and spot from the **previous session's**
  bhavcopy (what is known at the open). One position per stock at a time (v4's position / cooldown rule), applied once over the widest cell (NP YoY
  > 10 %, arm A); the narrower cells and arm B are the trades of that run that meet their test.
- Entry price, two ways: **open** = day 0's option open (`OpnPric`) + 1 tick; **day** = day 0's premium VWAP + 1 tick
  (the live "any time 09:15-15:20" rule). Liquidity: >= 50 contracts on day 0 (as v7; a known look-ahead on
  volume).
- Methods (the user: "consider v7 or v4 for arm B"): **v7** (walk up from at-the-money, 1 lot Rs 600-8,000, exits
  50 % stop / 5 sessions without a new closing high / T-1, no near-expiry), **v4** (at-the-money, vol budget
  Rs 2,000-8,000, v4's exits with a 20-session cap), **v5** (at-the-money, 1 lot Rs 10,000-30,000, 20 sessions).
  Net of charges and AMFI-category slippage.
- Per group: N, mean net % of premium, median, hit, total Rs, date-clustered t, mean per year 2021-2026.
  **Pass:** N >= 50, mean > 0, t >= 2, positive in >= 5 of 6 years including 2025 and 2026. Many groups are run
  (4 cells x 2 arms x 3 methods x 2 entries = 48), so a single pass among them is weak evidence; it goes to
  paper trading, not money.
