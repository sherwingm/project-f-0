# 02 · Groww API setup (Path B)

Result: a `.env` file the server can log in with, verified once from your computer.

## 1. Subscribe

Groww web → profile (top right) → **Settings** → **Trading APIs** → subscribe. As of September
2026 it is one flat plan, ₹499 + GST per month, covering orders, live quotes with open interest,
the option chain with Greeks and historical candles. There is no free tier and no sandbox; the
scanner's paper mode is where you practise.

## 2. Create a TOTP key (not an API key)

Go to the **Groww Cloud API Keys** page (groww.in/trade-api/api-keys). Under the dropdown next to
*Generate API Key* choose **Generate TOTP token**, name it, and copy both values:

- the **TOTP token** → `GROWW_TOTP_TOKEN`
- the **secret** (the string behind the QR code) → `GROWW_TOTP_SECRET`

Why TOTP: Groww's plain API-key flow needs a manual approval on their website every day, which
defeats a server. The TOTP key does not expire, so the server can generate the day's access token
by itself each morning and again if a call ever comes back unauthorised.

Keep the secret like a password: anyone with it can trade in your account.

## 3. Write `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```
APP_PASSWORD=<a long password you will type on the phone once>
BROKER=groww
PAPER=true
GROWW_TOTP_TOKEN=<from step 2>
GROWW_TOTP_SECRET=<from step 2>
GROWW_OI_CALLS_PER_POLL=60
POLL_SECONDS=30
MAX_LOTS_PER_ORDER=5
MAX_ORDERS_PER_DAY=20
ANTHROPIC_API_KEY=            # optional, enables "Explain these numbers"
```

Leave `PAPER=true` until you have finished the checklist in guide 05.

## 4. Verify the login

```bash
pip install -r requirements-server.txt
set -a; source .env; set +a          # Windows PowerShell: load the variables manually
python -m server.groww_login
```

Expected: `access token OK: xxxxxxxxxxxx… (nn chars)`. If it fails, see guide 06 (Groww errors).

The token endpoint allows 150 generations per day; the server uses one at start-up and one per
recovery, so this is never a problem in normal use.

## 5. Register your static IP with Groww (before real orders only)

From April 2026 every broker accepts API orders only from a static IP you have registered with
them; Groww's order endpoints refuse other addresses, while quotes and the option chain work from
anywhere. Market-data-only use (PAPER=true) needs no static IP.

When you are ready for real orders: get a static IP for the machine that will run the server
(guide 03 covers the options), then register it in Groww's Trading API settings. The rules allow
changing it at most once per calendar week, so pick the machine first and the IP second.

## Rate limits that matter (so you understand what the server does)

Groww shares one budget across all live-data calls: 10 per second, 300 per minute. Its one call
that returns open interest, `get_quote`, takes a single contract; the LTP call takes 50. So each
poll the server fetches LTP for all 210 stocks and 210 near futures in about ten calls, then
refreshes futures OI for 60 contracts in a rolling sweep. At a 30-second poll the whole
universe's OI cycles roughly every two minutes, and each row shows when its OI was last read.
Raise `GROWW_OI_CALLS_PER_POLL` towards 120 for a faster cycle if you never open strike tables
during the day; lower it if you see `429` errors in the log.
