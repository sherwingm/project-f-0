# Progress

Updated at the end of every session. `DECISIONS.md` is authoritative for rules and the strategy record.

**State as of 2026-10-13.**

## 2026-10-13
- New PC checkout (`D:\project-f-0-main\project-f-0-main`, linked to `origin/main`). Kotak consumer key regenerated
  (local `.env` and Render). Render: `PUBLIC_ACCESS=true` (no login, single user; real orders stay refused).
- **S1 v6 closed** (DECISIONS.md): the 3-session decay exit sold after 3.6 sessions on average and lost money
  (arm A −19 %, t −2.3; arm B −3.7 %, N 75), while the futures diagnostic of the same signal stayed strong
  (B +3.66 % over 20 sessions, t 4.25). The 2021-22 results events were back-filled into the local event store.
- **S1 v7 closed** (DECISIONS.md): current-month calls down to 3 sessions left, 5-session decay exit, 50 % stop,
  T-1. Arm A −17.3 % (t −1.5); arm B +31.8 % but t 1.1 and N 84. Near-expiry calls lost most (A −37 %): the stop
  closed nearly all of them within 2 sessions. Per-trade sheets: `python -m scanner.trade_sheet` (option peak and
  dip while held and after the exit), `data/results/S1_v6_trade_sheet.xlsx`, `S1_v7_trade_sheet.xlsx`.
- **Trading-terminal page** (`templates/index.html`, one file for Pages and the server): watchlist with tick time,
  % change, volume and pins; candle chart (TradingView Lightweight Charts 4.2.0) with volume, ATP line and previous
  close, timeframes 1m/5m/15m (server ticks) and 1D (120 sessions from the scan); option charts for ATM ± 5 strikes of
  an opened stock; tabs Overview (OHLC, ATP, buy/sell qty, 52-week range, futures, depth), Options (live chain),
  News (Google News headlines + filings), Results (3 quarters, QoQ / YoY), Signals (verdict card, AI); heatmap,
  top movers, price alerts, keyboard shortcuts, light/dark, phone layout, links like `#RELIANCE/options`.
- Server: Kotak's `avg_cost` (ATP), OHLC, LTQ, buy/sell qty, 52-week range, circuits now parsed; intraday tick
  buffer (`server/live.py`) and `server/candles.py`; `/api/intraday`, `/api/news`, richer `/api/chain`.
- Quarterly results: `scanner/financials.py` (NSE Integrated Filing XBRL from Mar 2025, older XBRL for YoY) →
  `data/financials.json`, refreshed nightly for stocks that just reported (40 a run at most).
- Intraday charts exist only for the time the server was polling: Render's free tier sleeps after 15 minutes
  without visits, so keep the page open during market hours (or move to the VM).

- **Forward paper test from 14 Oct** (`scanner/forward_s1.py`, nightly Action, page buttons **Arm A / Arm B**):
  S1 v7 rules without near-expiry trades, one session at a time from NSE's closing files: yesterday's results beats
  are bought at the session's average price, marked at each close (50 % stop, 5 sessions without a new high, T-1),
  and followed after the exit to T-1 (max peak / max dip while held and after). State `data/forward/s1_forward.json`.
  First signal expected: HCLTECH (results 12 Oct evening, +4.5 % vs its sector on 13 Oct), arm A only.
- **Data dates fixed:** the scan was stuck on 09 Oct (eod2 stopped at 25 Sep; the NSE fallback refused gaps over
  15 days, now 60). The events job ran after midnight and fetched the next day, so each session's results and
  Monday ban lists were missed; it now re-reads the last 3 days and the next ban list, and one failing source (BSE
  answering with text) no longer stops the run.
- **Options only:** "Buy CE / Buy PE" replace "Order: future"; the server refuses futures orders; the futures chart
  leg, futures alerts and the futures price block are gone (OI and PCR stay as information).
- **Charts:** with no live polls (closed market, restart, Render asleep) 1m/5m/15m show the last session from
  Kotak's historical API; a late start is filled from 09:15; errors say what happened instead of "Unexpected token".

- **Results page is the home page** (`templates/results.html`, `/` on the server; the terminal moved to
  `/terminal`): paper account, Arm A, Arm B, no chart (35 KB, loads at once). Each open paper position is a card:
  entry price, now, max up / max dip (traded price, with time), stop, auto-exit (T-2), P&L, Close. Closed trades
  show max up / dip while held and after the sale (the server keeps quoting the contract until its T-2 day). The
  terminal's Orders popup is gone (its Orders / Arm buttons open the results page).

- **Paper account restarted for the S1 rule trades (from 14 Oct)** (`server/rules.py`, ledger epoch
  "2026-10-14 S1 rules"; the hand-placed 30 Sep system-test trades are archived inside the ledger). Each "buy next
  session" signal of the forward test is bought twice, 1 lot each, outside the manual-order limits: at the open
  (first poll from 09:15, the strike picked overnight from day 0's prices, at the best ask) and at the close (first
  poll from 15:20, the walk on today's volume and average price, at ATP + 1 tick). Exits once a session at 15:20 on
  the last traded price: 50 % stop, 5 sessions without a new closing high, T-1; sold at the best bid. Each trade is
  tagged with its arms (A, B or both); the results page has one scoreboard per arm, by entry time, and the terminal
  shows Arm A / Arm B badges. The server pulls the scan at 08:40 and 09:05 for the morning list. Render must be
  awake at 09:15 and 15:20 (keep the page open, or a free uptime pinger every 5 minutes).

- **S1 v8 closed, and the live rules fail on recent data** (holdout used by the user's choice, 2026-10-14; NSE F&O
  files for 2025-02 → 2026-10 now cached, ban lists back-filled): on Apr 2025 – Sep 2026 calls on any result in a
  strong sector lost −27.6 % a trade (t −3.4); the live rules: arm A −3.3 % (t −0.25), arm B −14.5 % (t −1.0). Even
  the stock's own move after results was about zero in this period (20 sessions: A +0.2 %, B +0.1 %), so the
  2021-24 drift did not carry on. The live paper account keeps running as the only fresh evidence.

- **S2 started (price + futures OI build-up, stock options, 1-5 day holds).** Step 1 screen on the stock, year by
  year 2021-2026 (`python -m scanner.s2_screen`, all NSE F&O files 2021-2026 now cached): 1 of 48 cells passes —
  **short build-up** (price −3 % or more, futures OI +10 % or more, volume 1.5× average): the stock keeps falling,
  +0.62 % for a 5-session short (t 3.2), positive in 5 of 6 years including 2025 and 2026. Small for options: step 2
  must show a put can keep it after time decay and costs. S1's pages and paper trades are unchanged.

## Secrets and expiries (never the values)
- `LEDGER_GITHUB_TOKEN`: fine-grained GitHub token, Contents read/write on `project-f-0` only. Stored in Render →
  Environment (and later the VM `.env`; then deleted from Render). **EXPIRES 2026-10-30**: renew and replace
  before then, or the paper account stops being saved (the summary's `persistence.error` shows it).
- `APP_PASSWORD`: local `.env` and Render → Environment (`PUBLIC_ACCESS=false` is live since 2026-09-30). (A GitHub Actions secret is no longer needed: the
  opening-snapshot workflow was deleted.)
- `KOTAK_CONSUMER_KEY`: Render → Environment and local `.env`; market data only, no login needed.

## Built and working
- EOD scan (labels, OI/PCR, strikes, events, verdict card), phone page, GitHub Pages; nightly GitHub Action.
- Scan freshness: when eod2_data lags, the build fills the missing sessions from NSE's cash-market bhavcopy and
  index-close file (`scanner/cm_fallback.py`; listed in `meta.price_fallback_days`). Checked on 28–29 Sep 2026.
- Live server on Render: Kotak feed 213 stocks every 30 s, live labels, 09:30 snapshot, paper orders with real-depth
  fills, charges, stops, kill switch (first live run 2026-09-30).
- Paper account persistence (`server/durable.py`): committed to the `paper-state` branch on fills, exits, stop
  triggers and a 15-minute snapshot; restored on start. End-to-end restart test passed 2026-09-30.
- Position limits (DECISIONS.md): long-option cost ≤ 6 % of paper capital, max 3 open positions, daily loss
  halt 2 %.
- Backtest engine (`scanner/option_engine.py`): fills (VWAP/close + tick, ≥ 50 contracts), expiry rule,
  test/holdout split, date-clustered t.
- Guide 17: always-on Mumbai VM (Lightsail or Oracle), IST + NTP, systemd, Tailscale, the NSE-archive test.

## Strategy record (DECISIONS.md is authoritative)
- S1 v1 superseded; v2 closed (results-miss: no drift); v3 closed (strength score: selected stocks went the
  wrong way on the long side, 20-session t −2.34); v4 closed (results-beat naked call: 3 and 1 trades under the
  ₹2–8k budget).
- S1 v5 (same signal, ₹10–30k band, 1 lot, long call, current-month expiry) **closed 2026-09-30**: arm A 170
  trades, mean −1.2 %, t −0.13; arm B (strong sector) 57 trades, mean +42.7 %, t 2.29, positive in both
  sub-periods, but N 57 < 200.
- Only positive signal so far: results beats +1.3 % (all) / +1.9 % (strong sector) over 20 sessions net of
  the sector, t ≈ 3, 2021–2024.

## Paper account (live test, Render)
- Opened 2026-09-30 11:52 IST by the system-test rule (top live setups by volume ratio, 1 lot, ATM, stop 0.5x):
  APOLLOHOSP 8200 PE, MAXHEALTH 940 PE, FORTIS 780 PE (October expiry). At the 15:36 close: equity ₹5,15,590.29,
  unrealised +₹15,590.29 after exit charges, no stop triggered, 0 closed trades. Held overnight; the account is
  in the `paper-state` branch and restored on every restart.

## Known issues
- eod2_data stale since 2026-09-25: the fallback fills the gap from tonight's build (first run after the
  2026-09-30 push). The server's scan on 2026-09-30 still had the expired 29 Sep chains; the paper orders used
  the October contracts by hand.
- 2026-09-30 paper test: the ledger was wiped twice (11:05, this PC slept and Render slept; 13:47, Render
  redeployed when environment variables were saved). The three positions were restored from the 13:46 watcher
  log; stops were not watched between 13:47 and the restore. Saving environment variables on Render always
  redeploys: with persistence on, the account now survives it.
- Render free tier sleeps after 15 minutes without visits; until the VM runs, something must visit it during
  market hours.

## Next
1. Renew `LEDGER_GITHUB_TOKEN` before 2026-10-30.
2. Decide S1 v8 from the diagnostic: the results-beat drift is real in the stock (v4–v7 futures diagnostics),
   the losses come from the option expression and exits (DECISIONS.md). 2021-2024 is now heavily reused:
   any next version should be judged mainly on the 2025+ holdout.
3. Create the always-on VM (guide 17; Oracle Mumbai), token in its `.env`; confirm the live feed and a restart.
   Then Render becomes the mirror: `DATA_PROVIDER=none` and delete `LEDGER_GITHUB_TOKEN` there.
