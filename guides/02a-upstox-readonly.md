# 02a · Free read-only live data (Upstox Analytics Token)

Result: live LTP, futures OI and exact PCR for all F&O stocks during market hours, for ₹0, with
no trading permission anywhere in the setup. This is the cheapest way to get read-only live
data, and it is read-only by construction rather than by configuration.

## Why this and not a trading API

| | Upstox Analytics Token | Groww API | Kite Connect |
|---|---|---|---|
| Cost | ₹0 | ₹499 + GST/month | ₹500/month (data plan) |
| Can it place orders? | **No, ever** — the token is issued read-only | Yes | Yes |
| Login | One token, valid a year | TOTP each day | Browser login each day |
| Static IP | Not needed | Not for data | Not for data |
| OI in one call | Full quotes: 500 instruments per call, OI included | One contract per call | 500 per call, 1 call/s |
| Option chain with OI and IV | Yes, per underlying and expiry | Yes | No (assemble it) |

You need an Upstox account (free to open, no trades required) and nothing else.

## 1. Generate the token

1. Sign in at account.upstox.com/developer/apps.
2. Open the **Analytics** tab → **Generate Token** → Confirm.
3. Copy the full token (copy icon next to the truncated value). Only one Analytics Token is
   active per account; generating another revokes the previous one. It expires one year from
   generation; the server logs a clear 401 message when that day comes.

## 2. `.env`

```
APP_PASSWORD=<your page password>
DATA_PROVIDER=upstox
UPSTOX_ANALYTICS_TOKEN=<the token>
UPSTOX_CHAIN_CALLS_PER_POLL=12
POLL_SECONDS=30
ORDERS=false
ANTHROPIC_API_KEY=            # optional: "Explain these numbers" and "Weigh the evidence"
```

`ORDERS=false` is the default and means the page has no order controls at all; with Upstox as
the data source there is also no credential in the system that could place one.

## 3. Run

```bash
pip install -r requirements-server.txt
uvicorn server.app:app --env-file .env --host 0.0.0.0 --port 8000
```

Log line to expect: `live feed on (Upstox, read-only): LTP + futures OI every 30s, PCR/strike OI
for 12 stocks per poll`. Reach it from the phone as in guide 04.

## What refreshes when

Upstox allows 25 calls/s, 250/min and 1,000 per 30 minutes. Each poll spends two full-quote
calls (every stock and every near future, with OI) plus 12 option-chain calls on a rolling sweep.
So on a 30-second poll:

- **LTP and futures OI:** every stock, every 30 s.
- **Live PCR and per-strike OI:** each stock refreshed about every 9 minutes (210 ÷ 12 polls);
  each row shows the time its PCR was read. Opening a strike table pulls that stock's chain fresh
  if the cached one is older than two minutes.
- Total: about 840 calls per 30 minutes, under the cap. Raising `UPSTOX_CHAIN_CALLS_PER_POLL`
  to 18 brings the PCR cycle down to ~6 minutes and uses ~1,000 calls; do not go higher on a
  30-second poll.

## Reading the live numbers

- **Live %** is today's move versus the previous close (Upstox reports `net_change`; the server
  derives the previous close from it).
- **Live OI %** is the current futures OI versus the OI at yesterday's close from the EOD scan.
- **Live PCR** is put OI ÷ call OI across every strike of the nearest expiry, from the chain.
- Sort chips **Live %**, **Live OI %** and **Live PCR** appear while the market is open.

## If you later want the Groww or Kite paths

They stay in the code (`DATA_PROVIDER=groww|kite`, guide 02) but nothing in this guide depends
on them. The order sheet only exists when `ORDERS=true` is set explicitly.
