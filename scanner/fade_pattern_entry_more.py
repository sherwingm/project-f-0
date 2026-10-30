"""S1 v12 fade · more entry combinations on "Nifty up yesterday + gap down" days: 47 signs from the option, the stock,
Nifty, India VIX and the clock, every 1, 2 and 3 (one per family), with luck checks (numbers only)

    python -m scanner.fade_pattern_entry_more

Follows scanner.fade_pattern_entry: the same 73 pattern trades, the same entry (the first minute 09:17 – 15:00 where the
rule is true, buy at the next candle's open + 1 tick), v12 exit, real charges. A sign is read at a minute's close, so
only what was known then is used; a buy waits for the first candle that actually traded (the vendor fills no-trade minutes with the last price); stock, Nifty and VIX candles are matched by clock minute (last known value carried).
"with the trade" = pointing the option's way (up for a call, down for a put: for a put, "stock past VWAP with the
trade" means the stock is below its VWAP).
~15,000 rules on 73 trades from 31 days: many look good by luck alone. Pass bar:
  1. at least 20 trades, at least 8 in each half;
  2. the rule's own trades make money in BOTH halves (mean net % > 0);
  3. as a whole strategy it beats the 09:16 buy in BOTH halves: average over every pattern trade of the half, a day
     with no sign = no trade = 0, against the 09:16 buy on all of them;
  4. the rule's own net % has a date-clustered t of at least 2 (the strategy gate in DECISIONS.md);
  5. shuffle check: each rule's entry times are shuffled between trades of the same half (keeps WHEN it buys, drops
     WHAT the chart said). Family-wise: the rule's t must beat the best shuffled t of ALL rules in 95 % of 200
     shuffles, so testing ~15,000 rules is paid for. Clock-only rules have nothing to shuffle (n/a).
Changed after the first run: that run compared each rule with the 09:16 buy on the SAME trades. That flatters rules
that wait for a dip: when the option has already fallen 20 – 30 % below the 09:16 price, the 09:16 buy has hit its
−20 % stop, so "beating it on the same trades" is nearly automatic. Those same-trade columns are kept, marked "old bar".
Also: rules picked on the older half alone, then scored on the newer half (and the other way round).
Writes data/results/S1_fade_pattern_entry_more.xlsx.
"""
from __future__ import annotations

import json
from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd

from .build import ROOT
from .fade_indicators import RES, V12, minute_book, net_pct, nifty, rsi, supertrend
from .fade_market_pattern import market
from .fade_stop_trail import SPLIT, walk

FIRST, LAST = "09:17", "15:00"
CACHE = ROOT / "data" / "cache"
SPOT = CACHE / "index" / "feather" / "spot_1m"
if not SPOT.exists():                          # the cache copy can be missing: use the index-data repo it is made from
    SPOT = Path.home() / "fo-index-data" / "data" / "index" / "spot_1m"
NONE = 376                                    # clock slot meaning "no sign by 15:00"
SHUFFLES, MIN_TRADES, MIN_HALF = 600, 20, 8


def ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=n, adjust=False).mean()


def vwap(c: pd.DataFrame) -> pd.Series:
    v = c["v"].astype(float)
    return ((c["h"] + c["l"] + c["c"]) / 3 * v).cumsum() / v.cumsum().replace(0, np.nan)


def up_cross(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a > b) & (a.shift(1) <= b.shift(1))


def option_signs(c: pd.DataFrame, e0: float) -> dict[str, tuple[str, pd.Series]]:
    """name -> (family, bool series) on the option's own 1-minute candles."""
    o, h, lo, cl, t = c["o"], c["h"], c["l"], c["c"], c["t"]
    r = rsi(cl)
    s = {"opt RSI > 50": ("opt RSI", r > 50), "opt RSI > 60": ("opt RSI", r > 60),
         "opt RSI crossed above 50": ("opt RSI", up_cross(r, pd.Series(50, index=r.index))),
         "opt RSI back above 30 (after < 30)": ("opt RSI", (r < 30).cummax() & (r > 30)),
         "opt RSI back above 40 (after < 30)": ("opt RSI", (r < 30).cummax() & (r > 40))}
    for n in (9, 20, 50, 100, 200):
        s[f"opt above EMA {n}"] = ("opt EMA", cl > ema(cl, n))
    e9, e21 = ema(cl, 9), ema(cl, 21)
    s["opt EMA 9 above EMA 21"] = ("opt EMA cross", e9 > e21)
    s["opt EMA 9 just crossed above EMA 21"] = ("opt EMA cross", up_cross(e9, e21))
    for n, m in ((10, 3), (7, 2)):
        st = supertrend(h, lo, cl, n, m)
        s[f"opt Supertrend {n}×{m} up"] = ("opt Supertrend", st > 0)
        s[f"opt Supertrend {n}×{m} just turned up"] = ("opt Supertrend", (st > 0) & (st.shift(1) < 0))
    vw = vwap(c.assign(v=c["volume"]))
    s["opt above VWAP"] = ("opt VWAP", cl > vw)
    s["opt just crossed above VWAP"] = ("opt VWAP", up_cross(cl, vw))
    macd = ema(cl, 12) - ema(cl, 26)
    sig = ema(macd, 9)
    s["opt MACD above signal"] = ("opt MACD", macd > sig)
    s["opt MACD just crossed above signal"] = ("opt MACD", up_cross(macd, sig))
    mid, sd = cl.rolling(20).mean(), cl.rolling(20).std()
    s["opt back above lower Bollinger (after a close below)"] = ("opt Bollinger", (cl < mid - 2 * sd).cummax() & (cl > mid - 2 * sd))
    s["opt above middle Bollinger"] = ("opt Bollinger", cl > mid)
    ll, hh = lo.rolling(14).min(), h.rolling(14).max()
    k = 100 * (cl - ll) / (hh - ll).replace(0, np.nan)
    d = k.rolling(3).mean()
    s["opt Stochastic turned up from below 20"] = ("opt Stochastic", up_cross(k, d) & (k.shift(1) < 20))
    v = c["volume"].astype(float)
    s["opt volume spike (2× last 20 min) on a green candle"] = ("opt volume", (v > 2 * v.shift(1).rolling(20).mean()) & (cl > o))
    oi = c["oi"].replace(0, np.nan).ffill()
    s["opt OI lower than 15 candles ago"] = ("opt OI", oi < oi.shift(15))
    s["opt new high of the day"] = ("opt price", cl > h.cummax().shift(1))
    s["opt above the 09:15 – 09:29 range high"] = ("opt price", (t >= "09:30") & (cl > h[t <= "09:29"].max()))
    s["opt 2 green candles in a row"] = ("opt price", (cl > o) & (cl.shift(1) > o.shift(1)))
    low = lo.where(t >= "09:16").cummin()
    for x in (10, 20, 30):
        s[f"opt dipped {x} % below the 09:16 buy"] = ("opt dip", low <= e0 * (1 - x / 100))
    s["opt now below the 09:16 buy"] = ("opt dip", cl < e0)
    return s


def flip(c: pd.DataFrame, put: bool) -> pd.DataFrame:
    """For a put, mirror the prices so that 'up' always means 'with the trade'."""
    if not put:
        return c
    return c.assign(o=-c["o"], h=-c["l"], l=-c["h"], c=-c["c"])


def market_signs(c: pd.DataFrame, pre: str, put: bool, prev_close: float | None) -> dict[str, tuple[str, pd.Series]]:
    w = flip(c, put)
    cl = w["c"]
    s = {f"{pre} RSI with the trade": (f"{pre} momentum", rsi(cl) > 50),
         f"{pre} EMA 20 with the trade": (f"{pre} momentum", cl > ema(cl, 20)),
         f"{pre} Supertrend with the trade": (f"{pre} momentum", supertrend(w["h"], w["l"], cl) > 0),
         f"{pre} past its 09:15 open with the trade": (f"{pre} level", cl > w["o"].iloc[0])}
    if "v" in c and c["v"].sum() > 0:
        s[f"{pre} past VWAP with the trade"] = (f"{pre} level", cl > vwap(w))
    if prev_close is not None:
        s[f"{pre} past yesterday's close with the trade"] = (f"{pre} level", cl > (-prev_close if put else prev_close))
    return s


def vix_signs(c: pd.DataFrame) -> dict[str, tuple[str, pd.Series]]:
    cl = c["c"]
    return {"VIX above its 09:15 open": ("VIX", cl > c["o"].iloc[0]), "VIX up vs 15 minutes ago": ("VIX", cl > cl.shift(15))}


def stock_minutes(sym: str, day: str) -> pd.DataFrame | None:
    p = CACHE / "intraday" / f"{sym}_{day}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    if d.get("error") or not d.get("candles"):
        return None
    x = pd.DataFrame(d["candles"])
    x["t"] = pd.to_datetime(x["time"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.strftime("%H:%M")
    x = x.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"})
    return x[["t", "o", "h", "l", "c", "v"]].drop_duplicates("t").sort_values("t").reset_index(drop=True)


def spot_minutes(name: str, start: str) -> dict[str, pd.DataFrame]:
    fs = [p for p in sorted((SPOT / name).glob("*.*")) if p.stem >= start[:7]]
    d = pd.concat([pd.read_feather(p) if p.suffix == ".feather" else pd.read_parquet(p) for p in fs])
    d["day"], d["t"] = d["timestamp"].dt.strftime("%Y-%m-%d"), d["timestamp"].dt.strftime("%H:%M")
    d = d.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c"})
    return {k: g[["t", "o", "h", "l", "c"]].drop_duplicates("t").sort_values("t").reset_index(drop=True) for k, g in d.groupby("day")}


def on_option_clock(sig: pd.Series, t_src: pd.Series, t_opt: np.ndarray) -> np.ndarray:
    """A sign from another chart, read at each option minute: its last known value at or before that minute."""
    s = pd.Series(sig.fillna(False).to_numpy(bool), index=t_src.to_numpy())
    s = s[~s.index.duplicated()]
    idx = sorted(set(s.index) | set(t_opt))
    return s.reindex(idx).ffill().reindex(t_opt).fillna(False).to_numpy(bool)


def clock_signs(t: np.ndarray) -> dict[str, tuple[str, np.ndarray]]:
    return {f"clock {x} or later": ("clock", t >= x) for x in ("10:00", "11:00", "12:30")}


def minute_of(t: str) -> int:
    return (int(t[:2]) - 9) * 60 + int(t[3:5]) - 15


def outcomes(c: pd.DataFrame, full: pd.DataFrame, tick: float, side: str, lot: int, valid: np.ndarray) -> dict[str, np.ndarray]:
    """For every signal minute j: buy at j+1's open + 1 tick, v12 exit. Net %, net ₹, max up / dip while held, max up to 15:29."""
    n = len(c)
    out = {k: np.full(n + 1, np.nan) for k in ("net %", "net Rs", "held up", "held dip", "day up")}
    hf, h, lo = full["h"].to_numpy(), c["h"].to_numpy(), c["l"].to_numpy()
    day_hi = np.maximum.accumulate(hf[::-1])[::-1]
    vol = c["volume"].to_numpy()
    for j in np.flatnonzero(valid):
        k = j + 1
        while k < n - 1 and vol[k] == 0:                 # vendor-filled minute with no trade: wait for the first real trade
            k += 1
        if vol[k] == 0:
            continue                                     # nothing traded before 15:19: no entry
        e = max(tick, round(float(c["o"].iloc[k]) + tick, 2))
        s, at = walk(c, e, tick, V12, k)
        rs, p = net_pct(side, lot, e, s)
        end = (n - 1 if at is None else at) + 1
        out["net %"][j], out["net Rs"][j] = p, rs
        out["held up"][j], out["held dip"][j] = (h[k:end].max() / e - 1) * 100, (lo[k:end].min() / e - 1) * 100
        out["day up"][j] = (day_hi[k] / e - 1) * 100
    return out


def rule_list(names: list[str], fam: dict[str, str]) -> list[tuple[int, ...]]:
    out = []
    for k in (1, 2, 3):
        for combo in combinations(range(len(names)), k):
            if len({fam[names[i]] for i in combo}) == k:                 # one sign per family
                out.append(combo)
    return out


def build(f: pd.DataFrame) -> dict:
    book = minute_book()
    nd = nifty()
    nd.index = pd.to_datetime(nd.index)
    start = str(f["day0"].min())
    nif, vix = spot_minutes("NIFTY50", start), spot_minutes("INDIAVIX", start)
    keep, J, tabs, c2j, bases, missing, pre_, nodata = [], [], [], [], [], {"stock": 0, "Nifty": 0, "VIX": 0}, [], []
    for r in f.itertuples():
        full = book.get((r.symbol, r.day0, r.side, float(r.strike)))
        if full is None:
            continue
        full = full[full["t"] <= "15:29"].reset_index(drop=True)
        c = full[full["t"] <= "15:19"].reset_index(drop=True)
        put, e0 = r.side == "PE", float(f.at[r.Index, "entry 09:16+tick"])
        tt = c["t"].to_numpy()
        sg = {k: (fm, v.fillna(False).to_numpy(bool)) for k, (fm, v) in option_signs(c, e0).items()}
        i = nd.index.get_indexer([pd.Timestamp(r.day0)])[0]
        prev = float(nd["Close"].iloc[i - 1]) if i >= 1 else None
        gap = []
        for pre, src, pc in (("stock", stock_minutes(r.symbol, r.day0), None), ("Nifty", nif.get(r.day0), prev)):
            ms = market_signs(src, pre, put, pc) if src is not None and len(src) > 20 else {}
            if not ms:
                missing[pre] += 1
                gap.append(pre)
            for k, (fm, v) in ms.items():
                sg[k] = (fm, on_option_clock(v, src["t"], tt))
        vx = vix.get(r.day0)
        if vx is not None and len(vx) > 20:
            for k, (fm, v) in vix_signs(vx).items():
                sg[k] = (fm, on_option_clock(v, vx["t"], tt))
        else:
            missing["VIX"] += 1
            gap.append("VIX")
        sg |= clock_signs(tt)
        pre_.append((r, full, c, e0, sg))
        nodata.append(", ".join(gap))
    fullest = max(pre_, key=lambda x: len(x[4]))[4]
    names = list(fullest)
    fam = {k: fullest[k][0] for k in names}
    rl = rule_list(names, fam)
    R = np.array([list(x) + [len(names)] * (3 - len(x)) for x in rl])
    for r, full, c, e0, sg in pre_:
        tick, lot, side = (0.05 if r.day0 < SPLIT else 0.01), int(r.lot), r.side
        s0, _ = walk(c, e0, tick, V12, int((c["t"] < "09:17").sum()))
        bases.append(net_pct(side, lot, e0, s0))
        tt = c["t"].to_numpy()
        S = np.ones((len(c), len(names) + 1), bool)                       # last column: always true (pads 1- and 2-sign rules)
        for q, k in enumerate(names):
            S[:, q] = sg[k][1] if k in sg else False                      # no stock / Nifty / VIX data that day = no sign
        valid = (tt >= FIRST) & (tt <= LAST)
        valid[len(c) - 2:] = False
        M = valid[:, None] & S[:, R[:, 0]] & S[:, R[:, 1]] & S[:, R[:, 2]]
        j = M.argmax(axis=0)
        j[~M.any(axis=0)] = -1
        J.append(j.astype(np.int16))
        tabs.append(outcomes(c, full, tick, side, lot, valid))
        mins = np.array([minute_of(x) for x in tt])
        m2j = np.full(NONE + 1, -1)
        for k in range(NONE):
            q = np.searchsorted(mins, k)
            if q < len(c) and valid[q]:
                m2j[k] = q
        c2j.append((m2j, mins))
        keep.append(r.Index)
    L = max(len(x["net %"]) for x in tabs)
    tab = {k: np.full((len(tabs), L + 1), np.nan) for k in tabs[0]}
    for i, x in enumerate(tabs):
        for k, v in x.items():
            tab[k][i, :len(v) - 1] = v[:-1]                               # last column stays NaN = "no sign"
    Jm = np.stack(J, axis=1).astype(np.int64)                             # rules × trades
    Jm[Jm < 0] = L
    clock = np.full(Jm.shape, NONE)
    for i, (m2j, mins) in enumerate(c2j):
        ok = Jm[:, i] < L
        clock[ok, i] = mins[Jm[ok, i]]
    m2j = np.stack([np.where(x[0] < 0, L, x[0]) for x in c2j])
    g = f.loc[keep].reset_index(drop=True)
    g["09:16 net Rs"], g["09:16 net %"] = [b[0] for b in bases], [b[1] for b in bases]
    g["no minute data for"] = nodata
    return {"f": g, "names": names, "fam": fam, "rules": rl, "J": Jm, "clock": clock, "tab": tab, "m2j": m2j, "L": L,
            "missing": missing}


def ct(D: np.ndarray, C: np.ndarray) -> np.ndarray:
    """Date-clustered t of each row's mean (NaN = trade not taken); same CR1 formula as scanner.stats.clustered_t."""
    m = ~np.isnan(D)
    n = m.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = np.where(m, D, 0).sum(axis=1) / n
        e = np.where(m, D - mu[:, None], 0)
        S = e @ C
        g = ((m.astype(float) @ C) > 0).sum(axis=1)
        var = g / (g - 1) * (S ** 2).sum(axis=1) / n ** 2
        return np.where((g >= 2) & (var > 0), mu / np.sqrt(var), np.nan)


def nanmean(X: np.ndarray) -> np.ndarray:
    m = ~np.isnan(X)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(m, X, 0).sum(axis=1) / m.sum(axis=1)


def hhmm(x: float) -> str | None:
    if np.isnan(x):
        return None
    x = int(round(x)) + 15
    return f"{9 + x // 60:02d}:{x % 60:02d}"


def stats(B: dict, idx: np.ndarray) -> dict[str, np.ndarray]:
    """Per rule over the trades idx: what the rule made, and the 09:16 buy on the same trades."""
    f, J = B["f"], B["J"][:, idx]
    ar = idx[None, :]
    net, rs = B["tab"]["net %"][ar, J], B["tab"]["net Rs"][ar, J]
    taken = ~np.isnan(net)
    b916 = np.where(taken, f["09:16 net %"].to_numpy()[idx][None, :], np.nan)
    b916rs = np.where(taken, f["09:16 net Rs"].to_numpy()[idx][None, :], 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        o = {"trades": taken.sum(axis=1), "mean": nanmean(net), "median": np.nanmedian(np.where(taken, net, np.nan), axis=1),
             "fail": np.where(taken, net < 0, 0).sum(axis=1) / taken.sum(axis=1) * 100, "rs": np.where(taken, rs, 0).sum(axis=1),
             "b mean": nanmean(b916), "b rs": b916rs.sum(axis=1), "diff": net - b916}
    for k, nm in (("held up", "held up"), ("day up", "day up"), ("held dip", "held dip")):
        o[nm] = np.nanmedian(B["tab"][k][ar, J], axis=1)
    cl = B["clock"][:, idx].astype(float)
    cl[cl == NONE] = np.nan
    o["time"] = np.nanmedian(cl, axis=1)
    return o


def shuffle_net(B: dict, idx: np.ndarray, perm: np.ndarray) -> np.ndarray:
    """Each trade gets the entry clock minute the rule chose on another trade of the same half."""
    cl = B["clock"][:, idx][:, perm]
    j = B["m2j"][idx[None, :], cl]
    return B["tab"]["net %"][idx[None, :], j]


def per_trade(N: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """The rule as a whole strategy: average over every pattern trade in mask, a day with no sign counts 0 (no trade)."""
    return np.where(np.isnan(N[:, mask]), 0, N[:, mask]).sum(axis=1) / mask.sum()


def summary(B: dict, seed: int = 0) -> tuple[pd.DataFrame, dict]:
    f, names = B["f"], B["names"]
    pt, ot = np.flatnonzero(f["pattern"].to_numpy()), np.flatnonzero(~f["pattern"].to_numpy())
    older = (f["half"].to_numpy()[pt] == "train")
    days = pd.factorize(f["day0"].to_numpy()[pt])[0]
    C = np.eye(days.max() + 1)[days]
    P, O = stats(B, pt), stats(B, ot)
    base = f["09:16 net %"].to_numpy()[pt]
    D = P["diff"]
    net = D + base[None, :]
    t_net, t_old = ct(net, C), ct(D, C)
    n_old, n_new = (~np.isnan(net[:, older])).sum(axis=1), (~np.isnan(net[:, ~older])).sum(axis=1)
    m_old, m_new = nanmean(net[:, older]), nanmean(net[:, ~older])
    s_old, s_new = per_trade(net, older), per_trade(net, ~older)
    b_old, b_new = base[older].mean(), base[~older].mean()
    rl = B["rules"]
    clock_only = np.array([all(B["fam"][names[i]] == "clock" for i in x) for x in rl])
    c1 = (P["trades"] >= MIN_TRADES) & (n_old >= MIN_HALF) & (n_new >= MIN_HALF)
    c2 = c1 & (m_old > 0) & (m_new > 0)
    c3 = c2 & (s_old > b_old) & (s_new > b_new)
    c4 = c3 & (t_net >= 2)
    o2 = c1 & (nanmean(D[:, older]) > 0) & (nanmean(D[:, ~older]) > 0)          # the first run's bar (same-trade gain), kept to show why it was dropped
    o3 = o2 & (t_old >= 2)
    rng = np.random.default_rng(seed)
    io, inew = np.flatnonzero(older), np.flatnonzero(~older)
    elig = c1 & ~clock_only
    beat_self, beat_max, beat_max_old, luck = np.zeros(len(rl)), np.zeros(len(rl)), np.zeros(len(rl)), []
    for _ in range(SHUFFLES):
        perm = np.arange(len(pt))
        perm[io], perm[inew] = rng.permutation(io), rng.permutation(inew)
        Ns = shuffle_net(B, pt, perm)
        ts, tso = ct(Ns, C), ct(Ns - base[None, :], C)
        beat_self += np.nan_to_num(ts, nan=-np.inf) >= np.nan_to_num(t_net, nan=np.inf)
        beat_max += np.nanmax(np.where(elig, ts, np.nan)) >= np.nan_to_num(t_net, nan=np.inf)
        beat_max_old += np.nanmax(np.where(elig, tso, np.nan)) >= np.nan_to_num(t_old, nan=np.inf)
        so, sn = (~np.isnan(Ns[:, older])).sum(axis=1), (~np.isnan(Ns[:, ~older])).sum(axis=1)
        ok = ((~np.isnan(Ns)).sum(axis=1) >= MIN_TRADES) & (so >= MIN_HALF) & (sn >= MIN_HALF) & ~clock_only
        ok &= (nanmean(Ns[:, older]) > 0) & (nanmean(Ns[:, ~older]) > 0)
        ok &= (per_trade(Ns, older) > b_old) & (per_trade(Ns, ~older) > b_new) & (ts >= 2)
        luck.append(int(ok.sum()))
    p_self, p_fw = beat_self / SHUFFLES, beat_max / SHUFFLES
    c5 = c4 & ~clock_only & (p_fw < 0.05)
    o4 = o3 & ~clock_only & (beat_max_old / SHUFFLES < 0.05)
    dip = np.array([any(B["fam"][names[i]] == "opt dip" for i in x) for x in rl])
    yn = lambda m: np.where(m, "yes", "no")                                    # noqa: E731
    rows = pd.DataFrame({
        "entry rule": [" + ".join(names[i] for i in x) for x in rl], "signs": [len(x) for x in rl],
        "families": [" + ".join(B["fam"][names[i]] for i in x) for x in rl],
        "trades taken": P["trades"], "no sign by 15:00": len(pt) - P["trades"], "median entry time": [hhmm(x) for x in P["time"]],
        "fail %": P["fail"], "mean net %": P["mean"], "median net %": P["median"], "net t (date-clustered)": t_net, "total Rs": P["rs"],
        "per pattern trade % (no sign = no trade)": per_trade(net, np.ones(len(pt), bool)),
        "older half trades": n_old, "older half mean net %": m_old, "older half per pattern trade %": s_old,
        "newer half trades": n_new, "newer half mean net %": m_new, "newer half per pattern trade %": s_new,
        "other days: trades": O["trades"], "other days: mean net %": O["mean"], "other days at 09:16 %": O["b mean"],
        "median max up while held %": P["held up"], "median max up by 15:29 %": P["day up"], "median max dip while held %": P["held dip"],
        "same trades at 09:16: mean net % (old bar)": P["b mean"], "gain over 09:16 on the same trades % (old bar)": nanmean(D),
        "gain t on the same trades (old bar)": t_old,
        "shuffle p (this rule)": np.where(clock_only, np.nan, p_self), "shuffle p (all rules, family-wise)": np.where(clock_only, np.nan, p_fw),
        "1 enough trades": yn(c1), "2 makes money in both halves": yn(c2), "3 beats the 09:16 buy in both halves": yn(c3),
        "4 net t ≥ 2": yn(c4), "5 beats the shuffles": np.where(clock_only, "n/a", yn(c5)), "passes all": yn(c5 | (c4 & clock_only))})
    info = {"rules": len(rl), "signs": len(names), "c1": int(c1.sum()), "c2": int(c2.sum()), "c3": int(c3.sum()), "c4": int(c4.sum()),
            "c5": int(c5.sum()), "clock pass": int((c4 & clock_only).sum()), "luck mean": float(np.mean(luck)),
            "luck p95": float(np.percentile(luck, 95)), "old 3": int(o3.sum()), "old 4": int(o4.sum()),
            "luck p": float(np.mean(np.array(luck) >= int((c4 & ~clock_only).sum()))),
            "old 4 with a dip sign %": float(dip[o4].mean() * 100) if o4.any() else 0.0,
            "old 4 same trades at 09:16": float(np.nanmean(P["b mean"][o4])) if o4.any() else np.nan,
            "pattern trades": len(pt), "pattern days": int(days.max() + 1),
            "base": {"fail %": (base < 0).mean() * 100, "mean": base.mean(), "median": float(np.median(base)),
                     "rs": f["09:16 net Rs"].to_numpy()[pt].sum(), "older": b_old, "newer": b_new,
                     "other": f["09:16 net %"].to_numpy()[ot].mean()},
            "missing": B["missing"], "missing pattern": f.loc[pt, "no minute data for"].replace("", np.nan).dropna().tolist()}
    rows.insert(0, "rank", 0)
    return rows, info


def selection(rows: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    """Pick the top k rules by mean net % on one half only, then look at the other half they were not picked on."""
    e = rows[(rows["older half trades"] >= MIN_HALF) & (rows["newer half trades"] >= MIN_HALF)]
    out = []
    for pick, score, nm in (("older half mean net %", "newer half mean net %", "older"), ("newer half mean net %", "older half mean net %", "newer")):
        top = e.sort_values(pick, ascending=False).head(k)
        base_rate = (e[score] > 0).mean() * 100
        for _, r in top.iterrows():
            out.append({"picked on": f"{nm} half", "entry rule": r["entry rule"], "mean net % on the half it was picked on": r[pick],
                        "mean net % on the other half": r[score], "still makes money there": "yes" if r[score] > 0 else "no",
                        "all eligible rules that make money on that half %": base_rate})
    return pd.DataFrame(out)


def main() -> None:
    t = pd.read_feather(RES / "S1_fade_market_direction_trades.feather").sort_values("day0").reset_index(drop=True)
    f = market(t)
    f["pattern"] = (f["nifty prev day %"] > 0) & (f["nifty gap %"] < 0)
    B = build(f)
    rows, info = summary(B)
    sel = selection(rows)
    steps = ["passes all", "4 net t ≥ 2", "3 beats the 09:16 buy in both halves", "2 makes money in both halves", "1 enough trades"]
    rows = rows.assign(**{f"_{i}": rows[s] == "yes" for i, s in enumerate(steps)})
    rows = rows.sort_values([f"_{i}" for i in range(len(steps))] + ["net t (date-clustered)"], ascending=False)
    rows = rows.drop(columns=[f"_{i}" for i in range(len(steps))])
    rows["rank"] = np.arange(1, len(rows) + 1)
    from .fade_pattern_entry_more_xlsx import write
    write(RES / "S1_fade_pattern_entry_more.xlsx", B, rows, sel, info)
    pd.set_option("display.width", 320)
    cols = ["entry rule", "trades taken", "median entry time", "fail %", "mean net %", "net t (date-clustered)",
            "per pattern trade % (no sign = no trade)", "older half mean net %", "older half per pattern trade %", "newer half mean net %",
            "newer half per pattern trade %", "other days: mean net %", "shuffle p (all rules, family-wise)", "passes all"]
    print(rows[cols].head(25).round(2).to_string())
    print({k: v for k, v in info.items()})
    print(sel.round(2).to_string())


if __name__ == "__main__":
    main()
