# 06 · Troubleshooting

Find the message you see; each entry says what it means and what to do.

## Build (`python -m scanner.build`)

**`F&O data: unavailable: NSE refused the request ... (HTTP 403)`**
NSE's archive server (`nsearchives.nseindia.com`) is refusing this network. It routinely blocks
datacenter ranges (GitHub Actions, Render, Streamlit Cloud, AWS, GCP, Azure) and some corporate
proxies. Run the build from a home broadband or mobile connection; the code already sends
browser-like headers. Prices and volume still build; only OI/PCR/strikes are missing until a
successful run. If it fails from home too, open
`https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv` in a browser: if that works, retry
the build a minute later (NSE rate-limits bursts).

**`strike tables: error: cannot convert float NaN to integer`** (builds before 23 Sep 2026: `F&O data: error`)
A strike listed on one side only (a call with no put, or the reverse) in one stock's chain. Fixed:
the missing side now shows 0 OI and no price, the stock is noted inside its row, and the build
prints `note <SYMBOL>: [chain] ...` for every affected stock. OI, PCR and labels were never
affected by this error; the old banner claiming otherwise was wrong. To see which stocks carry
gaps on a given day: `python -m scanner.diagnose` (or with a date, `python -m scanner.diagnose 2026-09-18`).

**`note XYZ: [oi] no futures OI rows in the bhavcopy`**
That stock had no futures rows in NSE's file that day (new to F&O, or a data gap). It is shown as
Unclassified for the session; nothing else changes.

**`No F&O bhavcopy for 2026-09-22 (404)`**
That date's file is not published yet (usually by ~19:00 IST) or it was a holiday. The build
uses the latest date present in eod2 and expects the matching bhavcopy; wait and re-run.

**Header shows a date two sessions old**
`eod2_data` (the price source, on GitHub) has not synced the latest session yet. It usually
catches up in the evening; run the build again later or move the daily job to 21:30 IST.

**`NSE unreachable ...; using cached universe of 210 stocks`**
Warning only. The stock list came from the last successful fetch; it changes rarely.

**`Could not fetch F&O universe ... no cache`**
First build ever on a blocked network. Copy `data/cache/fo_universe.txt` from the zip (it is
included) or run once from a home connection.

**`ModuleNotFoundError: pandas` / `growwapi`**
The virtualenv is not active or requirements are not installed:
`source .venv/bin/activate && pip install -r requirements-server.txt`.

## GitHub Pages

**404 at the Pages URL** — Settings → Pages: branch must be `main`, folder `/docs`, and
`docs/index.html` must be committed (`git status`).

**Page never updates** — Actions tab: is the workflow enabled, did the last run fail with the
NSE 403? Then follow guide 01 step 5 and build from home.

**Phone shows an old page** — pull down to refresh; if using the home-screen icon, close it fully
and reopen. Pages can take a minute after a push.

## Server start-up

**`APP_PASSWORD is not set on the server`** (503) — `.env` not loaded. Use
`--env-file .env` or the systemd `EnvironmentFile=` line.

**`set GROWW_ACCESS_TOKEN, or GROWW_TOTP_TOKEN + GROWW_TOTP_SECRET`** — `BROKER=groww` without
credentials in `.env`.

**`no data/scan.json yet`** — run `python -m scanner.build` first or `POST /api/rebuild`.

**Port already in use** — another instance is running: `sudo systemctl stop fo-scanner` or change
`--port`.

## Groww

**`GrowwAPIAuthenticationException` / 401 at start-up**
TOTP token or secret is wrong, or the API subscription has lapsed. Run
`python -m server.groww_login` to see the raw error. Check the subscription page on Groww.

**401 in the middle of the day**
Access tokens are issued per day; the server regenerates once automatically on an auth error. If
it keeps happening, the TOTP secret's clock is off: the server's system time must be correct
(`timedatectl` on Linux) because TOTP codes are time-based.

**`GrowwAPIRateLimitException` / 429**
Live-data budget exceeded (10/s, 300/min shared). Lower `GROWW_OI_CALLS_PER_POLL` (try 40) or
raise `POLL_SECONDS` to 45. Opening many strike tables in quick succession also spends budget.

**`no NSE F&O contract on Groww for XYZ FUT 2026-09-30`**
The expiry in the scan does not match Groww's instrument file (for example the day after expiry,
before the next build). Rebuild the scan; if it persists, the instrument file changed format —
check `python -c "from growwapi import GrowwAPI; print(GrowwAPI(...).get_all_instruments().columns)"`.

**Orders refused with an IP message (PAPER=false)**
Your static IP is not registered with Groww, or it changed. Groww lets you change it once per
calendar week.

**`/api/live` shows `"error": ...`**
The feed keeps polling and shows the last error; it clears on the next good poll. Persistent
network errors on a VPS usually mean an outbound firewall rule.

**No live data although the market is open**
The first poll takes ~10 s (rate-limited); wait one poll interval. Check `market_open` in
`/api/live`: the server's clock/timezone must be right (it computes IST itself, but the system
clock must be accurate).

## Orders (paper or live)

**`preview the order first`** — the page always previews before placing; if you see this from
your own script, call `/api/order/preview` and pass its `token`.

**`order changed since preview`** — you edited after Review; tap Review again.

**`confirmation expired`** — more than 90 s passed since Review.

**`lots must be between 1 and 5`** — `MAX_LOTS_PER_ORDER` cap; change it in `.env` if intended.

**`daily cap of 20 orders reached`** — `MAX_ORDERS_PER_DAY`; resets at midnight IST on restart.

**`broker rejected the order: ...`** — the text after the colon is Groww's own reason (margin,
freeze quantity, price band, market closed).

## Phone

**Home-screen icon opens a blank page** — the Tailscale toggle on the phone is off, or the server
machine is asleep. Open the Tailscale app; it lists the server as online or offline.

**Asked for the password again** — the browser cleared credentials; enter `user` and
`APP_PASSWORD`.

**Table scrolls sideways** — you are zoomed in; double-tap to reset. The layout itself never
needs horizontal scrolling at phone widths.
