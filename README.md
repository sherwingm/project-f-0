# F&O EOD scanner (Quantis module)

A stock-level, end-of-day scanner for the NSE F&O segment, built as a single mobile-first HTML
page. It ranks and labels the current F&O universe from official closing data; it never emits a
buy/sell call, a strike, or a directional instruction, and the risk disclaimer is a permanent
fixed banner on every screen.

## What one build does

```
NSE fo_mktlots.csv ──► universe (live list, ~210 stocks; not hardcoded)
eod2_data (GitHub) ──► close, prev close, price %, volume, 20-day avg volume, volume ratio, 30 closes
NSE F&O bhavcopy   ──► futures OI (all expiries), OI change %, call OI, put OI, PCR
                   ──► label + the numbers behind it  ──► data/scan.json + docs/index.html
```

* Prices/volume come from the same `eod2_data` repo Quantis' `Eod2Provider` reads (NSE bhavcopy,
  corporate-action adjusted, EQ series). Files are cached under `data/eod2/` and fetched from
  GitHub when missing.
* OI and PCR come from NSE's official UDiFF F&O bhavcopy:
  `https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip`
  (free, published after close). Futures OI = sum of `OpnIntrst` over `STF` rows; OI change uses
  NSE's own `ChngInOpnIntrst`; PCR = put OI ÷ call OI over `STO` rows, all expiries combined.
* Every metric is computed for the **same session**: the latest date present in eod2_data, and
  the F&O bhavcopy for that date. The page prints that date at the top.

## Labels (descriptive, deterministic)

| Pattern | Label |
|---|---|
| price up, volume > 1.0× its 20-day average, futures OI rising | Bullish setup |
| price down, volume > 1.0× its 20-day average, futures OI rising | Bearish setup |
| PCR < 0.7 read as bullish sentiment, > 1.3 as bearish; **secondary**: it can only pull a contradicting pattern back to Neutral, never create a label | — |
| anything else | Neutral |
| OI/PCR missing | Unclassified (never guessed) |

Thresholds live in `scanner/classify.py`. Each row's expanded view lists the exact conditions
and values that produced its label.

## Data gaps never fail a build

Futures OI/PCR (what the labels use) and strike tables are computed in separate steps with
separate statuses (`OI/PCR: ok | strike tables: ok` in the build output and `meta.fo_status` /
`meta.chain_status` in the JSON). Within each step every stock is handled on its own: a stock
with no futures rows is Unclassified for the day, a strike listed on one side only gets 0 OI and
no price on the missing side, a chain that cannot be built is skipped with its reason shown
inside that stock's row. The build prints one `note SYMBOL: [stage] reason` line per gap and the
page lists the affected symbols under the summary. `python -m scanner.diagnose` inspects the
cached bhavcopy for a date and names the stocks and cells involved.

## Run it

```bash
pip install -r requirements.txt
python -m scanner.build            # writes data/scan.json and docs/index.html
python -m scanner.build --skip-fo  # prices/volume only (labels Unclassified), no NSE contact
```

Open `docs/index.html` in any browser. It is self-contained (data embedded), ~250 KB.

**NSE blocks some networks.** Requests to `nsearchives.nseindia.com` are refused (HTTP 403)
from many cloud/datacenter IP ranges and from locked-down proxies; from a normal Indian ISP or
mobile connection they work with the browser-like headers the code already sends. If the build
reports `F&O data: unavailable`, run it from a machine/network that can open that URL in a
browser, or run it on a schedule at home and push the result.

## Put it on your phone (free, ~3 minutes)

The page is static, so it needs no server, no cold starts and nothing that sleeps. GitHub Pages
is the fastest free host; Render "Static Site" or Netlify work identically (publish dir `docs/`).

1. Push this folder to a GitHub repo (private is fine for Pages on a paid plan; public works free).
2. Repo → Settings → Pages → Source: *Deploy from a branch*, branch `main`, folder `/docs`.
3. Your URL is `https://<user>.github.io/<repo>/`. Open it on the phone → browser menu →
   *Add to Home Screen*. It behaves like an app and opens full screen.
4. Refresh daily: `.github/workflows/daily.yml` runs at 20:30 IST Mon–Fri, rebuilds, commits
   `docs/index.html`, and Pages redeploys in about a minute. Enable it under Actions → *Run
   workflow* once to test. If GitHub's runner IPs are refused by NSE (see above), run
   `python -m scanner.build && git commit -am scan && git push` locally instead — or from a
   `cron` job on any always-on box in India.

## Server mode: live quotes, strikes, commentary, orders

The static page is the EOD scanner. `server/` wraps the same scan in a small FastAPI service
that adds the four extended features. Everything defaults to the safe setting.

```bash
pip install -r requirements-server.txt
cp .env.example .env            # set APP_PASSWORD at least
uvicorn server.app:app --env-file .env --host 0.0.0.0 --port 8000
```

Open `http://<host>:8000/` — user `user`, password `APP_PASSWORD`. The server rebuilds the scan
itself at 20:30 IST on weekdays (or `POST /api/rebuild`).

| Feature | What it does | Needs |
|---|---|---|
| Strike-level view | Nearest-expiry chain, ATM ± 8 strikes, OI, ΔOI, premiums; highest call-OI / put-OI strikes and max pain, all from the same bhavcopy | nothing extra (EOD) |
| Live quotes | LTP, day change, futures OI vs previous close for all 210 stocks every `POLL_SECONDS` during market hours; live premiums/OI on an open strike table; sort by live % | `BROKER=groww` with a Groww API subscription (₹499 + GST/month, TOTP key, see below), or `BROKER=kite` with Kite Connect's paid plan and the daily `python -m server.kite_login` |
| Plain-language reading | "Explain these numbers" on a row: Claude writes 90–130 words on what the data shows, what would confirm/contradict it, and the main risk. It is not allowed to say buy/sell/enter/exit/hold or name a strike to trade, and a filter rejects any output that does, falling back to a deterministic summary | `ANTHROPIC_API_KEY` |
| Orders | Tap a strike or "Order: future" → sheet → **Review** (liquidity class, expected fill from the live book, slippage, charges, margin, risk vs caps, paper/live badge) → **Place**. Every order needs a preview token (90 s, tamper-proof), lots ≤ `MAX_LOTS_PER_ORDER`, ≤ `MAX_ORDERS_PER_DAY`; real orders also need an explicit acknowledgement checkbox | `PAPER=true` works with no account: the honest paper engine (guide 12) fills against live depth, books full charges, enforces stops/risk caps and keeps a ledger. Real orders need `PAPER=false`, `BROKER=kite`, a Kite plan, and a **SEBI-whitelisted static IP** for the machine running the server |

`BROKER=fake` gives random-walk quotes with no account, for trying the live UI and the paper
order flow locally. `python -m scanner.demo --install` fills synthetic OI/PCR/strikes into the
scan (the page shows a "Demo data" notice) when NSE is unreachable.

Deployment: `render.yaml` runs the server on Render's free tier (EOD + commentary + live quotes
if you add Kite keys). Because API order placement must come from a static IP whitelisted with
your broker, keep `PAPER=true` on shared hosts; for real orders run the server at home or on a
VPS with a fixed IP and reach it over Tailscale/HTTPS.

### Kotak Neo (chosen): live data on the consumer key alone, paper orders

`DATA_PROVIDER=kotak` with `KOTAK_CONSUMER_KEY` feeds live LTP, futures OI and exact PCR for the
universe; Kotak's quotes/option-chain/scrip-master endpoints authenticate with the consumer key,
so no TOTP or MPIN is stored for a data-only or paper deployment. Adapter `server/kotak.py`:
49-instrument quote batches (about nine calls per poll), a rolling option-chain sweep for PCR and
per-strike OI, contracts from Kotak's scrip master (their epoch offset and `dStrikePrice;`
column handled). `KotakBroker` exists for real orders (`BROKER=kotak PAPER=false`, all five
credentials) and has not been run against a live account. `python -m server.kotak_login` checks
the setup. Tested against a fake SDK answering with the documented payloads.

### Read-only live data (alternative): Upstox Analytics Token

`DATA_PROVIDER=upstox` with `UPSTOX_ANALYTICS_TOKEN` gives live LTP, futures OI and exact PCR for
the whole universe for ₹0. The token is a 1-year read-only credential Upstox issues without the
OAuth flow; it cannot place orders, so the deployment has no trading permission anywhere in it.
Adapter: `server/upstox.py` (two 500-instrument quote calls per poll, plus a rolling
option-chain sweep for PCR and per-strike OI within Upstox's 1,000-calls-per-30-minutes cap).
Order controls exist only when `ORDERS=true` is set explicitly (default off).

### Evidence verdict (numbers + news)

`GET /api/verdict/{symbol}` ("Weigh the evidence" in a row) has Claude search the last ten days of
news with the web-search tool and weigh it against the row's numbers into a structured
assessment: lean, confidence, news found (with links), reasoning, risks, what would change it.
The same instruction guard as the commentary applies; a discarded or failed run returns a
data-only verdict marked `deterministic`. Cached per stock per scan date; `?refresh=1` re-runs.

### Call tracking

On any page (static or server), **Call mode** hides labels until you record your own bullish /
bearish / neutral call per stock; **Scoreboard** scores your calls and the system's labels by
the forward close (horizon 1/3/5 sessions, threshold ±0.5/1/2%) using the price history embedded
in the page, and keeps everything in the browser with export/import. Client-side only:
`templates/index.html`, `CALLS_KEY`.

### Status of each extended feature

| Feature | Tested here | Still needs |
|---|---|---|
| Strike-level view | Yes, against synthetic chains (`scanner.demo`) with the real code path | A build from a network NSE accepts, then it fills itself |
| Live quotes | Yes, with `DATA_PROVIDER=fake`, and with fake Kotak/Upstox/Groww APIs returning documented payloads | Kotak consumer key (free), or Upstox Analytics Token (free), or Groww (₹499 + GST/month) / Kite Connect (₹500/month) |
| Evidence verdict | Prompt, JSON parsing, guard and fallback exercised with a fake model | `ANTHROPIC_API_KEY`; web search usage billed per call |
| Call tracking | Blind call, reveal, scoring, scoreboard, export tested in the page | Nothing |
| Plain-language reading | Prompt, filter and fallback exercised; the API call itself needs a key | `ANTHROPIC_API_KEY` |
| Orders | Paper flow end to end (preview → tamper check → cap → fill → positions); Groww broker path against the fake SDK | Neither `GrowwBroker.place` nor `KiteBroker.place` has touched a real account: start with `PAPER=true`, then one lot |

### Groww (BROKER=groww)

Groww's Trading API is one subscription (₹499 + GST per month, Sept 2026) that covers orders, live
quotes with open interest, the option chain with Greeks and historical candles; there is no free
tier and no sandbox, so paper mode here is the practice environment. Setup:

1. groww.in → Profile → Trading APIs → subscribe; then on the Groww Cloud API Keys page choose
   **Generate TOTP token** (not "Generate API key": that one needs a manual approval every day).
   Put the token and secret in `.env` as `GROWW_TOTP_TOKEN` / `GROWW_TOTP_SECRET`. The server logs
   in by itself at start and again if a call comes back unauthorised. `python -m server.groww_login`
   checks the pair once.
2. `BROKER=groww PAPER=true` → live feed on, orders simulated. Register your static IP with
   Groww before switching `PAPER=false` (their order endpoints refuse other IPs).
3. Adapter: `server/groww.py`. Groww's per-instrument `get_quote` is the only call that returns
   OI (the WebSocket feed carries LTP and depth only), and all live-data calls share a 10/s,
   300/min budget, so each poll batches LTP for every stock and future (`get_ltp`, 50 per call)
   and refreshes futures OI for `GROWW_OI_CALLS_PER_POLL` contracts (default 60) in a rolling
   sweep: at a 30 s poll the whole universe's OI is refreshed roughly every two minutes and the
   page shows each contract's OI timestamp. Strike tables come from one `get_option_chain` call.
   Contracts are resolved against Groww's own instrument file, so lot sizes and trading symbols
   are the broker's, never derived.

Tested against a fake SDK that answers with the documented payloads (rate limiting, rolling OI
sweep, option-chain mapping, margin, place, order list, positions); not yet against a live
Groww account, so start with `PAPER=true`, then one lot.

Zerodha Kite is also wired in (`server/broker.py`, `server/live.py`). Upstox, Angel One SmartAPI
and Dhan would each be one `Provider` (`quote(keys)`) and one `Broker`
(`resolve/place/orders/positions`).

`python -m scanner.build --commentary` adds a page-level plain-English read-out of the whole scan
to the static page (same rules and filter as the per-stock reading; `pip install anthropic`).

## Design lines that are kept on purpose

* Labels and levels are deterministic rules; the AI reading describes, it never instructs.
* No order is ever placed without a preview and a tap on "Place"; nothing runs unattended.
* Paper mode is the default and the live badge is red on every order screen.
* The disclaimer stays fixed on every screen, including the order sheet behind it.

## Layout

```
scanner/universe.py   live F&O list from fo_mktlots.csv (cached fallback)
scanner/equity.py     eod2 loader, price %, volume ratio, 30-day closes
scanner/nse_fo.py     F&O bhavcopy download + futures OI / OI change / PCR
scanner/classify.py   label rules + reasons
scanner/strikes.py    nearest-expiry option chain, max-OI strikes, max pain
scanner/build.py      orchestration, scan.json, HTML render
scanner/demo.py       synthetic OI/PCR/strikes for UI testing (marked as demo)
templates/index.html  the mobile UI (JSON is injected at /*__SCAN_DATA__*/, server flags at /*__SERVER__*/{})
docs/index.html       built page (what gets hosted); docs/demo.html = same UI on demo data
data/scan.json        the same data as JSON, for reuse elsewhere in Quantis
server/app.py         FastAPI: page, /api/live, /api/chain, /api/commentary, /api/order(+preview), /api/orders
server/live.py        quote poller (Kite; FakeProvider for local demo)
server/broker.py      PaperBroker (default) and KiteBroker; preview tokens; contract naming
server/commentary.py  Anthropic call with the descriptive-only brief and output filter
server/kite_login.py  daily access-token helper
server/paper.py       paper ledger: book-walk fills, marks, stops, T-2 exits (guide 12)
server/charges.py     the full charge stack; server/liquidity.py, server/fills.py, server/risk.py
scanner/backtest_cheap_options.py  cheap-option backtest from NSE bhavcopies
scanner/backtest_labels.py         label backtest: labels vs the market-adjusted move that followed
scanner/bhav_cache.py              fill the F&O bhavcopy cache for a date range (both NSE formats)
scanner/results_export.py          result CSVs with one-line column notes -> data/results/
scanner/events/       free exchange-event feed: fetchers, taxonomy, buckets, store (guide 14)
scanner/event_study.py  market-adjusted returns around each event type (T-5..T+5)
scanner/model.py      walk-forward gradient boosting on scan + event features; scanner/verdict_rules.py
tests/                pytest suite (pip install -r requirements-dev.txt)
```
