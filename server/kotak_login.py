"""Check the Kotak Neo credentials from the machine that will run the server.

    python -m server.kotak_login          # uses the KOTAK_* variables from the environment / .env

Step 1 needs only KOTAK_CONSUMER_KEY (market data). Step 2 runs the TOTP login and MPIN
validation, which real orders need; it is skipped when those variables are not set.
"""
from __future__ import annotations

import os
import sys

from server.kotak import KotakSession, ScripMaster


def load_dotenv(path: str = ".env") -> None:
    """Fill os.environ from KEY=value lines in .env (variables already set win), so the check
    runs the same on Windows, where `set -a; source .env` is not available."""
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.split(" #", 1)[0].strip().strip("'\"")
        if k and k not in os.environ:
            os.environ[k] = v


def main() -> None:
    load_dotenv()
    key = os.getenv("KOTAK_CONSUMER_KEY")
    if not key:
        sys.exit("set KOTAK_CONSUMER_KEY (Neo app -> More -> Trade API -> Generate application)")
    s = KotakSession(key, os.getenv("KOTAK_MOBILE"), os.getenv("KOTAK_UCC"), os.getenv("KOTAK_TOTP_SECRET"), os.getenv("KOTAK_MPIN"))

    print("1. consumer key + scrip master … ", end="", flush=True)
    m = ScripMaster(s); m.load()
    print(f"OK ({len(m.eq)} equities, {len(m.fo)} NSE F&O contracts)")
    missing = [x for x in ("RELIANCE", "M&M", "BAJAJ-AUTO", "NAM-INDIA", "360ONE") if x not in m.eq]
    print("   symbol check:", "all mapped" if not missing else f"NOT mapped: {missing}")

    print("2. quotes (no login) … ", end="", flush=True)
    rel = m.eq.get("RELIANCE") or next(iter(m.eq.values()))
    fut = next((r for r in m.fo.values() if r["symbol"] == "RELIANCE" and r["type"] == "FUT"), None)
    items = [{"instrument_token": rel["token"], "exchange_segment": "nse_cm"}]
    if fut:
        items.append({"instrument_token": fut["token"], "exchange_segment": "nse_fo"})
    q = s.client().quotes(instrument_tokens=items, quote_type="all")
    rows = q if isinstance(q, list) else q.get("data", q)
    print("OK" if isinstance(rows, list) else f"unexpected: {str(q)[:200]}")
    for r in rows if isinstance(rows, list) else []:
        print(f"   {r.get('display_symbol')}: ltp {r.get('ltp')} prev close {(r.get('ohlc') or {}).get('close')} OI {r.get('open_int')}")

    if not s.can_trade:
        print("3. TOTP/MPIN login skipped (KOTAK_MOBILE / KOTAK_UCC / KOTAK_TOTP_SECRET / KOTAK_MPIN not all set); fine for read-only + paper")
        return
    print("3. TOTP login … ", end="", flush=True)
    d = s.login_view(); print(f"OK (view token for {d.get('greetingName') or d.get('ucc')})")
    print("4. MPIN validate … ", end="", flush=True)
    d = s.login_trade(); print(f"OK (kType {d.get('kType')})")


if __name__ == "__main__":
    main()
