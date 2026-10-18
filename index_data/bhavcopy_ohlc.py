"""§5 Full-OHLC daily index options and futures from NSE's raw F&O bhavcopy, 2021-01-01 → today.

    python -m index_data.bhavcopy_ohlc [--from 2021-01-01] [--to YYYY-MM-DD]    # run on the PC: NSE refuses cloud IPs

The stock cache (data/cache/fo_bhavcopy_*.csv) keeps no open / high / low (scanner/nse_fo.py:58) and is not touched.
This re-downloads each session's raw file and keeps the IDO / IDF rows with TradDt, TckrSymb, XpryDt, StrkPric,
OptnTp, OpnPric, HghPric, LwPric, ClsPric, SttlmPric, UndrlygPric, OpnIntrst, ChngInOpnIntrst, TtlTradgVol,
TtlTrfVal, NewBrdLotQty (old-format files before 2024-07-05 are mapped; UndrlygPric and NewBrdLotQty are null there,
TtlTrfVal is VAL_INLAKH x 1e5). Stored as STORE/options_daily/<underlying>/<YYYY>.parquet (FinInstrmTp kept).
Restart-safe: sessions already in the year's file are skipped. Raw files are not kept.
BSE (SENSEX): see bse_status() - no stable public URL is used here; documented in INDEX_DATA_REPORT.md.
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import date, timedelta

import pandas as pd

from .common import STORE, upsert_parquet

log = logging.getLogger("index_data.bhavcopy_ohlc")

KEEP = ["TradDt", "TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "OpnPric", "HghPric", "LwPric", "ClsPric",
        "SttlmPric", "UndrlygPric", "OpnIntrst", "ChngInOpnIntrst", "TtlTradgVol", "TtlTrfVal", "NewBrdLotQty"]
OLD = {"TIMESTAMP": "TradDt", "SYMBOL": "TckrSymb", "EXPIRY_DT": "XpryDt", "STRIKE_PR": "StrkPric",
       "OPTION_TYP": "OptnTp", "OPEN": "OpnPric", "HIGH": "HghPric", "LOW": "LwPric", "CLOSE": "ClsPric",
       "SETTLE_PR": "SttlmPric", "OPEN_INT": "OpnIntrst", "CHG_IN_OI": "ChngInOpnIntrst", "CONTRACTS": "TtlTradgVol"}


def to_index_rows(raw: pd.DataFrame, old_format: bool) -> pd.DataFrame:
    raw = raw.rename(columns=lambda c: str(c).strip())
    if old_format:
        d = raw.rename(columns=OLD)
        d["FinInstrmTp"] = raw["INSTRUMENT"].astype(str).str.strip().map({"OPTIDX": "IDO", "FUTIDX": "IDF"})
        d["TradDt"] = pd.to_datetime(d["TradDt"], format="%d-%b-%Y").dt.strftime("%Y-%m-%d")
        d["XpryDt"] = pd.to_datetime(d["XpryDt"], format="%d-%b-%Y").dt.strftime("%Y-%m-%d")
        d["TtlTrfVal"] = pd.to_numeric(raw.get("VAL_INLAKH"), errors="coerce") * 1e5
        d["UndrlygPric"] = float("nan")
        d["NewBrdLotQty"] = float("nan")
    else:
        d = raw.copy()
        d["TradDt"] = d["TradDt"].astype(str).str[:10]
        d["XpryDt"] = d["XpryDt"].astype(str).str[:10]
    d = d[d["FinInstrmTp"].isin(["IDO", "IDF"])].copy()
    d["TckrSymb"] = d["TckrSymb"].astype(str).str.strip()
    opt = d["OptnTp"].astype(str).str.strip()
    d["OptnTp"] = opt.where(opt.isin(["CE", "PE"]))
    for c in KEEP:
        if c not in d.columns:
            d[c] = float("nan")
    for c in ("StrkPric", "OpnPric", "HghPric", "LwPric", "ClsPric", "SttlmPric", "UndrlygPric", "OpnIntrst",
              "ChngInOpnIntrst", "TtlTradgVol", "TtlTrfVal", "NewBrdLotQty"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d[KEEP].reset_index(drop=True)


def done_days(store=STORE) -> set[str]:
    out = set()
    for f in (store / "options_daily").glob("*/*.parquet"):
        out |= set(pd.read_parquet(f, columns=["TradDt"])["TradDt"].unique())
    return out


def run(start: date, end: date, store=STORE) -> dict:
    from scanner.nse_fo import BhavcopyUnavailable, _download_raw
    have = done_days(store)
    stats = {"sessions": 0, "skipped_existing": 0, "unavailable": 0, "rows": 0, "errors": []}
    t0, d = time.monotonic(), start
    while d <= end:
        if d.weekday() >= 5:
            d += timedelta(days=1)
            continue
        if d.isoformat() in have:
            stats["skipped_existing"] += 1
            d += timedelta(days=1)
            continue
        for attempt in range(3):
            try:
                raw, old = _download_raw(d)
                rows = to_index_rows(raw, old)
                for (u, y), g in rows.groupby([rows["TckrSymb"], rows["TradDt"].str[:4]]):
                    upsert_parquet(store / "options_daily" / u / f"{y}.parquet", g,
                                   ["TradDt", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp"])
                stats["sessions"] += 1
                stats["rows"] += len(rows)
                break
            except BhavcopyUnavailable:
                stats["unavailable"] += 1
                break
            except Exception as exc:  # noqa: BLE001 - retry, then record and move on
                if attempt == 2:
                    stats["errors"].append(f"{d}: {exc}"[:200])
                time.sleep(3 * (attempt + 1))
        time.sleep(0.4)
        if stats["sessions"] % 50 == 0 and stats["sessions"]:
            log.info("%s: %d sessions, %d rows", d, stats["sessions"], stats["rows"])
        d += timedelta(days=1)
    stats["runtime_s"] = round(time.monotonic() - t0)
    return stats


def bse_status() -> str:
    return ("BSE publishes a derivatives bhavcopy on bseindia.com, but its archive URLs change format and need a "
            "browser session; it is not downloaded here. SENSEX daily option OHLC: not available from this layer "
            "(1-minute SENSEX options come from the Kotak recorder and Upstox).")


def main() -> None:
    ap = argparse.ArgumentParser(description="full-OHLC daily index options from NSE's raw F&O bhavcopy")
    ap.add_argument("--from", dest="start", default="2021-01-01")
    ap.add_argument("--to", dest="end", default=date.today().isoformat())
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    st = run(date.fromisoformat(a.start), date.fromisoformat(a.end))
    print(st)


if __name__ == "__main__":
    main()
