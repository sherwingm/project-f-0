"""S1 v10 fade · strike distance study (strategies/S1_v10_strike_distance_study.md). Descriptive only.

    EVENTS_DB=<seeded store> python -m scanner.strike_distance_study      # both windows, all variants
    python -m scanner.strike_distance_study --reuse                         # tables from the saved trades

The same signals, expiry, entries, exit and costs as scanner/backtest_s1_v10.py; only the strike choice changes:
v10's walk (baseline), the walk capped at 3 % / 5 % out of the money, one listed step closer than the baseline, or the
strike at the money.
"""
from __future__ import annotations

import argparse
import logging
import math
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

from . import backtest_s1_v10 as bt
from .build import ROOT

log = logging.getLogger("strike_distance_study")

RES = ROOT / "data" / "results"
CACHE = ROOT / "data" / "cache"
EOD2 = ROOT / "data" / "eod2"
WINDOWS = {"2022-24": ("2022-01-01", "2024-12-31"), "2025-26": ("2025-01-01", "2026-09-25")}
VARIANTS = ("baseline", "cap 3 %", "cap 5 %", "one step closer", "at the money")
ATM_STEPS = 2
ORIG_WALK = bt.walk                                      # v10's own walk (simulate() is pointed at a variant while it runs)


# ---------------------------------------------------------------- the strike rules (pure)
def otm_pct(k: float, spot: float, side: str) -> float:
    """% out of the money of strike k against spot (negative = in the money)."""
    return ((spot - k) if side == "PE" else (k - spot)) / spot * 100


def _path(strikes, spot: float, side: str) -> list[float]:
    ks = sorted(set(float(k) for k in strikes))
    k0 = bt.start_strike(ks, spot, side)
    if k0 is None:
        return []
    i = ks.index(k0)
    return (ks[: i + 1][::-1] if side == "PE" else ks[i:])[: bt.WALK_MAX]


def _liquid(q, entry: str):
    """(fill, source) if the quote passes v10's liquidity and minimum-premium tests, else None."""
    if q is None or not q.lot > 0:
        return None
    f = bt.entry_price(q, entry)
    if f is None or f[0] < bt.MIN_PREMIUM:
        return None
    return f


def walk_capped(cap: float):
    """v10's walk, stopping at the last strike within `cap` % out of the money of the previous close."""
    def walk(strikes, spot, side, quotes, entry):
        path = [k for k in _path(strikes, spot, side) if otm_pct(k, spot, side) <= cap + 1e-9]
        if not path:
            return "no_strike_within_cap"
        w = ORIG_WALK(path_strikes(path, side), spot, side, quotes, entry)
        return "no_strike_within_cap" if w == "walk_no_liquid_strike_in_band" else w
    return walk


def path_strikes(path: list[float], side: str) -> list[float]:
    """The strike list v10's walk needs so that its own path is exactly `path` (it starts at the strike nearest spot)."""
    return sorted(path)


def walk_closer(strikes, spot, side, quotes, entry):
    """One listed step nearer the money than v10's pick (no cost ceiling); the same trade if that pick is the start."""
    w = ORIG_WALK(strikes, spot, side, quotes, entry)
    if isinstance(w, str):
        return w
    q0, _px, _src, n = w
    if n == 0:
        return w
    path = _path(strikes, spot, side)
    j = path.index(q0.strike)
    for k in path[:j][::-1][:1]:
        q = quotes.get(k)
        f = _liquid(q, entry)
        if f is not None:
            return q, f[0], f[1], j - 1
    return "closer_strike_not_liquid"


def walk_atm(strikes, spot, side, quotes, entry):
    """The start strike (nearest the previous close), else the next liquid one out of the money (<= 2 steps); no cost
    limits."""
    for n, k in enumerate(_path(strikes, spot, side)[: ATM_STEPS + 1]):
        q = quotes.get(k)
        f = _liquid(q, entry)
        if f is not None:
            return q, f[0], f[1], n
    return "atm_not_liquid"


RULES = {"baseline": None, "cap 3 %": walk_capped(3.0), "cap 5 %": walk_capped(5.0),
         "one step closer": walk_closer, "at the money": walk_atm}


# ---------------------------------------------------------------- running
def run_window(name: str) -> pd.DataFrame:
    from . import amfi
    from .equity import load_symbol
    from .events.store import Store
    from .financials import load as load_fin
    from .nse_fo import BhavcopyUnavailable, download_fo_prices
    start, end = WINDOWS[name]
    bt.START, bt.END = start, end
    sessions = [d for d in sorted(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}" for p in CACHE.glob("fo_bhavcopy_*.csv"))
                if d <= end]
    bhav = bt.Bhav(CACHE)
    with Store() as st:
        results = [(e["symbol"], e["event_date"], e.get("event_time")) for e in st.all_of_type("results")]
    sigs = bt.signals(results, load_fin(), sessions, bhav, Counter())
    log.info("%s: %d signals", name, len(sigs))
    stock, stock_oc = {}, {}
    for sym in sorted({s["symbol"] for s in sigs}):
        try:
            f = load_symbol(sym, EOD2)
            f.index = f.index.strftime("%Y-%m-%d")
            stock[sym] = f[~f.index.duplicated(keep="last")]["Close"]
        except Exception as exc:  # noqa: BLE001
            log.info("%s: no eod2 (%s)", sym, exc)
    px: dict = {}

    def prices(d: str):
        if d not in px:
            try:
                px[d] = download_fo_prices(date.fromisoformat(d), CACHE)
            except (BhavcopyUnavailable, OSError, ValueError) as exc:
                log.warning("prices %s: %s", d, exc)
                px[d] = None
        return px[d]

    cats, frames, orig = amfi.load(), [], ORIG_WALK
    try:
        for v in VARIANTS:
            bt.walk = RULES[v] or orig
            for entry in bt.ENTRIES:
                fun = Counter()
                t = bt.simulate(sigs, entry, sessions, bhav, prices, cats.category_on, stock, stock_oc, fun)
                t["variant"], t["window"] = v, name
                frames.append(t)
                log.info("%s %s %s: %s", name, v, entry, dict(fun))
    finally:
        bt.walk = orig
    out = pd.concat(frames, ignore_index=True)
    out["otm_pct"] = [otm_pct(k, s, sd) for k, s, sd in zip(out["strike"], out["spot_prev_close"], out["side"])]
    return out


# ---------------------------------------------------------------- tables
def _valid(t: pd.DataFrame) -> pd.DataFrame:
    return t[t["e1_excluded"].fillna("") == ""]


def summary(t: pd.DataFrame) -> pd.DataFrame:
    from .stats import clustered_t
    rows = []
    for (w, v, entry), g0 in _valid(t).groupby(["window", "variant", "entry"], sort=False):
        for side in ("PE", "CE", "all"):
            g = g0 if side == "all" else g0[g0["side"] == side]
            r = g["e1_net_pct"].astype(float)
            rows.append({"window": w, "variant": v, "entry": entry, "side": side, "trades": len(g),
                         "mean net %": round(r.mean(), 2) if len(g) else None,
                         "median net %": round(r.median(), 2) if len(g) else None,
                         "hit %": round((r > 0).mean() * 100, 1) if len(g) else None,
                         "t": clustered_t(r, g["day0"]) if len(g) > 1 else None,
                         "mean net Rs": round(g["e1_net"].mean()) if len(g) else None,
                         "total net Rs": round(g["e1_net"].sum()) if len(g) else None,
                         "mean lot cost Rs": round(g["premium_rs"].mean()) if len(g) else None,
                         "lots over Rs 8,000": int((g["premium_rs"] > bt.BAND[1]).sum()),
                         "median % OTM": round(g["otm_pct"].median(), 2) if len(g) else None})
    order = {v: k for k, v in enumerate(VARIANTS)}
    return pd.DataFrame(rows).sort_values(["window", "entry", "variant"], key=lambda s: s.map(order) if s.name == "variant"
                                          else s, kind="stable").reset_index(drop=True)


def paired(t: pd.DataFrame) -> pd.DataFrame:
    """Per variant, window, entry: on the signals traded by both, the mean variant - baseline difference."""
    from .stats import clustered_t
    v_ = _valid(t)
    key = ["window", "entry", "symbol", "day0"]
    base = v_[v_["variant"] == "baseline"].set_index(key)
    rows = []
    for v in VARIANTS[1:]:
        for (w, entry), g in v_[v_["variant"] == v].groupby(["window", "entry"]):
            g = g.set_index(key)
            both = g.index.intersection(base.index)
            d_pct = g.loc[both, "e1_net_pct"].astype(float) - base.loc[both, "e1_net_pct"].astype(float)
            d_rs = g.loc[both, "e1_net"].astype(float) - base.loc[both, "e1_net"].astype(float)
            days = pd.Series(both.get_level_values("day0"), index=both)
            same = (g.loc[both, "strike"].astype(float) == base.loc[both, "strike"].astype(float)).sum()
            lv = base.index
            bw = base[(lv.get_level_values("window") == w) & (lv.get_level_values("entry") == entry)]
            dropped = bw.index.difference(g.index)
            rows.append({"variant": v, "window": w, "entry": entry, "paired signals": len(both),
                         "same strike as baseline": int(same),
                         "diff net % (variant - baseline)": round(d_pct.mean(), 2) if len(both) else None,
                         "t (net %)": clustered_t(d_pct.values, days.values) if len(both) > 1 else None,
                         "diff net Rs": round(d_rs.mean()) if len(both) else None,
                         "t (net Rs)": clustered_t(d_rs.values, days.values) if len(both) > 1 else None,
                         "baseline trades it drops": len(dropped),
                         "dropped trades' baseline net %": round(base.loc[dropped, "e1_net_pct"].astype(float).mean(), 2)
                         if len(dropped) else None,
                         "dropped trades' baseline net Rs total": round(base.loc[dropped, "e1_net"].astype(float).sum())
                         if len(dropped) else None})
    return pd.DataFrame(rows)


def guard(p: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for v in VARIANTS[1:]:
        g = p[p["variant"] == v].set_index(["window", "entry"])
        get = lambda w, e, c: g.loc[(w, e), c] if (w, e) in g.index else None     # noqa: E731
        ok_dir = all((get(w, e, "diff net % (variant - baseline)") or -1) > 0 and (get(w, e, "diff net Rs") or -1) > 0
                     for w in WINDOWS for e in bt.ENTRIES)
        t1, t2 = (get(w, "open", "t (net %)") for w in WINDOWS)
        pooled = round((t1 + t2) / math.sqrt(2), 3) if t1 is not None and t2 is not None else None
        each = t1 is not None and t2 is not None and min(t1, t2) >= 1
        cap_ok = True
        if v.startswith("cap"):
            cap_ok = all((get(w, e, "dropped trades' baseline net %") or 0) < 0 for w in WINDOWS for e in bt.ENTRIES)
        better = bool(ok_dir and pooled is not None and pooled >= 2 and each and cap_ok)
        rows.append({"variant": v, "better in both windows, both entries, % and Rs": ok_dir,
                     "pooled t (open entry, net %)": pooled, "t >= 1 in each window": each,
                     "dropped trades lost (caps only)": cap_ok if v.startswith("cap") else "n/a",
                     "BETTER": "YES" if better else "no"})
    return pd.DataFrame(rows)


def write(t: pd.DataFrame, answer: str | None = None) -> None:
    import xlsxwriter
    from .backtest_s1_v2 import md
    t.to_csv(RES / "S1_v10_strike_distance_trades.csv", index=False)
    s, p = summary(t), paired(t)
    g = guard(p)
    head = ("Descriptive only (strategies/S1_v10_strike_distance_study.md). Not out of sample. Same signals, expiry, "
            "entry, same-day exit and costs as the v10 backtest; only the strike changes. 'One step closer' and 'at the "
            "money' may break the Rs 600-8,000 lot budget (see 'lots over Rs 8,000').")
    if answer:
        head = head + "\n\n" + answer
    tables = [("Guard", "Is a variant better? (the pre-registered guard)", g),
              ("Paired vs baseline", "Same signals: variant minus baseline (same-day exit)", p),
              ("Summary", "Every variant, window, entry and side", s)]
    text = ["# S1 v10 fade · strike distance study\n", head + "\n"]
    for _n, title, df in tables:
        text += [f"## {title}\n", md(df)]
    (RES / "S1_v10_strike_distance.md").write_text("\n".join(text), encoding="utf-8")
    wb = xlsxwriter.Workbook(RES / "S1_v10_strike_distance.xlsx")
    F = lambda **k: wb.add_format({"font_name": "Arial", "font_size": 10, **k})         # noqa: E731
    H = F(bold=True, font_color="#FFFFFF", bg_color="#1F3864", text_wrap=True, align="center", valign="vcenter", border=1)
    num = F(num_format="#,##0.00;[Red]-#,##0.00")
    yes = F(bold=True, bg_color="#E2F0E4")
    for name, title, df in tables:
        ws = wb.add_worksheet(name)
        ws.write(0, 0, title, F(bold=True, font_size=12))
        if name == "Guard" and answer:
            ws.set_column(0, 0, 16)
            for k, line in enumerate(answer.splitlines()):
                ws.write(len(df) + 7 + k, 0, line, F(bold=line.startswith("Answer")))
        ws.write(1, 0, head.split("\n")[0], F(italic=True, font_size=9, font_color="#595959"))
        ws.set_row(3, 48)
        for c, h in enumerate(df.columns):
            ws.write(3, c, str(h), H)
            ws.set_column(c, c, 16 if c < 4 else 13)
        for i, row in enumerate(df.itertuples(index=False), 4):
            for c, v in enumerate(row):
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    ws.write_blank(i, c, None)
                elif isinstance(v, bool):
                    ws.write(i, c, "yes" if v else "no", F())
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    ws.write_number(i, c, float(v), num)
                elif hasattr(v, "item"):
                    ws.write_number(i, c, float(v), num)
                else:
                    ws.write(i, c, str(v), yes if v == "YES" else F())
        ws.freeze_panes(4, 0)
    wb.close()
    print("\n".join(text))


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v10 strike distance study (descriptive)")
    ap.add_argument("--reuse", action="store_true", help="rebuild the tables from the saved trades CSV")
    ap.add_argument("--window", choices=list(WINDOWS), help="run one window only")
    ap.add_argument("--answer", type=Path, help="a text file with the plain-language answer")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if a.reuse:
        t = pd.read_csv(RES / "S1_v10_strike_distance_trades.csv")
    else:
        t = pd.concat([run_window(w) for w in ([a.window] if a.window else WINDOWS)], ignore_index=True)
    write(t, a.answer.read_text(encoding="utf-8") if a.answer else None)


if __name__ == "__main__":
    main()
