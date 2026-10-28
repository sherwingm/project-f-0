"""S1 v12 fade · RSI, EMA 50/100/200 and Supertrend: do they explain the failures, and do they pick a better entry time? (numbers only)

    python -m scanner.fade_indicators

Part A (known before the 09:16 buy): daily RSI 14, close vs EMA 50 / 100 / 200 and Supertrend (10, 3) at the previous close,
for Nifty 50 and for the stock, plus the 09:15 gaps (Nifty and the stock). Each condition alone, then every pair.
Part B (entry time): on the option's own 1-minute candles, wait from 09:30 for a condition (RSI, EMA, Supertrend, combined),
buy at the next candle's open + 1 tick, v12 exit; compared with the 09:16 entry on the same trades.
Same 339 v12 backtest trades as fade_market_direction. Exploratory: many conditions tested, so a pattern only counts when it
points the same way in both halves (train before 2025-11-03, test after). Writes data/results/S1_fade_indicators.xlsx.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

from server import charges as ch

from .build import ROOT
from .fade_stop_trail import SPLIT, walk
from .fastio import read_table

RES = ROOT / "data" / "results"
EOD = ROOT / "data" / "eod2"
V12 = {"S": 20, "mode": "touch", "start": "09:17", "A": 10, "D": 2, "re": False}


def rsi(c: pd.Series, n: int = 14) -> pd.Series:
    d = c.diff()
    up, dn = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(), (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def supertrend(h: pd.Series, lo: pd.Series, c: pd.Series, n: int = 10, m: float = 3.0) -> pd.Series:
    """+1 = up trend (price above the band), -1 = down."""
    pc = c.shift(1)
    tr = pd.concat([h - lo, (h - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    mid = (h + lo) / 2
    ub, lb = (mid + m * atr).to_numpy(), (mid - m * atr).to_numpy()
    cl = c.to_numpy()
    fu, fl, d = ub.copy(), lb.copy(), np.ones(len(c))
    for i in range(1, len(c)):
        fu[i] = ub[i] if ub[i] < fu[i - 1] or cl[i - 1] > fu[i - 1] else fu[i - 1]
        fl[i] = lb[i] if lb[i] > fl[i - 1] or cl[i - 1] < fl[i - 1] else fl[i - 1]
        d[i] = 1 if cl[i] > fu[i - 1] else -1 if cl[i] < fl[i - 1] else d[i - 1]
    return pd.Series(d, index=c.index)


def daily(df: pd.DataFrame) -> pd.DataFrame:
    """Indicators at each close; shift(1) gives what was known before that day's open."""
    o = pd.DataFrame(index=df.index)
    o["rsi"] = rsi(df["Close"])
    for n in (50, 100, 200):
        o[f"ema{n}"] = df["Close"] > df["Close"].ewm(span=n, adjust=False).mean()
    o["st"] = supertrend(df["High"], df["Low"], df["Close"])
    o = o.shift(1)
    o["gap"] = (df["Open"] / df["Close"].shift(1) - 1) * 100
    return o


def nifty() -> pd.DataFrame:
    f = RES / "nifty_daily_ohlc_long.feather"
    if not f.exists():
        import yfinance as yf
        d = yf.download("^NSEI", start="2023-01-01", auto_adjust=False, progress=False)
        d.columns = [c[0] for c in d.columns]
        d.reset_index().to_feather(f)
    return pd.read_feather(f).set_index("Date")


def features(t: pd.DataFrame) -> pd.DataFrame:
    nd = daily(nifty())
    rows = []
    for r in t.itertuples():
        d0 = pd.Timestamp(r.day0)
        s = pd.read_csv(EOD / f"{r.symbol.lower()}.csv", parse_dates=["Date"]).drop_duplicates("Date").set_index("Date")
        sd = daily(s[s.index <= d0 + pd.Timedelta(days=1)])
        x = {}
        for pre, src in (("nifty", nd), ("stock", sd)):
            v = src.loc[d0] if d0 in src.index else None
            x[f"{pre}_rsi"] = None if v is None else round(float(v["rsi"]), 1)
            for n in (50, 100, 200):
                x[f"{pre}_above_ema{n}"] = None if v is None else bool(v[f"ema{n}"])
            x[f"{pre}_supertrend_up"] = None if v is None else bool(v["st"] > 0)
            x[f"{pre}_gap_pct"] = None if v is None else round(float(v["gap"]), 2)
        rows.append(x)
    return pd.concat([t.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def conditions(f: pd.DataFrame) -> dict[str, pd.Series]:
    """Binary conditions known before 09:16. 'with' = pointing the trade's way (down for a put, up for a call)."""
    put = f["side"] == "PE"
    c = {}
    for pre in ("nifty", "stock"):
        r = f[f"{pre}_rsi"]
        c[f"{pre} RSI < 30"], c[f"{pre} RSI 30-50"] = r < 30, (r >= 30) & (r < 50)
        c[f"{pre} RSI 50-70"], c[f"{pre} RSI > 70"] = (r >= 50) & (r < 70), r >= 70
        for n in (50, 100, 200):
            c[f"{pre} above EMA {n}"] = f[f"{pre}_above_ema{n}"] == True        # noqa: E712
        c[f"{pre} above all 3 EMAs"] = c[f"{pre} above EMA 50"] & c[f"{pre} above EMA 100"] & c[f"{pre} above EMA 200"]
        c[f"{pre} below all 3 EMAs"] = (f[f"{pre}_above_ema50"] == False) & (f[f"{pre}_above_ema100"] == False) & (f[f"{pre}_above_ema200"] == False)  # noqa: E712
        c[f"{pre} Supertrend up"] = f[f"{pre}_supertrend_up"] == True          # noqa: E712
        c[f"{pre} gap down"] = f[f"{pre}_gap_pct"] < 0
        trend_up = f[f"{pre}_supertrend_up"] == True                           # noqa: E712
        c[f"{pre} Supertrend with the trade"] = (trend_up & ~put) | (~trend_up & put)
        c[f"{pre} gap with the trade"] = ((f[f"{pre}_gap_pct"] > 0) & ~put) | ((f[f"{pre}_gap_pct"] < 0) & put)
    return {k: v.fillna(False).astype(bool) for k, v in c.items()}


def stat(f: pd.DataFrame, m: pd.Series, name: str) -> dict:
    g, rest = f[m], f[~m]
    out = {"condition": name, "trades": len(g), "fail %": g["fail"].mean() * 100 if len(g) else None,
           "fail % rest": rest["fail"].mean() * 100 if len(rest) else None,
           "mean net %": g["v12 net %"].mean() if len(g) else None, "mean net % rest": rest["v12 net %"].mean() if len(rest) else None,
           "total Rs": g["v12 net Rs"].sum()}
    for h in ("train", "test"):
        gh, rh = g[g["half"] == h], rest[rest["half"] == h]
        out[f"{h} trades"] = len(gh)
        out[f"{h} fail %"] = gh["fail"].mean() * 100 if len(gh) else None
        out[f"{h} fail % rest"] = rh["fail"].mean() * 100 if len(rh) else None
        out[f"{h} mean net %"] = gh["v12 net %"].mean() if len(gh) else None
    a = [[int(g["fail"].sum()), int((~g["fail"]).sum())], [int(rest["fail"].sum()), int((~rest["fail"]).sum())]]
    out["p (fail vs rest)"] = fisher_exact(a)[1] if len(g) and len(rest) else None
    d1 = (out["train fail %"] or 0) - (out["train fail % rest"] or 0)
    d2 = (out["test fail %"] or 0) - (out["test fail % rest"] or 0)
    out["same way both halves"] = "yes" if out["train trades"] >= 10 and out["test trades"] >= 10 and d1 * d2 > 0 else "no"
    out["reads as"] = "fails MORE" if (out["fail %"] or 0) > (out["fail % rest"] or 0) else "fails LESS"
    return out


# ---- Part B: entry time on the option's 1-minute candles ----
def minute_book() -> dict:
    ms = [read_table(RES / f"S1_v10_{s}_minutes.csv") for s in ("bandv10", "band12", "band050")]
    m = pd.concat(ms).drop_duplicates(["symbol", "day0", "side", "strike", "ts"])
    m["t"] = m["ts"].str[11:16]
    return {k: g.sort_values("ts").reset_index(drop=True) for k, g in m.groupby(["symbol", "day0", "side", "strike"])}


def option_signals(c: pd.DataFrame) -> dict[str, np.ndarray]:
    cl = c["c"]
    r = rsi(cl)
    st = supertrend(c["h"], c["l"], cl)
    e = {n: cl > cl.ewm(span=n, adjust=False).mean() for n in (50, 100, 200)}
    was_low = (r < 30).cummax()
    return {"RSI > 50": (r > 50).to_numpy(), "RSI back above 30 after < 30": (was_low & (r > 30)).to_numpy(),
            "close above EMA 50": e[50].to_numpy(), "close above EMA 100": e[100].to_numpy(), "close above EMA 200": e[200].to_numpy(),
            "Supertrend up": (st > 0).to_numpy(),
            "Supertrend up + RSI > 50": ((st > 0) & (r > 50)).to_numpy(),
            "Supertrend up + above EMA 50": ((st > 0) & e[50]).to_numpy(),
            "Supertrend up + RSI > 50 + above EMA 50": ((st > 0) & (r > 50) & e[50]).to_numpy()}


def net_pct(side: str, lot: int, buy: float, sell: float) -> tuple[float, float]:
    rs = (sell - buy) * lot - ch.leg(side, "BUY", lot, buy)["total"] - ch.leg(side, "SELL", lot, sell)["total"]
    return rs, rs / (buy * lot) * 100


def entry_timing(t: pd.DataFrame, book: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for r in t.itertuples():
        c = book.get((r.symbol, r.day0, r.side, float(r.strike)))
        if c is None:
            continue
        c = c[c["t"] <= "15:19"].reset_index(drop=True)
        tick, lot = (0.05 if r.day0 < SPLIT else 0.01), int(r.lot)
        e0 = float(getattr(r, "_8"))                       # 'entry 09:16+tick'
        i0 = int((c["t"] < "09:17").sum())
        s0, _ = walk(c, e0, tick, V12, i0)
        b_rs, b_pct = net_pct(r.side, lot, e0, s0)
        row = {"day0": r.day0, "symbol": r.symbol, "side": r.side, "half": r.half, "09:16 net %": round(b_pct, 2), "09:16 net Rs": round(b_rs, 2)}
        sig, tt = option_signals(c), c["t"].to_numpy()
        for name, ok in sig.items():
            j = next((i for i in range(len(c) - 2) if "09:30" <= tt[i] <= "13:00" and ok[i]), None)
            if j is None:
                row[f"{name} · at"], row[f"{name} · net %"], row[f"{name} · net Rs"] = None, None, None
                continue
            e = max(tick, round(float(c["o"].iloc[j + 1]) + tick, 2))
            s, _ = walk(c, e, tick, V12, j + 2)
            rs_, p = net_pct(r.side, lot, e, s)
            row[f"{name} · at"], row[f"{name} · net %"], row[f"{name} · net Rs"] = tt[j + 1], round(p, 2), round(rs_, 2)
        rows.append(row)
    d = pd.DataFrame(rows)
    names = list(option_signals(next(iter(book.values()))).keys())
    summ = [{"entry rule": "09:16 open + 1 tick (live rule)", "trades taken": len(d), "no entry by 13:00": 0,
             "fail %": (d["09:16 net %"] < 0).mean() * 100, "mean net %": d["09:16 net %"].mean(), "total Rs": d["09:16 net Rs"].sum(),
             "same trades at 09:16: mean net %": d["09:16 net %"].mean(),
             "train mean net %": d.loc[d.half == "train", "09:16 net %"].mean(), "test mean net %": d.loc[d.half == "test", "09:16 net %"].mean()}]
    for nme in names:
        k = d[d[f"{nme} · net %"].notna()]
        summ.append({"entry rule": f"wait from 09:30 for: {nme}", "trades taken": len(k), "no entry by 13:00": len(d) - len(k),
                     "fail %": (k[f"{nme} · net %"] < 0).mean() * 100, "mean net %": k[f"{nme} · net %"].mean(),
                     "total Rs": k[f"{nme} · net Rs"].sum(), "same trades at 09:16: mean net %": k["09:16 net %"].mean(),
                     "train mean net %": k.loc[k.half == "train", f"{nme} · net %"].mean(),
                     "test mean net %": k.loc[k.half == "test", f"{nme} · net %"].mean()})
    return d, pd.DataFrame(summ)


def main() -> None:
    t = pd.read_feather(RES / "S1_fade_market_direction_trades.feather")
    f = features(t)
    cond = conditions(f)
    single = pd.DataFrame([stat(f, m, k) for k, m in cond.items()])
    keys = list(cond)
    pairs = []
    for a, b in combinations(keys, 2):
        if a.split()[0] == b.split()[0] and a.split()[1] == b.split()[1]:      # same family (e.g. two RSI bands), skip
            continue
        m = cond[a] & cond[b]
        if m.sum() >= 20:
            pairs.append(stat(f, m, f"{a} AND {b}"))
    pairs = pd.DataFrame(pairs).sort_values("p (fail vs rest)")
    gd = f[f["nifty_gap_pct"] < 0]
    why = pd.DataFrame([stat(gd, m.loc[gd.index], k) for k, m in cond.items() if not k.startswith("nifty gap")])
    book = minute_book()
    timing_rows, timing = entry_timing(t, book)
    from .fade_indicators_xlsx import write
    write(RES / "S1_fade_indicators.xlsx", f, single, pairs, why, timing, timing_rows)
    print(single[["condition", "trades", "fail %", "fail % rest", "p (fail vs rest)", "same way both halves"]].round(3).to_string())
    print(pairs.head(15)[["condition", "trades", "fail %", "fail % rest", "p (fail vs rest)", "same way both halves"]].round(3).to_string())
    print(why.sort_values("p (fail vs rest)").head(10)[["condition", "trades", "fail %", "fail % rest", "p (fail vs rest)", "same way both halves"]].round(3).to_string())
    print(timing.round(2).to_string())


if __name__ == "__main__":
    main()
