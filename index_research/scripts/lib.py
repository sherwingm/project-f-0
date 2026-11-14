"""Shared helpers for the index research program (index_research/PROGRAM.md). No strategy logic here."""
import math
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
os.environ.setdefault("INDEX_STORE", os.path.join(os.path.dirname(REPO), "fo-index-data", "data", "index"))
from index_data import load as L  # noqa: E402
from server import charges as CH  # noqa: E402
from scanner.stats import clustered_t  # noqa: E402

START, END = date(2021, 10, 20), date(2026, 10, 28)
LOT = {"NIFTY50": 65, "NIFTYBANK": 30, "SENSEX": 20}
SLIP = {"NIFTY50": 1.0, "NIFTYBANK": 3.0, "SENSEX": 3.0}
SLIP_STRESS = {"NIFTY50": 3.0, "NIFTYBANK": 8.0, "SENSEX": 8.0}
D_END, V_END = date(2023, 12, 31), date(2025, 9, 30)
MIN_BARS = 300


def period(d):
    return "D" if d <= D_END else ("V" if d <= V_END else "L")


def minutes(index="NIFTY50"):
    """dict day -> 1-minute frame (09:15..15:29), sessions with >= MIN_BARS bars; cached as parquet."""
    cache = os.path.join(ROOT, "data", f"spot_{index}.parquet")
    if os.path.exists(cache):
        s = pd.read_parquet(cache)
    else:
        s = L.spot_1m(START, END, index)[["timestamp", "open", "high", "low", "close"]]
        s.to_parquet(cache)
    s["d"] = s["timestamp"].dt.date
    s["hm"] = s["timestamp"].dt.hour * 100 + s["timestamp"].dt.minute
    out = {}
    for d, g in s.groupby("d"):
        if len(g) >= MIN_BARS:
            out[d] = g.reset_index(drop=True)
    return out


def daily(days):
    """Daily OHLC from minute frames (close = last bar)."""
    rows = [{"d": d, "open": float(g["open"].iloc[0]), "high": float(g["high"].max()), "low": float(g["low"].min()),
             "close": float(g["close"].iloc[-1])} for d, g in days.items()]
    return pd.DataFrame(rows).set_index("d").sort_index()


def vix_daily():
    return daily(minutes("INDIAVIX"))


def fut_trade(index, day, direction, entry, exit_, slip_pts=None, cost_mult=1.0):
    """Net Rs and % of notional for 1 lot of the index future proxied by the index. direction +1 long / -1 short."""
    lot = LOT[index]
    s = (SLIP[index] if slip_pts is None else slip_pts) * cost_mult
    e = entry + direction * s
    x = exit_ - direction * s
    gross = direction * (x - e) * lot
    side_in, side_out = ("BUY", "SELL") if direction > 0 else ("SELL", "BUY")
    ch = (CH.leg("FUT", side_in, lot, e, on=day)["total"] + CH.leg("FUT", side_out, lot, x, on=day)["total"]) * cost_mult
    net = gross - ch
    return net, net / (entry * lot) * 100


def tstat(vals, days):
    vals = np.asarray(vals, float)
    if len(vals) < 4 or np.nanstd(vals) == 0:
        return np.nan
    t = clustered_t(vals, [str(d) for d in days])
    return np.nan if t is None else float(t)


def summary(T, col="net_pct", rs="net_rs"):
    """T: frame with day, net_pct, net_rs (+ optional net_pct_2x). Returns a dict of the standard statistics."""
    if len(T) == 0:
        return {"n": 0}
    x = T[col].astype(float)
    r = T[rs].astype(float)
    gp, gl = r[r > 0].sum(), -r[r < 0].sum()
    eq = r.cumsum()
    dd = (eq - eq.cummax()).min()
    srt = x.sort_values(ascending=False)
    k = max(1, int(round(len(x) * 0.05)))
    half = len(T) // 2
    Ts = T.sort_values("day")
    o = {"n": len(T), "win_pct": (x > 0).mean() * 100, "mean_pct": x.mean(), "median_pct": x.median(), "total_rs": r.sum(),
         "t": tstat(x, T["day"]), "pf": gp / gl if gl > 0 else np.nan, "max_dd_rs": dd,
         "mean_ex_top5pct": srt.iloc[k:].mean() if len(srt) > k else np.nan,
         "h1_mean": Ts[col].iloc[:half].mean(), "h2_mean": Ts[col].iloc[half:].mean()}
    if f"{col}_2x" in T:
        o["mean_2x"] = T[f"{col}_2x"].mean()
    return o


def p_upper(t):
    return 0.5 * math.erfc(t / math.sqrt(2)) if t == t else np.nan


def bh(cells, q=0.10, min_n=30):
    """cells: DataFrame with n, mean_pct, t, h1_mean, h2_mean. Adds p, tested, bh_pass, discovery_pass."""
    c = cells.copy()
    c["p"] = [p_upper(t) if isinstance(t, float) else np.nan for t in c["t"]]
    c["tested"] = (c["n"] >= min_n) & c["p"].notna()
    m = int(c["tested"].sum())
    c["bh_pass"] = False
    if m:
        sub = c[c["tested"]].sort_values("p")
        thr = [(i + 1) / m * q for i in range(m)]
        ok = [p <= th for p, th in zip(sub["p"], thr)]
        k = max([i for i, v in enumerate(ok) if v], default=-1)
        c.loc[sub.index[:k + 1], "bh_pass"] = True
    c["discovery_pass"] = c["bh_pass"] & (c["mean_pct"] > 0) & (c["t"] >= 2) & (c["h1_mean"] > 0) & (c["h2_mean"] > 0)
    return c


def validation_pass(s):
    return bool(s.get("n", 0) >= 20 and s["mean_pct"] > 0 and s["t"] >= 1.5 and s.get("mean_2x", 1) > 0 and s["mean_ex_top5pct"] > 0)


def boot_ci(T, col="net_pct", n=2000, seed=20261114):
    rng = np.random.default_rng(seed)
    g = T.groupby("day")[col].sum()
    cnt = T.groupby("day")[col].count()
    v, c = g.to_numpy(), cnt.to_numpy()
    means = []
    for _ in range(n):
        i = rng.integers(0, len(v), len(v))
        means.append(v[i].sum() / c[i].sum())
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def mc_drawdown(rs, capital=500000, n=5000, seed=20261114):
    rng = np.random.default_rng(seed)
    rs = np.asarray(rs, float)
    dds, ruin = [], 0
    for _ in range(n):
        eq = np.cumsum(rng.permutation(rs))
        dd = (eq - np.maximum.accumulate(np.concatenate([[0], eq]))[1:]).min()
        dds.append(dd)
        ruin += (capital + eq).min() <= capital * 0.5
    return {"mc_dd_median": float(np.median(dds)), "mc_dd_p5": float(np.percentile(dds, 5)), "risk_of_halving_pct": ruin / n * 100}


def save(df, name):
    p = os.path.join(ROOT, "results", name)
    df.to_csv(p, index=False)
    return p


def index_close_vix():
    """India VIX daily close from 2008 (vix_daily.parquet), extended with minute closes where the file has gaps."""
    v = pd.read_parquet(os.path.join(os.environ["INDEX_STORE"], "vix_daily.parquet"))
    v["d"] = pd.to_datetime(v["date"]).dt.date
    s = v.set_index("d")["close"].dropna()
    m = L.spot_1m(date(2025, 1, 1), END, "INDIAVIX")
    m["d"] = m["timestamp"].dt.date
    last = m.groupby("d")["close"].last()
    return pd.concat([s, last[last.index > s.index.max()]]).sort_index()
