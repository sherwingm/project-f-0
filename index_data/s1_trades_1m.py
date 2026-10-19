"""1-minute candles of S1's own paper trades: the stock and the option, for every day a position was open.

    KOTAK_CONSUMER_KEY=... INDEX_STORE=... python -m index_data.s1_trades_1m --ledger paper_ledger.json [--day D]
        [--since 2026-10-14]

The live server keeps its 30-second polls only in memory, so a trade's minute path is lost at the day's end. This
saves it from Kotak's history after the close, into STORE/s1_trades_1m/<day>/<SYMBOL>_stock.parquet and
<tradingsymbol>.parquet (source 'kotak'). The option must be fetched before it expires (Kotak serves no expired
contract); the stock can be fetched any time within 5 years. Positions come from the paper ledger (branch paper-state,
data/paper_ledger.json): every position open at any time on the day (rule trades of arms A, B, F and manual ones).
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .common import SMALL, STORE, Kotak, candles_frame, read_json, today_ist, upsert_parquet, write_json

log = logging.getLogger("index_data.s1_trades_1m")


def positions_on(ledger: dict, day: str) -> list[dict]:
    out = []
    for p in (ledger.get("positions") or []) + (ledger.get("closed") or []):
        o, c = str(p.get("opened_at") or "")[:10], str(p.get("closed_at") or "")[:10]
        if o and o <= day and (not c or c >= day):
            out.append(p)
    return out


def tokens(k: Kotak) -> tuple[dict, dict, dict]:
    """(equity SYMBOL -> token, F&O trading symbol -> token, (SYMBOL, CE/PE, expiry, strike) -> token)."""
    from server.kotak import _raise_if_error
    from .instruments import _stream, nse_expiry
    listing = k.client().scrip_master()
    _raise_if_error(listing, "scrip_master")
    paths = listing.get("filesPaths", []) if isinstance(listing, dict) else []
    eq, fo_trd, fo_key = {}, {}, {}
    cm = next(p for p in paths if p.rsplit("/", 1)[-1].startswith("nse_cm"))
    f = _stream(cm)
    try:
        for ch in pd.read_csv(f, chunksize=50000, low_memory=False,
                              usecols=lambda c: str(c).strip() in ("pSymbol", "pTrdSymbol")):
            ch = ch.rename(columns=lambda c: str(c).strip())
            t = ch["pTrdSymbol"].astype(str).str.strip()
            m = t.str.endswith("-EQ")
            eq.update(dict(zip(t[m].str[:-3], ch.loc[m, "pSymbol"].astype(str).str.strip())))
    finally:
        f.unlink(missing_ok=True)
    fo = next(p for p in paths if p.rsplit("/", 1)[-1].startswith("nse_fo"))
    f = _stream(fo)
    try:
        hdr = [str(c).strip() for c in pd.read_csv(f, nrows=0).columns]
        sc = next((c for c in hdr if c.startswith("dStrikePrice")), None)
        want = {"pSymbol", "pTrdSymbol", "pSymbolName", "pInstType", "pOptionType", "pExpiryDate", sc}
        for ch in pd.read_csv(f, chunksize=50000, low_memory=False, usecols=lambda c: str(c).strip() in want):
            ch = ch.rename(columns=lambda c: str(c).strip())
            ch = ch[ch["pInstType"].astype(str).str.strip() == "OPTSTK"]
            for r in ch.itertuples(index=False):
                tok = str(r.pSymbol).strip()
                fo_trd[str(r.pTrdSymbol).strip()] = tok
                strike = float(getattr(r, sc)) / 100.0 if sc and pd.notna(getattr(r, sc)) else None
                fo_key[(str(r.pSymbolName).strip(), str(r.pOptionType).strip().upper(), nse_expiry(r.pExpiryDate), strike)] = tok
    finally:
        f.unlink(missing_ok=True)
    return eq, fo_trd, fo_key


def save(f: pd.DataFrame, path: Path, meta: dict) -> int:
    f = f[f["timestamp"].dt.strftime("%H:%M") >= "09:15"]
    if f.empty:
        return 0
    for k2, v in meta.items():
        f[k2] = v
    f["source"] = "kotak"
    return upsert_parquet(path, f, ["timestamp"])


def run(ledger: dict, days: list[str], k: Kotak, store=STORE) -> dict:
    eq, fo_trd, fo_key = tokens(k)
    res = {"days": {}, "missing_tokens": []}
    for d in days:
        pos = positions_on(ledger, d)
        n_stock = n_opt = 0
        for sym in sorted({p["symbol"] for p in pos}):
            tok = eq.get(sym)
            if not tok:
                res["missing_tokens"].append(f"{sym}-EQ")
                continue
            f = candles_frame(k.history(f"nse_cm|{tok}", "1min", d, d))
            n_stock += save(f, store / "s1_trades_1m" / d / f"{sym}_stock.parquet", {"symbol": sym})
        for p in {p["tradingsymbol"]: p for p in pos}.values():
            tok = fo_trd.get(p["tradingsymbol"]) or fo_key.get((p["symbol"], p["instrument"], p["expiry"], float(p["strike"])))
            if not tok:
                res["missing_tokens"].append(p["tradingsymbol"])
                continue
            f = candles_frame(k.history(f"nse_fo|{tok}", "1min", d, d))
            n_opt += save(f, store / "s1_trades_1m" / d / f"{p['tradingsymbol']}.parquet",
                          {"symbol": p["symbol"], "tradingsymbol": p["tradingsymbol"], "option_type": p["instrument"],
                           "strike": float(p["strike"]), "expiry": p["expiry"],
                           "arms": ",".join((p.get("rule") or {}).get("arms") or [])})
        res["days"][d] = {"positions": len(pos), "stock_rows": n_stock, "option_rows": n_opt}
        log.info("%s: %s", d, res["days"][d])
    res["calls"] = k.calls
    return res


def session_days(since: str, until: str) -> list[str]:
    from .instruments import SPOT
    return [d.isoformat() for d in pd.bdate_range(since, until).date]


def main() -> None:
    ap = argparse.ArgumentParser(description="1-minute stock + option candles of S1's paper trades")
    ap.add_argument("--ledger", required=True, help="paper_ledger.json from the paper-state branch")
    ap.add_argument("--day", default=None, help="one day (default today)")
    ap.add_argument("--since", default=None, help="every weekday from this date to --day (first run)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ledger = json.loads(Path(a.ledger).read_text(encoding="utf-8"))
    day = a.day or today_ist().isoformat()
    days = session_days(a.since, day) if a.since else [day]
    res = run(ledger, days, Kotak())
    st = read_json(SMALL / "status.json", {}) or {}
    write_json(SMALL / "status.json", {**st, "s1_trades_1m": {"run_on": today_ist().isoformat(), **res}})
    print({d: v for d, v in res["days"].items()}, "missing:", res["missing_tokens"][:10], "calls:", res["calls"])


if __name__ == "__main__":
    main()
