"""Does the Upstox v3 market data feed (WebSocket) work with our Analytics Token? Read-only probe, no trading.

    set -a; . ~/fo_scanner/.env; set +a; .venv/bin/python scripts/upstox_ws_probe.py

Authorizes (GET /v3/feed/market-data-feed/authorize), connects, subscribes RELIANCE and NIFTY 50 in `full` mode and
counts the binary messages for 15 s. Never prints the token or the one-use URL.
"""
import asyncio
import json
import os
import sys

import requests
import websockets

KEYS = ["NSE_EQ|INE002A01018", "NSE_INDEX|Nifty 50"]


async def main() -> int:
    tok = os.environ.get("UPSTOX_ANALYTICS_TOKEN", "")
    if not tok:
        print("UPSTOX_ANALYTICS_TOKEN is empty")
        return 1
    r = requests.get("https://api.upstox.com/v3/feed/market-data-feed/authorize",
                     headers={"Accept": "application/json", "Authorization": f"Bearer {tok}"}, timeout=15)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    print("authorize:", r.status_code, body.get("status"), (body.get("errors") or [{}])[0].get("message", ""))
    url = ((body.get("data") or {}).get("authorized_redirect_uri"))
    if not url:
        return 1
    async with websockets.connect(url, max_size=2**22) as ws:
        print("connected")
        sub = {"guid": "probe1", "method": "sub", "data": {"mode": "full", "instrumentKeys": KEYS}}
        await ws.send(json.dumps(sub).encode())                  # Upstox wants the request as a binary frame
        n, size, seen = 0, 0, set()
        loop = asyncio.get_running_loop()
        end = loop.time() + 15
        while loop.time() < end:
            try:
                m = await asyncio.wait_for(ws.recv(), timeout=end - loop.time())
            except asyncio.TimeoutError:
                break
            n, size = n + 1, size + len(m)
            seen |= {k for k in KEYS if k.encode() in m}
        print(f"messages: {n}, bytes: {size}")
        print("keys with data:", sorted(seen))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
