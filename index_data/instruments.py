"""§1 Index contracts from Kotak's scrip master, with a daily snapshot so tokens survive their contract's expiry.

    KOTAK_CONSUMER_KEY=... python -m index_data.instruments      # -> STORE/instruments/YYYYMMDD.parquet

The server's loader keeps only stock F&O (server/kotak.py:209); this one keeps:
- nse_fo.csv: OPTIDX and FUTIDX for NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY;
- bse_fo.csv: SENSEX index options and futures (Kotak's BSE types: IO, IF);
- the spot / VIX names, which Kotak's history API takes by name (nse_cm|26000 is refused, nse_cm|Nifty 50 works).
BSE expiry dates: bse_fo's pExpiryDate is plain Unix time, not NSE's 1980-based epoch (EPOCH_OFFSET), which put
SENSEX 22-Oct-2026 at 2036-10-21 (DATA_ACCESS_AUDIT.md). Both are checked against the date in the trading symbol.
"""
from __future__ import annotations

import logging
import re
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

from .common import IST, STORE, Kotak, today_ist

log = logging.getLogger("index_data.instruments")

NSE_UNDERLYINGS = ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY")
BSE_UNDERLYINGS = ("SENSEX",)
NSE_TYPES = {"OPTIDX": "option", "FUTIDX": "future"}
BSE_TYPES = {"IO": "option", "IF": "future", "OPTIDX": "option", "FUTIDX": "future"}
SPOT = {"NIFTY": "nse_cm|Nifty 50", "BANKNIFTY": "nse_cm|Nifty Bank", "SENSEX": "bse_cm|SENSEX",
        "INDIAVIX": "nse_cm|INDIA VIX"}
STRIKE_STEP = {"NIFTY": 50, "BANKNIFTY": 100, "SENSEX": 100, "FINNIFTY": 50, "MIDCPNIFTY": 25}
MON = {m: i for i, m in enumerate(("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1)}
WEEKLY_MON = {**{str(i): i for i in range(1, 10)}, "O": 10, "N": 11, "D": 12}
_WEEKLY = re.compile(r"^[A-Z]+(\d{2})([1-9OND])(\d{2})\d")       # NIFTY26O19..., SENSEX26O22...
_MONTHLY = re.compile(r"^[A-Z]+(\d{2})(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)")


def nse_expiry(v) -> str | None:
    from server.kotak import EPOCH_OFFSET
    try:
        return datetime.fromtimestamp(int(float(v)) + EPOCH_OFFSET, tz=IST).date().isoformat()
    except (TypeError, ValueError):
        return None


def bse_expiry(v) -> str | None:
    """BSE pExpiryDate is plain Unix seconds (no NSE offset)."""
    try:
        return datetime.fromtimestamp(int(float(v)), tz=IST).date().isoformat()
    except (TypeError, ValueError):
        return None


def symbol_date(trd: str) -> tuple[str | None, str | None]:
    """(expiry ISO, 'weekly'/'monthly') read from a weekly symbol (NIFTY26O19..., the exact day) or a monthly one
    (NIFTY26OCT..., month only: returns YYYY-MM)."""
    m = _WEEKLY.match(trd)
    if m:
        y, mo, d = 2000 + int(m.group(1)), WEEKLY_MON[m.group(2)], int(m.group(3))
        try:
            return datetime(y, mo, d).date().isoformat(), "weekly"
        except ValueError:
            return None, None
    m = _MONTHLY.match(trd)
    if m:
        return f"{2000 + int(m.group(1))}-{MON[m.group(2)]:02d}", "monthly"
    return None, None


def _stream(url: str) -> Path:
    import requests
    tmp = Path(tempfile.gettempdir()) / ("idx_" + url.rsplit("/", 1)[-1])
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    return tmp


def parse(path: Path, segment: str) -> pd.DataFrame:
    """The index contracts of one scrip-master file (nse_fo / bse_fo), read in chunks (the files are large)."""
    want = ("pSymbol", "pTrdSymbol", "pSymbolName", "pInstType", "pOptionType", "pExpiryDate", "lLotSize",
            "pExchSeg", "pListingDate")
    header = [str(c).strip() for c in pd.read_csv(path, nrows=0).columns]
    strike_col = next((c for c in header if c.startswith("dStrikePrice")), None)
    cols = [c for c in header if c in want] + ([strike_col] if strike_col else [])
    unders, types = (NSE_UNDERLYINGS, NSE_TYPES) if segment == "nse_fo" else (BSE_UNDERLYINGS, BSE_TYPES)
    conv = nse_expiry if segment == "nse_fo" else bse_expiry
    parts = []
    for ch in pd.read_csv(path, chunksize=50000, low_memory=False, usecols=lambda c: str(c).strip() in cols):
        ch = ch.rename(columns=lambda c: str(c).strip())
        ch["pSymbolName"] = ch["pSymbolName"].astype(str).str.strip()
        ch["pInstType"] = ch["pInstType"].astype(str).str.strip().str.upper()
        ch = ch[ch["pSymbolName"].isin(unders) & ch["pInstType"].isin(types)]
        if len(ch):
            parts.append(ch)
    if not parts:
        return pd.DataFrame()
    d = pd.concat(parts, ignore_index=True)
    out = pd.DataFrame({
        "token": d["pSymbol"].astype(str).str.strip(),
        "exch_seg": segment,
        "trading_symbol": d["pTrdSymbol"].astype(str).str.strip(),
        "underlying": d["pSymbolName"],
        "inst_type": d["pInstType"].map(types),
        "expiry": d["pExpiryDate"].map(conv),
        "strike": (pd.to_numeric(d[strike_col], errors="coerce") / 100.0) if strike_col else None,
        "option_type": d["pOptionType"].astype(str).str.strip().str.upper().where(d["pInstType"].map(types) == "option"),
        "lot_size": pd.to_numeric(d.get("lLotSize"), errors="coerce").astype("Int64"),
        "listing_date": d["pListingDate"].map(conv) if "pListingDate" in d else None,
    })
    out.loc[out["inst_type"] == "future", "strike"] = None
    out["neosymbol"] = out["exch_seg"] + "|" + out["token"]
    return out


def check_expiries(df: pd.DataFrame) -> dict:
    """Compare each converted expiry with the date in its trading symbol: weekly symbols carry the exact day, monthly
    ones the month. Returns counts per segment (and fails loudly on the 22-Oct-2026 SENSEX check)."""
    out = {}
    for seg, g in df.groupby("exch_seg"):
        ok = bad = 0
        for trd, exp in zip(g["trading_symbol"], g["expiry"]):
            sd, kind = symbol_date(trd)
            if sd is None or exp is None:
                continue
            good = exp == sd if kind == "weekly" else exp.startswith(sd)
            ok, bad = ok + good, bad + (not good)
        out[seg] = {"checked": ok + bad, "mismatch": bad}
    sx = df[(df["underlying"] == "SENSEX") & df["trading_symbol"].str.startswith("SENSEX26O22")]
    if len(sx):
        out["SENSEX26O22 expiry"] = sorted(sx["expiry"].unique())
        if out["SENSEX26O22 expiry"] != ["2026-10-22"]:
            raise SystemExit(f"BSE expiry conversion is wrong: SENSEX26O22 -> {out['SENSEX26O22 expiry']}")
    return out


def load(k: Kotak) -> pd.DataFrame:
    from server.kotak import _raise_if_error
    listing = k.client().scrip_master()
    _raise_if_error(listing, "scrip_master")
    paths = listing.get("filesPaths", []) if isinstance(listing, dict) else []
    frames = []
    for seg in ("nse_fo", "bse_fo"):
        url = next((p for p in paths if p.rsplit("/", 1)[-1].startswith(seg)), None)
        if not url:
            raise SystemExit(f"scrip master has no {seg} file: {paths}")
        f = _stream(url)
        try:
            frames.append(parse(f, seg))
        finally:
            f.unlink(missing_ok=True)
    df = pd.concat(frames, ignore_index=True)
    return df


def snapshot(df: pd.DataFrame, day=None, store: Path = STORE) -> Path:
    day = day or today_ist()
    p = store / "instruments" / f"{day:%Y%m%d}.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, index=False)
    return p


def all_known(store: Path = STORE) -> pd.DataFrame:
    """Every contract ever snapshotted (tokens kept after expiry), newest snapshot wins per token."""
    files = sorted((store / "instruments").glob("*.parquet"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True).drop_duplicates("neosymbol", keep="last")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    k = Kotak()
    df = load(k)
    chk = check_expiries(df)
    p = snapshot(df)
    print(df.groupby(["exch_seg", "underlying", "inst_type"]).size().to_string())
    print("expiry check:", chk)
    print("->", p, len(df), "contracts")


if __name__ == "__main__":
    main()
