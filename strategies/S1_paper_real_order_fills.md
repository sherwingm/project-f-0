# Paper rule trades filled as real orders (from 2026-10-26)

The user, 2026-10-24: "i want you to do it the paper trading as the real order, first of all find the setup, then
read their documentation, then confirm it". Confirmed the same day: the real-order fill is the main paper P&L; an
unfilled buy waits 60 s, then cancels and the normal entry retries; the A/B 15:20 "close" entry is filled the same way.

Still paper: nothing is sent to a broker. What changes is the PRICE and TIME a rule trade (arms A, B, F, the below-Rs 2
rule) is filled at. The signals, the strike walks, the Rs 2 floor, the Rs 600-8,000 band, the -20 % stop, the v12
trail and the 15:20 exit decide exactly as before.

## What the documentation says a real order faces (read 2026-10-24)
- Kotak Neo Trade API: market orders are not allowed for retail algo trading (SEBI); a market order is turned into a
  limit order priced off the last traded price, for options: below Rs 1: Rs 0.10; Rs 1-5: 10 %; Rs 5-10: 5 %;
  Rs 10-100: 3 %; Rs 100-500: 2 %; above Rs 500: 1 %. With no last price an option order is rejected.
  (kotakneo.com/support/are-market-orders-allowed-trade-api; github.com/Kotak-Neo/Kotak-neo-api-v2: order types
  L / MKT / SL / SL-M, order report fields fldQty, unFldSz, avgPrc, rejRsn.)
- NSE: stock-option tick Rs 0.01 when the stock is below Rs 250, else Rs 0.05 (from 2025-11-03). Limit price
  protection: a limit more than Rs 20 (reference <= Rs 50) or 40 % (above) from the reference price is rejected.
  F&O orders are in whole lots.
- SEBI retail algo framework (from 2026-04-01): orders only from a registered static IP, daily 2FA login, under
  10 orders a second per exchange. Not simulated (they matter only for real orders); our rate is far below 10/s.

## The model (`server/order_sim.py`, run by `PaperLedger.work_orders` about every second)
1. **Buy** (an entry decision on quote q0): a limit order at q0's best ask plus Kotak's protection for that price,
   rounded up to the tick. It is checked against the NEXT quote at least ~1 s later (the order's travel time), never
   against q0. It fills when the asks at or below the limit hold the whole order (all lots; a real order could
   part-fill, so multi-lot orders are slightly pessimistic), at the average price of the asks it takes. Not filled:
   checked again each second; after 60 s (or at 15:20 for fade and open-window entries) it is cancelled and the
   entry walk retries as it always did. The 15:20 close entry is not retried: a cancelled one is refused.
2. **Sell** (a stop, trail, 15:20 or rule exit on quote q0's bid): from the next quote, each second, a limit at the
   current best bid minus the protection, rounded down; it fills when the bids at or above it hold the whole order,
   at their average. A sell is never cancelled: from 10 s unfilled it takes the whole visible bid side, and any
   quantity beyond it at the lowest visible bid minus one spread.
3. **Rejected** like the exchange would: no last price, or a limit outside the NSE price protection band around the
   last price. A rejected buy is cancelled (the entry retries); a rejected sell tries again the next second.
4. While a sell is working the position is marked `exiting`: no exit check fires again and the held-bid peak stops
   at the decision quote (`server/peak.py`, unchanged).
5. Orders in flight are kept in memory; a sell survives a restart (rebuilt from `exiting`), a buy does not (its
   signal is set back to waiting).

## What is recorded on each trade
- `pos.order` / `closed.entry_order`: the decision price (the old instant price), limit, placed / filled times, wait,
  attempts, the levels taken. `closed.exit_order`: the same for the sale.
- `closed.instant`: entry and exit at the old instant prices (decision ask, decision bid) and the net P&L they give,
  with real charges; `closed.fill_cost_rs` = instant net - real-order net. The v12 review reports both, so trades
  before 2026-10-26 (instant fills) stay comparable.
- Shadows (v11, v10, 5 % trail, +100 %, np25, fd2) still read instant bids; they are not order-filled.
- The A/B close entry's old price (ATP + Rs 0.01) is kept as `entry_order.old_price`.

Switch: `PAPER_REAL_ORDERS` (default true on the server); false restores instant fills.
