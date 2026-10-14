"""S2 step 2 · short build-up → one bought put at Rs 600-8,000 a lot, exit at day d+5 (50 % stop, T-1), as
strategies/S2_step2_short_buildup_put.md pre-registers it (numbers only).

    python -m scanner.backtest_s2_put

Signals: step 1's passing cell (data/results/S2_screen_signals.csv, written by `python -m scanner.s2_screen`):
short build-up, price <= -3 %, combined futures OI >= +10 %, volume >= 1.5x. The put: current monthly expiry if
>= 10 sessions remain after day d (else the next monthly); from the put nearest the stock's day-d close (a tie: the
higher) walking DOWN to the first with >= 50 contracts on day d+1, fill >= Rs 2 and one lot at Rs 600-8,000;
fill = day d+1's premium VWAP (else close) + 1 tick.
"""
from __future__ import annotations

import argparse
import bisect
import logging
import math
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest_s1_v4 as v4
from .backtest_cheap_options import sessions_to
from .backtest_s1_v6 import Quote, fill_at
from .build import ROOT
from .option_engine import TICK, choose_expiry
from .stats import clustered_t

log = logging.getLogger("backtest_s2_put")

BAND, CONTRACTS, MIN_PREMIUM, STOP, T_MINUS = (600.0, 8000.0), 50, 2.0, 0.5, 1
CELL = {"class": "short_buildup", "price_thr": 3.0, "oi_thr": 10.0}
END = "2026-09-25"                                  # the last session with stock closes (eod2)
YEARS = tuple(str(y) for y in range(2021, 2027))


@dataclass(frozen=True)
class Variant:
    name: str
    hold: int
    stop: bool = True


VARIANTS = (Variant("h5", 5), Variant("h3", 3), Variant("h5_nostop", 5, stop=False))
PRIMARY = "h5"


# ---------------------------------------------------------------- rules (pure)
def put_strike(strikes, spot: float) -> float | None:
    """The listed strike nearest spot; a tie: the higher."""
    ks = sorted(set(float(k) for k in strikes))
    return min(ks, key=lambda k: (abs(k - spot), -k)) if ks and spot else None


def walk_put(strikes, spot: float, quotes: dict[float, Quote], min_contracts: int = CONTRACTS,
             band: tuple[float, float] = BAND):
    """From the put nearest spot downward: the first with >= min_contracts on day d+1, fill >= Rs 2 and one lot in
    `band`. Returns (quote, fill, source, strikes walked) or the reason there is none."""
    ks = sorted(set(float(k) for k in strikes))
    k0 = put_strike(ks, spot)
    if k0 is None:
        return "no_strike_or_expiry"
    down = [k for k in reversed(ks) if k <= k0]
    for n, k in enumerate(down):
        q = quotes.get(k)
        if q is None or not q.lot > 0:
            continue
        f = fill_at(q, min_contracts)
        if f is None:
            continue
        px, source = f
        if px < MIN_PREMIUM:
            return "lottery_refused"
        cost = px * q.lot
        if cost < band[0]:
            return "walk_below_band"
        if cost > band[1]:
            continue
        return q, px, source, n
    return "walk_no_liquid_strike_in_band"


def exit_step(day_no: int, close: float, fill: float, to_expiry: int, var: Variant) -> str | None:
    """Day `day_no` of the trade (1 = day d+1): stop, then the time exit at day `hold`, then T-1."""
    if var.stop and close <= STOP * fill:
        return "0_stop"
    if day_no >= var.hold:
        return "1_time"
    if to_expiry <= T_MINUS:
        return "2_t_minus_1"
    return None


# ---------------------------------------------------------------- data
class Bhav:
    """Per session: PE closes {(sym, expiry, strike): close}, the PE chains, spot and future closes."""

    def __init__(self, cache: Path):
        self.cache, self._c = cache, {}

    def day(self, d: str) -> dict | None:
        if d in self._c:
            return self._c[d]
        f = self.cache / f"fo_bhavcopy_{d.replace('-', '')}.csv"
        if not f.exists():
            return None
        b = pd.read_csv(f, usecols=lambda c: c in ("TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp",
                                                    "ClsPric", "UndrlygPric"))
        b["XpryDt"] = b["XpryDt"].astype(str).str[:10]
        pe = b[(b["FinInstrmTp"] == "STO") & (b["OptnTp"] == "PE")]
        fut = b[b["FinInstrmTp"] == "STF"].sort_values("XpryDt")
        spot = {}
        if "UndrlygPric" in b.columns:
            u = b[(b["FinInstrmTp"] == "STO") & (b["UndrlygPric"] > 0)].drop_duplicates("TckrSymb")
            spot = dict(zip(u["TckrSymb"], u["UndrlygPric"].astype(float)))
        for s, c in zip(fut["TckrSymb"], fut["ClsPric"]):
            spot.setdefault(s, float(c))
        day = {"puts": dict(zip(zip(pe["TckrSymb"], pe["XpryDt"], pe["StrkPric"].astype(float)), pe["ClsPric"].astype(float))),
               "chain": {s: g for s, g in pe.groupby("TckrSymb")},
               "futs": dict(zip(zip(fut["TckrSymb"], fut["XpryDt"]), fut["ClsPric"].astype(float))), "spot": spot}
        if len(self._c) > 40:
            self._c.pop(next(iter(self._c)))
        self._c[d] = day
        return day


def put_quotes(p: pd.DataFrame, sym: str, exp: str) -> dict[float, Quote]:
    rows = p[(p["TckrSymb"] == sym) & (p["XpryDt"].astype(str).str[:10] == exp) & (p["OptnTp"] == "PE")]
    num = lambda v: float(v) if v == v else math.nan                # noqa: E731
    return {float(r["StrkPric"]): Quote(float(r["StrkPric"]), num(r["TtlTradgVol"]), num(r["TtlTrfVal"]),
                                        int(r["NewBrdLotQty"]) if r["NewBrdLotQty"] == r["NewBrdLotQty"] else 0,
                                        num(r["ClsPric"]), num(r["LwPric"]), num(r["HghPric"]))
            for _, r in rows.iterrows()}


# ---------------------------------------------------------------- the simulation
def simulate(sig: pd.DataFrame, var: Variant, sessions: list[str], bhav: Bhav, prices, ban: dict[str, set[str]],
             category, stock: dict[str, pd.Series], funnel: Counter, end: str = END) -> pd.DataFrame:
    cal = [date.fromisoformat(d) for d in sessions]
    rows = []
    for r in sig.itertuples():
        i = bisect.bisect_left(sessions, r.date)
        if i >= len(sessions) or sessions[i] != r.date or i + var.hold >= len(sessions) or sessions[i + var.hold] > end:
            funnel["outside_window"] += 1
            continue
        d, d1 = sessions[i], sessions[i + 1]
        if r.symbol in ban.get(d1, set()):
            funnel["in_ban_on_entry_day"] += 1
            continue
        b0 = bhav.day(d)
        chain = b0["chain"].get(r.symbol) if b0 else None
        spot = b0["spot"].get(r.symbol) if b0 else None
        exp = choose_expiry(chain["XpryDt"], cal, cal[i]) if chain is not None else None
        if exp is None or not spot:
            funnel["no_strike_or_expiry"] += 1
            continue
        p = prices(d1)
        if p is None:
            funnel["no_day1_prices"] += 1
            continue
        w = walk_put(chain.loc[chain["XpryDt"] == exp, "StrkPric"], spot, put_quotes(p, r.symbol, exp))
        if isinstance(w, str):
            funnel[w] += 1
            continue
        q, fill, src, walked = w
        cat, _ = category(r.symbol, d)
        path = _path(r.symbol, exp, q.strike, fill, i + 1, sessions, cal, bhav, stock.get(r.symbol), var)
        slip = v4.SLIPPAGE.get(cat, v4.SLIPPAGE["unknown"])
        charges = slippage = net = None
        if not path["excluded"]:
            charges, slippage, net = v4.net_of(fill, path["exit_price"], q.lot, slip)
        rows.append({"arm": "S2", "variant": var.name, "signal_date": d, "entry_date": d1, "symbol": r.symbol,
                     "category": cat, "sector": "", "ar0_pct": r.price_pct, "raw0_pct": r.price_pct,
                     "oi_pct": r.oi_pct, "vol_ratio": r.vol_ratio, "expiry": exp, "spot0": round(float(spot), 2),
                     "strike": q.strike, "opt": "PE", "strikes_walked": walked,
                     "distance_pct": round((1 - q.strike / float(spot)) * 100, 3), "contracts_day1": q.contracts,
                     "lot": q.lot, "lots": 1, "qty": q.lot, "entry_price": fill, "entry_source": src,
                     "premium_rs": round(fill * q.lot, 2), "exit_date": path["exit_date"],
                     "exit_reason": path["reason"], "exit_price": path["exit_price"], "held": path["held"],
                     "charges": charges, "slippage": slippage, "net": net,
                     "net_pct": None if net is None else round(net / (fill * q.lot) * 100, 3),
                     "excluded": path["excluded"], f"stock_short_r{var.hold}": getattr(r, f"r{var.hold}", None)})
        funnel["traded"] += 1
    return pd.DataFrame(rows)


def _path(sym: str, exp: str, k: float, fill: float, e: int, sessions: list[str], cal: list[date], bhav: Bhav,
          stock: pd.Series | None, var: Variant) -> dict:
    fut0 = stock0 = None
    for j in range(e, len(sessions)):
        b = bhav.day(sessions[j])
        if b is None:
            continue
        c = b["puts"].get((sym, exp, k))
        if c is None:
            return {"exit_date": sessions[j], "reason": None, "exit_price": None, "held": j - e,
                    "excluded": "contract_changed"}
        f = b["futs"].get((sym, exp))
        px = float(stock.get(sessions[j], math.nan)) if stock is not None else math.nan
        if fut0 is None:
            fut0, stock0 = f, px
        elif f and fut0 and stock0 and not (math.isnan(px) or math.isnan(stock0)) and \
                abs((f / fut0) / (px / stock0) - 1) > v4.CA_TOLERANCE:
            return {"exit_date": sessions[j], "reason": None, "exit_price": None, "held": j - e,
                    "excluded": "price_adjusted"}
        why = exit_step(j - e + 1, c, fill, sessions_to(cal, cal[j], date.fromisoformat(exp)), var)
        if why:
            return {"exit_date": sessions[j], "reason": why, "exit_price": max(0.0, round(c - TICK, 2)),
                    "held": j - e, "excluded": ""}
    return {"exit_date": sessions[-1], "reason": None, "exit_price": None, "held": None, "excluded": "no_exit_in_data"}


# ---------------------------------------------------------------- summaries
def metrics(g: pd.DataFrame) -> dict:
    g = g[g["excluded"].fillna("") == ""]
    r = g["net_pct"].astype(float)
    out = {"n": len(g), "win_pct": round((r > 0).mean() * 100, 1) if len(g) else None,
           "mean_pct": round(r.mean(), 2) if len(g) else None, "median_pct": round(r.median(), 2) if len(g) else None,
           "t": clustered_t(r, g["signal_date"]) if len(g) > 1 else None,
           "total_rs": round(g["net"].sum()) if len(g) else None,
           "avg_lot_rs": round(g["premium_rs"].mean()) if len(g) else None}
    for why in ("0_stop", "1_time", "2_t_minus_1"):
        out[f"exit_{why}_pct"] = round((g["exit_reason"] == why).mean() * 100, 1) if len(g) else None
    return out


def by_year(g: pd.DataFrame) -> dict:
    g = g[g["excluded"].fillna("") == ""]
    return {y: (round(g[g["entry_date"].str[:4] == y]["net_pct"].astype(float).mean(), 2)
                if (g["entry_date"].str[:4] == y).any() else None) for y in YEARS}


def gate(g: pd.DataFrame) -> list[dict]:
    m, yrs = metrics(g), by_year(g)
    pos = sum(1 for y in YEARS if (yrs[y] or 0) > 0)
    rows = [{"test": "net mean > 0 after costs (% of premium)", "value": m["mean_pct"], "ok": (m["mean_pct"] or 0) > 0},
            {"test": "date-clustered t >= 2", "value": m["t"], "ok": (m["t"] or 0) >= 2},
            {"test": "positive in >= 5 of 6 years incl. 2025 and 2026", "value": f"{pos} of 6 (2025 {yrs['2025']}, 2026 {yrs['2026']})",
             "ok": pos >= 5 and (yrs["2025"] or 0) > 0 and (yrs["2026"] or 0) > 0},
            {"test": "N >= 200", "value": m["n"], "ok": m["n"] >= 200}]
    for x in rows:
        x["result"] = "pass" if x.pop("ok") else "fail"
    rows.append({"test": "OVERALL", "value": "", "result": "PASS" if all(x["result"] == "pass" for x in rows) else "FAIL"})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="S2 step 2: short build-up -> one bought put (numbers only)")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from . import amfi
    from .backtest_s1_v2 import md
    from .equity import load_symbol
    from .events.store import Store
    from .nse_fo import BhavcopyUnavailable, download_fo_prices

    sig = pd.read_csv(a.out_dir / "S2_screen_signals.csv")
    sig = sig[(sig["class"] == CELL["class"]) & (sig["price_thr"] == CELL["price_thr"]) & (sig["oi_thr"] == CELL["oi_thr"])]
    sig = sig.sort_values(["date", "symbol"])
    sessions = sorted(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}" for p in a.cache_dir.glob("fo_bhavcopy_*.csv"))
    with Store() as st:
        ban: dict[str, set[str]] = {}
        for e in st.all_of_type("ban"):
            if e.get("subtype") == "in":
                ban.setdefault(e["event_date"], set()).add(e["symbol"])
    cats = amfi.load()
    stock = {}
    for s in sig["symbol"].unique():
        try:
            f = load_symbol(s, a.eod2_dir)
            f.index = f.index.strftime("%Y-%m-%d")
            stock[s] = f["Close"]
        except Exception as exc:  # noqa: BLE001
            log.info("%s: no eod2 (%s)", s, exc)
    bhav = Bhav(a.cache_dir)
    _px: dict[str, pd.DataFrame | None] = {}

    def prices(d: str):
        if d not in _px:
            try:
                _px[d] = download_fo_prices(date.fromisoformat(d), a.cache_dir)
            except (BhavcopyUnavailable, OSError, ValueError) as exc:
                log.warning("prices %s: %s", d, exc)
                _px[d] = None
            if len(_px) > 30:
                _px.pop(next(iter(_px)))
        return _px[d]

    frames, funnels = [], {}
    for var in VARIANTS:
        f = Counter(signals=len(sig))
        frames.append(simulate(sig, var, sessions, bhav, prices, ban, cats.category_on, stock, f))
        funnels[var.name] = f
    trades = pd.concat(frames, ignore_index=True)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(a.out_dir / "S2_put_trades.csv", index=False)

    summary = pd.DataFrame([{"variant": v.name, **metrics(trades[trades["variant"] == v.name]),
                             **by_year(trades[trades["variant"] == v.name])} for v in VARIANTS])
    funnel = pd.DataFrame([{"variant": k, **dict(f)} for k, f in funnels.items()]).fillna(0)
    prim = trades[(trades["variant"] == PRIMARY) & (trades["excluded"].fillna("") == "")]
    stock_side = {"n": len(prim), "short_stock_5d_mean": round(prim["stock_short_r5"].astype(float).mean(), 3),
                  "short_stock_5d_t": clustered_t(prim["stock_short_r5"].astype(float), prim["signal_date"])}
    dist = pd.cut(prim["distance_pct"].astype(float), [-100, 0, 2, 5, 10, 100],
                  labels=["above spot", "0-2 %", "2-5 %", "5-10 %", "> 10 %"]).astype(str)
    by_dist = pd.DataFrame([{"strike below the stock": b, **metrics(prim[dist == b])}
                            for b in ("above spot", "0-2 %", "2-5 %", "5-10 %", "> 10 %")])
    sec = [
        "# S2 step 2 put backtest report\n\nNumbers only. strategies/S2_step2_short_buildup_put.md.\n",
        f"Signals (step 1's cell): {len(sig)}; window to {END}; 1 bought put, Rs 600-8,000 a lot, exit at d+5 "
        "(50 % stop, T-1), fill = day d+1 VWAP + 1 tick, net of charges and slippage.\n",
        "## Main table (net % of premium)\n\n" + md(summary),
        "## Signals removed by each filter\n\n" + md(funnel),
        f"## The same trades as a 5-session short stock position (step 1's measure)\n\n{stock_side}\n",
        f"## By strike distance below the stock ({PRIMARY})\n\n" + md(by_dist),
        f"## Pass test ({PRIMARY})\n\n" + md(pd.DataFrame(gate(trades[trades["variant"] == PRIMARY]))),
    ]
    (a.out_dir / "S2_put_backtest_report.md").write_text("\n".join(sec), encoding="utf-8")
    print("\n".join(sec[1:]))


if __name__ == "__main__":
    main()
