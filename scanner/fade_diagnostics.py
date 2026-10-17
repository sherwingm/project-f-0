"""S1 v10 fade · diagnostics (strategies/S1_v10_fade_diagnostics.md). Descriptive only, no rule change.

    python -m scanner.fade_diagnostics            # features + tables -> data/results/S1_v10_fade_diagnostics.md / .xlsx
    python -m scanner.fade_diagnostics --answers FILE   # also put the verified plain-language answers in the report

Why losers lose (Q1), the market vs the stock's own move (Q2), the pre-run (Q3, Q6), the three result numbers (Q4), the
user's example stocks (Q5) and other measures (Q7), on the 2022-24 and 2025-26 fade trades and on every results filing.
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .build import ROOT

log = logging.getLogger("fade_diagnostics")

RES = ROOT / "data" / "results"
EOD2 = ROOT / "data" / "eod2"
BHAV = ROOT / "data" / "cache"
IDX_CACHE = ROOT / "data" / "cache" / "index"
WINDOWS = {"2022-24": ("2022-01-01", "2024-12-31", "_2022_24"), "2025-26": ("2025-01-01", "2026-09-25", "")}
EXAMPLES = ("BPCL", "OBEROIRLTY", "BEL", "ADANIPORTS", "BAJFINANCE", "BOSCHLTD", "HCLTECH", "POLYCAB", "SONACOMS")
NEVER_UP, ROUND_TRIP = 10.0, 30.0
MIN_N, MIN_T = 30, 2.0


# ---------------------------------------------------------------- pure helpers
def pct(a, b):
    """(a / b - 1) x 100, NaN when either is missing or b <= 0."""
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return math.nan
    return (a / b - 1) * 100 if b > 0 and not (math.isnan(a) or math.isnan(b)) else math.nan


def loser_class(peak_pct: float, net_pct: float) -> str:
    if net_pct >= 0:
        return "winner"
    if peak_pct < NEVER_UP:
        return "never up"
    if peak_pct >= ROUND_TRIP:
        return "round trip"
    return "other"


def bucket(x: float, cuts: list[float], labels: list[str]) -> str | None:
    """labels[i] for cuts[i-1] < x <= cuts[i]; the last label above the last cut."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    for c, lab in zip(cuts, labels):
        if x <= c:
            return lab
    return labels[-1]


def reversal(pre_run: float, reaction: float) -> float:
    """Positive = day 0 moved opposite to the run before it."""
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (pre_run, reaction)) or pre_run == 0:
        return math.nan
    return -math.copysign(1.0, pre_run) * reaction


def parse_index_file(text: str, name: str = "nifty 50") -> dict | None:
    """Open / high / low / close of `name` from NSE's ind_close_all CSV text."""
    df = pd.read_csv(io.StringIO(text))
    df.columns = [str(c).strip() for c in df.columns]
    row = df[df["Index Name"].astype(str).str.strip().str.lower() == name.lower()]
    if row.empty:
        return None
    r = row.iloc[0]
    num = lambda k: pd.to_numeric(str(r.get(k, "")).replace(",", ""), errors="coerce")        # noqa: E731
    out = {"open": num("Open Index Value"), "high": num("High Index Value"), "low": num("Low Index Value"),
           "close": num("Closing Index Value")}
    return {k: (float(v) if v == v else math.nan) for k, v in out.items()}


# ---------------------------------------------------------------- data access
def index_ohlc(day: str, cache: Path = IDX_CACHE) -> dict | None:
    """NIFTY 50's day OHLC from NSE's daily index file (cached)."""
    import requests
    from .cm_fallback import INDEX_URL, NSE_HEADERS
    d = date.fromisoformat(day)
    f = cache / f"ind_close_all_{d:%d%m%Y}.csv"
    if not f.exists():
        r = requests.get(INDEX_URL.format(dmy=d.strftime("%d%m%Y")), headers=NSE_HEADERS, timeout=60)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        cache.mkdir(parents=True, exist_ok=True)
        f.write_text(r.text, encoding="utf-8")
        import time
        time.sleep(0.4)                                   # be gentle with NSE's archive
    return parse_index_file(f.read_text(encoding="utf-8"))


class Daily:
    """eod2 daily OHLCV by ISO date, loaded once per symbol (downloads a missing file into data/eod2)."""

    def __init__(self, eod2: Path = EOD2):
        self.eod2, self._f = eod2, {}

    def get(self, sym: str) -> pd.DataFrame | None:
        if sym not in self._f:
            from .equity import load_symbol
            try:
                f = load_symbol(sym, self.eod2)
                f.index = f.index.strftime("%Y-%m-%d")
                self._f[sym] = f[~f.index.duplicated(keep="last")]
            except Exception as exc:  # noqa: BLE001 - not every stock has an eod2 file
                log.info("%s: no eod2 (%s)", sym, exc)
                self._f[sym] = None
        return self._f[sym]


def nifty_closes() -> pd.Series:
    f = pd.read_csv(EOD2 / "nifty 50.csv", parse_dates=["Date"])
    s = f.set_index(f["Date"].dt.strftime("%Y-%m-%d"))["Close"]
    return s[~s.index.duplicated(keep="last")].sort_index()


def stock_features(df: pd.DataFrame | None, cal: list[str], i: int) -> dict:
    """Pre-run 5/20/60, 52-week place, volume ratio (all to day -1), and day 0's gap, open->close, close->close."""
    out = {k: math.nan for k in ("pre5", "pre20", "pre60", "pos52", "vol_ratio", "gap", "oc", "cc", "s_open", "s_close")}
    if df is None or i < 61:
        return out
    c = df["Close"]
    prev = cal[i - 1]
    cp = c.get(prev)
    for n in (5, 20, 60):
        out[f"pre{n}"] = pct(cp, c.get(cal[i - 1 - n]))
    win = df.loc[(df.index >= cal[max(0, i - 252)]) & (df.index <= prev)]
    if len(win) > 50 and cp == cp:
        lo, hi = win["Low"].min(), win["High"].max()
        out["pos52"] = (cp - lo) / (hi - lo) if hi > lo else math.nan
    vol = df["Volume"]
    before = vol.loc[(vol.index < prev)].tail(20)
    if prev in vol.index and len(before) >= 10 and before.mean() > 0:
        out["vol_ratio"] = float(vol[prev]) / float(before.mean())
    d0 = cal[i]
    if d0 in df.index:
        o, cl = df.at[d0, "Open"], df.at[d0, "Close"]
        out.update(gap=pct(o, cp), oc=pct(cl, o), cc=pct(cl, cp), s_open=float(o), s_close=float(cl))
    return out


class FutOI:
    """Combined stock-futures open interest per session from the cached F&O bhavcopies."""

    def __init__(self, cache: Path = BHAV):
        self.cache, self._d = cache, {}

    def day(self, d: str) -> dict:
        if d not in self._d:
            f = self.cache / f"fo_bhavcopy_{d.replace('-', '')}.csv"
            if not f.exists():
                self._d[d] = {}
            else:
                b = pd.read_csv(f, usecols=lambda c: c in ("TckrSymb", "FinInstrmTp", "OpnIntrst"))
                b = b[b["FinInstrmTp"] == "STF"]
                self._d[d] = b.groupby(b["TckrSymb"].astype(str).str.strip())["OpnIntrst"].sum().to_dict()
        return self._d[d]

    def change(self, sym: str, cal: list[str], i: int, n: int = 5) -> float:
        if i < n + 1:
            return math.nan
        return pct(self.day(cal[i - 1]).get(sym), self.day(cal[i - 1 - n]).get(sym))


# ---------------------------------------------------------------- building the tables of features
def trade_rows(name: str, cal: list[str], daily: Daily, nifty: pd.Series, sectors: dict, members: dict,
               oi: FutOI, fin: dict, times: dict) -> pd.DataFrame:
    from .fade_timeline import option_ohlc
    from .peak_study import result_quality
    start, end, tag = WINDOWS[name]
    t = pd.read_csv(RES / f"S1_v10_trades{tag}.csv")
    vw = t[(t["entry"] == "vwap") & (t["e1_excluded"].fillna("") == "")].set_index(["symbol", "day0"])["e1_net_pct"]
    t = t[(t["entry"] == "open") & (t["e1_excluded"].fillna("") == "")].reset_index(drop=True)
    pos = {d: k for k, d in enumerate(cal)}
    rows = []
    for r in t.itertuples():
        i = pos.get(r.day0)
        if i is None:
            continue
        o = option_ohlc(r.day0, r.symbol, r.expiry, float(r.strike), r.side) or (math.nan,) * 4
        f = stock_features(daily.get(r.symbol), cal, i)
        nf = market_features(nifty, cal, i, r.day0)
        q = result_quality(fin, r.symbol, r.filed)
        sign = -1 if r.side == "PE" else 1                       # the fade's direction: puts gain when the stock falls
        spot = float(r.spot_prev_close)
        otm = (spot - float(r.strike)) / spot * 100 if r.side == "PE" else (float(r.strike) - spot) / spot * 100
        ftime = times.get((r.symbol, r.filed))
        rows.append({
            "window": name, "side": r.side, "symbol": r.symbol, "filed": r.filed, "filed_time": ftime, "day0": r.day0,
            "category": r.category, "np_yoy": r.np_yoy, "np_qoq": r.np_qoq, "rev_yoy": r.rev_yoy,
            "eps_yoy": q.get("eps_yoy"), "eps_qoq": q.get("eps_qoq"),
            "strike": r.strike, "expiry": r.expiry, "lot": r.lot, "entry": r.entry_price, "premium_rs": r.premium_rs,
            "opt_open": o[0], "opt_high": o[1], "opt_low": o[2], "opt_close": o[3],
            "peak_pct": pct(o[1], r.entry_price), "dip_pct": pct(o[2], r.entry_price),
            "net_pct": r.e1_net_pct, "net_rs": r.e1_net, "vwap_net_pct": vw.get((r.symbol, r.day0), math.nan),
            "loser_class": loser_class(pct(o[1], r.entry_price), r.e1_net_pct),
            **f, "stock_fade_pct": sign * f["oc"] if f["oc"] == f["oc"] else math.nan,
            **nf, "stock_fade_net_nifty": sign * (f["oc"] - nf["n_oc"]) if f["oc"] == f["oc"] else math.nan,
            "sector_cc": sector_cc(r.symbol, cal, i, daily, sectors, members),
            "pre5_net": f["pre5"] - nf["n_pre5"], "pre20_net": f["pre20"] - nf["n_pre20"],
            "oi5": oi.change(r.symbol, cal, i), "otm_pct": otm,
            "dte": sum(1 for d in cal[i + 1:] if d <= r.expiry) if r.expiry <= cal[-1] else math.nan,
            "filing": "pre-open" if (r.filed == r.day0 and ftime and ftime < "09:15") else "after close / overnight",
            "period": r.period})
        sc = rows[-1]["sector_cc"]
        rows[-1]["stock_fade_net_sector"] = sign * (f["cc"] - sc) if (f["cc"] == f["cc"] and sc == sc) else math.nan
    return pd.DataFrame(rows)


_NIFTY_DAY: dict[str, dict] = {}


def market_features(nifty: pd.Series, cal: list[str], i: int, d0: str) -> dict:
    c = nifty
    prev = cal[i - 1]
    if d0 not in _NIFTY_DAY:
        try:
            _NIFTY_DAY[d0] = index_ohlc(d0) or {}
        except Exception as exc:  # noqa: BLE001 - the day's index file unavailable: NaN, counted
            log.warning("NIFTY %s: %s", d0, exc)
            _NIFTY_DAY[d0] = {}
    k = _NIFTY_DAY[d0]
    return {"n_oc": pct(k.get("close"), k.get("open")), "n_cc": pct(c.get(d0, k.get("close")), c.get(prev)),
            "n_pre5": pct(c.get(prev), c.get(cal[i - 6])), "n_pre20": pct(c.get(prev), c.get(cal[i - 21]))}


def sector_cc(sym: str, cal: list[str], i: int, daily: Daily, sectors: dict, members: dict) -> float:
    k = sectors.get(sym)
    if not k:
        return math.nan
    d0, prev = cal[i], cal[i - 1]
    vals = []
    for p in members.get(k, ()):
        if p == sym:
            continue
        df = daily.get(p)
        if df is not None and d0 in df.index and prev in df.index:
            vals.append(pct(df.at[d0, "Close"], df.at[prev, "Close"]))
    vals = [v for v in vals if v == v]
    return float(np.mean(vals)) if len(vals) >= 3 else math.nan


def filing_rows(name: str, cal: list[str], daily: Daily, nifty: pd.Series, results: list) -> pd.DataFrame:
    """Q6: every results filing of an F&O stock with day 0 in the window, one per stock and day 0 (the earliest)."""
    from .backtest_s1_v2 import day0_index
    from .backtest_s1_v10 import Bhav
    start, end, _tag = WINDOWS[name]
    bhav = Bhav(BHAV)
    sess = sorted(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}" for p in BHAV.glob("fo_bhavcopy_*.csv"))
    pos = {d: k for k, d in enumerate(cal)}
    seen, rows = set(), []
    for sym, d, tm in sorted(results, key=lambda r: (r[1], r[2] or "99:99")):
        j = day0_index(sess, d, tm)
        if j is None or j < 1 or not start <= sess[j] <= end or (sym, sess[j]) in seen:
            continue
        seen.add((sym, sess[j]))
        prevday = bhav.day(sess[j - 1])
        if prevday is None or sym not in prevday["syms"]:
            continue
        i = pos.get(sess[j])
        if i is None:
            continue
        f = stock_features(daily.get(sym), cal, i)
        nf = market_features(nifty, cal, i, sess[j])
        rows.append({"window": name, "symbol": sym, "filed": d, "day0": sess[j], **f, **nf,
                     "pre5_net": f["pre5"] - nf["n_pre5"], "pre20_net": f["pre20"] - nf["n_pre20"],
                     "oc_net": f["oc"] - nf["n_oc"], "cc_net": f["cc"] - nf["n_cc"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- tables
def stats(v: pd.Series, dates: pd.Series) -> dict:
    from .stats import clustered_t
    v = pd.to_numeric(v, errors="coerce")
    m = v.notna()
    v, dates = v[m], dates[m]
    return {"n": int(len(v)), "mean": round(v.mean(), 2) if len(v) else None,
            "median": round(v.median(), 2) if len(v) else None,
            "hit_pct": round((v > 0).mean() * 100, 1) if len(v) else None,
            "t": clustered_t(v, dates) if len(v) > 1 else None}


BUCKETS = {
    # name: (column, side or None, cuts, labels)
    "NIFTY day-0 open->close": ("n_oc", None, [-0.3, 0.3], ["down < -0.3 %", "flat", "up > +0.3 %"]),
    "NIFTY day-0 close->close": ("n_cc", None, [-0.3, 0.3], ["down < -0.3 %", "flat", "up > +0.3 %"]),
    "Pre-run 20 sessions": ("pre20", None, [-5, 5], ["fell > 5 %", "-5 to +5 %", "rose > 5 %"]),
    "Pre-run 5 sessions": ("pre5", None, [-3, 3], ["fell > 3 %", "-3 to +3 %", "rose > 3 %"]),
    "Pre-run 20, net of NIFTY": ("pre20_net", None, [-5, 5], ["fell > 5 %", "-5 to +5 %", "rose > 5 %"]),
    "Pre-run 5, net of NIFTY": ("pre5_net", None, [-3, 3], ["fell > 3 %", "-3 to +3 %", "rose > 3 %"]),
    "Day-0 gap at the open": ("gap", None, [-2, 1.9999], ["gap down <= -2 %", "-2 to +2 %", "gap up >= +2 %"]),
    "Place in 52-week range": ("pos52", None, [0.33, 0.67], ["near the low", "middle", "near the high"]),
    "NP YoY (puts)": ("np_yoy", "PE", [25, 50, 100], ["10-25 %", "25-50 %", "50-100 %", "> 100 %"]),
    "NP QoQ (puts)": ("np_qoq", "PE", [10, 30], ["0-10 %", "10-30 %", "> 30 %"]),
    "Revenue YoY (puts)": ("rev_yoy", "PE", [10, 20], ["0-10 %", "10-20 %", "> 20 %"]),
    "NP YoY (calls)": ("np_yoy", "CE", [-50, -25], ["< -50 %", "-25 to -50 %", "-10 to -25 %"]),
    "NP QoQ (calls)": ("np_qoq", "CE", [-30, -10], ["< -30 %", "-10 to -30 %", "0 to -10 %"]),
    "Revenue YoY (calls)": ("rev_yoy", "CE", [0, 10], ["< 0 %", "0-10 %", "> 10 %"]),
    "EPS YoY (puts)": ("eps_yoy", "PE", [25, 50], ["<= 25 %", "25-50 %", "> 50 %"]),
    "EPS YoY (calls)": ("eps_yoy", "CE", [-50, -25], ["< -50 %", "-25 to -50 %", "> -25 %"]),
    "EPS QoQ (puts)": ("eps_qoq", "PE", [10, 30], ["<= 10 %", "10-30 %", "> 30 %"]),
    "EPS QoQ (calls)": ("eps_qoq", "CE", [-30, -10], ["< -30 %", "-10 to -30 %", "> -10 %"]),
    "Volume ratio day -1": ("vol_ratio", None, [1, 2], ["< 1x", "1-2x", "> 2x"]),
    "Futures OI 5-session change": ("oi5", None, [-5, 5], ["<= -5 %", "-5 to +5 %", "> +5 %"]),
    "Strike distance (% OTM)": ("otm_pct", None, [2, 5], ["< 2 %", "2-5 %", "> 5 %"]),
    "Sessions to expiry": ("dte", None, [5, 15], ["<= 5", "6-15", "> 15"]),
    "Sector day 0": ("sector_cc", None, [-0.5, 0.5], ["down < -0.5 %", "flat", "up > +0.5 %"]),
    "Filing time": ("filing", None, None, ["pre-open", "after close / overnight"]),          # categorical
}
QUESTION_OF = {"NIFTY": "Q2", "Pre-run": "Q3", "Day-0 gap": "Q3", "Place": "Q3", "NP": "Q4", "Revenue": "Q4",
               "EPS": "Q7", "Volume": "Q7", "Futures": "Q7", "Strike": "Q7", "Sessions": "Q7", "Sector": "Q7",
               "Filing": "Q7"}


def compare(f: pd.DataFrame) -> pd.DataFrame:
    """Every bucket of every BUCKETS entry, per side: per-window mean vs the rest of its side, the pooled date-clustered
    t of the difference, the VWAP-entry check and the consistency guard."""
    from .stats import clustered_diff_t
    rows = []
    for name, (col, only, cuts, labels) in BUCKETS.items():
        q = next(v for k, v in QUESTION_OF.items() if name.startswith(k))
        for side in (("PE", "CE") if only is None else (only,)):
            s = f[f["side"] == side].copy()
            s["b"] = s[col] if cuts is None else s[col].map(lambda x: bucket(x, cuts, labels))
            for lab in labels:
                row = {"question": q, "measure": name, "side": side, "bucket": lab}
                same_dir, signs = True, []
                for w in WINDOWS:
                    sw = s[s["window"] == w]
                    inb, rest = sw[sw["b"] == lab], sw[(sw["b"] != lab) & sw["b"].notna()]
                    d = (inb["net_pct"].mean() - rest["net_pct"].mean()) if len(inb) and len(rest) else math.nan
                    row.update({f"n {w}": len(inb), f"mean {w}": round(inb["net_pct"].mean(), 1) if len(inb) else None,
                                f"rest {w}": round(rest["net_pct"].mean(), 1) if len(rest) else None,
                                f"vwap {w}": round(inb["vwap_net_pct"].mean(), 1) if len(inb) else None})
                    signs.append(np.sign(d) if d == d else 0)
                inb, rest = s[s["b"] == lab], s[(s["b"] != lab) & s["b"].notna()]
                t = clustered_diff_t(inb["net_pct"], inb["day0"], rest["net_pct"], rest["day0"]) \
                    if len(inb) > 1 and len(rest) > 1 else None
                tv = clustered_diff_t(inb["vwap_net_pct"], inb["day0"], rest["vwap_net_pct"], rest["day0"]) \
                    if len(inb) > 1 and len(rest) > 1 else None
                same_dir = signs[0] != 0 and signs[0] == signs[1]
                enough = all(row[f"n {w}"] >= MIN_N for w in WINDOWS)
                stands = bool(enough and same_dir and t is not None and abs(t) >= MIN_T)
                row.update({"pooled diff t": t, "vwap diff t": tv, "same direction both windows": same_dir,
                            "N >= 30 both": enough, "STANDS OUT": "YES" if stands else "",
                            "only with open entry": "flag" if stands and (tv is None or np.sign(tv) != np.sign(t)) else ""})
                rows.append(row)
    return pd.DataFrame(rows)


def loser_anatomy(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for w in WINDOWS:
        for side in ("PE", "CE"):
            s = f[(f["window"] == w) & (f["side"] == side)]
            losers = s[s["net_pct"] < 0]
            row = {"window": w, "side": side, "trades": len(s), "losers": len(losers),
                   "losers %": round(len(losers) / len(s) * 100, 1) if len(s) else None}
            for c in ("never up", "round trip", "other"):
                g = losers[losers["loser_class"] == c]
                row[f"{c}: share of losers %"] = round(len(g) / len(losers) * 100, 1) if len(losers) else None
                row[f"{c}: mean net %"] = round(g["net_pct"].mean(), 1) if len(g) else None
                row[f"{c}: stock faded %"] = round((g["stock_fade_pct"] > 0).mean() * 100, 1) if len(g) else None
            rows.append(row)
    return pd.DataFrame(rows)


def two_by_two(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for w in WINDOWS:
        for side in ("PE", "CE"):
            s = f[(f["window"] == w) & (f["side"] == side) & f["stock_fade_pct"].notna()]
            for faded in (True, False):
                for won in (True, False):
                    g = s[((s["stock_fade_pct"] > 0) == faded) & ((s["net_pct"] > 0) == won)]
                    rows.append({"window": w, "side": side, "stock faded": "yes" if faded else "no",
                                 "option won": "yes" if won else "no", "n": len(g),
                                 "share %": round(len(g) / len(s) * 100, 1) if len(s) else None,
                                 "mean net %": round(g["net_pct"].mean(), 1) if len(g) else None,
                                 "mean stock fade %": round(g["stock_fade_pct"].mean(), 2) if len(g) else None,
                                 "mean strike OTM %": round(g["otm_pct"].mean(), 2) if len(g) else None})
    return pd.DataFrame(rows)


def fade_vs_market(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for w in WINDOWS:
        for side in ("PE", "CE", "all"):
            s = f[f["window"] == w] if side == "all" else f[(f["window"] == w) & (f["side"] == side)]
            for col, lab in (("stock_fade_pct", "stock fade, raw (open->close)"),
                             ("stock_fade_net_nifty", "stock fade net of NIFTY (open->close)"),
                             ("stock_fade_net_sector", "stock fade net of its sector (close->close)")):
                rows.append({"window": w, "side": side, "measure": lab, **stats(s[col], s["day0"])})
    return pd.DataFrame(rows)


def run_done_opposite(fl: pd.DataFrame) -> pd.DataFrame:
    """Q6 on every filing: reversal = -sign(pre-run) x day-0 reaction, by run size."""
    rows = []
    for w in WINDOWS:
        s = fl[fl["window"] == w]
        for pre in ("pre5", "pre20", "pre5_net", "pre20_net"):
            for react in (("oc", "cc") if not pre.endswith("_net") else ("oc_net", "cc_net")):
                for lab, lo, hi in (("run < 3 %", 0, 3), ("run 3-8 %", 3, 8), ("run > 8 %", 8, 1e9)):
                    g = s[(s[pre].abs() >= lo) & (s[pre].abs() < hi)]
                    rv = pd.Series([reversal(a, b) for a, b in zip(g[pre], g[react])], index=g.index)
                    st = stats(rv, g["day0"])
                    rows.append({"window": w, "pre-run": pre, "reaction": react, "run size": lab, **st,
                                 "moved opposite %": round((rv > 0).sum() / rv.notna().sum() * 100, 1)
                                 if rv.notna().sum() else None})
    return pd.DataFrame(rows)


def examples(f: pd.DataFrame) -> pd.DataFrame:
    e = f[f["symbol"].isin(EXAMPLES)].sort_values(["symbol", "day0"]).copy()

    def reading(r) -> str:
        bits = [f"{'put' if r.side == 'PE' else 'call'} {r.net_pct:+.0f} %",
                f"stock {'faded' if r.stock_fade_pct > 0 else 'moved WITH the numbers'} ({r.oc:+.1f} % open->close)",
                f"NIFTY {r.n_oc:+.1f} % that day", f"stock {r.pre20:+.1f} % in the 20 sessions before",
                f"option peak {r.peak_pct:+.0f} %, dip {r.dip_pct:+.0f} %"]
        return "; ".join(bits)
    e["reading"] = [reading(r) for r in e.itertuples()]
    keep = ["symbol", "day0", "side", "np_yoy", "np_qoq", "rev_yoy", "entry", "net_pct", "peak_pct", "dip_pct",
            "loser_class", "oc", "stock_fade_pct", "n_oc", "pre5", "pre20", "pre20_net", "gap", "reading"]
    return e[keep]


# ---------------------------------------------------------------- run
def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    from .events.store import Store
    from .financials import load as load_fin
    from .sectors import load_map
    nifty = nifty_closes()
    cal = list(nifty.index)
    daily, oi, fin = Daily(), FutOI(), load_fin()
    sectors = load_map()
    members: dict[str, list[str]] = {}
    for s, k in sectors.items():
        members.setdefault(k, []).append(s)
    with Store() as st:
        res = [(e["symbol"], e["event_date"], e.get("event_time")) for e in st.all_of_type("results")]
    times = {}
    for sym, d, tm in res:
        if tm and (sym, d) not in times or (tm and tm < times[(sym, d)]):
            times[(sym, d)] = tm
    f = pd.concat([trade_rows(w, cal, daily, nifty, sectors, members, oi, fin, times) for w in WINDOWS],
                  ignore_index=True)
    fl = pd.concat([filing_rows(w, cal, daily, nifty, res) for w in WINDOWS], ignore_index=True)
    return f, fl


def write(f: pd.DataFrame, fl: pd.DataFrame, answers: str | None = None) -> None:
    import xlsxwriter
    from .backtest_s1_v2 import md
    RES.mkdir(parents=True, exist_ok=True)
    f.to_csv(RES / "S1_v10_fade_diag_features.csv", index=False)
    fl.to_csv(RES / "S1_v10_fade_diag_filings.csv", index=False)
    cmp_ = compare(f)
    tables = [
        ("Q1 Loser anatomy", "Q1 · Losers: never up (peak < +10 %), round trip (peak >= +30 %, then a loss), other",
         loser_anatomy(f)),
        ("Q1 Stock vs option", "Q1 · Did the stock fade? Did the option win? (2x2)", two_by_two(f)),
        ("Q2 Fade vs market", "Q2 · The stock's fade: raw, net of NIFTY 50, net of its sector", fade_vs_market(f)),
        ("Buckets (Q2-Q4, Q7)", "Q2-Q4, Q7 · Every bucket vs the rest of its side (net % of premium, open entry)", cmp_),
        ("Q6 Run done->opposite", "Q6 · All results filings of F&O stocks: does day 0 move opposite to the pre-run?",
         run_done_opposite(fl)),
        ("Q5 Your 9 stocks", "Q5 · The user's example stocks: every fade trade", examples(f)),
    ]
    head = ("Descriptive only (strategies/S1_v10_fade_diagnostics.md). Not out of sample; "
            f"{len(cmp_)} bucket tests were run, so a few will pass by chance. A bucket STANDS OUT only with N >= 30 and "
            "the same direction in both windows and |pooled date-clustered t| >= 2.")
    counts = (f"Fade trades: {len(f)} ({', '.join(f'{w} {int((f.window == w).sum())}' for w in WINDOWS)}); "
              f"results filings (Q6): {len(fl)} ({', '.join(f'{w} {int((fl.window == w).sum())}' for w in WINDOWS)}).")
    text = ["# S1 v10 fade · diagnostics\n", head + "\n", counts + "\n"]
    if answers:
        text += ["## Answers (verified)\n", answers + "\n"]
    stand = cmp_[cmp_["STANDS OUT"] == "YES"]
    text += ["## Buckets that stand out\n", md(stand) if len(stand) else "None.\n"]
    for _sheet, title, df in tables:
        text += [f"## {title}\n", md(df)]
    (RES / "S1_v10_fade_diagnostics.md").write_text("\n".join(text), encoding="utf-8")

    wb = xlsxwriter.Workbook(RES / "S1_v10_fade_diagnostics.xlsx")
    F = lambda **k: wb.add_format({"font_name": "Arial", "font_size": 10, **k})         # noqa: E731
    H = F(bold=True, font_color="#FFFFFF", bg_color="#1F3864", text_wrap=True, align="center", valign="vcenter", border=1)
    yes = F(bold=True, bg_color="#E2F0E4")
    note = F(italic=True, font_size=9, font_color="#595959")
    num = F(num_format="0.0;[Red]-0.0")

    def table(ws, r0, df, wide=None):
        ws.set_row(r0, 42)
        for c, h in enumerate(df.columns):
            ws.write(r0, c, str(h), H)
            ws.set_column(c, c, (wide or {}).get(str(h), 12))
        for i, row in enumerate(df.itertuples(index=False), 1):
            for c, v in enumerate(row):
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    ws.write_blank(r0 + i, c, None)
                elif isinstance(v, (bool, np.bool_)):
                    ws.write(r0 + i, c, "yes" if v else "no", F())
                elif isinstance(v, (int, float, np.integer, np.floating)):
                    ws.write_number(r0 + i, c, float(v), num)
                else:
                    ws.write(r0 + i, c, str(v), yes if v == "YES" else F())
        return r0 + len(df) + 2

    ws = wb.add_worksheet("Answers")
    ws.set_column(0, 0, 140)
    ws.write(0, 0, "S1 v10 fade · diagnostics: answers to your questions", F(bold=True, font_size=13))
    ws.write(1, 0, head, note)
    ws.write(2, 0, counts, note)
    for k, line in enumerate((answers or "Answers are added after the verification run.").splitlines()):
        ws.write(4 + k, 0, line, F(text_wrap=True, valign="top"))
    wide = {"measure": 26, "bucket": 16, "reading": 110, "pre-run": 10, "run size": 10}
    for sheet, title, df in tables:
        w = wb.add_worksheet(sheet[:31])
        w.write(0, 0, title, F(bold=True, font_size=12))
        table(w, 2, df, wide)
        w.freeze_panes(3, 0)
    wb.close()
    print("\n".join(text[:6]))


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v10 fade diagnostics (descriptive)")
    ap.add_argument("--answers", type=Path, help="a text file with the verified plain-language answers")
    ap.add_argument("--reuse", action="store_true", help="reuse the feature CSVs instead of rebuilding them")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if a.reuse:
        f = pd.read_csv(RES / "S1_v10_fade_diag_features.csv")
        fl = pd.read_csv(RES / "S1_v10_fade_diag_filings.csv")
    else:
        f, fl = build()
    write(f, fl, a.answers.read_text(encoding="utf-8") if a.answers else None)


if __name__ == "__main__":
    main()
