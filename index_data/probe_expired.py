"""§2 Expired-token retention probe (Kotak): does historical_data still answer for a contract after it expired?

    KOTAK_CONSUMER_KEY=... python -m index_data.probe_expired [--token 47141] [--label 2026-10-20]

Default contract: NIFTY 19-Oct-2026 22650 CE, token 47141 (expired 2026-10-19). Checks: 1-minute 2026-10-12 → 10-16,
the expiry day, 5-minute, daily, whether the token is still in the scrip master, and NIFTY spot as the control.
Appends the result to SMALL/probe_expired.json (one entry per run).
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from .common import SMALL, Kotak, read_json, today_ist, write_json

log = logging.getLogger("index_data.probe_expired")


def probe(k: Kotak, token: str, start: str, end: str, expiry: str) -> dict:
    neo = f"nse_fo|{token}"
    checks = [("1min before expiry", neo, "1min", start, end), ("1min expiry day", neo, "1min", expiry, expiry),
              ("5min", neo, "5min", start, expiry), ("daily", neo, "D", start, expiry),
              ("control: NIFTY 50 spot 1min expiry day", "nse_cm|Nifty 50", "1min", expiry, expiry)]
    out = []
    for lab, s, iv, a, b in checks:
        try:
            rows = k.history(s, iv, a, b)
            out.append({"check": lab, "call": f"{s} {iv} {a}..{b}", "rows": len(rows),
                        "first": rows[0][0] if rows else None, "last": rows[-1][0] if rows else None, "error": None})
        except Exception as exc:  # noqa: BLE001
            out.append({"check": lab, "call": f"{s} {iv} {a}..{b}", "rows": 0, "error": str(exc)[:300]})
    try:
        from . import instruments as I
        listed = token in set(I.load(k)["token"])
    except Exception as exc:  # noqa: BLE001
        listed = f"error: {exc}"[:200]
    out.append({"check": "still in the scrip master", "result": listed})
    return {"run_on": today_ist().isoformat(), "token": token, "contract": "NIFTY 19-Oct-2026 22650 CE",
            "expired_on": expiry, "checks": out,
            "verdict": ("retained" if out[0]["rows"] > 0 else "not retained")}


def main() -> None:
    ap = argparse.ArgumentParser(description="Kotak expired-token retention probe")
    ap.add_argument("--token", default="47141")
    ap.add_argument("--start", default="2026-10-12")
    ap.add_argument("--end", default="2026-10-16")
    ap.add_argument("--expiry", default="2026-10-19")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    res = probe(Kotak(), a.token, a.start, a.end, a.expiry)
    hist = read_json(SMALL / "probe_expired.json", []) or []
    write_json(SMALL / "probe_expired.json", hist + [res])
    print(pd.DataFrame(res["checks"]).to_string())
    print("verdict:", res["verdict"])


if __name__ == "__main__":
    main()
