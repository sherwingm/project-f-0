# Build spec 11 · Honest paper-trading engine + cheap-option backtest

You are working in the `fo_scanner` repository (Python 3.11+, FastAPI server in `server/`, EOD scan in
`scanner/`, single-page UI in `templates/index.html`). Read `README.md`, `guides/02b-kotak-live-paper.md`
and `guides/10-evidence-review.md` first. Then implement the steps below **in order**, running the tests
after each step and committing after each step with a message that names the step.

Hard constraints, never relax them:
- No code path may place a real order. `BROKER=none` + `PAPER=true` stays the default. Do not touch the
  Kotak/Groww/Kite order classes except where this spec says.
- Never write credentials anywhere but `.env`. Never print them.
- Do not weaken the instruction guard in `server/commentary.py` / `server/verdict.py`.
- The static page (`python -m scanner.build` → `docs/index.html`) must keep working with no server.
- Every new rule is a parameter in `server/config.py` with an env override and the default given here.

---

## Step 1 · Depth in live quotes

`server/kotak.py::KotakProvider.quote()` already receives Kotak's 5-level depth in each quote
(`depth.buy[]` / `depth.sell[]`, each `{price, quantity, orders}` as strings). Pass it through:

- For every `NSE:` and `NFO:` key, add `"depth": {"bid": [(price, qty), ...5], "ask": [(price, qty), ...5]}`
  with floats/ints, best level first.
- Add `KotakProvider.quote_one(tradingsymbol)` that resolves a single F&O trading symbol via the scrip
  master and returns the same dict with depth, for on-demand use by the fill engine (options are not in
  the polling universe).
- `server/live.py::LiveFeed.poll_once()` keeps `depth` for the equity and the future in each row
  (`row["depth"]`, `row["fut_depth"]`). The fake provider in `live.py` must emit synthetic depth too.

Test: fake SDK quote with depth → `feed.snapshot()["quotes"][sym]["fut_depth"]["ask"][0]` is a tuple.

## Step 2 · Charges (`server/charges.py`)

One table, `CHARGES_EFFECTIVE = "2026-04-01"`, rates as module constants (env-overridable via
`CHARGES_JSON` if set). Function `round_trip(instrument, side_entry, qty, entry_px, exit_px) -> dict`
and `leg(instrument, side, qty, px) -> dict` returning every component and `total`:

| Component | Futures | Options |
|---|---|---|
| Brokerage per order | min(0.03% × value, ₹20) | ₹20 |
| STT (sell side only) | 0.05% × contract value | 0.15% × premium |
| NSE transaction charge (each side) | ₹1.83 per lakh of value | ₹35.53 per lakh of premium |
| SEBI fee (each side) | ₹10 per crore | ₹10 per crore of premium |
| Stamp duty (buy side only) | 0.002% × value | 0.003% × premium |
| GST | 18% × (brokerage + NSE charge + SEBI) | same |
| STT on exercise (long ITM option held to expiry) | — | 0.15% × intrinsic value |

Acceptance (must match to the rupee, ±1): one lot (500) of a ₹1,000 future bought and sold at ₹1,000 →
total ≈ ₹330. One lot (500) of a ₹30 option bought and sold at ₹30 → total ≈ ₹83.

## Step 3 · Liquidity classification (`server/liquidity.py`)

`classify(contract, quote, lots, sessions_to_expiry) -> {"class": "accept"|"penalty"|"lottery"|"refuse", "reasons": [...], "spread_pct", "visible_qty", "oi"}`

Futures (defaults, all env-overridable):
- accept: spread ≤ 0.05% of mid and order qty ≤ 25% of visible depth on the relevant side
- penalty (add ½ spread to the fill): spread 0.05–0.15%
- refuse: spread > 0.15%, or qty > 50% of visible depth, or no bid/ask

Options:
- accept: spread ≤ 3% of mid, strike OI ≥ 50 lots, order qty ≤ 20% of visible depth
- penalty: spread 3–8%
- **lottery** (not refused; this is the "cheap / near-expiry" bucket to be tested): premium < ₹2 **or**
  sessions_to_expiry ≤ 2. Fill rule for lottery: best ask + 1 tick for buys, best bid − 1 tick for sells,
  regardless of spread. Tag every such fill `bucket="cheap_near_expiry"`.
- refuse: no bid or no ask, OI < 50 lots (unless lottery: then allow if there is an ask), order qty > 100% of
  visible depth.

Every `refuse` is appended to `data/refusals.jsonl` with symbol, contract, reasons, quote snapshot, time.

## Step 4 · Fill engine (`server/fills.py`)

`fill(side, qty, depth, tick=0.05, mode) -> {"price", "levels": [...], "overflow_qty", "slippage_vs_mid"}`

- Buy: walk `depth["ask"]` from the best level; sell: walk `depth["bid"]`. Price = VWAP of the levels
  consumed. Add one tick adverse (latency).
- `penalty` mode adds a further ½ spread adverse. `lottery` mode uses best level ± 1 tick only.
- Overflow (qty beyond visible depth): fill the visible part, price the remainder at the worst visible level
  plus one full quoted spread (adverse), and report `overflow_qty`.
- Market closed: paper orders are **queued**, not filled at the close. They fill at the first poll at or after
  09:20 IST of the next session using that poll's depth (`data/paper_queue.jsonl`). The Review screen says so.
- Stop-loss exits (Step 5) fill at the bid-walk (for longs) at the first poll after the trigger, never at the
  stop price itself.

Tests: single-level fill, multi-level VWAP, overflow pricing, tick rounding, penalty, lottery.

## Step 5 · Paper ledger (`server/paper.py`, replaces the fill logic inside `PaperBroker`)

- `PAPER_CAPITAL` (default 500000). Ledger file `data/paper_ledger.json`: cash, positions, closed trades,
  daily P&L history.
- Each position stores: contract, side, qty, entry fill (price, levels, class, bucket), entry charges, stop
  price (required for futures; optional for options), max loss at entry, `opened_at`, `expiry`.
- Every live poll marks open positions to the current bid/ask (long marked at bid, short at ask) and updates
  unrealised P&L; realised P&L on close is net of both legs' charges.
- Exits: manual (order sheet, opposite side), stop (auto, Step 4 rule), **forced exit at T-2**: on the
  second-last session before a contract's expiry, close it at the first poll after 09:20 with tag
  `forced_t2` (stock derivatives are physically settled; the paper account never holds to expiry).
- Expose `GET /api/paper/summary` (capital, equity, day P&L, week P&L, drawdown from peak, open margin,
  kill-switch state) and `GET /api/paper/positions`, `GET /api/paper/trades`.

## Step 6 · Risk controls (`server/risk.py`)

All server-side, checked at preview and again at place:
- `RISK_PER_TRADE_PCT` default 0.5 → max loss per trade ≤ ₹2,500 on ₹5 lakh. Long option: premium × qty.
  Futures: |entry − stop| × qty (stop required). Lots are capped to satisfy this; the sheet shows the cap.
- `DAILY_LOSS_HALT_PCT` default 1.0 → once (realised + unrealised) day P&L ≤ −1% of capital, **no new entries**
  until the next session; exits remain allowed. `WEEKLY_LOSS_HALT_PCT` default 3.0 likewise for the week.
- `DRAWDOWN_REVIEW_PCT` default 10 → a banner "review labels and sizing" on the page; not a block.
- `MARGIN_CAP_PCT` default 30 → sum of margin of open positions + new order ≤ 30% of capital. Margin
  source: Kotak `margin_required` when a trade session exists, else `MARGIN_ESTIMATE_PCT` (default 18) of
  notional for futures / short options, premium for long options.
- Intensity: `MAX_NEW_POSITIONS_PER_DAY` 3, `MAX_NEW_POSITIONS_PER_MONTH` 20 (paper account).
- Every block is returned as a readable error to the sheet and logged.

## Step 7 · Review screen and Orders screen (`templates/index.html`)

Review shows, before Place: liquidity class and reasons; expected fill price and slippage vs mid; the
depth levels that would be consumed; charges for entry and estimated round trip; margin; risk used vs the
per-trade cap; day P&L and kill-switch state; the `cheap_near_expiry` tag when it applies with the line
"tracked as its own bucket on the scoreboard". A queued (market-closed) order says when it will fill.

Orders screen shows open positions with MTM P&L net of charges, stop, expiry and T-2 date; closed
trades with net P&L and bucket; the paper summary line; refusals count with a link to the reasons.

## Step 8 · Honest scoreboard

- `scanner/build.py` adds `meta.index_closes` (last 30 NIFTY 50 closes from eod2's `daily/nifty 50.csv`,
  or whichever index file eod2 provides; fall back to none) so the page can compute market-adjusted returns.
- Scoring rule in the page: for a call on session D, forward return = stock close(D+h)/close(D) − 1 minus
  the same for the index; a hit is direction correct given |adjusted move| > threshold; at most one scored
  call per stock per 3 sessions (later duplicates shown but not scored).
- Show, next to accuracy: "hits needed to beat a coin at this N: 31/50, 59/100, 112/200, 217/400" (formula
  N/2 + 1.645·√N/2) and whether the current count clears it.
- Add a second score from the paper ledger: realistic-net return per trade (after fills and charges),
  overall and by bucket (`normal`, `cheap_near_expiry`). Labels and your calls are scored on the same rules.
- Add a naive baseline row: "always bullish on the top-10 volume-ratio stocks", scored the same way.

## Step 9 · Backtest of cheap options (`scanner/backtest_cheap_options.py`)

Runs on a machine that can reach `nsearchives.nseindia.com` (home connection). Uses
`scanner.nse_fo.download_fo_bhavcopy` (cached under `data/cache/`, at most 1 download per second) and the
eod2 equity data.

```
python -m scanner.backtest_cheap_options --months 12 --max-premium 2 --dte 3 7 --out data/backtest_cheap.csv
```

For every session in the window, for every stock in the F&O universe: each call and put with
`ClsPric ≤ max-premium` and 3–7 sessions to expiry. Record: date, symbol, contract, strike, premium, spot,
sessions to expiry, the scanner label that day (`scanner.classify` on that day's futures OI/PCR + equity
metrics), and then two outcomes: (a) option close 3 sessions later, (b) intrinsic value at expiry from the
expiry-day underlying close. Net both of charges from Step 2 (buy leg + sell leg or exercise STT), plus one
tick adverse each way.

Output CSV plus a printed table: count, % with net payoff > 0, mean and median net multiple (payoff ÷ cost),
best, worst, total net P&L per ₹1,000 risked — for: all cheap calls, calls on Bullish-labelled stocks,
puts on Bearish-labelled stocks, and by sessions-to-expiry. Print the binomial line for each group's N.
Do not interpret; just print the numbers.

Test on synthetic bhavcopies (no network): build three sessions of fake bhavcopy DataFrames with known
prices so the multiples are checkable by hand.

## Step 10 · Docs and hand-off

- Add `guides/12-paper-engine.md` explaining fills, buckets, charges, risk rules and how to read the
  scoreboard; update `09-command-cheatsheet.md` with the new env keys and the backtest command.
- Run the full test suite and `python -m scanner.build`; confirm the static page still renders.
- Final commit: "paper engine v1: fills, charges, risk, honest scoring, cheap-option backtest".

Report back with: the test results, the two charge acceptance numbers, and the backtest summary table for
the last 12 months (calls on Bullish-labelled stocks vs all cheap calls).
