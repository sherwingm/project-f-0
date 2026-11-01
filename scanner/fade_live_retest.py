"""S1 fade · the past studies re-run on the live websocket data, 27 – 30 Oct 2026 (numbers only)

    python -m scanner.fade_live_retest

Plan written first: strategies/S1_fade_live_retest.md. Trades = every live fade trade in paper-state's ledger whose day
has a websocket file (data/candles_1s/<date>.jsonl, copied from the VM: 1-second candles of last price, best bid, ask).
Stock, Nifty 50 and India VIX 1-minute candles (not recorded by the stream) and the option's later sessions come from the
Upstox historical API, cached in data/cache/intraday/. Tests:
  1 live vs replay   v12 replayed on the 1-second bid from the live fill, against the ledger's sale;
  2 stops            −20 % (v12), −25, −30, −40 %, none, the rest v12, on the bid, from the live fill;
  3 max up / dip     from the live fill: while held, after the sale (rest of day 0, then later sessions to the last
                     websocket day), overall; on the bid and on the last price;
  4 market pattern   Nifty's previous day and 09:15 gap per day; "Nifty up yesterday + gap down" vs the rest;
  5 entry rules      the 15,061 rules of scanner.fade_pattern_entry_more (same 47 signs, option signs on 1-minute candles
                     built from the websocket): buy at the ask of the first quote of the first traded minute after the
                     sign, v12 exit on the bid; baseline = the first ask of the 09:16 minute. Does a rule's backtest mean
                     predict its live mean (Spearman)?
  6 models           scanner.fade_ml's three models trained on the 335 backtest trades (market inputs known at 09:16,
                     scanner.fade_market_pattern set A), scored on the live trades.
~23 trades on 4 days: a reality check of the backtest's picture, not a verdict. Writes data/results/S1_fade_live_retest.xlsx.
"""
from __future__ import annotations

import json
import subprocess
import time as _time
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from .build import ROOT
from .fade_indicators import RES, V12, net_pct
from .fade_market_pattern import inputs, market
from .fade_ml import models
from .fade_pattern_entry_more import (FIRST, LAST, clock_signs, market_signs, on_option_clock, option_signs, rule_list,
                                      vix_signs)
from .fade_stop_trail import walk

LIVE = ROOT / "data" / "candles_1s"
INTRA = ROOT / "data" / "cache" / "intraday"
API = "https://api.upstox.com/v3/historical-candle/{k}/minutes/1/{d}/{d}"
INDEX = {"NIFTY": "NSE_INDEX|Nifty 50", "VIX": "NSE_INDEX|India VIX"}
STOPS = [20, 25, 30, 40, None]
TICK = 0.01
_up = None


# ---- data ----
def ledger() -> dict:
    out = subprocess.run(["git", "show", "origin/paper-state:data/paper_ledger.json"], cwd=ROOT, capture_output=True,
                         check=True).stdout
    return json.loads(out.decode("utf-8"))


def live_trades(L: dict) -> pd.DataFrame:
    days = {p.stem for p in LIVE.glob("*.jsonl")}
    rows = []
    for x in L["closed"]:
        if (x.get("rule") or {}).get("strategy") != "fade" or x["opened_at"][:10] not in days:
            continue
        buy, qty = float(x["entry"]["price"]), int(x["qty"])
        rows.append({"day": x["opened_at"][:10], "symbol": x["symbol"], "side": x["instrument"], "strike": float(x["strike"]),
                     "expiry": x["expiry"], "ts": x["tradingsymbol"], "qty": qty, "lots": x.get("lots"),
                     "bought at": x["opened_at"][11:19], "buy": buy, "sold at": x["closed_at"][11:19],
                     "sell": float(x["exit"]["price"]), "live why": x["reason"], "live net Rs": float(x["net_pnl"]),
                     "live net %": float(x["net_pnl"]) / (buy * qty) * 100})
    return pd.DataFrame(rows).sort_values(["day", "bought at"]).reset_index(drop=True)


def seconds(day: str) -> dict[str, pd.DataFrame]:
    d = pd.read_json(LIVE / f"{day}.jsonl", lines=True, dtype={"t": str})
    return {k: g.sort_values("t", kind="stable").reset_index(drop=True) for k, g in d.groupby("ts")}


def minutes(s: pd.DataFrame) -> pd.DataFrame:
    """1-minute candles 09:15 – 15:29 from the websocket seconds; a minute with no tick repeats the last close, volume 0."""
    s = s[s["t"] >= "09:15:00"]
    x = s.assign(m=s["t"].str[:5], vv=s["v"].clip(lower=0))
    g = x.groupby("m").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), volume=("vv", "sum"),
                           ask=("a", "first"), first=("t", "first"))
    idx = [f"{9 + (i + 15) // 60:02d}:{(i + 15) % 60:02d}" for i in range(375)]
    g = g.reindex(idx)
    g["c"] = g["c"].ffill().bfill()
    for k in ("o", "h", "l"):
        g[k] = g[k].fillna(g["c"])
    g["volume"] = g["volume"].fillna(0)
    g["oi"] = 0.0
    return g.rename_axis("t").reset_index()


def upstox() :
    global _up
    if _up is None:
        from server.upstox import UpstoxProvider
        _up = UpstoxProvider("")
    return _up


def cached(name: str, day: str, fetch) -> pd.DataFrame | None:
    """Upstox 1-minute candles, cached as data/cache/intraday/<name>_<day>.json (the earlier studies' format)."""
    p = INTRA / f"{name}_{day}.json"
    if not p.exists():
        try:
            c = fetch()
        except Exception as exc:                                       # noqa: BLE001 (a missing day is reported, not fatal)
            c, err = [], str(exc)
        else:
            err = None if c else "no candles"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"symbol": name, "day": day, "tf": 1, "candles": c, "error": err}))
        _time.sleep(0.25)
    d = json.loads(p.read_text())
    if d.get("error") or not d.get("candles"):
        return None
    x = pd.DataFrame(d["candles"])
    x["t"] = pd.to_datetime(x["time"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.strftime("%H:%M")
    x = x.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"})
    return x[["t", "o", "h", "l", "c", "v"]].drop_duplicates("t").sort_values("t").reset_index(drop=True)


def index_1m(name: str, day: str) -> pd.DataFrame | None:
    def fetch():
        r = requests.get(API.format(k=quote(INDEX[name], safe=""), d=day), timeout=20).json()
        out = []
        for c in (r.get("data") or {}).get("candles") or []:
            t = pd.Timestamp(c[0])
            out.append({"time": int(t.timestamp()), "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5] or 0, "atp": None})
        return sorted(out, key=lambda c: c["time"])
    return cached(f"IDX_{name}", day, fetch)


def stock_1m(sym: str, day: str) -> pd.DataFrame | None:
    return cached(sym, day, lambda: upstox().history(f"NSE:{sym}", 1, day))


def option_1m(ts: str, day: str) -> pd.DataFrame | None:
    return cached(f"OPT_{ts}", day, lambda: upstox().history(f"NFO:{ts}", 1, day))


def sessions(days: list[str]) -> list[str]:
    """Trading sessions from 5 calendar weeks before the first live day to the last, by Nifty's 1-minute candles."""
    out = []
    for d in pd.bdate_range(pd.Timestamp(min(days)) - pd.Timedelta(days=10), max(days)):
        if index_1m("NIFTY", f"{d:%Y-%m-%d}") is not None:
            out.append(f"{d:%Y-%m-%d}")
    return out


def it(tr: pd.DataFrame):
    """Rows with attribute names: 'bought at' -> bought_at, 'live net %' -> live_net_pct."""
    return tr.rename(columns=lambda c: c.replace(" %", "_pct").replace(" ", "_")).itertuples()


# ---- the opening book and entry quotes ----
SPREAD = 0.10                                         # the live entry's spread limit (v10 entry: spread <= 10 % of the ask)


def fresh_row(s: pd.DataFrame) -> int:
    """First row of today's book. For a few seconds after 09:15 the websocket repeats the previous session's last bid / ask
    while trades print elsewhere; today's book starts at the first row with the day's volume reset (v < 0) or a bid / ask
    that differs from the first book seen (the 09:14:5x snapshot when there is one)."""
    T = s["t"].to_numpy()
    i9 = int(np.searchsorted(T, "09:15:00"))
    b0, a0 = s["bc"].iloc[0], s["a"].iloc[0]
    ch = (s["v"].to_numpy() < 0) | (s["bc"].to_numpy() != b0) | (s["a"].to_numpy() != a0)
    w = np.flatnonzero(ch[i9:])
    return i9 + int(w[0]) if len(w) else i9


def entry_row(s: pd.DataFrame, i: int, fresh: int, until: str = "15:20:00") -> int | None:
    """First row from i (and not before today's book) with a two-sided quote whose spread is <= 10 % of the ask."""
    T, A, Bd = s["t"].to_numpy(), s["a"].to_numpy(float), s["bc"].to_numpy(float)
    i = max(i, fresh)
    ok = (A[i:] > 0) & (Bd[i:] > 0) & ((A[i:] - Bd[i:]) <= SPREAD * A[i:] + 1e-9) & (T[i:] < until)
    w = np.flatnonzero(ok)
    return i + int(w[0]) if len(w) else None


# ---- exits on the 1-second bid ----
def exit_bid(s: pd.DataFrame, i0: int, e: float, stop: float | None, start: str = "09:16:00") -> tuple[float, str, str, int]:
    """v12 on the best bid from row i0 on: stop at bid <= (1 - stop) x e from `start`; trail on at bid >= 1.10 x e, sells at
    bid <= 0.98 x the highest bid since; else the first bid from 15:20. Fills at that bid. -> (price, time, why, row)."""
    T, B = s["t"].to_numpy(), s["bc"].to_numpy(float)
    cut = int(np.searchsorted(T, "15:20:00"))
    b, t = B[i0:cut], T[i0:cut]
    cand = []
    if stop is not None:
        w = np.flatnonzero((b <= e * (1 - stop / 100) + 1e-9) & (t >= start))
        if len(w):
            cand.append((int(w[0]), "stop"))
    a = np.flatnonzero((b >= e * 1.10 - 1e-9) & (t >= start))           # the live trail also starts at 09:16
    if len(a):
        pk = np.maximum.accumulate(b[a[0]:])
        w = np.flatnonzero(b[a[0]:] <= 0.98 * pk + 1e-9)
        if len(w):
            cand.append((int(a[0] + w[0]), "trail"))
    if cand:
        i, why = min(cand)
        return float(b[i]), str(t[i]), why, i0 + i
    j = min(cut, len(T) - 1)
    return float(B[j]), str(T[j]), "15:20", j


def window(s: pd.DataFrame, a: int, b: int, e: float) -> dict:
    """Max up / dip in rows a .. b-1, % of e, on the bid and on the last price."""
    x = s.iloc[a:b]
    x = x[x["t"] < "15:30:00"]
    if not len(x):
        return {"up bid": np.nan, "dip bid": np.nan, "up last": np.nan, "dip last": np.nan}
    return {"up bid": (x["bh"].max() / e - 1) * 100, "dip bid": (x["bl"].min() / e - 1) * 100,
            "up last": (x["h"].max() / e - 1) * 100, "dip last": (x["l"].min() / e - 1) * 100}


# ---- tests ----
def test_exits(tr: pd.DataFrame, sec: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Each exit twice: from the live fill as booked, and from a fill on today's book (a live buy made on the previous
    session's leftover ask is re-made at the first today's-book ask with spread <= 10 %, at or after the live fill)."""
    rep, mx = [], []
    for r in it(tr):
        s = sec[r.day][r.ts]
        T, A = s["t"].to_numpy(), s["a"].to_numpy(float)
        fr = fresh_row(s)
        i0 = int(np.searchsorted(T, r.bought_at, side="right"))          # the first quote after the fill second
        stale = i0 - 1 < fr
        ie = entry_row(s, i0, fr) if stale else i0 - 1
        ef = float(A[ie]) if stale else r.buy
        row = {"day": r.day, "symbol": r.symbol, "side": r.side, "ts": r.ts, "bought at": r.bought_at, "buy": r.buy,
               "live sold at": r.sold_at, "live sell": r.sell, "live why": r.live_why, "live net %": r.live_net_pct,
               "today's book from": T[fr], "live buy on the old book": "yes" if stale else "no",
               "today's-book buy at": T[ie], "today's-book buy": ef}
        for lab, start, e in (("", i0, r.buy), ("today's book · ", ie + 1, ef)):
            for st in STOPS:
                p_, t, why, j = exit_bid(s, start, e, st)
                rs, pc = net_pct(r.side, r.qty, e, p_)
                nm = lab + ("no stop" if st is None else f"stop −{st} %")
                row[f"{nm} · sold at"], row[f"{nm} · sell"], row[f"{nm} · why"], row[f"{nm} · net %"], row[f"{nm} · net Rs"] = t, p_, why, pc, rs
                if st == 20 and lab:
                    sold = j
        row["replay − live (points)"] = row["stop −20 % · net %"] - r.live_net_pct
        row["replay matches live"] = "same price" if abs(row["stop −20 % · sell"] - r.sell) < 0.0051 else (
            "within 3 points" if abs(row["replay − live (points)"]) <= 3 else "off by more")
        rep.append(row)
        held = window(s, ie, sold + 1, ef)
        after = window(s, sold + 1, len(s), ef)
        later = []
        for d in [d for d in sorted(sec) if d > r.day]:
            m = option_1m(r.ts, d)
            if m is not None:
                later.append(m)
        lt = pd.concat(later) if later else None
        lu = (lt["h"].max() / ef - 1) * 100 if lt is not None else np.nan
        ld = (lt["l"].min() / ef - 1) * 100 if lt is not None else np.nan
        mx.append({"day": r.day, "symbol": r.symbol, "side": r.side, "ts": r.ts, "today's-book buy": ef,
                   "today's-book net %": row["today's book · stop −20 % · net %"],
                   "held max up % (bid)": held["up bid"], "held max up % (last)": held["up last"],
                   "held max dip % (bid)": held["dip bid"], "held max dip % (last)": held["dip last"],
                   "after sale, day 0 max up % (bid)": after["up bid"], "after sale, day 0 max up % (last)": after["up last"],
                   "after sale, day 0 max dip % (last)": after["dip last"],
                   "later sessions found": len(later), "later sessions max up % (last)": lu, "later sessions max dip % (last)": ld,
                   "overall max up % (last)": np.nanmax([held["up last"], after["up last"], lu]),
                   "overall max dip % (last)": np.nanmin([held["dip last"], after["dip last"], ld])})
    return pd.DataFrame(rep), pd.DataFrame(mx)


def day_moves(days: list[str], sess: list[str]) -> pd.DataFrame:
    rows = []
    for d in days:
        i = sess.index(d)
        n, p1, p2 = index_1m("NIFTY", d), index_1m("NIFTY", sess[i - 1]), index_1m("NIFTY", sess[i - 2])
        c1, c2 = float(p1["c"].iloc[-1]), float(p2["c"].iloc[-1])
        rows.append({"day": d, "nifty prev day %": (c1 / c2 - 1) * 100, "nifty gap %": (float(n["o"].iloc[0]) / c1 - 1) * 100,
                     "nifty open to close %": (float(n["c"].iloc[-1]) / float(n["o"].iloc[0]) - 1) * 100, "nifty prev close": c1})
    out = pd.DataFrame(rows)
    out["pattern"] = (out["nifty prev day %"] > 0) & (out["nifty gap %"] < 0)
    return out


def test_pattern(tr: pd.DataFrame, rep: pd.DataFrame, mx: pd.DataFrame, dm: pd.DataFrame) -> pd.DataFrame:
    x = tr.merge(dm, on="day").assign(**{"overall max up % (last)": mx["overall max up % (last)"].to_numpy(),
                                        "held max up % (last)": mx["held max up % (last)"].to_numpy(),
                                        "book %": rep["today's book · stop −20 % · net %"].to_numpy(),
                                        "book Rs": rep["today's book · stop −20 % · net Rs"].to_numpy()})
    out = []
    for lab, g in (("Nifty up yesterday + gap down", x[x["pattern"]]), ("all other live trades", x[~x["pattern"]]), ("all", x)):
        out.append({"group": lab, "days": g["day"].nunique(), "trades": len(g),
                    "as booked: fail %": (g["live net %"] < 0).mean() * 100, "as booked: mean net %": g["live net %"].mean(),
                    "as booked: total Rs": g["live net Rs"].sum(),
                    "today's book: fail %": (g["book %"] < 0).mean() * 100, "today's book: mean net %": g["book %"].mean(),
                    "today's book: median net %": g["book %"].median(), "today's book: total Rs": g["book Rs"].sum(),
                    "median held max up %": g["held max up % (last)"].median(), "median overall max up %": g["overall max up % (last)"].median()})
    return pd.DataFrame(out)


def grid(m: pd.DataFrame | None, s: pd.DataFrame) -> pd.DataFrame:
    """1-minute candles 09:15 – 15:19 on a full grid for the signs: Upstox's exchange candles (a minute with no trade repeats
    the last close, volume 0). The websocket's own minutes only when Upstox has none: their opens carry the last price."""
    if m is None:
        x = minutes(s)
    else:
        idx = [f"{9 + (i + 15) // 60:02d}:{(i + 15) % 60:02d}" for i in range(375)]
        x = m.set_index("t").reindex(idx).rename(columns={"v": "volume"})
        x["c"] = x["c"].ffill().bfill()
        for k in ("o", "h", "l"):
            x[k] = x[k].fillna(x["c"])
        x["volume"] = x["volume"].fillna(0)
        x["oi"] = 0.0
        x = x.rename_axis("t").reset_index()
    return x[x["t"] <= "15:19"].reset_index(drop=True)


def test_rules(tr: pd.DataFrame, sec: dict, dm: pd.DataFrame) -> tuple[list, list, list]:
    """Every rule on every live trade. Signs on exchange 1-minute candles; the buy at the ask of the first today's-book
    quote with spread <= 10 % from the start of the minute after the sign; v12 on the bid. Baseline: the same buy from 09:16."""
    per, names, R, rl = [], None, None, None
    prev = dm.set_index("day")["nifty prev close"]
    for r in it(tr):
        s = sec[r.day][r.ts]
        T, A = s["t"].to_numpy(), s["a"].to_numpy(float)
        fr = fresh_row(s)
        c = grid(option_1m(r.ts, r.day), s)
        tt = c["t"].to_numpy()
        ib = entry_row(s, int(np.searchsorted(T, "09:16:00")), fr)
        e0 = float(A[ib])
        put = r.side == "PE"
        sg = {k: (fm, v.fillna(False).to_numpy(bool)) for k, (fm, v) in option_signs(c, e0).items()}
        for pre, src, pc in (("stock", stock_1m(r.symbol, r.day), None), ("Nifty", index_1m("NIFTY", r.day), prev[r.day])):
            if src is not None and len(src) > 20:
                for k, (fm, v) in market_signs(src, pre, put, pc).items():
                    sg[k] = (fm, on_option_clock(v, src["t"], tt))
        vx = index_1m("VIX", r.day)
        if vx is not None and len(vx) > 20:
            for k, (fm, v) in vix_signs(vx).items():
                sg[k] = (fm, on_option_clock(v, vx["t"], tt))
        sg |= clock_signs(tt)
        if names is None:
            names = list(sg)
            rl = rule_list(names, {k: sg[k][0] for k in names})
            R = np.array([list(x) + [len(names)] * (3 - len(x)) for x in rl])
        S = np.ones((len(c), len(names) + 1), bool)
        for q, k in enumerate(names):
            S[:, q] = sg[k][1] if k in sg else False
        valid = (tt >= FIRST) & (tt <= LAST)
        valid[len(c) - 2:] = False
        M = valid[:, None] & S[:, R[:, 0]] & S[:, R[:, 1]] & S[:, R[:, 2]]
        j = M.argmax(axis=0)
        j[~M.any(axis=0)] = -1
        outj, rsj = np.full(len(c) + 1, np.nan), np.full(len(c) + 1, np.nan)
        whenj, cache = np.full(len(c) + 1, None, dtype=object), {}
        for q in np.flatnonzero(valid):
            ie = entry_row(s, int(np.searchsorted(T, f"{tt[q + 1]}:00")), fr)
            if ie is None:
                continue
            if ie not in cache:
                p_, _, _, _ = exit_bid(s, ie + 1, float(A[ie]), 20)
                cache[ie] = net_pct(r.side, r.qty, float(A[ie]), p_)
            rsj[q], outj[q] = cache[ie]
            whenj[q] = T[ie][:8]
        jj = np.where(j >= 0, j, len(c))                                  # the last slot stays NaN = no sign
        b = exit_bid(s, ib + 1, e0, 20)
        bn = net_pct(r.side, r.qty, e0, b[0])
        per.append({"trade": f"{r.day} {r.symbol} {r.side}", "day": r.day, "09:16 ask": e0, "09:16 bought at": T[ib],
                    "09:16 net %": bn[1], "09:16 net Rs": bn[0], "J": jj, "outj": outj,
                    "net": outj[jj], "rs": rsj[jj], "when": whenj[jj]})
    return per, names, rl


def rules_table(per: list, names: list, rl: list, dm: pd.DataFrame, shuffles: int = 200) -> tuple[pd.DataFrame, dict]:
    keys = [" + ".join(names[i] for i in x) for x in rl]
    N = np.stack([p["net"] for p in per], axis=1)
    Rs = np.stack([p["rs"] for p in per], axis=1)
    base = np.array([p["09:16 net %"] for p in per])
    taken = ~np.isnan(N)
    with np.errstate(invalid="ignore", divide="ignore"):
        live = pd.DataFrame({"entry rule": keys, "live trades": taken.sum(axis=1),
                             "live mean net %": np.where(taken, N, 0).sum(axis=1) / taken.sum(axis=1),
                             "live total Rs": np.where(taken, Rs, 0).sum(axis=1),
                             "live 09:16 on the same trades %": np.where(taken, base[None, :], 0).sum(axis=1) / taken.sum(axis=1),
                             "live per trade % (no sign = no trade)": np.where(taken, N, 0).sum(axis=1) / N.shape[1]})
    bt = pd.read_excel(RES / "S1_fade_pattern_entry_more.xlsx", sheet_name="Rules", header=1,
                       usecols=["rank", "entry rule", "trades taken", "mean net %", "other days: trades", "other days: mean net %",
                                "net t (date-clustered)", "passes all"])
    bt["backtest all days: trades"] = bt["trades taken"] + bt["other days: trades"]
    bt["backtest all days: mean net %"] = ((bt["mean net %"] * bt["trades taken"]).fillna(0) + (bt["other days: mean net %"] * bt["other days: trades"]).fillna(0)) / bt["backtest all days: trades"]
    bt = bt.rename(columns={"rank": "backtest rank", "trades taken": "backtest pattern days: trades", "mean net %": "backtest pattern days: mean net %",
                            "other days: mean net %": "backtest other days: mean net %", "net t (date-clustered)": "backtest pattern t"})
    out = live.merge(bt, on="entry rule", how="left")
    e = out[(out["live trades"] >= 10) & (out["backtest all days: trades"] >= 30)]
    info = {"rules": len(out), "matched": int(out["backtest rank"].notna().sum()), "eligible": len(e),
            "spearman all": spearmanr(e["backtest all days: mean net %"], e["live mean net %"]).statistic if len(e) > 5 else np.nan,
            "spearman pattern": spearmanr(e["backtest pattern days: mean net %"], e["live mean net %"], nan_policy="omit").statistic if len(e) > 5 else np.nan,
            "beat 09:16 share": float((e["live mean net %"] > e["live 09:16 on the same trades %"]).mean() * 100) if len(e) else np.nan,
            "base mean": float(base.mean()), "base rs": float(sum(p["09:16 net Rs"] for p in per))}
    # null: one shared relabelling of trades within each day (each rule keeps its timing; the chart-to-trade link breaks)
    O = np.stack([p["outj"] for p in per])                                  # trades × minute slots (last slot NaN)
    Jm = np.stack([p["J"] for p in per], axis=1)                            # rules × trades
    days = np.array([p["day"] for p in per])
    em = out.index.isin(e.index)
    btm = out.loc[em, "backtest all days: mean net %"].to_numpy()
    rng, null = np.random.default_rng(0), []
    for _ in range(shuffles):
        perm = np.arange(len(per))
        for d in np.unique(days):
            w = np.flatnonzero(days == d)
            perm[w] = rng.permutation(w)
        Np = O[np.arange(len(per))[None, :], Jm[em][:, perm]]
        with np.errstate(invalid="ignore", divide="ignore"):
            lm = np.nanmean(Np, axis=1)
        null.append(spearmanr(btm, lm, nan_policy="omit").statistic)
    info["null spearman mean"], info["null spearman p95"] = float(np.mean(null)), float(np.percentile(null, 95))
    info["null p"] = float(np.mean(np.array(null) >= info["spearman all"]))
    top = e.sort_values("backtest all days: mean net %", ascending=False).head(100)
    info["top100 backtest -> live mean"] = float(top["live mean net %"].mean())
    info["bottom100 backtest -> live mean"] = float(e.sort_values("backtest all days: mean net %").head(100)["live mean net %"].mean())
    return out, info


def pair_auc(y: np.ndarray, p: np.ndarray, day: np.ndarray) -> tuple[float, int]:
    """AUC over failed / won pairs from the SAME day only (day-wide inputs cannot rank these): (AUC, pairs)."""
    hit, n = 0.0, 0
    for i in np.flatnonzero(y == 1):
        for j in np.flatnonzero((y == 0) & (day == day[i])):
            if np.isnan(p[i]) or np.isnan(p[j]):
                continue
            hit += 1.0 if p[i] > p[j] else 0.5 if p[i] == p[j] else 0.0
            n += 1
    return (hit / n if n else np.nan), n


def test_models(tr: pd.DataFrame, rep: pd.DataFrame, dm: pd.DataFrame, sess: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fail = the today's-book replay loses. Trade-level AUC, plus the same-day pairs AUC: with 4 days, the day-wide inputs
    (Nifty) mostly sort days, not trades."""
    bt = market(pd.read_feather(RES / "S1_fade_market_direction_trades.feather").sort_values("day0").reset_index(drop=True))
    bt["fail"] = bt["fail"].astype(bool)
    a_bt, _ = inputs(bt)
    rows = []
    for r in it(tr):
        i = sess.index(r.day)
        s0, s1, s2 = stock_1m(r.symbol, r.day), stock_1m(r.symbol, sess[i - 1]), stock_1m(r.symbol, sess[i - 2])
        d = dm.set_index("day").loc[r.day]
        ok = s0 is not None and s1 is not None and s2 is not None
        rows.append({"side": r.side, "nifty prev day %": d["nifty prev day %"], "nifty gap %": d["nifty gap %"],
                     "stock gap %": (s0["o"].iloc[0] / s1["c"].iloc[-1] - 1) * 100 if ok else np.nan,
                     "stock prev day %": (s1["c"].iloc[-1] / s2["c"].iloc[-1] - 1) * 100 if ok else np.nan})
    lf = pd.DataFrame(rows)
    for c in ("nifty open to close %", "nifty close move %", "nifty high from open %", "nifty low from open %"):
        lf[c] = np.nan                                                    # whole-day inputs (set B): not used here
    a_live, _ = inputs(lf)
    net = rep["today's book · stop −20 % · net %"].to_numpy()
    y = (net < 0).astype(int)
    day = tr["day"].to_numpy()
    keep = lf[["stock gap %", "stock prev day %"]].notna().all(axis=1).to_numpy()
    out, probs = [], pd.DataFrame({"trade": tr["day"] + " " + tr["symbol"], "today's-book net %": net, "failed": y})
    for name, mk in models().items():
        m = mk().fit(a_bt, bt["fail"].astype(int))
        p = np.full(len(tr), np.nan)
        p[keep] = m.predict_proba(a_live[keep])[:, 1]
        probs[f"{name}: fail chance %"] = p * 100
        k = keep & ~np.isnan(p)
        half = p >= np.nanmedian(p)                                       # ties fall together, never split by row order
        spread_ok = len(np.unique(p[k])) >= 3
        pa, npairs = pair_auc(y, p, day)
        out.append({"model (trained on the 335 backtest trades)": name, "live trades scored": int(k.sum()),
                    "AUC on live (0.50 = coin flip)": roc_auc_score(y[k], p[k]) if 0 < y[k].sum() < k.sum() else np.nan,
                    "same-day pairs AUC": pa, "same-day pairs": npairs, "distinct scores": len(np.unique(p[k])),
                    "fail % of its riskier half": y[k & half].mean() * 100 if spread_ok else np.nan,
                    "fail % of its safer half": y[k & ~half].mean() * 100 if spread_ok else np.nan,
                    "mean net % riskier half": net[k & half].mean() if spread_ok else np.nan,
                    "mean net % safer half": net[k & ~half].mean() if spread_ok else np.nan})
    gd = (lf["nifty gap %"] < 0).to_numpy()
    out.append({"model (trained on the 335 backtest trades)": "Rule: Nifty gap down", "live trades scored": len(tr),
                "AUC on live (0.50 = coin flip)": roc_auc_score(y, gd.astype(float)) if 0 < y.sum() < len(y) else np.nan,
                "same-day pairs AUC": pair_auc(y, gd.astype(float), day)[0], "same-day pairs": pair_auc(y, gd.astype(float), day)[1],
                "distinct scores": 2,
                "fail % of its riskier half": y[gd].mean() * 100 if gd.any() else np.nan, "fail % of its safer half": y[~gd].mean() * 100 if (~gd).any() else np.nan,
                "mean net % riskier half": net[gd].mean() if gd.any() else np.nan,
                "mean net % safer half": net[~gd].mean() if (~gd).any() else np.nan})
    return pd.DataFrame(out), probs.assign(**{c: lf[c] for c in ("nifty prev day %", "nifty gap %", "stock gap %", "stock prev day %")})


def backtest_style(tr: pd.DataFrame, rep: pd.DataFrame) -> pd.DataFrame:
    """What the vendor-candle backtest would book: the first exchange 1-minute candle from 09:16, its open + 1 tick, v12 on
    1-minute last prices (Upstox exchange candles), against the live result and the today's-book replay."""
    rows = []
    for (_, r), (_, q) in zip(tr.iterrows(), rep.iterrows()):
        out = {"day": r["day"], "symbol": r["symbol"], "ts": r["ts"], "live buy": r["buy"], "live bought at": r["bought at"],
               "live net %": r["live net %"], "today's-book buy": q["today's-book buy"],
               "today's-book net %": q["today's book · stop −20 % · net %"]}
        m = option_1m(r["ts"], r["day"])
        if m is not None:
            c = m[m["t"] <= "15:19"].reset_index(drop=True)
            k = int((c["t"] < "09:16").sum())
            e = round(float(c["o"].iloc[k]) + TICK, 2)
            sl, _ = walk(c, e, TICK, V12, k + 1)
            out["backtest-style buy at"], out["backtest-style buy"] = c["t"].iloc[k], e
            out["backtest-style net %"] = net_pct(r["side"], r["qty"], e, sl)[1]
        rows.append(out)
    return pd.DataFrame(rows)


def main() -> None:
    L = ledger()
    tr = live_trades(L)
    days = sorted(tr["day"].unique())
    sec = {d: seconds(d) for d in sorted(p.stem for p in LIVE.glob("*.jsonl"))}
    sess = sessions(days)
    rep, mx = test_exits(tr, sec)
    dm = day_moves(days, sess)
    pat = test_pattern(tr, rep, mx, dm)
    bs = backtest_style(tr, rep)
    per, names, rl = test_rules(tr, sec, dm)
    rt, rinfo = rules_table(per, names, rl, dm)
    md, probs = test_models(tr, rep, dm, sess)
    from .fade_live_retest_xlsx import write
    write(RES / "S1_fade_live_retest.xlsx", tr, rep, mx, dm, pat, bs, per, rt, rinfo, md, probs)
    pd.set_option("display.width", 300)
    print(tr[["day", "symbol", "side", "bought at", "buy", "sold at", "sell", "live why", "live net %"]].round(2).to_string())
    print(rep[[c for c in rep.columns if c.endswith("net %") or c in ("symbol", "replay matches live")]].round(1).to_string())
    print(mx.round(1).to_string())
    print(dm.round(2).to_string())
    print(pat.round(2).to_string())
    print(bs.round(2).to_string())
    print(rinfo)
    print(md.round(3).to_string())


if __name__ == "__main__":
    main()
