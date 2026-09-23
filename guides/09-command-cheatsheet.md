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
