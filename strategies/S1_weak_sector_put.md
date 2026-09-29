# S1 · Weak-sector put

Strategy 1 under the gate in `DECISIONS.md`. Every choice is fixed here; nothing is tuned after a backtest.
Backtest: `python -m scanner.backtest_s1` (writes `data/results/s1_trades.csv`, `s1_summary.csv`).

## Universe
- F&O stocks on the signal day (point in time: stock futures in that day's NSE bhavcopy).
- Each stock has one **sector index**, from `data/sector_map.csv` (`python -m scanner.sectors`):
  1. membership of NIFTY PSU BANK, then NIFTY PRIVATE BANK, then NIFTY BANK, then NIFTY PHARMA (NSE's
     constituent lists);
  2. otherwise the stock's NSE industry (NIFTY 500 list): Financial Services → NIFTY FINANCIAL SERVICES ·
     Information Technology → NIFTY IT · Healthcare → NIFTY HEALTHCARE INDEX · Automobile and Auto Components →
     NIFTY AUTO · Fast Moving Consumer Goods → NIFTY FMCG · Consumer Durables → NIFTY CONSUMER DURABLES ·
     Metals & Mining → NIFTY METAL · Realty → NIFTY REALTY · Media Entertainment & Publication → NIFTY MEDIA ·
     Oil Gas & Consumable Fuels → NIFTY OIL & GAS · Power → NIFTY ENERGY · Capital Goods, Construction,
     Construction Materials, Telecommunication → NIFTY INFRASTRUCTURE · Services → NIFTY SERVICES SECTOR;
  3. any other industry (Chemicals, Textiles, Diversified, …) or a stock not in NIFTY 500: no sector, never traded.
- A sector is **weak** on day D when all three hold (eod2 index closes):
  - 1-month return (21 sessions) minus NIFTY 500's 1-month return < 0;
  - 3-month return (63 sessions) minus NIFTY 500's 3-month return < 0;
  - close < its 50-session simple moving average (including D).

## Trigger (after the close of day D)
The stock's sector is weak on D **and** either:
- **results miss:** a results event dated within the last 15 sessions (D−14 … D) whose day+1 reaction is
  below −2 % (close T−1 → close T+1, stock minus NIFTY 50, the event study's proxy), with T+1 ≤ D; or
- **weak stock:** close < its 20-session moving average **and** its 1-month return < its sector's 1-month return;

**and** the stock is not in the F&O ban list on D. One open trade per stock: a trigger while a trade is open is
ignored.

## Instrument
- The **next-month** stock put: the second expiry after D in D's bhavcopy.
- Strike: the highest listed strike K with 0.97 × spot ≤ K ≤ spot (ATM to 3 % OTM), spot = D's underlying
  close (UDiFF `UndrlygPric`; before 2024-07-05, the nearest stock future's close). No such strike: no trade.
- 1 lot (the contract's lot size; before 2024-07-05, today's lot size, as the old files have none).

## Entry
- Next session (D+1) "09:20 fill", engine rules: the option's opening price that session + 1 tick (₹0.05).
  NSE publishes no historical order book, so the session open is the price used for 09:20.
- Refused, as the paper engine refuses: premium < ₹2 (lottery, `ALLOW_LOTTERY=false`), strike open interest
  < 50 lots on D, no opening trade (open = 0).

## Exit (the first to happen, checked on each close from the entry day)
In this order when several hold on the same close:
1. stock close ≤ its prior 1-month low (the lowest close of the 21 sessions before that day);
2. option close ≥ 2.5 × entry premium;
3. option close ≤ 0.5 × entry premium;
4. 10 sessions after the entry session;
5. 5 sessions before expiry.

Exit fill: that session's option close − 1 tick (not below 0).

## Sizing and costs
- 1 lot; maximum loss = the premium paid (plus charges).
- Charges: `server/charges.py` (effective 2026-04-01) on both legs.
- A trade whose contract is adjusted for a corporate action while open (it disappears from the bhavcopy, or the
  raw future moves differently from eod2's adjusted close by > 3 %) is excluded from the results and counted.

## Known limits of the backtest
- Sector membership and NSE industry are today's lists applied to all dates (NSE does not publish free
  history of index constituents).
- Results and ban events come from the event store: 2021-22 back-filled on the point-in-time universe, 2023
  onward on the universe at the time of that back-fill.
