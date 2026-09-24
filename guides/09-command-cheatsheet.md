# 09 · Command cheat sheet

```bash
# ---------- first time
unzip fo_scanner.zip && cd fo_scanner
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                          # EOD page only
pip install -r requirements-server.txt                   # server (adds fastapi, growwapi, pyotp, anthropic, kiteconnect)

# ---------- build the scan (run after 19:30 IST from a home/mobile connection)
python -m scanner.build                                  # NSE list + eod2 prices + NSE F&O bhavcopy -> data/scan.json, docs/index.html
python -m scanner.build --skip-fo                        # prices/volume only, no NSE contact
python -m scanner.build --commentary                     # + page-level AI read-out (needs ANTHROPIC_API_KEY)
python -m scanner.demo --install                         # synthetic OI/strikes for UI testing (page shows DEMO)
python -m scanner.diagnose [YYYY-MM-DD]                  # NaNs, one-sided strikes, missing futures, per stock, from the cached bhavcopy

# ---------- publish the static page (Path A)
git add docs data/scan.json && git commit -m scan && git push

# ---------- Groww
python -m server.kotak_login                             # verify KOTAK_CONSUMER_KEY (and the TOTP/MPIN login if set)
python -m server.groww_login                             # verify GROWW_TOTP_TOKEN / GROWW_TOTP_SECRET once

# ---------- run the server (Path B)
uvicorn server.app:app --env-file .env --host 0.0.0.0 --port 8000
sudo systemctl enable --now fo-scanner                   # after installing the unit from guide 03
journalctl -u fo-scanner -f                              # log

# ---------- try the live UI with no broker
DATA_PROVIDER=fake APP_PASSWORD=x uvicorn server.app:app --port 8000

# ---------- Kotak live data + paper (chosen): guide 02b
DATA_PROVIDER=kotak KOTAK_CONSUMER_KEY=... ORDERS=true PAPER=true BROKER=none APP_PASSWORD=x uvicorn server.app:app --port 8000

# ---------- read-only live data via Upstox (alternative): guide 02a
DATA_PROVIDER=upstox UPSTOX_ANALYTICS_TOKEN=... APP_PASSWORD=x uvicorn server.app:app --port 8000

# ---------- events, event study, model, verdict card (guide 14)
python -m scanner.events.run --day 2026-09-24            # fetch/classify/store today's exchange events
python -m scanner.events.run --backfill 2023-01-01 2026-09-24        # 3-year fill, resumable
python -m scanner.events.run --backfill 2023-01-01 2026-09-24 --rating-attachments   # rating PDFs pass
python -m scanner.event_study --since 2023-01-01         # CAR table + data/event_patterns.json
python -m scanner.model --train --since 2023-01-01       # walk-forward train -> data/model.pkl + report
python -m scanner.model --report                         # print the saved model report

# ---------- paper engine (guide 12)
python -m pytest                                         # the test suite (pip install -r requirements-dev.txt)
python -m scanner.backtest_cheap_options --months 12 --max-premium 2 --dte 3 7 --out data/backtest_cheap.csv
                                                         # cheap-option backtest from NSE bhavcopies (home connection)
rm data/paper_ledger.json data/paper_orders.jsonl data/paper_queue.jsonl   # start the paper account over

# ---------- Tailscale
sudo tailscale up                                        # server; phone: install app, sign in
# phone URL: http://<machine-name>:8000/   (user "user", password APP_PASSWORD)

# ---------- API (curl -u user:PASSWORD)
GET  /api/scan            current scan
GET  /api/live            latest quotes, poll time, feed error if any
GET  /api/chain/RELIANCE  nearest-expiry strikes (+ live overlay when open)
GET  /api/commentary/RELIANCE
GET  /api/verdict/RELIANCE    evidence verdict (numbers + news); ?refresh=1 re-runs
POST /api/order/preview   -> token          POST /api/order  (with token)
GET  /api/orders  GET /api/positions        POST /api/rebuild
GET  /api/paper/summary     paper account: equity, day/week P&L, drawdown, margin, kill switch
GET  /api/paper/positions   open paper positions: marks, stops, T-2 dates
GET  /api/paper/trades      closed paper trades net of fills and charges, with per-bucket stats
GET  /api/paper/refusals    orders refused for liquidity, with reasons and the quote
```

## `.env` keys

| Key | Meaning | Default |
|---|---|---|
| `APP_PASSWORD` | required; login for page and API | — |
| `DATA_PROVIDER` | `none` / `kotak` / `upstox` / `groww` / `kite` / `fake` — where live quotes come from | none |
| `KOTAK_CONSUMER_KEY` | Kotak Neo Trade API token; enough for live data (guide 02b) | — |
| `KOTAK_MOBILE`, `KOTAK_UCC`, `KOTAK_TOTP_SECRET`, `KOTAK_MPIN` | only for real orders through Kotak | — |
| `KOTAK_CHAIN_CALLS_PER_POLL` | option-chain calls per poll for live PCR | 12 |
| `UPSTOX_ANALYTICS_TOKEN` | 1-year read-only token (guide 02a) | — |
| `UPSTOX_CHAIN_CALLS_PER_POLL` | option-chain calls per poll for live PCR | 12 |
| `ORDERS` | order sheet on/off (keep false for read-only) | false |
| `BROKER` | `none` / `groww` / `kite` / `fake`, only when `ORDERS=true` | none |
| `PAPER` | simulate orders locally | true |
| `GROWW_TOTP_TOKEN`, `GROWW_TOTP_SECRET` | Groww TOTP key (headless login) | — |
| `GROWW_ACCESS_TOKEN` | alternative: pasted daily token | — |
| `GROWW_OI_CALLS_PER_POLL` | futures OI quotes per poll | 60 |
| `POLL_SECONDS` | live poll interval | 30 |
| `MAX_LOTS_PER_ORDER`, `MAX_ORDERS_PER_DAY` | server-side caps | 5, 20 |
| `ANTHROPIC_API_KEY`, `COMMENTARY_MODEL` | AI reading | —, claude-sonnet-4-6 |
| `KITE_API_KEY`, `KITE_API_SECRET`, `KITE_ACCESS_TOKEN` | Zerodha alternative | — |

Events and model (guide 14):

| Key | Meaning | Default |
|---|---|---|
| `EVENTS_DB` | SQLite event store | data/events.sqlite |
| `EVENTS_RATE_SECONDS` | shared floor between any two fetcher requests | 1.0 |
| `EVENT_ORDER_BUCKETS_PCT` | order/capex buckets, % of market cap | 1,5,20 |
| `EVENT_DEAL_BUCKETS_PCT` | deal buckets, % of shares outstanding | 0.5,2,5 |
| `EVENT_INSIDER_BUCKETS_PCT` | insider buckets, % of company traded | 0.1,1,3 |
| `EVENT_REGISTERED_CRAS` | rating agencies accepted for `rating` events | CRISIL,ICRA,CARE,… |
| `EVENTS_RECENT_SESSIONS` / `EVENTS_ANALYST_SESSIONS` / `EVENTS_UPCOMING_SESSIONS` | join windows | 10 / 5 / 10 |
| `EVENT_RSS_ET` / `EVENT_RSS_MC` / `EVENT_RSS_BS` | tier-3 feeds (analyst views only) | ET/MC/BS |

Paper engine (guide 12; all server-side):

| Key | Meaning | Default |
|---|---|---|
| `PAPER_CAPITAL` | starting capital of the paper account | 500000 |
| `CHARGES_JSON` | override any charge rate in `server/charges.py`, e.g. `{"OPT_NSE_PER_LAKH": 35.03}` | — |
| `FILL_TICK` | tick size for fills (latency tick, rounding against the order) | 0.05 |
| `PAPER_QUEUE_FILL_AT` | when market-closed orders fill (IST, first poll at/after) | 09:20 |
| `NSE_HOLIDAYS` | comma-separated YYYY-MM-DD trading holidays | — |
| `LIQ_FUT_ACCEPT_SPREAD_PCT` / `LIQ_FUT_REFUSE_SPREAD_PCT` | futures spread bands, % of mid | 0.05 / 0.15 |
| `LIQ_FUT_ACCEPT_DEPTH_PCT` / `LIQ_FUT_REFUSE_DEPTH_PCT` | order size as % of visible depth | 25 / 50 |
| `LIQ_OPT_ACCEPT_SPREAD_PCT` / `LIQ_OPT_REFUSE_SPREAD_PCT` | options spread bands, % of mid | 3 / 8 |
| `LIQ_OPT_ACCEPT_DEPTH_PCT` / `LIQ_OPT_REFUSE_DEPTH_PCT` | order size as % of visible depth | 20 / 100 |
| `LIQ_OPT_MIN_OI_LOTS` | strike OI floor for options | 50 |
| `LOTTERY_MAX_PREMIUM` / `LOTTERY_MAX_SESSIONS` | the cheap / near-expiry bucket | 2 / 2 |
| `ALLOW_LOTTERY` | trade the cheap / near-expiry bucket (false: refused, "cheap/near-expiry disabled (ALLOW_LOTTERY)") | false |
| `RISK_PER_TRADE_PCT` | max loss per trade, % of capital (lots capped to fit) | 0.5 |
| `DAILY_LOSS_HALT_PCT` / `WEEKLY_LOSS_HALT_PCT` | kill switch: no new entries past this loss | 1.0 / 3.0 |
| `DRAWDOWN_REVIEW_PCT` | "review labels and sizing" banner threshold | 10 |
| `MARGIN_CAP_PCT` / `MARGIN_ESTIMATE_PCT` | margin cap, % of capital / estimate, % of notional | 30 / 18 |
| `MAX_NEW_POSITIONS_PER_DAY` / `MAX_NEW_POSITIONS_PER_MONTH` | intensity caps | 3 / 20 |
| `BLOCK_EXPIRY_DAY_ENTRIES` | no new position on its own expiry day | true |
