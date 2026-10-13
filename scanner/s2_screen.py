"""S2 step 1 · price + futures OI build-up, stock-level screen, year by year 2021-2026, as
strategies/S2_oi_buildup_screen.md pre-registers it (numbers only; not a trade).

    python -m scanner.s2_screen

Day d: price change %, combined futures OI change % (all expiries, from the cached F&O bhavcopies), volume ratio
(volume ÷ the 20 sessions before). Four classes (long build-up, short build-up, short covering, long unwinding) on a
48-cell grid; enter at day d+1's open, exit at day d+h's close, signed (short = −return), net of 0.1 %.
"""
from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .build import ROOT
from .stats import clustered_t

log = logging.getLogger("s2_screen")

START, END = "2021-01-01", "2026-09-25"
CLASSES = {"long_buildup": (1, 1, 1), "short_buildup": (-1, 1, -1), "short_covering": (1, -1, 1),
           "long_unwinding": (-1, -1, -1)}                 # class -> (price sign, OI sign, trade direction)
PRICE_THR, OI_THR, VOL_RATIO, HOLDS = (2.0, 3.0), (5.0, 10.0), 1.5, (1, 3, 5)
COOLDOWN, COST_PCT, VOL_WINDOW = 5, 0.1, 20
YEARS = tuple(str(y) for y in range(2021, 2027))
PASS_T, PASS_MEAN, PASS_YEARS = 3.0, {1: 0.4, 3: 0.6, 5: 0.6}, 5


# ---------------------------------------------------------------- pure rules
def classify(price_pct: float, oi_pct: float, vol_ratio: float, p_thr: float, oi_thr: float) -> str | None:
    """The build-up class of one stock-day, or None."""
    if any(map(lambda v: v is None or (isinstance(v, float) and math.isnan(v)), (price_pct, oi_pct, vol_ratio))):
        return None
    if vol_ratio < VOL_RATIO or abs(price_pct) < p_thr or abs(oi_pct) < oi_thr:
        return None
    for name, (ps, os_, _) in CLASSES.items():
        if np.sign(price_pct) == ps and np.sign(oi_pct) == os_:
            return name
    return None


def skip_days(sessions: list[str], expiries: set[str]) -> set[str]:
    """Expiry days and the session after each (the rollover moves the combined OI)."""
    out = set()
    for i, d in enumerate(sessions):
        if d in expiries:
            out.add(d)
            if i + 1 < len(sessions):
                out.add(sessions[i + 1])
    return out


def signed_return(opens: np.ndarray, closes: np.ndarray, i: int, h: int, direction: int) -> float:
    """Enter at the open of i+1, exit at the close of i+h; signed by the direction, net of the cost."""
    if i + h >= len(closes) or not opens[i + 1] > 0 or not closes[i + h] > 0:
        return math.nan
    return direction * (closes[i + h] / opens[i + 1] - 1) * 100 - COST_PCT


# ---------------------------------------------------------------- data
def oi_panel(cache_dir: Path, start: str = START, end: str = END) -> tuple[pd.DataFrame, set[str]]:
    """(date × symbol combined stock-futures OI, the set of stock-futures expiry dates), cached once as CSV."""
    cached = cache_dir / f"s2_oi_panel_{start}_{end}.csv"
    exp_file = cache_dir / f"s2_expiries_{start}_{end}.txt"
    if cached.exists() and exp_file.exists():
        return pd.read_csv(cached, index_col=0), set(exp_file.read_text().split())
    rows, expiries = {}, set()
    files = sorted(cache_dir.glob("fo_bhavcopy_*.csv"))
    for n, f in enumerate(files):
        d = f"{f.stem[-8:-4]}-{f.stem[-4:-2]}-{f.stem[-2:]}"
        if not start <= d <= end:
            continue
        b = pd.read_csv(f, usecols=lambda c: c in ("TckrSymb", "FinInstrmTp", "XpryDt", "OpnIntrst"))
        s = b[b["FinInstrmTp"] == "STF"]
        expiries |= set(s["XpryDt"].astype(str).str[:10])
        rows[d] = s.groupby(s["TckrSymb"].astype(str).str.strip())["OpnIntrst"].sum()
        if n % 200 == 0:
            log.info("OI panel: %d of %d files", n, len(files))
    panel = pd.DataFrame(rows).T.sort_index()
    panel.to_csv(cached)
    exp_file.write_text("\n".join(sorted(expiries)))
    return panel, expiries


def prices(symbols, eod2_dir: Path) -> dict[str, pd.DataFrame]:
    from .equity import load_symbol
    out = {}
    for s in symbols:
        try:
            f = load_symbol(s, eod2_dir)
            f.index = f.index.strftime("%Y-%m-%d")
            out[s] = f[~f.index.duplicated(keep="last")]
        except Exception as exc:  # noqa: BLE001 - delisted / renamed symbols without eod2 history
            log.info("%s: no eod2 (%s)", s, exc)
    return out


# ---------------------------------------------------------------- the screen
def sector_loo(px: dict[str, pd.DataFrame], sessions: list[str]) -> dict[str, pd.Series]:
    """Each stock's leave-one-out sector daily return (equal weight, >= 3 other members that day)."""
    from .sectors import load_map
    sector_of = load_map()
    rets = pd.DataFrame({s: f["Close"].reindex(sessions).pct_change() for s, f in px.items() if s in sector_of})
    out = {}
    for k in set(sector_of[s] for s in rets.columns):
        members = [s for s in rets.columns if sector_of[s] == k]
        m = rets[members]
        tot, cnt = m.sum(axis=1, min_count=1), m.notna().sum(axis=1)
        for s in members:
            own = m[s]
            c = cnt - own.notna()
            out[s] = ((tot - own.fillna(0)) / c.where(c >= 3)).astype(float)
    return out


def signals(panel: pd.DataFrame, px: dict[str, pd.DataFrame], expiries: set[str]) -> pd.DataFrame:
    """Every (stock, day d, cell) signal with its signed returns for h = 1, 3, 5 (and net of the sector), after
    the cooldown."""
    sessions = list(panel.index)
    loo = sector_loo(px, sessions)
    skip = skip_days(sessions, expiries)
    rows = []
    for sym in panel.columns:
        f = px.get(sym)
        if f is None:
            continue
        oi = panel[sym]
        f = f[(f.index >= sessions[0]) & (f.index <= sessions[-1])]
        idx = list(f.index)
        if len(idx) < VOL_WINDOW + 2:
            continue
        o, c, v = (f[k].to_numpy(dtype=float) for k in ("Open", "Close", "Volume"))
        oi_d = oi.reindex(idx).to_numpy(dtype=float)
        avg = pd.Series(v).rolling(VOL_WINDOW).mean().shift(1).to_numpy()
        sec = loo[sym].reindex(idx).to_numpy(dtype=float) if sym in loo else None
        last: dict[tuple, int] = {}
        for i in range(1, len(idx)):
            d = idx[i]
            if d in skip or not (oi_d[i] > 0 and oi_d[i - 1] > 0) or not (c[i - 1] > 0) or not avg[i] > 0:
                continue
            pc, oc, vr = (c[i] / c[i - 1] - 1) * 100, (oi_d[i] / oi_d[i - 1] - 1) * 100, v[i] / avg[i]
            for p_thr in PRICE_THR:
                for oi_thr in OI_THR:
                    k = classify(pc, oc, vr, p_thr, oi_thr)
                    if k is None:
                        continue
                    key = (k, p_thr, oi_thr)
                    if key in last and i - last[key] < COOLDOWN:
                        continue
                    last[key] = i
                    direction = CLASSES[k][2]
                    rows.append({"symbol": sym, "date": d, "class": k, "price_thr": p_thr, "oi_thr": oi_thr,
                                 "price_pct": round(pc, 2), "oi_pct": round(oc, 2), "vol_ratio": round(vr, 2),
                                 **{f"r{h}": signed_return(o, c, i, h, direction) for h in HOLDS},
                                 **{f"x{h}": (signed_return(o, c, i, h, direction)
                                              - direction * (np.prod(1 + sec[i + 1:i + h + 1]) - 1) * 100)
                                    if sec is not None and i + h < len(idx) and not np.isnan(sec[i + 1:i + h + 1]).any()
                                    else math.nan for h in HOLDS}})
    return pd.DataFrame(rows)


def table(sig: pd.DataFrame) -> pd.DataFrame:
    out = []
    for (k, p_thr, oi_thr), g in sig.groupby(["class", "price_thr", "oi_thr"]):
        for h in HOLDS:
            x = g.dropna(subset=[f"r{h}"])
            r = x[f"r{h}"]
            years = {y: round(r[x["date"].str[:4] == y].mean(), 3) if (x["date"].str[:4] == y).any() else None
                     for y in YEARS}
            t = clustered_t(r, x["date"]) if len(x) > 1 else None
            pos = sum(1 for y in YEARS if (years[y] or 0) > 0)
            xs = g.dropna(subset=[f"x{h}"])
            ok = (t or 0) >= PASS_T and r.mean() >= PASS_MEAN[h] and pos >= PASS_YEARS \
                and (years["2025"] or 0) > 0 and (years["2026"] or 0) > 0
            out.append({"class": k, "price_thr": p_thr, "oi_thr": oi_thr, "h": h, "n": len(x),
                        "mean": round(r.mean(), 3), "median": round(r.median(), 3),
                        "hit": round((r > 0).mean() * 100, 1), "t": t, **years, "years_pos": pos,
                        "vs_sector": round(xs[f"x{h}"].mean(), 3) if len(xs) else None,
                        "vs_sector_t": clustered_t(xs[f"x{h}"], xs["date"]) if len(xs) > 1 else None,
                        "PASS": "PASS" if ok else ""})
    return pd.DataFrame(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="S2 step 1: price + futures OI build-up screen (stock level)")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data" / "results")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from .backtest_s1_v2 import md

    panel, expiries = oi_panel(a.cache_dir)
    px = prices(panel.columns, a.eod2_dir)
    sig = signals(panel, px, expiries)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    sig.to_csv(a.out_dir / "S2_screen_signals.csv", index=False)
    tab = table(sig)
    passed = tab[tab["PASS"] == "PASS"]
    per_day = sig[(sig["price_thr"] == 2.0) & (sig["oi_thr"] == 5.0)].groupby(["date", "class"]).size()
    lines = ["# S2 step 1 screen report: price + futures OI build-up (stock level, not a trade)\n",
             f"Window {panel.index[0]} → {panel.index[-1]} ({len(panel)} sessions, {panel.shape[1]} stocks with "
             f"futures). Enter at day d+1's open, exit at day d+h's close, signed, net of {COST_PCT:g} %. Expiry days "
             "and the session after skipped. Pass: t ≥ 3, mean ≥ 0.6 % (h 3, 5) / 0.4 % (h 1), positive in ≥ 5 of 6 "
             "years including 2025 and 2026.\n",
             f"Signals per day (2 % / 5 % cell): median {per_day.groupby('class').median().to_dict()}.\n",
             f"## Cells that pass: {len(passed)} of {len(tab)}\n\n" + md(passed),
             "## All cells (mean % per year)\n\n" + md(tab)]
    (a.out_dir / "S2_screen_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[2:4]))
    print(md(tab))


if __name__ == "__main__":
    main()
