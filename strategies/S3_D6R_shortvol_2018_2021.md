# S3 D6R · the D6 selling studies re-run on 2018-2021 (pre-registered, no new parameters)

Written 2026-10-29, before running. **Same rules as D6** (`strategies/S3_D6_D7_daily_shortvol_vix_regime.md`): the
weekly ATM short straddle (expiry close → next expiry, held to settlement) and the monthly put-write at k = 0.94 and
k = 0.98. Same pricing (ClsPric, both legs need volume > 0), the same 1 % entry slippage, `server/charges.py` on the sell
orders, no STT at settlement, and the same margin bases (12 % / 15 % of notional). Nothing is tuned on the new years.

## The only differences, forced by the data
1. **Spot for strike choice and settlement:**
   - D6 used the 1-minute close at 15:29, which starts only on 2021-10-21.
   - Here: NSE's official NIFTY 50 closing value (`index_data/index_close.py`). That is the value NIFTY options
     actually settle at on expiry day.
   - **Check:** on the overlap (expiries 2021-10-21 → 2021-12-31) both versions are run, and the trade-by-trade
     difference is reported.
2. **Lot:** D6 used 50 before 2024-04-26. Before 2021 the NSE lot was 75; circular 28/2021 sets 50 for contracts
   expiring from 2021-07-29. The lot changes ₹ figures and the fixed ₹20 fees only, not % of the credit much.
3. **Calendar:** NIFTY weekly options started in Feb 2019. Before that, "next expiry" is the next monthly. Those trades
   are kept, as the D6 code does (consecutive traded expiries), and reported as their own row.

## Window and reporting
- Entries on expiry days from 2018-01-01. The settlement expiry must be on or before 2021-12-31. Nothing after
  2021-12-31 is read.
- Reported per structure:
  - 2018-01 → 2021-12 in total;
  - by year;
  - the monthly-only period (to the first weekly expiry, Feb 2019);
  - trades, win rate, mean and median net % of the credit, t, the worst trade, and mean net % of margin.
- **The question:** do the plain selling structures still lose (mean net % of the credit ≤ 0) on years they were not
  tested on? This is a descriptive check with no gate, as D6 was. A positive result here would not make selling allowed
  (it is outside "long options only").
