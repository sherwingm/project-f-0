# S3 D6-D7 · unconditional short vol on daily prices, and the VIX regime map (descriptive)

Pre-registered 2026-10-23, before running. Source: the user's research note, Section 1 (Pillai 2026: unconditional
short-vol structures on Nifty lose net of costs; put-write k = 0.94 wins 91.6 % of months but returns −0.9 %) and
Section 3's VIX regime map. Nothing after 2025-09-30 is read. The NIFTY test window is reported as its own row.

## D6 · Weekly short straddle and monthly put-write on the NSE bhavcopy
Data: `options_daily/NIFTY` (daily ClsPric, volume, lot) and the 1-minute spot close at 15:29 (from 2021-10-21).
Window: entries from 2021-10-21; expiries up to 2024-09-30 (main); 2024-10-01 → 2025-09-30 reported separately.
- **Weekly straddle:** at the close of each NIFTY expiry day (an expiry that traded on its date), sell the ATM CE and
  PE of the next weekly expiry.
  - ATM = the strike nearest the 15:29 spot.
  - Price: that day's ClsPric; both legs need volume > 0 that day.
  - Hold to expiry and settle at intrinsic against the expiry day's 15:29 spot.
- **Monthly put-write:** at the close of each monthly expiry day (the last expiry of its month), sell the next monthly
  expiry's put at the strike nearest k × spot, for k = 0.94 and k = 0.98. Same pricing and settlement.
- **Costs:**
  - entry slippage 1 % of the premium;
  - `server/charges.py` on the sell order (STT 0.15 %, brokerage, exchange, GST);
  - at expiry the seller of an ITM option pays no STT; brokerage on settlement is ignored.
- **Lot:** the bhavcopy lot of the contract on the entry day; where it is not known (before 2024-07-05), the lot in
  force then, from NSE circulars: 50 to 2024-04-25, then 25.
- **Reported:** trades, win rate, mean and median net % of the credit, t, the worst trade, net % of margin (12 % of
  notional for the straddle; 15 % of notional for the put), and the same by year.

## D7 · Does India VIX overstate the next week's move, by regime?
Data: 1-minute NIFTY spot and India VIX (the rescaled loader), daily closes 2021-10-21 → 2025-09-30.
- For each close: VIX (annualised %) against the realised vol over the next 5 sessions. Realised vol = the square root
  of the sum of squared 1-minute log returns, the overnight gaps included, annualised over 5 / 252 of a year.
- **Buckets:** VIX < 13, 13-14, 14-20, 20-22, > 22, each split by the 5-day VIX change (rising vs falling).
- **Reported:** days, mean VIX, mean RV, mean VIX − RV, the share of days with RV > VIX, and the same for the next 21
  sessions.
- **Reading:** the research's map says sell in 14-20 and avoid above 20-22 when rising. That holds only if the VIX − RV
  gap is reliably positive in 14-20 and shrinks or turns negative when VIX is high and rising.
