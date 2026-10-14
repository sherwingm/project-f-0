"""S2 · the last session's short build-ups, for the S2 page (no trades: the put is traded only if step 2 passes).

    python -m scanner.s2_live            # -> data/s2/signals.json (run by the nightly Action)

Short build-up (strategies/S2_oi_buildup_screen.md, the passing cell): on day d the stock fell 3 % or more, the
combined stock-futures OI rose 10 % or more and the volume was at least 1.5x its 20-session average; a stock-futures
expiry day and the session after it are skipped. For each signal, the put the step-2 rule would start from: walking
down from the strike nearest the close to the first put with >= 50 contracts on day d and a lot of Rs 600-8,000 (the
rule itself reads day d+1's volume and average price; this is the evening's preview).
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from .backtest_s2_put import BAND, CELL, put_quotes, walk_put
from .build import ROOT
from .s2_screen import VOL_WINDOW, classify

log = logging.getLogger("s2_live")
OUT = ROOT / "data" / "s2" / "signals.json"
HISTORY = 20                                     # sessions of past signal lists kept on the page


def combined_oi(bhav: pd.DataFrame) -> tuple[pd.Series, set[str]]:
    """Stock-futures OI summed over expiries per symbol, and the stock-futures expiry dates in the file."""
    s = bhav[bhav["FinInstrmTp"] == "STF"]
    return s.groupby(s["TckrSymb"].astype(str).str.strip())["OpnIntrst"].sum(), set(s["XpryDt"].astype(str).str[:10])


def find_signals(oi_d: pd.Series, oi_prev: pd.Series, px: dict[str, pd.DataFrame], d: str) -> list[dict]:
    """The short build-ups of day d from the two sessions' combined OI and each stock's daily bars."""
    out = []
    for sym in sorted(set(oi_d.index) & set(oi_prev.index)):
        f = px.get(sym)
        if f is None or d not in f.index or not (oi_d[sym] > 0 and oi_prev[sym] > 0):
            continue
        i = f.index.get_loc(d)
        if i < VOL_WINDOW + 1:
            continue
        c, c0, v = float(f["Close"].iloc[i]), float(f["Close"].iloc[i - 1]), float(f["Volume"].iloc[i])
        avg = float(f["Volume"].iloc[i - VOL_WINDOW:i].mean())
        if not (c0 > 0 and avg > 0):
            continue
        pc, oc, vr = (c / c0 - 1) * 100, (oi_d[sym] / oi_prev[sym] - 1) * 100, v / avg
        if classify(pc, oc, vr, CELL["price_thr"], CELL["oi_thr"]) == CELL["class"]:
            out.append({"symbol": sym, "close": round(c, 2), "price_pct": round(pc, 2), "oi_pct": round(float(oc), 2),
                        "vol_ratio": round(vr, 2)})
    return sorted(out, key=lambda x: x["price_pct"])


def preview_put(sig: dict, bhav: pd.DataFrame, prices: pd.DataFrame | None, d: str, cal: list[date]) -> dict:
    from .option_engine import choose_expiry
    pe = bhav[(bhav["FinInstrmTp"] == "STO") & (bhav["OptnTp"] == "PE") & (bhav["TckrSymb"] == sig["symbol"])]
    if pe.empty:
        return {"put": None, "put_note": "no stock options"}
    exp = choose_expiry(pe["XpryDt"].astype(str).str[:10], cal, date.fromisoformat(d))
    if exp is None or prices is None:
        return {"put": None, "put_note": "no expiry or prices"}
    w = walk_put(pe.loc[pe["XpryDt"].astype(str).str[:10] == exp, "StrkPric"], sig["close"],
                 put_quotes(prices, sig["symbol"], exp))
    if isinstance(w, str):
        why = {"walk_below_band": f"cheapest liquid lot below Rs {BAND[0]:,.0f}",
               "walk_no_liquid_strike_in_band": f"no put with >= 50 contracts and a lot of Rs {BAND[0]:,.0f}-{BAND[1]:,.0f}",
               "lottery_refused": "premium below Rs 2"}.get(w, w)
        return {"put": None, "put_note": why}
    q, px, _src, walked = w
    return {"put": {"expiry": exp, "strike": q.strike, "premium": px, "lot": q.lot, "lot_cost": round(px * q.lot),
                    "below_spot_pct": round((1 - q.strike / sig["close"]) * 100, 2), "contracts": q.contracts}}


def run(today: date | None = None, cache: Path = ROOT / "data" / "cache", eod2: Path = ROOT / "data" / "eod2",
        out: Path = OUT) -> dict:
    from .cm_fallback import IST, fill
    from .equity import load_symbol
    from .nse_fo import BhavcopyUnavailable, download_fo_bhavcopy, download_fo_prices

    today = today or datetime.now(IST).date()
    got, d = [], today
    while len(got) < 2 and (today - d).days < 12:
        if d.weekday() < 5:
            try:
                got.append((d.isoformat(), download_fo_bhavcopy(d, cache)))
            except BhavcopyUnavailable:
                pass
        d -= timedelta(days=1)
    prev_state = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    if len(got) < 2:
        log.warning("fewer than two F&O bhavcopies found; nothing to do")
        return prev_state
    (d1, b1), (d0, b0) = got
    oi1, exp1 = combined_oi(b1)
    oi0, exp0 = combined_oi(b0)
    state = {"rule": "short build-up: price -3 % or more, combined futures OI +10 % or more, volume 1.5x its 20-day "
                     "average (expiry day and the day after skipped); S2 step 2 decides whether a put is traded",
             "session": d1, "generated": datetime.now(IST).isoformat(timespec="minutes"), "signals": [], "note": None,
             "history": [h for h in prev_state.get("history", []) if h.get("session") != d1]}
    if d1 in exp1 or d1 in exp0 or d0 in exp0 or d0 in exp1:
        state["note"] = "expiry or rollover session: the combined OI jumps, so no signals are read today"
    else:
        px = {}
        for s in sorted(oi1.index):
            try:
                f = load_symbol(s, eod2)
                px[s] = f[f.index >= pd.Timestamp(today - timedelta(days=90))]
            except Exception as exc:  # noqa: BLE001
                log.info("%s: no eod2 (%s)", s, exc)
        fill(px, cache, today)
        for f in px.values():
            f.index = f.index.strftime("%Y-%m-%d")
        sigs = find_signals(oi1, oi0, px, d1)
        try:
            prices = download_fo_prices(date.fromisoformat(d1), cache)
        except (BhavcopyUnavailable, OSError, ValueError):
            prices = None
        cal = sorted({date.fromisoformat(d) for d in px[next(iter(px))].index}) if px else []
        b1 = b1.assign(XpryDt=b1["XpryDt"].astype(str).str[:10])
        state["signals"] = [{**s, **preview_put(s, b1, prices, d1, cal)} for s in sigs]
    state["history"] = ([{"session": d1, "symbols": [s["symbol"] for s in state["signals"]], "note": state["note"]}]
                        + state["history"])[:HISTORY]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(state, indent=1), encoding="utf-8")
    return state


def main() -> None:
    ap = argparse.ArgumentParser(description="S2: the last session's short build-ups -> data/s2/signals.json")
    ap.add_argument("--today", type=date.fromisoformat)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    st = run(a.today)
    print(st.get("session"), st.get("note") or "", [(s["symbol"], s["price_pct"], s["oi_pct"]) for s in st.get("signals", [])])


if __name__ == "__main__":
    main()
