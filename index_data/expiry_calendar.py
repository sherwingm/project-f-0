"""§6 Expiry calendar per underlying: history from the bhavcopy XpryDt (2021 →), forward from the scrip-master
snapshots (and Upstox's expired-instrument lists when present). Reconciled with data/nse_holidays.json.

    python -m index_data.expiry_calendar      # -> STORE/expiries.parquet, SMALL/expiries_next.json

    from index_data.expiry_calendar import nearest_expiry
    nearest_expiry("NIFTY", "2023-07-05")          # -> "2023-07-06" (the Thursday weekly)
    nearest_expiry("NIFTY", "2026-10-14")          # -> "2026-10-19" (the Tuesday weekly of 20-Oct, moved to Monday:
                                                   #    20-Oct-2026 is an exchange holiday)
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .common import ROOT, SMALL, STORE, today_ist, write_json

log = logging.getLogger("index_data.expiry_calendar")
UNDERLYINGS = ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50", "SENSEX")
CACHE = ROOT / "data" / "cache"


def from_bhavcopy(cache: Path = CACHE) -> pd.DataFrame:
    rows = set()
    for f in sorted(cache.glob("fo_bhavcopy_*.csv")):
        b = pd.read_csv(f, usecols=lambda c: c in ("TckrSymb", "FinInstrmTp", "XpryDt"))
        b = b[b["FinInstrmTp"] == "IDO"]
        for u, e in zip(b["TckrSymb"].astype(str).str.strip(), b["XpryDt"].astype(str).str[:10]):
            rows.add((u, e))
    return pd.DataFrame(sorted(rows), columns=["underlying", "expiry_date"]).assign(source="nse_bhavcopy")


def from_options_daily(store: Path = STORE) -> pd.DataFrame:
    rows = set()
    for f in (store / "options_daily").glob("*/*.parquet"):
        d = pd.read_parquet(f, columns=["TckrSymb", "FinInstrmTp", "XpryDt"])
        d = d[d["FinInstrmTp"] == "IDO"]
        rows |= set(zip(d["TckrSymb"], d["XpryDt"]))
    return pd.DataFrame(sorted(rows), columns=["underlying", "expiry_date"]).assign(source="nse_bhavcopy_ohlc")


def from_scrip_master(store: Path = STORE) -> pd.DataFrame:
    files = sorted((store / "instruments").glob("*.parquet"))
    if not files:
        return pd.DataFrame(columns=["underlying", "expiry_date", "source"])
    d = pd.concat([pd.read_parquet(f, columns=["underlying", "inst_type", "expiry"]) for f in files])
    d = d[d["inst_type"] == "option"].drop_duplicates(["underlying", "expiry"])
    return d.rename(columns={"expiry": "expiry_date"})[["underlying", "expiry_date"]].assign(source="kotak_scrip_master")


def from_upstox(store: Path = STORE) -> pd.DataFrame:
    p = store / "upstox_expiries.json"
    if not p.exists():
        return pd.DataFrame(columns=["underlying", "expiry_date", "source"])
    d = json.loads(p.read_text(encoding="utf-8"))
    return pd.DataFrame([(u, e) for u, es in d.items() for e in es], columns=["underlying", "expiry_date"]).assign(
        source="upstox_expired")


def holidays() -> set[str]:
    try:
        h = json.loads((ROOT / "data" / "nse_holidays.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    vals = h if isinstance(h, list) else (h.get("dates") or h.get("holidays") or [])
    return {str(x.get("date") if isinstance(x, dict) else x)[:10] for x in vals}


def build(store: Path = STORE) -> pd.DataFrame:
    d = pd.concat([from_bhavcopy(), from_options_daily(store), from_scrip_master(store), from_upstox(store)],
                  ignore_index=True)
    d = d[d["underlying"].isin(UNDERLYINGS) & d["expiry_date"].str.match(r"^\d{4}-\d{2}-\d{2}$")]
    d = d.groupby(["underlying", "expiry_date"])["source"].apply(lambda s: ",".join(sorted(set(s)))).reset_index()
    d["month"] = d["expiry_date"].str[:7]
    last = d.groupby(["underlying", "month"])["expiry_date"].transform("max")
    d["is_monthly"] = d["expiry_date"] == last
    per_month = d.groupby(["underlying", "month"])["expiry_date"].transform("count")
    d["is_weekly"] = (~d["is_monthly"]) | (per_month > 1)        # the month's last weekly is also its monthly
    d["weekday"] = pd.to_datetime(d["expiry_date"]).dt.day_name()
    hol = holidays()
    d["on_holiday_or_weekend"] = d["expiry_date"].isin(hol) | pd.to_datetime(d["expiry_date"]).dt.weekday.ge(5)
    usual = d.groupby(["underlying", d["expiry_date"].str[:4]])["weekday"].agg(lambda s: s.mode().iloc[0])
    d["usual_weekday"] = [usual.get((u, e[:4])) for u, e in zip(d["underlying"], d["expiry_date"])]
    d["shifted"] = d["weekday"] != d["usual_weekday"]
    return d.drop(columns=["month"]).sort_values(["underlying", "expiry_date"]).reset_index(drop=True)


@lru_cache(maxsize=1)
def _table(store: str = str(STORE)) -> pd.DataFrame:
    p = Path(store) / "expiries.parquet"
    return pd.read_parquet(p) if p.exists() else build(Path(store))


def nearest_expiry(underlying: str, day: str, monthly: bool = False) -> str | None:
    """The first expiry on or after `day` for the underlying (monthly=True: the first monthly)."""
    t = _table()
    t = t[(t["underlying"] == underlying) & (t["expiry_date"] >= str(day)[:10])]
    if monthly:
        t = t[t["is_monthly"]]
    return t["expiry_date"].iloc[0] if len(t) else None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    d = build()
    STORE.mkdir(parents=True, exist_ok=True)
    d.to_parquet(STORE / "expiries.parquet", index=False)
    today = today_ist().isoformat()
    nxt = {u: g[g["expiry_date"] >= today]["expiry_date"].head(3).tolist() for u, g in d.groupby("underlying")}
    summary = {u: {"expiries": int(len(g)), "first": g["expiry_date"].min(), "last": g["expiry_date"].max(),
                   "shifted": int(g["shifted"].sum()), "on_holiday_or_weekend": int(g["on_holiday_or_weekend"].sum())}
               for u, g in d.groupby("underlying")}
    write_json(SMALL / "expiries_next.json", {"as_of": today, "next": nxt, "summary": summary})
    print(json.dumps(summary, indent=1))
    print("next:", nxt)
    _table.cache_clear()
    for u, day in (("NIFTY", "2023-07-05"), ("NIFTY", "2026-10-14")):
        print(u, day, "->", nearest_expiry(u, day))


if __name__ == "__main__":
    main()
