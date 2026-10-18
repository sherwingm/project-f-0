"""Data-access probe for Upstox (DATA_ACCESS_AUDIT.md). Read-only; runs on GitHub Actions with the
UPSTOX_ANALYTICS_TOKEN secret, so the token never leaves GitHub. Prints one JSON line per probe
(status, rows, first / last timestamp, error text) and writes data/results/upstox_probe.json.

    UPSTOX_ANALYTICS_TOKEN=... python -m scanner.upstox_probe
"""
from __future__ import annotations

import gzip
import io
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import requests

TOKEN = os.environ.get("UPSTOX_ANALYTICS_TOKEN", "")
H = {"Accept": "application/json", "Authorization": f"Bearer {TOKEN}"}
OUT: list[dict] = []
MASTER = "https://assets.upstox.com/market-quote/instruments/exchange/{ex}.json.gz"


def scrub(text: str) -> str:
    return str(text).replace(TOKEN, "***") if TOKEN else str(text)


def call(label: str, url: str, params: dict | None = None) -> dict:
    time.sleep(0.6)                                   # well inside 25/s, 250/min, 1000/30 min
    try:
        r = requests.get(url, headers=H, params=params, timeout=60)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    except Exception as exc:  # noqa: BLE001
        row = {"probe": label, "url": url.replace("https://api.upstox.com", ""), "http": None, "error": scrub(exc)[:300]}
        OUT.append(row); print(json.dumps(row), flush=True); return {}
    data = body.get("data") if isinstance(body, dict) else None
    candles = data.get("candles") if isinstance(data, dict) else None
    row = {"probe": label, "url": url.replace("https://api.upstox.com", ""), "params": params, "http": r.status_code,
           "status": body.get("status") if isinstance(body, dict) else None}
    if isinstance(candles, list):
        row.update(rows=len(candles), first=candles[-1][0] if candles else None, last=candles[0][0] if candles else None,
                   sample=candles[-1] if candles else None)
    elif isinstance(data, list):
        row.update(rows=len(data), sample=data[:3])
    if r.status_code != 200 or (isinstance(body, dict) and body.get("status") == "error"):
        row["error"] = scrub(json.dumps(body.get("errors") if isinstance(body, dict) else r.text))[:400]
    OUT.append(row)
    print(json.dumps(row, default=str), flush=True)
    return body if isinstance(body, dict) else {}


def master(ex: str) -> list[dict]:
    r = requests.get(MASTER.format(ex=ex), timeout=120)
    r.raise_for_status()
    return json.loads(gzip.open(io.BytesIO(r.content)).read())


def hist(label, key, unit, interval, to_d, from_d):
    return call(label, f"https://api.upstox.com/v3/historical-candle/{quote(key, safe='')}/{unit}/{interval}/{to_d}/{from_d}")


def nearest(rows, name, inst, spot, step, expiry=None, typ="CE"):
    c = [r for r in rows if r.get("underlying_symbol") == name and r.get("instrument_type") == typ
         and r.get("segment", "").endswith("_FO")]
    if not c:
        return None
    exps = sorted({r["expiry"] for r in c})
    e = expiry or exps[0]
    c = [r for r in c if r["expiry"] == e]
    return min(c, key=lambda r: abs(float(r["strike_price"]) - spot)) if c else None


def main() -> None:
    if not TOKEN:
        raise SystemExit("UPSTOX_ANALYTICS_TOKEN is not set")
    # recent sessions: the last 5 weekdays before today
    days, d = [], date.today()
    while len(days) < 5:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            days.append(d.isoformat())
    lo, hi = days[-1], days[0]
    print(json.dumps({"window": [lo, hi]}), flush=True)

    # a: index spot, 1-minute
    hist("a NIFTY 50 spot 1min, last 5 sessions", "NSE_INDEX|Nifty 50", "minutes", 1, hi, lo)
    hist("a India VIX 1min, last 5 sessions", "NSE_INDEX|India VIX", "minutes", 1, hi, lo)
    hist("a SENSEX spot 1min", "BSE_INDEX|SENSEX", "minutes", 1, hi, lo)
    # depth / range limits for index spot
    hist("depth NIFTY 1min 2022-01-03", "NSE_INDEX|Nifty 50", "minutes", 1, "2022-01-03", "2022-01-03")
    hist("depth NIFTY 1min 2020-03-23", "NSE_INDEX|Nifty 50", "minutes", 1, "2020-03-23", "2020-03-23")
    hist("range NIFTY 1min 31 days", "NSE_INDEX|Nifty 50", "minutes", 1, hi,
         (date.fromisoformat(hi) - timedelta(days=31)).isoformat())
    hist("range NIFTY 1min 90 days", "NSE_INDEX|Nifty 50", "minutes", 1, hi,
         (date.fromisoformat(hi) - timedelta(days=90)).isoformat())
    hist("f India VIX daily 2015-2026", "NSE_INDEX|India VIX", "days", 1, hi, "2015-01-01")

    # b, c, h, g: current index options from the instrument masters
    nse, bse = master("NSE"), master("BSE")
    spot = {"NIFTY": None, "BANKNIFTY": None, "SENSEX": None}
    for name, key in (("NIFTY", "NSE_INDEX|Nifty 50"), ("BANKNIFTY", "NSE_INDEX|Nifty Bank"), ("SENSEX", "BSE_INDEX|SENSEX")):
        b = call(f"spot close {name}", f"https://api.upstox.com/v3/historical-candle/{quote(key, safe='')}/days/1/{hi}/{lo}")
        c = ((b.get("data") or {}).get("candles") or [[None, None, None, None, None]])[0]
        spot[name] = c[4]
    for name, rows, step, lab in (("NIFTY", nse, 50, "b NIFTY nearest weekly ATM CE"),
                                  ("BANKNIFTY", nse, 100, "h BANKNIFTY nearest (monthly) ATM CE"),
                                  ("SENSEX", bse, 100, "g SENSEX nearest weekly ATM CE")):
        if spot[name] is None:
            continue
        r = nearest(rows, name, "OPTIDX", float(spot[name]), step)
        if r:
            OUT.append({"contract": lab, "instrument_key": r["instrument_key"], "trading_symbol": r.get("trading_symbol"),
                        "expiry": r.get("expiry")})
            print(json.dumps(OUT[-1], default=str), flush=True)
            hist(lab + " 1min", r["instrument_key"], "minutes", 1, hi, lo)
            if name == "NIFTY":
                hist(lab + " 5min", r["instrument_key"], "minutes", 5, hi, lo)

    # d, e: expired contracts (the Expired Instruments API)
    exp = call("d expiries list (expired instruments) NIFTY", "https://api.upstox.com/v2/expired-instruments/expiries",
               {"instrument_key": "NSE_INDEX|Nifty 50"})
    exps = sorted(exp.get("data") or []) if isinstance(exp.get("data"), list) else []
    picks = []
    last_week = [e for e in exps if e < date.today().isoformat()][-1:] if exps else []
    jan25 = [e for e in exps if e.startswith("2025-01")][:1]
    jan23 = [e for e in exps if e.startswith("2023-01")][:1]
    for e, lab in ((last_week, "d expired last week"), (jan25, "e expired Jan 2025"), (jan23, "e expired Jan 2023")):
        if not e:
            OUT.append({"probe": lab, "error": "expiry not in the expired-instruments list"}); continue
        oc = call(f"{lab}: option contracts on {e[0]}", "https://api.upstox.com/v2/expired-instruments/option/contract",
                  {"instrument_key": "NSE_INDEX|Nifty 50", "expiry_date": e[0]})
        cons = oc.get("data") or []
        if cons:
            k = sorted(cons, key=lambda r: r.get("strike_price", 0))[len(cons) // 2]
            key = k.get("instrument_key")
            to_d = e[0]
            fr = (date.fromisoformat(e[0]) - timedelta(days=4)).isoformat()
            call(f"{lab}: {k.get('trading_symbol')} 1min", f"https://api.upstox.com/v2/expired-instruments/historical-candle/"
                 f"{quote(key, safe='')}/1minute/{to_d}/{fr}")
    print(json.dumps({"expiries_listed": len(exps), "first": exps[:3], "last": exps[-3:]}), flush=True)

    Path("data/results").mkdir(parents=True, exist_ok=True)
    Path("data/results/upstox_probe.json").write_text(json.dumps(OUT, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
