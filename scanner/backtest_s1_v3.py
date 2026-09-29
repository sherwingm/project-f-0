"""S1 v3 · strength score, one trade a day, as strategies/S1_v3_strength_score.md pre-registers it (numbers only).

    python -m scanner.backtest_s1_v3        # the diagnostic on the test window; stops if the 20-session t < 1.5

Needs data/results/S1_v3_model_oos.csv (scanner.model.oos_predictions over 2021-2024: every quarter predicted
by a model trained only on earlier, purged rows).
"""
from __future__ import annotations

import argparse
import bisect
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest_s1_v2 import BIAS, Market, _ret, compound, day0_index, load_inputs, md, option_universe
from .build import ROOT
from .nse_fo import fo_metrics
from .option_engine import TEST_PERIODS, monthly, split_statement, window
from .results_coverage import benchmark_returns
from .stats import clustered_t

log = logging.getLogger("backtest_s1_v3")

# ---------------------------------------------------------------- the pre-registered parameters
MODEL_POINTS, TOP_DECILE = 3, 0.9
SECTOR_BOTH, SECTOR_ONE = 2, 1
EVENT_POINTS, EVENT_WINDOW, RESULTS_ABS = 2, 5, 2.0
VOLUME_POINTS, VOLUME_RATIO, VOLUME_WINDOW = 1, 1.5, 20
LIQ_CONTRACTS, LIQ_OI_LOTS = 100, 50
MAX_PER_DAY, MIN_SCORE = 3, 1
HOLD, COOLDOWN = 20, 10                          # diagnostic: a selection blocks the stock for t+1 .. t+31
HORIZONS, STOP_T = (5, 20), 1.5
CLOSE = (15, 30)                                 # an order / rating / deal filed before 15:30 counts that session
OOS_PATH = ROOT / "data" / "results" / "S1_v3_model_oos.csv"


# ---------------------------------------------------------------- rules (pure, tested one by one)
def model_points(p_up: float, p_down: float, cut_up: float, cut_down: float) -> tuple[int, int]:
    """3 points to long if p_up is in the day's top decile, to short if p_down is."""
    ok = lambda p, c: p is not None and c is not None and not (math.isnan(p) or math.isnan(c)) and p >= c
    return (MODEL_POINTS if ok(p_up, cut_up) else 0), (MODEL_POINTS if ok(p_down, cut_down) else 0)


def sector_points(rel21: float | None, rel63: float | None) -> tuple[int, int]:
    """2 points when both relative returns agree with the direction, 1 when one does."""
    vals = [v for v in (rel21, rel63) if v is not None and not math.isnan(v)]
    up, down = sum(v > 0 for v in vals), sum(v < 0 for v in vals)
    pts = lambda k: SECTOR_BOTH if k == 2 else SECTOR_ONE if k == 1 else 0
    return pts(up), pts(down)


def event_session(cal: list[str], event_date: str, event_time: str | None) -> int | None:
    """The session an order win / rating / deal counts from: its own session if filed before 15:30 or without a
    time (end-of-day files); otherwise the next session."""
    i = bisect.bisect_left(cal, event_date)
    same = i < len(cal) and cal[i] == event_date
    if same:
        if not event_time:
            return i
        try:
            h, m = (int(x) for x in str(event_time).split(":")[:2])
        except ValueError:
            h, m = 99, 0
        if (h, m) < CLOSE:
            return i
    j = bisect.bisect_right(cal, event_date)
    return j if j < len(cal) else None


def event_points(directions: set[int]) -> tuple[int, int]:
    return (EVENT_POINTS if 1 in directions else 0), (EVENT_POINTS if -1 in directions else 0)


def volume_points(vol_ratio: float, oi_change: float | None, day_return: float) -> tuple[int, int]:
    """1 point: volume ratio > 1.5 and futures OI up, to long on an up close (long buildup), to short on a down
    close (short buildup)."""
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (vol_ratio, oi_change, day_return)):
        return 0, 0
    if not (vol_ratio > VOLUME_RATIO and oi_change > 0):
        return 0, 0
    return (VOLUME_POINTS if day_return > 0 else 0), (VOLUME_POINTS if day_return < 0 else 0)


def direction(long_pts: int, short_pts: int) -> tuple[int, int] | None:
    """(+1 long / -1 short, total); a tie is no trade."""
    if long_pts == short_pts:
        return None
    return (1, long_pts) if long_pts > short_pts else (-1, short_pts)


def atm_strike(strikes, spot: float) -> float | None:
    ks = sorted(set(strikes))
    return min(ks, key=lambda k: (abs(k - spot), -k)) if ks and spot else None


def liquid(contracts: float, oi: float, lot: int) -> bool:
    return lot > 0 and contracts >= LIQ_CONTRACTS and oi >= LIQ_OI_LOTS * lot


def select(cands: list[dict], passes) -> list[dict]:
    """The top score among candidates with score >= 1 whose liquidity passes (a failure scores 0); every stock
    tied at that score, up to 3, ordered by the model probability in the direction, then symbol."""
    order = sorted(cands, key=lambda c: (-c["score"], -(c["p_dir"] if c["p_dir"] == c["p_dir"] else -1.0), c["symbol"]))
    out, top = [], None
    for c in order:
        if c["score"] < MIN_SCORE or (top is not None and c["score"] < top):
            break
        if not passes(c):
            continue
        top = c["score"]
        out.append(c)
        if len(out) == MAX_PER_DAY:
            break
    return out


# ---------------------------------------------------------------- inputs
@dataclass
class Signals:
    events: dict[str, list[tuple[int, int]]] = field(default_factory=dict)    # symbol -> [(session, direction)]
    model: dict[str, dict[str, tuple[float, float]]] = field(default_factory=dict)   # day -> symbol -> (p_up, p_down)
    volume: dict[str, np.ndarray] = field(default_factory=dict)


def tier1_events(m: Market, store_rows: dict[str, list[dict]]) -> dict[str, list[tuple[int, int]]]:
    """symbol -> [(session, direction)] of the pre-registered tier-1 events."""
    out: dict[str, list[tuple[int, int]]] = {}
    for e in store_rows["results"]:
        sym = e["symbol"]
        i = day0_index(m.cal, e["event_date"], e.get("event_time"))
        if i is None or i < 1 or sym not in m.close:
            continue
        br, _ = benchmark_returns(m, sym)
        ab = (_ret(m.close[sym], i, 1) - br[i]) * 100
        if not math.isnan(ab) and abs(ab) >= RESULTS_ABS:
            out.setdefault(sym, []).append((i, 1 if ab > 0 else -1))
    for kind, keep in (("order_win", lambda e: e.get("bucket") == "major"),
                       ("rating", lambda e: e.get("subtype") in ("upgrade", "downgrade")),
                       ("block_deal", lambda e: e.get("subtype") in ("fund_buy", "fund_sell"))):
        for e in store_rows[kind]:
            if e.get("tier") != 1 or not keep(e) or not e.get("direction"):
                continue
            i = event_session(m.cal, e["event_date"], e.get("event_time"))
            if i is not None:
                out.setdefault(e["symbol"], []).append((i, int(np.sign(e["direction"]))))
    return out


def load_model(path: Path = OOS_PATH) -> dict[str, dict[str, tuple[float, float]]]:
    df = pd.read_csv(path)
    return {d: dict(zip(g["symbol"], zip(g["p_up"], g["p_down"]))) for d, g in df.groupby("day")}


def volume_ratio(vol: np.ndarray) -> np.ndarray:
    v = pd.Series(vol)
    return (v / v.rolling(VOLUME_WINDOW).mean().shift(1)).to_numpy()


# ---------------------------------------------------------------- the diagnostic
def run_selection(m: Market, sig: Signals, bhav, ban: dict[str, set[str]], start: str, end: str,
                  lots_fallback: dict[str, int] | None = None) -> pd.DataFrame:
    """Each session's selection under the diagnostic's holding assumption, with each h-session signed excess return."""
    lots_fallback = lots_fallback or {}
    blocked_until: dict[str, int] = {}
    rows = []
    days = [d for d in m.cal if start <= d <= end]
    for n, d in enumerate(days, 1):
        i = m.pos[d]
        b = bhav(d)
        if b is None or i + 1 >= len(m.cal):
            continue
        opt = b[b["FinInstrmTp"] == "STO"]
        universe = set(opt["TckrSymb"])
        oi = {r["symbol"]: r.get("oi_change_pct") for r in fo_metrics(b).to_dict("records")}
        probs = sig.model.get(d, {})
        ups = np.array([p[0] for p in probs.values()])
        downs = np.array([p[1] for p in probs.values()])
        cut_up = float(np.quantile(ups, TOP_DECILE)) if len(ups) else math.nan
        cut_down = float(np.quantile(downs, TOP_DECILE)) if len(downs) else math.nan
        ban_next = ban.get(m.cal[i + 1], set())
        cands = []
        for sym in universe:
            if sym in ban_next or blocked_until.get(sym, -1) >= i or sym not in m.close:
                continue
            p_up, p_down = probs.get(sym, (math.nan, math.nan))
            mp = model_points(p_up, p_down, cut_up, cut_down)
            st = m.state(sym, i)
            sp = sector_points(st[0], st[1]) if st is not None else (0, 0)
            ev = {dr for s, dr in sig.events.get(sym, ()) if i - EVENT_WINDOW + 1 <= s <= i}
            ep = event_points(ev)
            vr = sig.volume.get(sym)
            vp = volume_points(vr[i] if vr is not None else math.nan, oi.get(sym), _ret(m.close[sym], i, 1))
            dirn = direction(mp[0] + sp[0] + ep[0] + vp[0], mp[1] + sp[1] + ep[1] + vp[1])
            if dirn is None:
                continue
            cands.append({"symbol": sym, "dir": dirn[0], "score": dirn[1], "p_dir": p_up if dirn[0] > 0 else p_down,
                          "model": mp[0] if dirn[0] > 0 else mp[1], "sector": sp[0] if dirn[0] > 0 else sp[1],
                          "event": ep[0] if dirn[0] > 0 else ep[1], "volume": vp[0] if dirn[0] > 0 else vp[1]})
        groups = {s: g for s, g in opt.groupby("TckrSymb", sort=False)} if cands else {}
        spot = _spots(b)

        def passes(c: dict) -> bool:
            g = groups.get(c["symbol"])
            if g is None or c["symbol"] not in spot:
                return False
            g = g[g["OptnTp"] == ("CE" if c["dir"] > 0 else "PE")]
            ahead = [e for e in monthly(g["XpryDt"].astype(str).str[:10]) if e > d]
            if not ahead:
                return False
            g = g[g["XpryDt"].astype(str).str[:10] == ahead[0]]
            k = atm_strike(g["StrkPric"].astype(float), spot[c["symbol"]])
            r = g[g["StrkPric"].astype(float) == k].iloc[0]
            lot = _lot(b, c["symbol"], lots_fallback)
            return liquid(float(r.get("TtlTradgVol", 0) or 0), float(r["OpnIntrst"] or 0), lot)

        for c in select(cands, passes):
            blocked_until[c["symbol"]] = i + 1 + HOLD + COOLDOWN              # selectable again from t+32
            br, kind = benchmark_returns(m, c["symbol"])
            row = {"signal_date": d, **c, "benchmark": kind}
            for h in HORIZONS:
                ex = ((_ret(m.close[c["symbol"]], i + h, h) - compound(br, i + h, h)) * 100
                      if i + h < len(m.cal) else math.nan)
                row[f"ex{h}"] = c["dir"] * ex
            rows.append(row)
        if n % 100 == 0:
            log.info("%s: %d of %d sessions, %d selected", d, n, len(days), len(rows))
    return pd.DataFrame(rows)


def _spots(b: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {}
    if "UndrlygPric" in b.columns:
        u = b[(b["FinInstrmTp"] == "STO") & (b["UndrlygPric"] > 0)].drop_duplicates("TckrSymb")
        out = dict(zip(u["TckrSymb"], u["UndrlygPric"].astype(float)))
    f = b[b["FinInstrmTp"] == "STF"].sort_values("XpryDt")
    for s, c in zip(f["TckrSymb"], f["ClsPric"]):
        out.setdefault(s, float(c))                   # old format: the nearest future's close
    return out


def _lot(b: pd.DataFrame, sym: str, fallback: dict[str, int]) -> int:
    g = b[b["TckrSymb"] == sym]
    if "NewBrdLotQty" in g.columns:
        v = pd.to_numeric(g["NewBrdLotQty"], errors="coerce").dropna()
        if len(v) and v.iloc[0] > 0:
            return int(v.iloc[0])
    oi = [int(x) for x in g["OpnIntrst"].fillna(0) if x > 0]
    return int(np.gcd.reduce(oi)) if oi else fallback.get(sym, 0)


def summarise_diagnostic(sel: pd.DataFrame) -> pd.DataFrame:
    cuts = [("all", "all", sel)]
    cuts += [("score", str(s), sel[sel["score"] == s]) for s in sorted(sel["score"].unique(), reverse=True)]
    cuts += [("direction", n, sel[sel["dir"] == v]) for n, v in (("long", 1), ("short", -1))]
    cuts += [("period", n, sel[sel["signal_date"].between(a, b)]) for n, a, b in TEST_PERIODS]
    out = []
    for by, group, g in cuts:
        for h in HORIZONS:
            x = g[[f"ex{h}", "signal_date"]].dropna()
            v = x[f"ex{h}"]
            out.append({"by": by, "group": group, "horizon": h, "n": len(v),
                        "mean_pct": round(v.mean(), 3) if len(v) else None,
                        "median_pct": round(v.median(), 3) if len(v) else None,
                        "share_positive_pct": round((v > 0).mean() * 100, 2) if len(v) else None,
                        "t_clustered": clustered_t(v, x["signal_date"]) if len(v) > 1 else None})
    return pd.DataFrame(out)


def stop_rule(summary: pd.DataFrame) -> tuple[bool, float | None]:
    """(stop, the overall 20-session clustered t): stop when t < 1.5 (or missing)."""
    r = summary[(summary["by"] == "all") & (summary["horizon"] == 20)]
    t = None if r.empty else r["t_clustered"].iloc[0]
    return (t is None or t < STOP_T), t


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v3 strength score (numbers only)")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from .equity import load_symbol
    from .events.store import Store

    start, end = window()                                          # test window only; the holdout is untouched
    universe = option_universe(a.cache_dir, start, end)
    syms = set().union(*universe.values())
    inp = load_inputs(a.eod2_dir, a.cache_dir, syms)
    m = Market(inp)
    with Store() as st:
        rows = {k: st.all_of_type(k) for k in ("results", "order_win", "rating", "block_deal")}
    vol = {}
    for s in syms:
        try:
            v = load_symbol(s, a.eod2_dir)["Volume"]
        except Exception:  # noqa: BLE001
            continue
        v.index = [x.strftime("%Y-%m-%d") for x in v.index]
        vol[s] = volume_ratio(v[~v.index.duplicated(keep="last")].reindex(m.cal).to_numpy(dtype=float))
    sig = Signals(events=tier1_events(m, rows), model=load_model(), volume=vol)
    cols = ["TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "OpnIntrst", "ChngInOpnIntrst",
            "UndrlygPric", "NewBrdLotQty", "TtlTradgVol"]

    def bhav(d: str):
        f = a.cache_dir / f"fo_bhavcopy_{d.replace('-', '')}.csv"
        return pd.read_csv(f, usecols=lambda c: c in cols) if f.exists() else None

    sel = run_selection(m, sig, bhav, inp.ban, start, end, inp.lots)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    sel.to_csv(a.out_dir / "S1_v3_diagnostic_selections.csv", index=False)
    summary = summarise_diagnostic(sel)
    stop, t20 = stop_rule(summary)
    sessions = [d for d in m.cal if start <= d <= end]
    uni = pd.DataFrame([{"year": y, "stocks": len(set().union(*(v for d, v in universe.items() if d[:4] == y))),
                         "sessions": sum(d[:4] == y for d in universe)} for y in sorted({d[:4] for d in universe})])
    head = "\n".join([
        "# S1 v3 backtest report", "", "Numbers only.", "", "## 1. Header", "",
        f"- {split_statement((sessions[0], sessions[-1]))}",
        f"- Sessions cached: {sum(d in universe for d in sessions)} of {len(sessions)}; missing: "
        f"{', '.join(d for d in sessions if d not in universe) or 'none'}.",
        f"- {BIAS}",
        f"- Model: out-of-sample walk-forward probabilities for {len(sig.model)} sessions "
        f"({min(sig.model)} to {max(sig.model)}); earlier sessions give 0 model points.",
        "- Definition: strategies/S1_v3_strength_score.md (pre-registered).", "",
        "Universe size by year:", "", md(uni)])
    verdict = (f"STOP: overall 20-session date-clustered t = {t20} < {STOP_T}; option backtest not run." if stop
               else f"Diagnostic clears: overall 20-session date-clustered t = {t20} >= {STOP_T}.")
    diag = "## 2. Diagnostic (selected stocks, return net of the leave-one-out sector, signed by direction, %)\n\n" + \
        md(summary) + "\n" + verdict + "\n"
    (a.out_dir / "S1_v3_backtest_report.md").write_text(head + "\n" + diag, encoding="utf-8")
    print(diag)


if __name__ == "__main__":
    main()
