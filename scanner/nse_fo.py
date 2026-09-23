"""Futures OI, OI change and put-call ratio from NSE's official F&O bhavcopy (UDiFF format).

Source (free, official):
    https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip

One file per trading day, published after market close (usually by ~19:00 IST). It has one
row per contract with, among others:
    TckrSymb       underlying symbol
    FinInstrmTp    STF = stock future, STO = stock option, IDF/IDO = index future/option
    OptnTp         CE / PE for options
    OpnIntrst      open interest (contracts)
    ChngInOpnIntrst change in OI vs previous session

Per stock we compute (all expiries combined):
    fut_oi          sum of OpnIntrst over STF rows
    fut_oi_prev     fut_oi - sum of ChngInOpnIntrst over STF rows
    oi_change_pct   (fut_oi - fut_oi_prev) / fut_oi_prev * 100
    pcr             sum of PE OpnIntrst / sum of CE OpnIntrst over STO rows
    put_oi, call_oi the two numerators, so the PCR can be verified
"""
from __future__ import annotations

import io
import logging
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)

# NSE's CDN rejects requests that do not look like a browser.
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

BHAVCOPY_URL = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv.zip"
# Before the UDiFF cutover (2024-07-05) the F&O bhavcopy lived in the old format and layout:
OLD_BHAVCOPY_URL = "https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{yyyy}/{MON}/fo{dd}{MON}{yyyy}bhav.csv.zip"
UDIFF_FROM = date(2024, 7, 5)
OLD_TO_UDIFF = {"SYMBOL": "TckrSymb", "EXPIRY_DT": "XpryDt", "STRIKE_PR": "StrkPric", "OPTION_TYP": "OptnTp",
                "CLOSE": "ClsPric", "OPEN_INT": "OpnIntrst", "CHG_IN_OI": "ChngInOpnIntrst",
                "CONTRACTS": "TtlTradgVol", "TIMESTAMP": "TradDt"}
OLD_INSTRUMENT = {"FUTSTK": "STF", "OPTSTK": "STO", "FUTIDX": "IDF", "OPTIDX": "IDO"}

COLUMNS = ["TradDt", "TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "UndrlygPric",
           "OpnIntrst", "ChngInOpnIntrst", "TtlTradgVol"]
OPTIONAL_COLUMNS = ["NewBrdLotQty"]          # lot size per contract; kept when present (older caches lack it)
_WANTED = set(COLUMNS) | set(OPTIONAL_COLUMNS)


class BhavcopyUnavailable(Exception):
    """Raised when the file for a date does not exist (holiday, not yet published, or blocked)."""


def download_fo_bhavcopy(day: date, cache_dir: Path | None = None, timeout: int = 60) -> pd.DataFrame:
    """Download (or read from cache) the F&O bhavcopy for ``day`` and return the useful columns."""
    ymd = day.strftime("%Y%m%d")
    cache_file = (cache_dir / f"fo_bhavcopy_{ymd}.csv") if cache_dir else None
    if cache_file and cache_file.exists():
        return pd.read_csv(cache_file, usecols=lambda c: c in _WANTED)

    old_format = day < UDIFF_FROM
    if old_format:
        mon = day.strftime("%b").upper()
        url = OLD_BHAVCOPY_URL.format(yyyy=day.year, MON=mon, dd=f"{day.day:02d}")
    else:
        url = BHAVCOPY_URL.format(ymd=ymd)
    r = requests.get(url, headers=NSE_HEADERS, timeout=timeout)
    if r.status_code == 404:
        raise BhavcopyUnavailable(f"No F&O bhavcopy for {day} (404)")
    if r.status_code in (401, 403):
        raise BhavcopyUnavailable(f"NSE refused the request for {day} (HTTP {r.status_code}); "
                                  "this usually means the client IP or headers are blocked")
    r.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(name) as fh:
            if old_format:
                df = _from_old_format(pd.read_csv(fh), day)
            else:
                df = pd.read_csv(fh, usecols=lambda c: c in _WANTED)

    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_file, index=False)
    return df


def _from_old_format(df: pd.DataFrame, day: date) -> pd.DataFrame:
    """Old-format columns -> the UDiFF names the rest of the code reads. UndrlygPric does not exist
    in the old files and is left null; NewBrdLotQty likewise."""
    df = df.rename(columns=lambda c: str(c).strip())
    out = pd.DataFrame()
    out["TradDt"] = pd.to_datetime(df["TIMESTAMP"], format="%d-%b-%Y").dt.strftime("%Y-%m-%d")
    out["TckrSymb"] = df["SYMBOL"].astype(str).str.strip()
    out["FinInstrmTp"] = df["INSTRUMENT"].astype(str).str.strip().map(OLD_INSTRUMENT)
    out["XpryDt"] = pd.to_datetime(df["EXPIRY_DT"], format="%d-%b-%Y").dt.strftime("%Y-%m-%d")
    out["StrkPric"] = pd.to_numeric(df["STRIKE_PR"], errors="coerce")
    opt = df["OPTION_TYP"].astype(str).str.strip()
    out["OptnTp"] = opt.where(opt.isin(["CE", "PE"]))
    out["ClsPric"] = pd.to_numeric(df["CLOSE"], errors="coerce")
    out["UndrlygPric"] = float("nan")
    out["OpnIntrst"] = pd.to_numeric(df["OPEN_INT"], errors="coerce").fillna(0).astype(int)
    out["ChngInOpnIntrst"] = pd.to_numeric(df["CHG_IN_OI"], errors="coerce").fillna(0)
    out["TtlTradgVol"] = pd.to_numeric(df["CONTRACTS"], errors="coerce").fillna(0)
    return out[out["FinInstrmTp"].notna()].reset_index(drop=True)


def latest_available_bhavcopy(not_after: date, lookback_days: int = 7,
                              cache_dir: Path | None = None) -> tuple[date, pd.DataFrame]:
    """Walk back from ``not_after`` until a bhavcopy exists (skips weekends/holidays)."""
    last_error: Exception | None = None
    for i in range(lookback_days):
        day = not_after - timedelta(days=i)
        if day.weekday() >= 5:
            continue
        try:
            return day, download_fo_bhavcopy(day, cache_dir=cache_dir)
        except BhavcopyUnavailable as exc:
            last_error = exc
            continue
    raise BhavcopyUnavailable(f"No F&O bhavcopy found in the {lookback_days} days up to {not_after}: {last_error}")


def fo_metrics(bhav: pd.DataFrame) -> pd.DataFrame:
    """Reduce a bhavcopy to one row per stock with futures OI, OI change % and PCR."""
    stf = bhav[bhav["FinInstrmTp"] == "STF"]
    sto = bhav[bhav["FinInstrmTp"] == "STO"]

    fut = stf.groupby("TckrSymb").agg(fut_oi=("OpnIntrst", "sum"),
                                       fut_oi_chg=("ChngInOpnIntrst", "sum"),
                                       fut_volume=("TtlTradgVol", "sum"))
    fut["fut_oi_prev"] = fut["fut_oi"] - fut["fut_oi_chg"]
    fut["oi_change_pct"] = (fut["fut_oi_chg"] / fut["fut_oi_prev"].where(fut["fut_oi_prev"] > 0)) * 100

    opt = sto.pivot_table(index="TckrSymb", columns="OptnTp", values="OpnIntrst", aggfunc="sum", fill_value=0)
    opt = opt.rename(columns={"CE": "call_oi", "PE": "put_oi"})
    for col in ("call_oi", "put_oi"):
        if col not in opt:
            opt[col] = 0
    opt["pcr"] = opt["put_oi"] / opt["call_oi"].where(opt["call_oi"] > 0)

    out = fut.join(opt[["call_oi", "put_oi", "pcr"]], how="left")
    out.index.name = "symbol"
    return out.reset_index()

