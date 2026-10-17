"""S1 v10 fade · descriptive backtest 2025-2026 (numbers only): the same trades under the same-day exit (E1) and under
the carried-trade rule (E2).

    python -m scanner.backtest_s1_v10

strategies/S1_v10_backtest_2025_26.md pre-registers every choice. Signals: results filings whose day 0 is in
2025-01-01 .. 2026-09-25; strong numbers -> a bought put, weak numbers -> a bought call (scanner/fade_live.classify).
The option: current monthly expiry with >= 2 sessions left (else the next), from the strike nearest the previous
close walking away from the money to the first with >= 50 contracts on day 0, fill >= Rs 2 and one lot at Rs 600-8,000.
Entry: day 0's open + 1 tick (side report: premium VWAP + 1 tick). E1: day 0's close - 1 tick. E2: on each close from
day 0, close <= 0.80 x entry (stop), close <= 0.75 x the highest close since entry (trail) or T-1, at that close - 1 tick.
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

import pandas as pd

from . import backtest_s1_v4 as v4
from .backtest_cheap_options import sessions_to
from .build import ROOT
from .option_engine import TICK, premium_vwap
from .stats import clustered_t

log = logging.getLogger("backtest_s1_v10")

START, END = "2025-01-01", "2026-09-25"
BAND, MIN_CONTRACTS, MIN_PREMIUM, WALK_MAX = (600.0, 8000.0), 50, 2.0, 15
STOP, TRAIL, T_MINUS, MIN_LEFT = 0.80, 0.75, 1, 2
ENTRIES = ("open", "vwap")
PERIODS = (("2025 H1", "2025-01-01", "2025-06-30"), ("2025 H2", "2025-07-01", "2025-12-31"),
           ("2026 H1", "2026-01-01", "2026-06-30"), ("2026 Q3", "2026-07-01", "2026-09-30"))


@dataclass(frozen=True)
class Q:
    """One option strike on day 0."""
    strike: float
    contracts: float
    turnover: float
    lot: int
    open: float
    close: float
    low: float | None = None
    high: float | None = None


# ---------------------------------------------------------------- rules (pure)
def start_strike(strikes, spot: float, side: str) -> float | None:
    """The listed strike nearest spot; a tie: the lower for calls, the higher for puts."""
    ks = sorted(set(float(k) for k in strikes))
    return min(ks, key=lambda k: (abs(k - spot), -k if side == "PE" else k)) if ks and spot else None


def entry_price(q: Q, entry: str) -> tuple[float, str] | None:
    """Day 0's fill: the open + 1 tick ("open"), or the premium VWAP (else the close) + 1 tick ("vwap")."""
    if not q.contracts >= MIN_CONTRACTS:                      # also catches NaN
        return None
    if entry == "open":
        base, src = q.open, "open"
    else:
        v = premium_vwap(q.turnover, q.contracts, q.lot, q.strike, q.low, q.high)
        base, src = (v, "vwap") if v is not None else (q.close, "close")
    if base is None or (isinstance(base, float) and math.isnan(base)) or base <= 0:
        return None
    return round(base + TICK, 2), src


def walk(strikes, spot: float, side: str, quotes: dict[float, Q], entry: str):
    """From the start strike away from the money (down for puts, up for calls), at most 15 strikes: the first with a
    fill (>= 50 contracts), a fill >= Rs 2 and one lot within Rs 600-8,000. Returns (quote, fill, source, strikes
    walked past) or the reason there is none."""
    ks = sorted(set(float(k) for k in strikes))
    k0 = start_strike(ks, spot, side)
    if k0 is None:
        return "no_strike_or_expiry"
    i = ks.index(k0)
    path = (ks[: i + 1][::-1] if side == "PE" else ks[i:])[:WALK_MAX]
    for n, k in enumerate(path):
        q = quotes.get(k)
        if q is None or not q.lot > 0:
            continue
        f = entry_price(q, entry)
        if f is None:
            continue
        px, src = f
        if px < MIN_PREMIUM:
            return "premium_below_2"
        cost = px * q.lot
        if cost < BAND[0]:
            return "walk_below_band"
        if cost > BAND[1]:
            continue
        return q, px, src, n
    return "walk_no_liquid_strike_in_band"


def carry_step(close: float, fill: float, peak: float, to_expiry: int) -> tuple[float, str | None]:
    """One close under the carried-trade rule: (the new highest close, the exit reason or None). The entry price is
    the first value of the peak; stop first, then trail, then T-1."""
    peak = max(peak, close)
    if close <= STOP * fill:
        return peak, "stop"
    if close <= TRAIL * peak:
        return peak, "trail"
    if to_expiry <= T_MINUS:
        return peak, "t_minus_1"
    return peak, None


def net_of(opt: str, entry: float, exit_: float, qty: int, slip: float) -> tuple[float, float, float]:
    """(charges, slippage, net) for one bought option held to a sale."""
    from server import charges as ch
    c = ch.leg(opt, "BUY", qty, entry)["total"] + (ch.leg(opt, "SELL", qty, exit_)["total"] if exit_ > 0 else 0.0)
    s = slip * qty * (entry + exit_)
    return round(c, 2), round(s, 2), round((exit_ - entry) * qty - c - s, 2)


def period_of(day: str) -> str:
    for name, a, b in PERIODS:
        if a <= day <= b:
            return name
    return "other"


# ---------------------------------------------------------------- data
class Bhav:
    """Per session from the cached F&O bhavcopy: option closes, the STO chain, spot, future closes, option stocks."""

    def __init__(self, cache: Path):
        self.cache, self._c = cache, {}

    def day(self, d: str) -> dict | None:
        if d in self._c:
            return self._c[d]
        f = self.cache / f"fo_bhavcopy_{d.replace('-', '')}.csv"
        if not f.exists():
            return None
        b = pd.read_csv(f, usecols=lambda c: c in ("TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric",
                                                    "UndrlygPric"))
        b["XpryDt"] = b["XpryDt"].astype(str).str[:10]
        b["TckrSymb"] = b["TckrSymb"].astype(str).str.strip()
        sto = b[b["FinInstrmTp"] == "STO"]
        fut = b[b["FinInstrmTp"] == "STF"].sort_values("XpryDt")
        spot = {}
        if "UndrlygPric" in b.columns:
            u = sto[sto["UndrlygPric"] > 0].drop_duplicates("TckrSymb")
            spot = dict(zip(u["TckrSymb"], u["UndrlygPric"].astype(float)))
        for s, c in zip(fut["TckrSymb"], fut["ClsPric"]):
            spot.setdefault(s, float(c))
        day = {"opt": dict(zip(zip(sto["TckrSymb"], sto["XpryDt"], sto["StrkPric"].astype(float), sto["OptnTp"]),
                               sto["ClsPric"].astype(float))),
               "futs": dict(zip(zip(fut["TckrSymb"], fut["XpryDt"]), fut["ClsPric"].astype(float))),
               "chain": {s: g for s, g in sto.groupby("TckrSymb")}, "spot": spot, "syms": set(sto["TckrSymb"])}
        if len(self._c) > 40:
            self._c.pop(next(iter(self._c)))
        self._c[d] = day
        return day


def quotes_of(p: pd.DataFrame, sym: str, exp: str, side: str) -> dict[float, Q]:
    rows = p[(p["TckrSymb"].astype(str).str.strip() == sym) & (p["XpryDt"].astype(str).str[:10] == exp)
             & (p["OptnTp"] == side)]
    num = lambda v: float(v) if v == v else math.nan                    # noqa: E731
    return {float(r["StrkPric"]): Q(float(r["StrkPric"]), num(r["TtlTradgVol"]), num(r["TtlTrfVal"]),
                                    int(r["NewBrdLotQty"]) if r["NewBrdLotQty"] == r["NewBrdLotQty"] else 0,
                                    num(r["OpnPric"]), num(r["ClsPric"]), num(r["LwPric"]), num(r["HghPric"]))
            for _, r in rows.iterrows()}


# ---------------------------------------------------------------- the simulation
def signals(results, fin: dict, sessions: list[str], bhav: Bhav, funnel: Counter) -> list[dict]:
    """One signal per stock and day 0 (the earliest filing), classified by the numbers as filed."""
    from .backtest_s1_v2 import day0_index
    from .event_screens import num_or_none
    from .fade_live import classify
    from .peak_study import result_quality
    seen, out = set(), []
    for sym, d, t in sorted(results, key=lambda r: (r[1], r[2] or "99:99")):
        i = day0_index(sessions, d, t)
        if i is None or i < 1 or not START <= sessions[i] <= END or (sym, i) in seen:
            continue
        seen.add((sym, i))
        funnel["results_filings"] += 1
        prev = bhav.day(sessions[i - 1])
        if prev is None or sym not in prev["syms"]:
            funnel["no_options_in_previous_bhavcopy"] += 1
            continue
        q = result_quality(fin, sym, d)
        if any(num_or_none(q.get(k)) is None for k in ("net_profit_yoy", "net_profit_qoq", "revenue_yoy")):
            funnel["numbers_missing"] += 1
            continue
        side = classify(q)
        if side is None:
            funnel["neither_strong_nor_weak"] += 1
            continue
        out.append({"symbol": sym, "i": i, "filed": d, "side": side, "np_yoy": num_or_none(q["net_profit_yoy"]),
                    "np_qoq": num_or_none(q["net_profit_qoq"]), "rev_yoy": num_or_none(q["revenue_yoy"])})
    return sorted(out, key=lambda s: (s["i"], s["symbol"]))


def simulate(sigs: list[dict], entry: str, sessions: list[str], bhav: Bhav, prices, category,
             stock: dict[str, pd.Series], stock_oc: dict, funnel: Counter) -> pd.DataFrame:
    from .fade_live import choose_expiry
    cal = [date.fromisoformat(d) for d in sessions]
    rows = []
    for s in sigs:
        sym, i, side = s["symbol"], s["i"], s["side"]
        d0 = sessions[i]
        prev, b0 = bhav.day(sessions[i - 1]), bhav.day(d0)
        chain = prev["chain"].get(sym)
        spot = prev["spot"].get(sym)
        exp = choose_expiry(chain["XpryDt"][chain["OptnTp"] == side], cal[i],
                            lambda t, e: sessions_to(cal, t, date.fromisoformat(e))) if chain is not None else None
        if exp is None or not spot:
            funnel["no_strike_or_expiry"] += 1
            continue
        p = prices(d0)
        if p is None or b0 is None:
            funnel["no_day0_prices"] += 1
            continue
        strikes = chain.loc[(chain["XpryDt"] == exp) & (chain["OptnTp"] == side), "StrkPric"]
        w = walk(strikes, spot, side, quotes_of(p, sym, exp, side), entry)
        if isinstance(w, str):
            funnel[w] += 1
            continue
        q, fill, src, walked = w
        cat, _ = category(sym, d0)
        slip = v4.SLIPPAGE.get(cat, v4.SLIPPAGE["unknown"])
        path = _path(sym, side, exp, q.strike, fill, i, sessions, cal, bhav, stock.get(sym))
        row = {"entry": entry, "side": side, "symbol": sym, "filed": s["filed"], "day0": d0, "category": cat,
               "np_yoy": s["np_yoy"], "np_qoq": s["np_qoq"], "rev_yoy": s["rev_yoy"], "expiry": exp,
               "spot_prev_close": round(float(spot), 2), "strike": q.strike, "strikes_walked": walked,
               "contracts_day0": q.contracts, "lot": q.lot, "entry_price": fill, "entry_source": src,
               "premium_rs": round(fill * q.lot, 2), "period": period_of(d0),
               "stock_oc_signed_pct": stock_oc.get((sym, d0))}
        for name in ("e1", "e2"):
            x = path[name]
            row[f"{name}_excluded"] = x["excluded"]
            row[f"{name}_exit_date"], row[f"{name}_reason"] = x["date"], x["reason"]
            row[f"{name}_exit_price"], row[f"{name}_held"] = x["price"], x["held"]
            if not x["excluded"]:
                c, sl, net = net_of(side, fill, x["price"], q.lot, slip)
                row[f"{name}_net"], row[f"{name}_net_pct"] = net, round(net / (fill * q.lot) * 100, 3)
        rows.append(row)
        funnel["traded"] += 1
    return pd.DataFrame(rows)


def _path(sym: str, side: str, exp: str, k: float, fill: float, i0: int, sessions: list[str], cal: list[date],
          bhav: Bhav, stock: pd.Series | None) -> dict:
    """E1 (day 0's close) and E2 (the carried-trade rule on each close from day 0) over the same closes."""
    e1 = {"excluded": "", "date": None, "reason": "same_day", "price": None, "held": 0}
    e2 = {"excluded": "", "date": None, "reason": None, "price": None, "held": None}
    fut0 = stock0 = None
    peak, e2_open = fill, True
    expiry = date.fromisoformat(exp)
    for j in range(i0, len(sessions)):
        b = bhav.day(sessions[j])
        if b is None:
            continue
        c = b["opt"].get((sym, exp, k, side))
        if c is None:
            gone = {"excluded": "contract_changed", "date": sessions[j], "reason": None, "price": None, "held": j - i0}
            if j == i0:
                return {"e1": gone, "e2": dict(gone)}
            if e2_open:
                e2 = gone
            break
        f = b["futs"].get((sym, exp))
        px = float(stock.get(sessions[j], math.nan)) if stock is not None else math.nan
        if fut0 is None:
            fut0, stock0 = f, px
        elif f and fut0 and stock0 and not (math.isnan(px) or math.isnan(stock0)) and \
                abs((f / fut0) / (px / stock0) - 1) > v4.CA_TOLERANCE:
            if e2_open:
                e2 = {"excluded": "price_adjusted", "date": sessions[j], "reason": None, "price": None, "held": j - i0}
            break
        sell = max(0.0, round(c - TICK, 2))
        if j == i0:
            e1.update(date=sessions[j], price=sell)
        if e2_open:
            to_exp = sessions_to(cal, cal[j], expiry) if expiry <= cal[-1] else 99
            peak, why = carry_step(c, fill, peak, to_exp)
            if why:
                e2.update(date=sessions[j], reason=why, price=sell, held=j - i0)
                e2_open = False
                break
    if e2_open and not e2["excluded"]:
        e2.update(excluded="no_exit_in_data")
    if e1["price"] is None:
        e1["excluded"] = "no_day0_close"
    return {"e1": e1, "e2": e2}


# ---------------------------------------------------------------- summaries
def metrics(g: pd.DataFrame, ex: str) -> dict:
    g = g[g[f"{ex}_excluded"].fillna("") == ""]
    r = g[f"{ex}_net_pct"].astype(float)
    out = {"n": len(g), "hit_pct": round((r > 0).mean() * 100, 1) if len(g) else None,
           "mean_pct": round(r.mean(), 2) if len(g) else None, "median_pct": round(r.median(), 2) if len(g) else None,
           "p10": round(r.quantile(0.1), 1) if len(g) else None, "p90": round(r.quantile(0.9), 1) if len(g) else None,
           "t": clustered_t(r, g["day0"]) if len(g) > 1 else None,
           "total_rs": round(g[f"{ex}_net"].sum()) if len(g) else None,
           "avg_lot_rs": round(g["premium_rs"].mean()) if len(g) else None,
           "held_sessions": round(g[f"{ex}_held"].astype(float).mean(), 1) if len(g) else None}
    if ex == "e2":
        for why in ("stop", "trail", "t_minus_1"):
            out[f"exit_{why}_pct"] = round((g["e2_reason"] == why).mean() * 100, 1) if len(g) else None
    return out


def paired(t: pd.DataFrame) -> pd.DataFrame:
    return t[(t["e1_excluded"].fillna("") == "") & (t["e2_excluded"].fillna("") == "")]


def table(t: pd.DataFrame, by: str | None, groups) -> pd.DataFrame:
    rows = []
    for gname in groups:
        g = t if by is None else t[t[by] == gname]
        for ex, label in (("e1", "E1 same day"), ("e2", "E2 carry rule")):
            rows.append({"group": gname if by else "all", "exit": label, **metrics(g, ex)})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v10 fade: descriptive backtest 2025-2026 (numbers only)")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from . import amfi
    from .backtest_s1_v2 import md
    from .equity import load_symbol
    from .events.store import Store
    from .financials import load as load_fin
    from .nse_fo import BhavcopyUnavailable, download_fo_prices
    from .stats import clustered_t as ct

    sessions = sorted(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}" for p in a.cache_dir.glob("fo_bhavcopy_*.csv"))
    sessions = [d for d in sessions if d <= END]
    bhav, funnel = Bhav(a.cache_dir), Counter()
    with Store() as st:
        results = [(e["symbol"], e["event_date"], e.get("event_time")) for e in st.all_of_type("results")]
    sigs = signals(results, load_fin(), sessions, bhav, funnel)
    log.info("signals: %d (%s)", len(sigs), dict(funnel))
    stock, stock_oc = {}, {}
    for sym in sorted({s["symbol"] for s in sigs}):
        try:
            f = load_symbol(sym, a.eod2_dir)
            f.index = f.index.strftime("%Y-%m-%d")
            f = f[~f.index.duplicated(keep="last")]
            stock[sym] = f["Close"]
            for s in (x for x in sigs if x["symbol"] == sym):
                d0 = sessions[s["i"]]
                if d0 in f.index and f.loc[d0, "Open"] > 0:
                    mv = (f.loc[d0, "Close"] / f.loc[d0, "Open"] - 1) * 100
                    stock_oc[(sym, d0)] = round(float(-mv if s["side"] == "PE" else mv), 3)
        except Exception as exc:  # noqa: BLE001
            log.info("%s: no eod2 (%s)", sym, exc)
    _px: dict[str, pd.DataFrame | None] = {}

    def prices(d: str):
        if d not in _px:
            try:
                _px[d] = download_fo_prices(date.fromisoformat(d), a.cache_dir)
            except (BhavcopyUnavailable, OSError, ValueError) as exc:
                log.warning("prices %s: %s", d, exc)
                _px[d] = None
        return _px[d]

    cats = amfi.load()
    frames, funnels = [], {}
    for entry in ENTRIES:
        f = Counter(signals=len(sigs))
        frames.append(simulate(sigs, entry, sessions, bhav, prices, cats.category_on, stock, stock_oc, f))
        funnels[entry] = f
        log.info("%s: %s", entry, dict(f))
    trades = pd.concat(frames, ignore_index=True)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(a.out_dir / "S1_v10_trades.csv", index=False)

    prim = trades[trades["entry"] == "open"]
    pr = paired(prim)
    periods = [p[0] for p in PERIODS]
    excl = pd.DataFrame([{"entry": e, **{f"{ex}_{k}": int(v) for ex in ("e1", "e2")
                                         for k, v in trades[trades["entry"] == e][f"{ex}_excluded"].fillna("")
                                         .replace("", "none").value_counts().items()}} for e in ENTRIES]).fillna(0)
    oc = pr["stock_oc_signed_pct"].dropna().astype(float)
    side_oc = pd.DataFrame([{"side": sd, "n": int(len(g)), "stock_open_to_close_signed_mean_pct":
                             round(g.mean(), 3) if len(g) else None, "t": ct(g, pr.loc[g.index, "day0"]) if len(g) > 1 else None}
                            for sd, g in ((sd, pr[pr["side"] == sd]["stock_oc_signed_pct"].dropna().astype(float))
                                          for sd in ("PE", "CE"))] +
                           [{"side": "all", "n": len(oc), "stock_open_to_close_signed_mean_pct": round(oc.mean(), 3),
                             "t": ct(oc, pr.loc[oc.index, "day0"]) if len(oc) > 1 else None}])
    fun = pd.DataFrame([{"entry": k, **dict(f)} for k, f in funnels.items()]).fillna(0)
    head = ("Descriptive only: no gate, no promotion, no rule change follows. **Not out of sample**: 2025-01-01 onward is "
            "the holdout S1 v8 already used, the fade pattern was seen on 2021-2026 in S1 v9, and the E2 exit was chosen "
            "after the eight carried trades were seen. Entry is day 0's open + 1 tick; the live fill is the ask at the "
            "first poll that fits, later and dearer. The live liquidity test (two-sided quote, spread <= 10 %) is a "
            ">= 50 contract count here.")
    text = "\n".join([
        f"# S1 v10 fade · descriptive backtest {START} .. {END}\n\nNumbers only. strategies/S1_v10_backtest_2025_26.md.\n\n{head}\n",
        "Net % of premium after charges and slippage. Headline tables use the trades valid under both exits "
        f"({len(pr)} of {len(prim)} traded; exclusions below). t is date-clustered on day 0.\n",
        "## All trades\n\n" + md(table(pr, None, ["all"])),
        "## Puts (strong numbers) and calls (weak numbers)\n\n" + md(table(pr, "side", ["PE", "CE"])),
        "## By period (day 0)\n\n" + md(table(pr, "period", periods)),
        "## Side report: entry at day 0's premium VWAP + 1 tick\n\n" + md(table(paired(trades[trades["entry"] == "vwap"]),
                                                                                  None, ["all"])),
        "## The stock's day-0 open to close, signed (positive = it moved against the headline, as the fade bets)\n\n"
        + md(side_oc),
        "## Exclusions by exit (counted; \"none\" = valid)\n\n" + md(excl),
        "## Signals removed, in order\n\n" + md(fun),
    ])
    (a.out_dir / "S1_v10_backtest_report.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
