# 08 · Broker API comparison (reference, September 2026)

Condensed from the research review done for this build. Prices and limits change; the official
developer pages are the source of truth before you pay for anything.

## Why Groww is wired in

You trade on Groww. Its API is one flat subscription (₹499 + GST/month) covering orders, live
quotes with open interest, the option chain with Greeks and historical candles, with an official
Python SDK. Its two limitations shaped the adapter: the WebSocket feed carries LTP and depth only
(no OI), and the single call that returns OI takes one contract at a time under a shared
10/s, 300/min budget — hence the batched-LTP plus rolling-OI design in `server/groww.py`.

## The field

| Broker | Cost for live data + orders | OI access | Option chain call | Sandbox | Notes |
|---|---|---|---|---|---|
| **Groww** | ₹499 + GST/month, one plan | `get_quote`, one contract per call; chain has OI per strike | Yes (OI, LTP, Greeks, IV) | No | TOTP key allows headless daily login; 1000 WebSocket subscriptions (LTP/depth only) |
| **Zerodha Kite Connect** | Personal plan free (orders only, no market data); Connect ₹500/month per key for live + historical | Quote endpoint, 500 instruments/call but throttled to 1 call/s; OI in WebSocket full mode | No (assemble from instrument dump) | No | No sandbox at all; manual login once a day is expected |
| **Upstox** | Free | Option-chain endpoint with OI, prev OI, IV, Greeks; 25 req/s | Yes | **Yes** (place/modify/cancel) | 1-year read-only data token avoids daily re-login for market data |
| **Angel One SmartAPI** | Free | Full-mode quote and WebSocket carry OI | No native chain endpoint | No | Client code + MPIN + TOTP login |
| **Dhan v2** | Data API free if ≥25 trades in 30 days, else ₹499 + tax/month | OI in WebSocket quote packets; single-call chain (1 call per 3 s) | Yes | Via third-party only | 5 WebSocket connections, unlimited instruments |
| **Fyers v3** | Free | Per-symbol depth calls, ~100k calls/day cap | Yes (v3) | No | Call cap makes all-universe per-strike OI polling awkward |

## Regulatory constants (all brokers)

- Static IP registered with the broker for order placement; one change per calendar week;
  reads exempt at most brokers.
- 10 orders per second per exchange is the threshold above which a strategy must be registered.
- OAuth + 2FA login; daily session end; broker adds the algo identifier to each API order.

## Hosting

- NSE's archive server blocks most datacenter IPs. Run the EOD build from a residential
  connection; a phone hotspot works in a pinch.
- For real orders you need a fixed IP: a home ISP static-IP add-on (~₹150–300 + GST/month on
  Airtel/ACT business plans) or an Indian VPS (AWS Lightsail Mumbai from ~₹300/month,
  DigitalOcean Bangalore from ~$4/month). Hetzner has no Indian region.
- Reach the server from the phone with Tailscale; never expose the port directly.

## If you ever want a second adapter

Each broker is one `Provider` class with `quote(keys)` in `server/live.py` and one `Broker` class
with `resolve / margin / place / orders / positions` in `server/broker.py`; `server/groww.py` is
the template. Upstox would be the natural second one: free, with a sandbox for order testing.
