"""§9 Kotak vs Upstox on the same live contracts: fetch Upstox 1-minute candles for the contracts the Kotak recorder
captured (sessions from 2026-10-19 on, or --from), store them (source 'upstox') and compare on (token, timestamp).

    UPSTOX_ANALYTICS_TOKEN=... INDEX_STORE=... python -m index_data.reconcile [--from 2026-10-19] [--max-contracts 300]

The NSE / BSE exchange token is the same number in both (Kotak pSymbol, Upstox NSE_FO|<token> / BSE_FO|<token>).
Result -> SMALL/reconcile.json and status.json: matched minutes, mean / max absolute close difference, minutes in
one source only.
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta

import pandas as pd

from .common import SMALL, STORE, candles_frame, read_json, upsert_parquet, write_json
from .upstox_common import Upstox

log = logging.getLogger("index_data.reconcile")


def kotak_rows(start: str, store=STORE) -> pd.DataFrame:
    parts = []
    for f in (store / "options_1m").glob("*/*/*.parquet"):
        if f.stem >= start:
            d = pd.read_parquet(f)
            d = d[d["source"] == "kotak"]
            if len(d):
                parts.append(d.assign(underlying=f.parent.parent.name, expiry=f.parent.name))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def run(start: str, max_contracts: int, store=STORE) -> dict:
    k = kotak_rows(start, store)
    if k.empty:
        return {"error": f"no Kotak recorder rows on or after {start}"}
    u = Upstox()
    seg = {"SENSEX": "BSE_FO"}
    contracts = k.drop_duplicates("token")[["token", "underlying", "expiry", "trading_symbol", "strike", "option_type"]]
    contracts = contracts.head(max_contracts)
    ups = []
    for c in contracts.itertuples():
        days = k[k["token"] == c.token]["timestamp"].dt.date
        a, b = days.min(), days.max()
        key = f"{seg.get(c.underlying, 'NSE_FO')}|{c.token}"
        rows = []
        s = a
        while s <= b:
            t = min(b, s + timedelta(days=27))
            body = u.get(f"/v3/historical-candle/{u.q(key)}/minutes/1/{t}/{s}")
            rows += (body.get("data") or {}).get("candles") or []
            s = t + timedelta(days=1)
        f = candles_frame(rows)
        if f.empty:
            continue
        f = f[f["timestamp"].dt.strftime("%H:%M") >= "09:15"]
        f.insert(1, "token", c.token)
        f.insert(2, "trading_symbol", c.trading_symbol)
        f.insert(3, "strike", c.strike)
        f.insert(4, "option_type", c.option_type)
        f["source"] = "upstox"
        for d, g in f.groupby(f["timestamp"].dt.date):
            upsert_parquet(store / "options_1m" / c.underlying / c.expiry / f"{d.isoformat()}.parquet", g,
                           ["source", "token", "timestamp"])
        ups.append(f)
    up = pd.concat(ups, ignore_index=True) if ups else pd.DataFrame(columns=["token", "timestamp", "close"])
    kk = k[k["token"].isin(contracts["token"])][["token", "timestamp", "close"]]
    m = kk.merge(up[["token", "timestamp", "close"]], on=["token", "timestamp"], how="outer", suffixes=("_kotak", "_upstox"),
                 indicator=True)
    both = m[m["_merge"] == "both"]
    diff = (both["close_kotak"] - both["close_upstox"]).abs()
    return {"from": start, "contracts": int(len(contracts)), "upstox_calls": u.calls, "matched_minutes": int(len(both)),
            "mean_abs_close_diff": round(float(diff.mean()), 4) if len(both) else None,
            "max_abs_close_diff": round(float(diff.max()), 4) if len(both) else None,
            "share_identical_close_pct": round(float((diff < 1e-9).mean() * 100), 2) if len(both) else None,
            "only_kotak": int((m["_merge"] == "left_only").sum()), "only_upstox": int((m["_merge"] == "right_only").sum())}


def main() -> None:
    ap = argparse.ArgumentParser(description="Kotak vs Upstox 1-minute reconciliation")
    ap.add_argument("--from", dest="start", default="2026-10-19")
    ap.add_argument("--max-contracts", type=int, default=300)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    res = run(a.start, a.max_contracts)
    write_json(SMALL / "reconcile.json", res)
    st = read_json(SMALL / "status.json", {}) or {}
    write_json(SMALL / "status.json", {**st, "reconcile": res})
    print(res)


if __name__ == "__main__":
    main()
