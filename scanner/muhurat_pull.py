"""The Muhurat session's prices for the paper account's open options (numbers only).

    python -m scanner.muhurat_pull 2026-11-08 <paper_ledger.json>

Sunday 8 Nov 2026 was a special NSE session (about 14:20 - 15:30, then a short post-close window). The project lists it as a
holiday (data/nse_holidays.json), so the server recorded and traded nothing: the paper account did not see it. This reads
Upstox's public 1-minute history (no token) for every option held that day and writes data/muhurat/<date>.json: per contract
the first and last traded price, high, low and candle count of the window. The results page uses it as the previous close of
the next session's gap (server/app.py /api/paper/gaps), and the report below tells how big the moves were. Prices are LAST
prices (no bids were recorded); the session's one-minute candles repeat the last price when nothing trades, so only candles
with volume count.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests

from .build import ROOT

IST = timezone(timedelta(hours=5, minutes=30))
API = "https://api.upstox.com/v3/historical-candle/{k}/minutes/1/{d}/{d}"
WINDOW = ("14:00", "15:35")                    # the special session and its closing window, IST


def hm(ts) -> str:
    return datetime.fromisoformat(str(ts)).strftime("%H:%M")


def conv(c: dict) -> list:
    """A server.upstox candle {time, open, high, low, close, volume} as [IST time, o, h, l, c, volume]."""
    return [datetime.fromtimestamp(c["time"], IST).isoformat(), c["open"], c["high"], c["low"], c["close"], c["volume"]]


def candles(key: str, day: str) -> list[list]:
    r = requests.get(API.format(k=quote(key, safe=""), d=day), timeout=30).json()
    time.sleep(0.25)
    return sorted((r.get("data") or {}).get("candles") or [], key=lambda c: str(c[0]))


def window(cs: list[list], traded_only: bool) -> dict | None:
    """First / last price, high, low of the window (candle = [time, o, h, l, c, volume, oi])."""
    w = [c for c in cs if WINDOW[0] <= hm(c[0]) <= WINDOW[1] and (not traded_only or (c[5] or 0) > 0)]
    if not w:
        return None
    return {"open": w[0][1], "high": max(c[2] for c in w), "low": min(c[3] for c in w), "close": w[-1][4],
            "t_open": hm(w[0][0]), "t_close": hm(w[-1][0]), "n": len(w)}


def last_price_before(cs: list[list], upto: str = "15:30") -> float | None:
    x = [c for c in cs if hm(c[0]) <= upto and (c[5] or 0) > 0]
    return x[-1][4] if x else (cs[-1][4] if cs else None)


def main(day: str, ledger_path: str) -> None:
    from server.upstox import UpstoxProvider
    up = UpstoxProvider("")
    led = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    held = [p for p in led["positions"] if p["opened_at"][:10] < day]
    prev = max(p["opened_at"][:10] for p in led["positions"] + led["closed"] if p["opened_at"][:10] < day)
    out, rows = {}, []
    for p in held:
        ts = p["tradingsymbol"]
        if ts in out:
            continue
        try:
            cs = up.history(f"NFO:{ts}", 1, day)
            fri = up.history(f"NFO:{ts}", 1, prev)
        except Exception as exc:                                    # noqa: BLE001 - reported, not fatal
            print("no candles:", ts, str(exc)[:80])
            continue
        time.sleep(0.25)
        cs, fri = [conv(c) for c in cs], [conv(c) for c in fri]
        w = window(cs, True)
        if w:
            out[ts] = w
        rows.append({"ts": ts, "friday_close": last_price_before(fri), **(w or {})})
    stocks = {}                                                    # the underlying stocks (the index has no candles for a special session)
    for sym in sorted({p["symbol"] for p in held}):
        try:
            cs, fri = [conv(c) for c in up.history(f"NSE:{sym}", 1, day)], [conv(c) for c in up.history(f"NSE:{sym}", 1, prev)]
        except Exception:                                           # noqa: BLE001
            continue
        time.sleep(0.25)
        w = window(cs, True)
        if w and fri:
            stocks[sym] = {"friday_close": last_price_before(fri), **w}
    dest = ROOT / "data" / "muhurat"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{day}.json").write_text(json.dumps(
        {"date": day, "window": list(WINDOW), "previous_session": prev, "source": "Upstox 1-minute history (last prices, traded candles only)",
         "prices": out, "stocks": stocks}, indent=1), encoding="utf-8")
    traded = [r for r in rows if r.get("open")]
    print(f"{day}: {len(held)} open positions, {len(rows)} contracts fetched, {len(traded)} traded in the window; previous session {prev}")
    if stocks:
        sm = sorted(((v["close"] / v["friday_close"] - 1) * 100, k) for k, v in stocks.items())
        print(f"  underlying stocks (Friday close -> Muhurat close): median {sm[len(sm) // 2][0]:+.2f} %, "
              f"worst {sm[0][0]:+.2f} % ({sm[0][1]}), best {sm[-1][0]:+.2f} % ({sm[-1][1]}), {len(stocks)} stocks traded")
    mv = []
    for r in traded:
        if r["friday_close"]:
            mv.append((r["ts"], (r["close"] / r["friday_close"] - 1) * 100, (r["open"] / r["friday_close"] - 1) * 100))
    mv.sort(key=lambda x: x[1])
    if mv:
        import statistics
        c = [m[1] for m in mv]
        print(f"  option close vs Friday's close: median {statistics.median(c):+.1f} %, worst {mv[0][1]:+.1f} % ({mv[0][0]}), best {mv[-1][1]:+.1f} % ({mv[-1][0]})")
        for T in (10, 20, 50):
            print(f"  moved >= {T} % at the close: {sum(x >= T for x in c)} up, {sum(x <= -T for x in c)} down of {len(c)}")
    print(f"  not traded in the window: {len(rows) - len(traded)} contracts")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
