# 02b · Kotak Neo live data + paper trading (the chosen path)

Result: live LTP, futures OI and PCR from Kotak during market hours, paper orders with simulated
fills, nothing in the system able to place a real order. Cost ₹0 (Kotak's Trade API is free).

## What you need from Kotak

Only one value for this setup: the **consumer key**.

Neo app or web → **More** → **Trade API** card → **Generate application** → copy the token.
That token is `KOTAK_CONSUMER_KEY`. Kotak's quote, option-chain and scrip-master endpoints
authenticate with it alone, so the server never logs in with your mobile, TOTP or MPIN.

Leave `KOTAK_MOBILE`, `KOTAK_UCC`, `KOTAK_TOTP_SECRET` and `KOTAK_MPIN` empty. They are needed
only for real orders through Kotak (guide 03's "when you get there" section), and with them empty
the code cannot reach Kotak's order endpoints at all.

## `.env`

```
APP_PASSWORD=<pick a password>
DATA_PROVIDER=kotak
KOTAK_CONSUMER_KEY=<the token>
KOTAK_CHAIN_CALLS_PER_POLL=12
POLL_SECONDS=30
ORDERS=true
PAPER=true
BROKER=none
MAX_LOTS_PER_ORDER=5
MAX_ORDERS_PER_DAY=20
ANTHROPIC_API_KEY=            # optional: "Explain these numbers" and "Weigh the evidence"
```

`ORDERS=true PAPER=true BROKER=none` turns on the order sheet with local simulated fills
(`data/paper_orders.jsonl`); `BROKER=none` guarantees no route to a real order.

## Verify, then run

```bash
pip install -r requirements-server.txt        # includes kotakneoapi and pyotp
python -m server.kotak_login                  # reads .env from the current directory itself
```

Expected output:

```
1. consumer key + scrip master … OK (N equities, M NSE F&O contracts)
   symbol check: all mapped
2. quotes (no login) … OK
   RELIANCE-EQ: ltp 1243.90 prev close 1226.40 OI 0
   RELIANCE26SEPFUT: ltp 1248.10 prev close 1230.05 OI 12345678
3. TOTP/MPIN login skipped (...); fine for read-only + paper
```

Line 2 is the one that matters: a price and an OI on the futures line means the field names
match on your account. Then:

```bash
uvicorn server.app:app --env-file .env --host 0.0.0.0 --port 8000
```

Log line to expect: `live feed on (Kotak Neo, consumer key only): LTP + futures OI every 30s,
PCR/strike OI for 12 stocks per poll`. Reach it from the phone as in guide 04.

## What refreshes when

Kotak's quote endpoint takes 50 instruments per call at up to 25 calls a second, so every poll
fetches LTP, volume, previous close and futures OI for all 210 stocks and their near futures in
about nine calls. Its option-chain endpoint returns every strike's OI for one underlying per call;
the server sweeps 12 underlyings per poll, so on a 30-second poll:

- **LTP, Live %, futures OI, Live OI %:** every stock, every 30 s.
- **Live PCR and per-strike OI:** each stock about every 9 minutes; each row shows the time its
  PCR was read. Opening a strike table pulls that stock's chain fresh if the cached one is older
  than two minutes.

Kotak publishes 25 requests/second for market data but not a per-minute cap; the server holds
itself to 20/s and 200/min. If the log shows `429`, lower `KOTAK_CHAIN_CALLS_PER_POLL` to 8.

## Reading the live numbers

- **Live %** is today's move versus the previous close that Kotak reports in the quote.
- **Live OI %** is the current futures OI versus the OI at yesterday's close from the EOD scan.
- **Live PCR** is put OI ÷ call OI across the strikes Kotak returns for the nearest expiry
  (60 each side; stock chains rarely have more).

## When you eventually want real orders through Kotak

Fill the four other `KOTAK_*` values, set `BROKER=kotak` and `PAPER=false`, register a static IP
with Kotak (required for API orders since April 2026) and run `python -m server.kotak_login`
again: steps 3 and 4 then exercise the TOTP and MPIN login. The order path has not been run
against a live account; start with one lot of a liquid future.
