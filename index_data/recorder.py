"""§3 Nightly recorder of live index options (Kotak Neo, 1-minute), run by .github/workflows/index-recorder.yml.

    KOTAK_CONSUMER_KEY=... INDEX_STORE=<index-data checkout>/data/index python -m index_data.recorder [--day YYYY-MM-DD]

For NIFTY, SENSEX and BANKNIFTY: the two nearest expiries (NIFTY / SENSEX weeklies and monthlies as they come,
BANKNIFTY monthly), strikes within ±5 % of the day's spot close (Kotak `D`), CE and PE. One 1-minute call per contract
for the day; a contract seen for the first time is filled back to its listing date (< 30-day windows). Parquet:
STORE/options_1m/<underlying>/<expiry>/<date>.parquet, deduplicated on (token, timestamp), source 'kotak'.
After the close the quotes are the closing book: STORE/chain_eod/<date>.parquet holds them (last price, best bid / ask,
OI). Status: SMALL/status.json. Exit 1 when any underlying yields zero contracts.
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import date, timedelta

import pandas as pd

from . import instruments as I
from .common import SMALL, STORE, Kotak, candles_frame, read_json, today_ist, upsert_parquet, write_json

log = logging.getLogger("index_data.recorder")

UNDERLYINGS = ("NIFTY", "SENSEX", "BANKNIFTY")
BAND = 0.05
N_EXPIRIES = 2
QUOTE_BATCH = 49
MAX_BACKFILL_DAYS = 120                    # first sight of a contract: back to its listing, at most this far


def spot_close(k: Kotak, under: str, day: date) -> float | None:
    """The day's close of the underlying from Kotak daily candles, None when the day has no candle (no session)."""
    rows = k.history(I.SPOT[under], "D", (day - timedelta(days=10)).isoformat(), day.isoformat())
    f = candles_frame(rows)
    f = f[f["timestamp"].dt.date == day]
    return float(f["close"].iloc[-1]) if len(f) else None


def select(contracts: pd.DataFrame, under: str, spot: float, day: date) -> pd.DataFrame:
    o = contracts[(contracts["underlying"] == under) & (contracts["inst_type"] == "option")
                  & (contracts["expiry"] >= day.isoformat())]
    exps = sorted(o["expiry"].unique())[:N_EXPIRIES]
    o = o[o["expiry"].isin(exps)]
    return o[(o["strike"] - spot).abs() <= BAND * spot].copy()


def record_contract(k: Kotak, c, day: date, known: set[str], store=STORE) -> int:
    first = c.neosymbol not in known
    start = day
    if first:
        listing = pd.to_datetime(c.listing_date, errors="coerce") if isinstance(c.listing_date, str) else pd.NaT
        start = listing.date() if pd.notna(listing) else day - timedelta(days=28)
        start = min(max(start, day - timedelta(days=MAX_BACKFILL_DAYS)), day)   # a bad listing date cannot run away
    rows = k.history_range(c.neosymbol, "1min", start, day) if first else \
        k.history(c.neosymbol, "1min", day.isoformat(), day.isoformat())
    f = candles_frame(rows)
    f = f[f["timestamp"].dt.strftime("%H:%M") >= "09:15"]
    if f.empty:
        return 0
    f.insert(1, "token", c.token)
    f.insert(2, "trading_symbol", c.trading_symbol)
    f.insert(3, "strike", c.strike)
    f.insert(4, "option_type", c.option_type)
    f["source"] = "kotak"
    n = 0
    for d, g in f.groupby(f["timestamp"].dt.date):
        p = store / "options_1m" / c.underlying / c.expiry / f"{d.isoformat()}.parquet"
        upsert_parquet(p, g, ["token", "timestamp"])
        n += len(g)
    known.add(c.neosymbol)
    return n


def chain_snapshot(k: Kotak, sel: pd.DataFrame, day: date, store=STORE) -> int:
    """The closing book of the selected contracts from Kotak quotes (taken after the close, see the module doc)."""
    from server.kotak import _parse_quote
    rows = []
    items = [{"instrument_token": t, "exchange_segment": s} for t, s in zip(sel["token"], sel["exch_seg"])]
    by_tok = {(s, t): r for s, t, r in zip(sel["exch_seg"], sel["token"], sel.itertuples())}
    for i in range(0, len(items), QUOTE_BATCH):
        time.sleep(0.3)
        resp = k.client().quotes(instrument_tokens=items[i:i + QUOTE_BATCH], quote_type="all")
        k.calls += 1
        data = resp if isinstance(resp, list) else (resp.get("data") if isinstance(resp, dict) else None)
        for q in data or []:
            key = (str(q.get("exchange", "")).lower(), str(q.get("exchange_token", "")))
            c = by_tok.get(key)
            if c is None:
                continue
            p = _parse_quote(q, fo=True)
            dp = p.get("depth") or {}
            rows.append({"date": day.isoformat(), "underlying": c.underlying, "expiry": c.expiry, "token": c.token,
                         "trading_symbol": c.trading_symbol, "strike": c.strike, "option_type": c.option_type,
                         "ltp": p.get("last_price"), "bid": (dp.get("bid") or [(None,)])[0][0],
                         "ask": (dp.get("ask") or [(None,)])[0][0], "oi": p.get("open_interest"),
                         "volume": p.get("volume"), "quote_time": p.get("timestamp")})
    if rows:
        upsert_parquet(store / "chain_eod" / f"{day:%Y%m%d}.parquet", pd.DataFrame(rows), ["token"])
    return len(rows)


def run(day: date | None = None) -> dict:
    t0 = time.monotonic()
    day = day or today_ist()
    k = Kotak()
    contracts = I.load(k)
    chk = I.check_expiries(contracts)
    I.snapshot(contracts, day)
    known_file = STORE / "recorded_tokens.json"
    known = set(read_json(known_file, []))
    status = {"run_at": pd.Timestamp.now(tz="Asia/Kolkata").isoformat(timespec="seconds"), "session": day.isoformat(),
              "expiry_check": chk, "underlyings": {}, "failures": []}
    sels = []
    for u in UNDERLYINGS:
        try:
            spot = spot_close(k, u, day)
        except Exception as exc:  # noqa: BLE001
            status["failures"].append(f"{u} spot: {exc}"[:300])
            spot = None
        if spot is None:
            status["underlyings"][u] = {"spot": None, "contracts": 0, "rows": 0}
            continue
        sel = select(contracts, u, spot, day)
        sels.append(sel)
        rows = 0
        log.info("%s spot %.2f: %d contracts on %s", u, spot, len(sel), sorted(sel["expiry"].unique()))
        for c in sel.itertuples():
            try:
                rows += record_contract(k, c, day, known)
            except Exception as exc:  # noqa: BLE001 - one contract must not stop the night
                status["failures"].append(f"{c.trading_symbol}: {exc}"[:300])
        status["underlyings"][u] = {"spot": spot, "contracts": int(len(sel)), "rows": rows,
                                    "expiries": sorted(sel["expiry"].unique())}
    try:
        status["chain_eod_rows"] = chain_snapshot(k, pd.concat(sels) if sels else pd.DataFrame(), day) if sels else 0
    except Exception as exc:  # noqa: BLE001
        status["failures"].append(f"chain snapshot: {exc}"[:300])
    from .common import write_json as wj
    wj(known_file, sorted(known))
    status.update(calls=k.calls, runtime_s=round(time.monotonic() - t0, 1),
                  contracts=sum(v["contracts"] for v in status["underlyings"].values()))
    hist = read_json(SMALL / "status.json", {}) or {}
    runs = (hist.get("recent_runs") or [])[-29:] + [{k2: status[k2] for k2 in ("run_at", "session", "contracts", "calls",
                                                                              "runtime_s")} | {"failures": len(status["failures"])}]
    write_json(SMALL / "status.json", {**hist, "recorder": status, "recent_runs": runs})
    return status


def main() -> None:
    ap = argparse.ArgumentParser(description="nightly index-options recorder (Kotak, 1-minute)")
    ap.add_argument("--day", help="record this past session instead of today (YYYY-MM-DD)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    day = date.fromisoformat(a.day) if a.day else None
    st = run(day)
    print({k: st[k] for k in ("session", "contracts", "calls", "runtime_s")}, "failures:", len(st["failures"]))
    est = st["contracts"] * 1.5 / 60
    print(f"estimate for a normal night: ~{st['contracts']} calls, ~{est:.0f} min")
    no_session = all(v.get("spot") is None for v in st["underlyings"].values())
    if no_session:
        print("no session on", st["session"], "(no daily candle): nothing recorded")
        return
    zero = [u for u, v in st["underlyings"].items() if v["contracts"] == 0]
    if zero:
        raise SystemExit(f"zero contracts for {zero}")


if __name__ == "__main__":
    main()
