# 12 · The paper engine: fills, buckets, charges, risk rules, and how to read the scoreboard

The paper account (`ORDERS=true PAPER=true BROKER=none`) is built to answer one question honestly:
**would this way of trading have made money after real fills and real costs?** Every rule below exists
to stop the account from flattering you. Nothing in it can reach a broker.

## How a paper order becomes a position

1. **Quote.** The engine fetches the contract's live 5-level depth (`quote_one` for options; futures come
   from the poll). No live depth → no fill, ever. Orders placed while the market is closed are **queued**
   (`data/paper_queue.jsonl`) and fill at the first poll at or after 09:20 IST of the next session,
   against *that poll's* book — never at yesterday's close. Every check runs again at that moment.
2. **Liquidity class** (`server/liquidity.py`), judged against the side of the book the order trades against:

   | Class | Futures | Options | Fill rule |
   |---|---|---|---|
   | accept | spread ≤ 0.05% of mid and order ≤ 25% of visible depth | spread ≤ 3%, strike OI ≥ 50 lots, order ≤ 20% of depth | book walk + 1 tick |
   | penalty | spread 0.05–0.15% or order 25–50% of depth | spread 3–8% or order 20–100% of depth | walk + 1 tick + ½ spread |
   | lottery | — | premium < ₹2 **or** ≤ 2 sessions to expiry | best ask + 1 tick (buys) / best bid − 1 tick (sells) |
   | refuse | spread > 0.15%, order > 50% of depth, or a missing side | no bid or ask, OI < 50 lots, order > 100% of depth, spread > 8% | logged to `data/refusals.jsonl`, order rejected |

   The lottery class is **off by default** (`ALLOW_LOTTERY=false`): a cheap or near-expiry option is refused
   with the reason "cheap/near-expiry disabled (ALLOW_LOTTERY)" and logged like any other refusal. With `ALLOW_LOTTERY=true`, a
   *lottery* order is not refused for spread or OI — that is the point of the bucket — but it still
   needs the side it trades against, and it is tagged **cheap_near_expiry** on every screen and score.
3. **Fill** (`server/fills.py`). Buys walk the asks, sells walk the bids; the price is the volume-weighted
   average of the levels consumed, plus one tick against you for latency, rounded to the tick against you.
   Quantity beyond the visible book fills at the worst visible level plus one full quoted spread. A LIMIT
   price is a cap on that fill: if the walk lands beyond it the order is rejected — the engine never rests
   orders. The Review screen shows the exact levels that would be consumed and the slippage vs mid.
4. **Charges** (`server/charges.py`, rates effective 2026-04-01, override any with `CHARGES_JSON`):
   brokerage (min(0.03% × value, ₹20) futures, ₹20 flat options), STT on the sell side (0.05% futures,
   0.15% of premium options; 0.15% of intrinsic on exercise), NSE transaction charge (₹1.83/lakh futures,
   ₹35.53/lakh of premium options), SEBI ₹10/crore, stamp duty on the buy side (0.002% / 0.003%), 18% GST
   on brokerage + NSE + SEBI. Reference round trips, one lot of 500: ₹1,000 future ≈ ₹330; ₹30 option ≈ ₹83.
5. **Risk gate** (`server/risk.py`) — every entry, at preview and again at place; exits are never blocked:
   - per trade: max loss ≤ `RISK_PER_TRADE_PCT` (0.5%) of capital — premium × qty for a long option,
     |entry − stop| × qty otherwise. **Futures and short options need a stop.** Lots are capped to fit.
   - kill switch: day P&L ≤ −`DAILY_LOSS_HALT_PCT` (1%) → no new entries until the next session; week
     P&L ≤ −`WEEKLY_LOSS_HALT_PCT` (3%) → none until next week. Latched even if P&L recovers.
   - drawdown ≥ `DRAWDOWN_REVIEW_PCT` (10%) from peak equity → a "review labels and sizing" banner, not a block.
   - margin: open positions + this order ≤ `MARGIN_CAP_PCT` (30%) of capital. Kotak's `margin_required`
     when a trade session exists, else `MARGIN_ESTIMATE_PCT` (18%) of notional (long options: the premium).
   - intensity: ≤ `MAX_NEW_POSITIONS_PER_DAY` (3) and ≤ `MAX_NEW_POSITIONS_PER_MONTH` (20); no entries on
     a contract's expiry day.

## Life of a position (`data/paper_ledger.json`)

Every poll marks longs at the best bid and shorts at the best ask (a long option with no bid marks at 0);
unrealised P&L is net of entry charges and of the charges to exit at the mark. Exits:

- **manual** — the opposite side on the order sheet or the Close button on the Orders screen, reviewed first;
- **stop** — long: bid ≤ stop, short: ask ≥ stop. The exit fills by walking the book at the *next* poll,
  never at the stop price; a gap through your stop costs what it would really cost.
- **forced_t2** — at the second-last session before expiry (09:20 onwards) every position in that contract
  is closed: stock derivatives are physically settled and this account never holds to expiry.

Realised P&L of a closed trade = gross move − both legs' charges. `return_pct` is on the capital the trade
committed (premium for long options, margin otherwise); `r_multiple` is net P&L over the max loss it was
sized for.

## How to read the scoreboard

Two scores, deliberately separate:

1. **Calls and labels** — direction only, market-adjusted. A call on session D is scored on the stock's
   move to D+h **minus NIFTY 50's move** over the same sessions (`meta.index_closes`; raw when a build has
   no index). A bullish/bearish call is a hit only when the adjusted move exceeds the threshold in its
   direction; smaller moves and neutral calls are shown but not scored, and only the first call per stock
   in any 3 sessions counts. The line "hits needed to beat a coin at this N: 31/50, 59/100, 112/200,
   217/400" is N/2 + 1.645·√N/2 — below it, the accuracy is indistinguishable from coin-flipping. The
   **baseline row** ("always bullish on the top-10 volume-ratio stocks") is scored identically: beat it
   before believing the labels, and expect labels near 33–40% (see guide 10).
2. **Paper trades, realistic net** — what the trades actually made after fills and charges, overall and by
   bucket (`normal` vs `cheap_near_expiry`). A high hit rate with a negative mean net is the classic
   cheap-option shape: many small losses, a rare large win. The bucket exists so that shape cannot hide
   inside the ordinary trades — and `python -m scanner.backtest_cheap_options` (guide 09) measures the same
   bucket across a year of history instead of your handful of fills. Rows that cannot be valued are flagged
   in the CSV's `excluded` column and left out of the summary: a close below intrinsic value (a stale print
   from a contract that did not trade), and contracts spanning a bonus, split or demerger (NSE adjusts their
   strikes, so the old strike cannot be valued against the post-action price).

## Files and endpoints

| | |
|---|---|
| `data/paper_ledger.json` | capital, cash, positions, closed trades, daily equity, halts |
| `data/paper_orders.jsonl` | one line per order event (queued, filled, rejected, cancelled, auto exits) |
| `data/paper_queue.jsonl` | orders waiting for the next session's 09:20 poll |
| `data/refusals.jsonl` | refused orders with reasons and the quote they were judged on |
| `GET /api/paper/summary` | equity, day/week P&L, drawdown, open margin, kill switch, limits |
| `GET /api/paper/positions` `trades` `refusals` | the Orders screen's data; trades include per-bucket stats |

Delete `data/paper_ledger.json` (with the queue and order log) to start the account over.
