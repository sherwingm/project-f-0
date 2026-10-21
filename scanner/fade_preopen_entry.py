"""S1 fade · buying at the open: a fair-price limit sent for 09:15 (test 1), and the stock future's pre-open (test 2).

    python -m scanner.fade_preopen_entry

strategies/S1_fade_preopen_entry.md fixes every choice. Test 1: limit L = Black-Scholes from the stock's day-0 open (the
cash pre-open price) with the previous close's implied volatility x c (c = the results-day IV drop, fixed on 2022-24);
filled on 1-minute candles 09:15-09:29 when the low trades through L. Test 2: the stock's day-0 open -> close, signed as
the fade. Writes data/results/S1_fade_preopen_entry.md and _trades.csv.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

import pandas as pd

from server import charges as ch

from .backtest_s1_v2 import md
from .backtest_s1_v10 import Bhav
from .build import ROOT
from .equity import load_symbol
from .stats import clustered_t

RES, CACHE, EOD2 = ROOT / "data" / "results", ROOT / "data" / "cache", ROOT / "data" / "eod2"
TICK_CHANGE, CALIB_END, FUT_PREOPEN = "2025-11-03", "2024-10-17", "2025-12-08"
R = 0.065
FUT_COST = 0.05                                                   # % round trip, test 2
HALF = lambda d: "Oct24-Oct25" if d < TICK_CHANGE else "Nov25-Sep26"     # noqa: E731


# ---------- Black-Scholes ----------
def _n(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs(side: str, s: float, k: float, t: float, v: float) -> float:
    if t <= 0 or v <= 0:
        return max(0.0, s - k) if side == "CE" else max(0.0, k - s)
    d1 = (math.log(s / k) + (R + v * v / 2) * t) / (v * math.sqrt(t))
    d2 = d1 - v * math.sqrt(t)
    if side == "CE":
        return s * _n(d1) - k * math.exp(-R * t) * _n(d2)
    return k * math.exp(-R * t) * _n(-d2) - s * _n(-d1)


def iv(side: str, price: float, s: float, k: float, t: float) -> float | None:
    if not (price > 0 and s > 0 and t > 0):
        return None
    lo, hi = 1e-4, 5.0
    if bs(side, s, k, t, lo) > price or bs(side, s, k, t, hi) < price:
        return None                                               # below intrinsic / above any vol
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if bs(side, s, k, t, mid) < price else (lo, mid)
    return (lo + hi) / 2


def years(d: str, expiry: str) -> float:
    days = (date.fromisoformat(expiry) - date.fromisoformat(d)).days
    return (days if days > 0 else 0.5) / 365


# ---------- shared ----------
class Eq:
    def __init__(self):
        self._c: dict[str, pd.DataFrame | None] = {}

    def get(self, sym: str) -> pd.DataFrame | None:
        if sym not in self._c:
            try:
                f = load_symbol(sym, EOD2)
                f.index = f.index.strftime("%Y-%m-%d")
                self._c[sym] = f[~f.index.duplicated(keep="last")]
            except Exception:  # noqa: BLE001
                self._c[sym] = None
        return self._c[sym]

    def oc(self, sym: str, d: str, prev: str) -> tuple[float, float, float] | None:
        f = self.get(sym)
        if f is None or d not in f.index or prev not in f.index:
            return None
        return float(f.at[d, "Open"]), float(f.at[d, "Close"]), float(f.at[prev, "Close"])


def sessions() -> list[str]:
    return sorted(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}" for p in CACHE.glob("fo_bhavcopy_*.csv"))


def prev_of(cal: list[str], d: str) -> str | None:
    i = cal.index(d) if d in cal else -1
    return cal[i - 1] if i > 0 else None


# ---------- calibration (c) ----------
def calibrate(bhav: Bhav, cal: list[str]) -> tuple[float, int, int]:
    t = pd.read_csv(RES / "S1_v10_trades_2022_24.csv")
    t = t[(t["entry"] == "open") & (t["e1_excluded"].fillna("") == "") & (t["day0"] < CALIB_END)]
    ratios = []
    for r in t.itertuples():
        p = prev_of(cal, r.day0)
        bp, b0 = bhav.day(p) if p else None, bhav.day(r.day0)
        if not bp or not b0:
            continue
        key = (r.symbol, str(r.expiry)[:10], float(r.strike), r.side)
        cp, c0 = bp["opt"].get(key), b0["opt"].get(key)
        sp, s0 = bp["spot"].get(r.symbol), b0["spot"].get(r.symbol)
        if not (cp and c0 and sp and s0):
            continue
        vp = iv(r.side, cp, sp, float(r.strike), years(p, key[1]))
        v0 = iv(r.side, c0, s0, float(r.strike), years(r.day0, key[1]))
        if vp and v0:
            ratios.append(v0 / vp)
    return float(pd.Series(ratios).median()), len(ratios), len(t)


# ---------- test 1 ----------
def fill_sim(m: pd.DataFrame, lim: float, tick: float, mid: bool) -> tuple[str, float] | None:
    w = m[(m["t"] >= "09:15") & (m["t"] <= "09:29")]
    hit = w[w["l"] <= lim - tick + 1e-9]
    if hit.empty:
        return None
    r = hit.iloc[0]
    px = min(lim, (float(r["h"]) + float(r["l"])) / 2) if mid else min(lim, float(r["h"]))
    return r["t"], round(math.floor(px / tick + 1e-9) * tick, 2) if mid else round(px, 2)


def exits(m: pd.DataFrame, side: str, lot: int, entry: float, tick: float, t_fill: str) -> dict:
    after = m[m["t"] > t_fill]

    def net(sell: float) -> float:
        return (sell - entry) * lot - ch.leg(side, "BUY", lot, entry)["total"] - ch.leg(side, "SELL", lot, sell)["total"]
    v10 = max(tick, round(float(m["c"].iloc[-1]) - tick, 2))
    v11 = v10
    hit = after[after["l"] <= 0.80 * entry + 1e-9]
    if not hit.empty:
        v11 = max(tick, round(min(0.80 * entry, float(hit.iloc[0]["o"])) - tick, 2))
    return {"v10": round(net(v10), 2), "v11": round(net(v11), 2)}


def test1(bhav: Bhav, cal: list[str], eq: Eq, c: float) -> pd.DataFrame:
    base = pd.read_csv(RES / "S1_fade_realistic_entry_trades.csv")
    base = base[base["B_excluded"].fillna("") == ""]
    con = pd.read_csv(RES / "S1_v10_bandv10_contracts.csv")
    con = {(r.symbol, r.day0, r.side): r for r in con.itertuples()}
    mins = pd.read_csv(RES / "S1_v10_bandv10_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    by = {k: g.sort_values("ts").reset_index(drop=True) for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
    variants = {"main": (c, 1.0, False), "c=1": (1.0, 1.0, False), "Lx0.90": (c, 0.90, False),
                "Lx1.10": (c, 1.10, False), "mid fill": (c, 1.0, True)}
    rows = []
    for b in base.itertuples():
        r = con[(b.symbol, b.day0, b.side)]
        k, exp, lot = float(r.strike), str(r.expiry)[:10], int(r.lot)
        tick = 0.05 if b.day0 < TICK_CHANGE else 0.01
        out = {"symbol": b.symbol, "day0": b.day0, "side": b.side, "lot": lot, "strike": k, "expiry": exp,
               "half": HALF(b.day0), "entry_A": b.entry_A, "entry_B": b.entry_B, "A_v11": b.A_v11_net,
               "B_v11": b.B_v11_net, "A_v10": b.A_v10_net, "B_v10": b.B_v10_net}
        p = prev_of(cal, b.day0)
        bp = bhav.day(p) if p else None
        cp = bp["opt"].get((b.symbol, exp, k, b.side)) if bp else None
        sp = bp["spot"].get(b.symbol) if bp else None
        o = eq.oc(b.symbol, b.day0, p) if p else None
        vp = iv(b.side, cp, sp, k, years(p, exp)) if cp and sp else None
        if not (vp and o):
            rows.append({**out, "no_L": "no_iv" if not vp else "no_eod2"})
            continue
        s_open = sp * o[0] / o[2]
        out.update({"no_L": "", "iv_prev": round(vp, 4), "s_open": round(s_open, 2), "opt_prev_close": cp})
        m = by[(b.symbol, b.day0, b.side, k)]
        m = m[(m["t"] >= "09:15") & (m["t"] <= "15:19")]
        for name, (cc, mult, mid) in variants.items():
            raw = bs(b.side, s_open, k, years(b.day0, exp), vp * cc) * mult
            lim = math.floor(raw / tick + 1e-9) * tick
            out[f"{name}_L"] = round(lim, 2)
            f = fill_sim(m, lim, tick, mid) if lim >= 0.05 else None
            if f is None:
                out[f"{name}_filled"] = False
                continue
            t_fill, px = f
            out.update({f"{name}_filled": True, f"{name}_t": t_fill, f"{name}_fill": px,
                        **{f"{name}_{x}": v for x, v in exits(m, b.side, lot, px, tick, t_fill).items()}})
        rows.append(out)
    return pd.DataFrame(rows)


def line(g: pd.DataFrame, net: str, prem: pd.Series, **lab) -> dict:
    if g.empty:
        return {**lab, "n": 0}
    pct = g[net] / prem.loc[g.index] * 100
    return {**lab, "n": len(g), "win %": round((g[net] > 0).mean() * 100, 1), "mean %": round(pct.mean(), 2),
            "median %": round(pct.median(), 1), "total Rs": round(g[net].sum()),
            "t": clustered_t(pct, g["day0"]) if len(g) > 1 else None}


# ---------- test 2 ----------
def test2(bhav: Bhav, cal: list[str], eq: Eq) -> pd.DataFrame:
    a = pd.read_csv(RES / "S1_v10_trades_2022_24.csv").assign(window="2022-24")
    b = pd.read_csv(RES / "S1_v10_trades.csv").assign(window="2025-26")
    t = pd.concat([a, b], ignore_index=True)
    t = t[(t["entry"] == "open") & (t["e1_excluded"].fillna("") == "")]
    rows = []
    for r in t.itertuples():
        p = prev_of(cal, r.day0)
        o = eq.oc(r.symbol, r.day0, p) if p else None
        if not o or not (o[0] > 0 and o[1] > 0):
            rows.append({"symbol": r.symbol, "day0": r.day0, "side": r.side, "window": r.window, "excluded": "no_eod2"})
            continue
        sign = -1 if r.side == "PE" else 1
        gross = sign * (o[1] / o[0] - 1) * 100
        s_open = float(r.spot_prev_close) * o[0] / o[2] if r.spot_prev_close == r.spot_prev_close else math.nan
        net = gross - FUT_COST
        rows.append({"symbol": r.symbol, "day0": r.day0, "side": r.side, "window": r.window, "excluded": "",
                     "gross_pct": round(gross, 3), "net_pct": round(net, 3), "lot": int(r.lot),
                     "lot_value_rs": round(s_open * int(r.lot)), "net_rs_per_lot": round(net / 100 * s_open * int(r.lot)),
                     "option_e1_net_pct": r.e1_net_pct, "after_fut_preopen": r.day0 >= FUT_PREOPEN})
    return pd.DataFrame(rows)


def st2(g: pd.DataFrame, **lab) -> dict:
    if g.empty:
        return {**lab, "n": 0}
    return {**lab, "n": len(g), "win %": round((g["net_pct"] > 0).mean() * 100, 1), "mean net %": round(g["net_pct"].mean(), 3),
            "median net %": round(g["net_pct"].median(), 3), "t": clustered_t(g["net_pct"], g["day0"]) if len(g) > 1 else None,
            "mean Rs per lot": round(g["net_rs_per_lot"].mean()), "total Rs (1 lot each)": round(g["net_rs_per_lot"].sum()),
            "median lot value Rs": round(g["lot_value_rs"].median())}


def main() -> None:
    cal, bhav, eq = sessions(), Bhav(CACHE), Eq()
    c, nc, ntot = calibrate(bhav, cal)
    t1 = test1(bhav, cal, eq, c)
    t1.to_csv(RES / "S1_fade_preopen_entry_trades.csv", index=False)
    t2 = test2(bhav, cal, eq)
    t2.to_csv(RES / "S1_fade_preopen_future_trades.csv", index=False)
    parts = ["# S1 fade · buying at the open: a fair-price limit (option) and the stock future's pre-open\n",
             "Pre-registered: strategies/S1_fade_preopen_entry.md (research summary there). Descriptive; nothing live "
             "changes. t is date-clustered; real only with t >= 2 and the same sign in both halves/windows.\n",
             f"## Calibration\n\nc (day-0 close IV / previous close IV, median) = **{c:.3f}** from {nc} of {ntot} 2022-24 "
             f"fade trades (day 0 before {CALIB_END}).\n"]
    ok = t1[t1["no_L"].fillna("") == ""]
    prem = {e: t1[f"entry_{e}"] * t1["lot"] for e in "AB"}
    rows = []
    for name in ("main", "c=1", "Lx0.90", "Lx1.10", "mid fill"):
        f = ok[ok[f"{name}_filled"] == True]                                  # noqa: E712
        pl = f[f"{name}_fill"] * f["lot"]
        for h in ("all", "Oct24-Oct25", "Nov25-Sep26"):
            g = f if h == "all" else f[f["half"] == h]
            lab = {"variant": name, "period": h, "fills": f"{len(g)} / {len(ok) if h == 'all' else (ok['half'] == h).sum()}"}
            rows.append(line(g, f"{name}_v11", pl, **lab, entry="limit L"))
            if name == "main":
                rows.append(line(g, "B_v11", prem["B"], **lab, entry="B 09:16 (same trades)"))
                rows.append(line(g, "A_v11", prem["A"], **lab, entry="A opening print (same trades)"))
    parts.append(f"## Test 1 · limit at a fair price, v11 exit ({len(ok)} of {len(t1)} trades got an L)\n\n" + md(pd.DataFrame(rows)))
    f = ok[ok["main_filled"] == True]                                          # noqa: E712
    v10 = [line(f, "main_v10", f["main_fill"] * f["lot"], exit="v10", entry="limit L"),
           line(f, "B_v10", prem["B"], exit="v10", entry="B (same trades)")]
    parts.append("### Test 1, v10 exit (main variant)\n\n" + md(pd.DataFrame(v10)))
    nf = ok[ok["main_filled"] != True]                                         # noqa: E712
    parts.append("### The trades the limit did not fill (what B did on them)\n\n" +
                 md(pd.DataFrame([line(nf, "B_v11", prem["B"], group="not filled", entry="B v11")])))
    ratio = (f["main_fill"] / f["entry_B"] - 1) * 100
    lvsA = (ok["main_L"] / ok["entry_A"] - 1) * 100
    parts.append("### Prices\n\n" + md(pd.DataFrame([
        {"measure": "fill vs B entry, median %", "value": round(ratio.median(), 1)},
        {"measure": "fill below B entry, share %", "value": round((ratio < 0).mean() * 100, 1)},
        {"measure": "L vs the opening print A, median %", "value": round(lvsA.median(), 1)},
        {"measure": "filled in the 09:15 candle, share %", "value": round((f["main_t"] == "09:15").mean() * 100, 1)},
        {"measure": "no L (no IV / no eod2)", "value": int((t1["no_L"].fillna("") != "").sum())}])))
    x = t2[t2["excluded"] == ""]
    rows2 = [st2(x, group="all"), st2(x[x["side"] == "PE"], group="puts -> sell future"),
             st2(x[x["side"] == "CE"], group="calls -> buy future"),
             st2(x[x["window"] == "2022-24"], group="2022-24"), st2(x[x["window"] == "2025-26"], group="2025-26"),
             st2(x[x["after_fut_preopen"]], group=f"from {FUT_PREOPEN} (futures pre-open live)")]
    parts.append(f"## Test 2 · stock future at the pre-open price, open -> close, net of {FUT_COST} %\n\n" + md(pd.DataFrame(rows2))
                 + f"\n\n{(t2['excluded'] != '').sum()} trades without eod2 prices. Proxy: the stock's own open and close.\n")
    text = "\n".join(parts)
    (RES / "S1_fade_preopen_entry.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
