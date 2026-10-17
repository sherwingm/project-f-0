"""S1 v10 fade · diagnostics (strategies/S1_v10_fade_diagnostics.md, with its 2026-10-18 addendum). Descriptive only.

    python -m scanner.fade_diagnostics            # features + tables -> data/results/S1_v10_fade_diagnostics.md / .xlsx
    python -m scanner.fade_diagnostics --answers FILE   # also put the verified plain-language answers in the report
    python -m scanner.fade_diagnostics --reuse    # rebuild the tables from the feature CSVs

Why losers lose (Q1), the market vs the stock's own move (Q2), the pre-run (Q3, Q6), the three result numbers (Q4), the
user's example stocks (Q5) and other measures (Q7), on the 2022-24 and 2025-26 fade trades and on every results filing.
"""
from __future__ import annotations

import argparse
import io
import logging
import math
from datetime import date
from pathlib import Path
from statistics import NormalDist

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
MIN_N, MIN_DATES, MIN_T, MIN_T_EACH = 30, 15, 2.0, 1.0
CA_JUMP = 20.0                                           # a one-day move above this inside a look-back blanks the feature
SPECIAL_OUT = {"2022-10-24": "Muhurat", "2023-11-12": "Muhurat", "2024-03-02": "short special session",
               "2024-05-18": "short special session", "2024-11-01": "Muhurat", "2025-10-21": "Muhurat"}
SPECIAL_KEPT = {"2024-01-20": "full Saturday session", "2025-02-01": "budget day", "2026-02-01": "budget day"}
SLOTS = ["pre-open day 0", "in session day -1", "after close day -1", "non-session day / earlier"]


# ---------------------------------------------------------------- pure helpers
def pct(a, b):
    """(a / b - 1) x 100, NaN when either is missing or b <= 0."""
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return math.nan
    return (a / b - 1) * 100 if b > 0 and not (math.isnan(a) or math.isnan(b)) else math.nan


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return math.nan


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


def filing_slot(cal: list[str], i: int, filed: str, ftime: str | None) -> tuple[str, int]:
    """(slot, index of the last close before the filing) for a filing whose day 0 is cal[i]."""
    t = str(ftime or "")[:5]
    if filed == cal[i]:
        return SLOTS[0], i - 1
    if filed == cal[i - 1] and t:
        if "09:15" <= t < "15:30":
            return SLOTS[1], i - 2                       # day -1's close already holds part of the reaction
        if t >= "15:30":
            return SLOTS[2], i - 1
    if filed == cal[i - 1]:
        return "time unknown", i - 1
    return SLOTS[3], i - 1


def pooled_t(t1, t2) -> float | None:
    """Two independent windows' t combined: (t1 + t2) / sqrt(2)."""
    return None if t1 is None or t2 is None else round((t1 + t2) / math.sqrt(2), 3)


def chance_consistent(n_tests: int, draws: int = 400_000) -> float:
    """Expected number of buckets passing the 'consistent' test when nothing is real (independent N(0,1) t's)."""
    z = np.random.default_rng(0).standard_normal((draws, 2))
    ok = (np.sign(z[:, 0]) == np.sign(z[:, 1])) & (np.abs(z).min(axis=1) >= MIN_T_EACH) \
        & (np.abs(z.sum(axis=1)) / math.sqrt(2) >= MIN_T)
    return round(float(ok.mean()) * n_tests, 1)


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


def jump_days(c: pd.Series, cal: list[str], lo: int, hi: int) -> set[str]:
    """Dates in cal[lo..hi] whose close moved more than CA_JUMP % from the previous available close."""
    sub = c.reindex(cal[max(0, lo):hi + 1]).dropna()
    r = (sub / sub.shift(1) - 1).abs()
    return set(sub.index[r > CA_JUMP / 100])


def stock_features(df: pd.DataFrame | None, cal: list[str], i: int, base: int | None = None) -> dict:
    """Pre-runs 5/20/60, 52-week place, distance below the 52-week high and volume ratio, all ending at cal[base] (the
    last close before the filing; default day -1), and day 0's gap, open->close, close->close, the reaction before
    entry (open vs cal[base]), the whole reaction (close vs cal[base]) and the day range."""
    base = i - 1 if base is None else base
    keys = ("pre5", "pre20", "pre60", "pos52", "dd52", "vol_ratio", "gap", "oc", "cc", "full", "pre_entry",
            "s_open", "s_high", "s_low", "s_close", "range_pct")
    out = {k: math.nan for k in keys}
    out["ca_blank"] = ""
    if df is None or base < 61:
        return out
    c = df["Close"]
    cb = _num(c.get(cal[base]))
    jumps = jump_days(c, cal, base - 252, base)
    blank = []
    for n in (5, 20, 60):
        if any(cal[base - n] < d <= cal[base] for d in jumps):
            blank.append(f"pre{n}")
        else:
            out[f"pre{n}"] = pct(cb, c.get(cal[base - n]))
    win = df.loc[(df.index >= cal[max(0, base - 251)]) & (df.index <= cal[base])]
    if jumps:
        blank.append("pos52")
    elif len(win) > 50 and cb == cb:
        lo, hi = win["Low"].min(), win["High"].max()
        out["pos52"] = (cb - lo) / (hi - lo) if hi > lo else math.nan
        out["dd52"] = pct(cb, hi)
    vol, bd = df["Volume"], cal[base]
    before = vol.loc[vol.index < bd].tail(20)
    if bd in vol.index and len(before) >= 10 and before.mean() > 0:
        out["vol_ratio"] = float(vol[bd]) / float(before.mean())
    d0, cprev = cal[i], c.get(cal[i - 1])
    if d0 in df.index:
        o, h, lo_, cl = (_num(df.at[d0, k]) for k in ("Open", "High", "Low", "Close"))
        out.update(gap=pct(o, cprev), oc=pct(cl, o), cc=pct(cl, cprev), full=pct(cl, cb), pre_entry=pct(o, cb),
                   s_open=o, s_high=h, s_low=lo_, s_close=cl, range_pct=(h - lo_) / o * 100 if o > 0 else math.nan)
    out["ca_blank"] = ",".join(blank)
    return out


def beta(c: pd.Series | None, nifty: pd.Series, cal: list[str], base: int, n: int = 250) -> float:
    """The stock's beta to NIFTY 50 from up to n daily close->close returns ending at cal[base] (>= 150 needed)."""
    if c is None or base < n:
        return math.nan
    ds = cal[base - n:base + 1]
    s, m = c.reindex(ds), nifty.reindex(ds)
    rs, rm = s / s.shift(1) - 1, m / m.shift(1) - 1
    ok = rs.notna() & rm.notna() & (rs.abs() <= CA_JUMP / 100)
    if ok.sum() < 150:
        return math.nan
    x, y = rm[ok].to_numpy(dtype=float), rs[ok].to_numpy(dtype=float)
    v = x.var()
    return float(((x - x.mean()) * (y - y.mean())).mean() / v) if v > 0 else math.nan


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


class OptDay:
    """Day-0 option rows from the bhavcopy price file, one day held at a time (trades come sorted by day)."""

    def __init__(self, cache: Path = BHAV):
        self.cache, self.day, self.rows = cache, None, {}

    def get(self, day: str, sym: str, expiry: str, strike: float, side: str):
        if day != self.day:
            self.day, self.rows = day, {}
            f = self.cache / f"fo_prices_{day.replace('-', '')}.csv"
            if f.exists():
                p = pd.read_csv(f)
                p["TckrSymb"] = p["TckrSymb"].astype(str).str.strip()
                p["XpryDt"] = p["XpryDt"].astype(str).str[:10]
                self.rows = {(r.TckrSymb, r.XpryDt, float(r.StrkPric), r.OptnTp): r for r in p.itertuples(index=False)}
        return self.rows.get((sym, expiry, float(strike), side))


def nifty_closes() -> pd.Series:
    f = pd.read_csv(EOD2 / "nifty 50.csv", parse_dates=["Date"])
    s = f.set_index(f["Date"].dt.strftime("%Y-%m-%d"))["Close"]
    return s[~s.index.duplicated(keep="last")].sort_index()


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

    def change(self, sym: str, cal: list[str], base: int, n: int = 5) -> float:
        if base < n:
            return math.nan
        return pct(self.day(cal[base]).get(sym), self.day(cal[base - n]).get(sym))


_NIFTY_DAY: dict[str, dict] = {}


def market_features(nifty: pd.Series, cal: list[str], i: int, d0: str, base: int | None = None) -> dict:
    base = i - 1 if base is None else base
    if d0 not in _NIFTY_DAY:
        try:
            _NIFTY_DAY[d0] = index_ohlc(d0) or {}
        except Exception as exc:  # noqa: BLE001 - the day's index file unavailable: NaN, counted
            log.warning("NIFTY %s: %s", d0, exc)
            _NIFTY_DAY[d0] = {}
    k, c = _NIFTY_DAY[d0], nifty
    nb, close0 = c.get(cal[base]), c.get(d0, k.get("close"))
    return {"n_open": k.get("open", math.nan), "n_oc": pct(k.get("close"), k.get("open")),
            "n_cc": pct(close0, c.get(cal[i - 1])), "n_full": pct(close0, nb), "n_pre_entry": pct(k.get("open"), nb),
            "n_pre5": pct(nb, c.get(cal[base - 5])), "n_pre20": pct(nb, c.get(cal[base - 20]))}


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


# ---------------------------------------------------------------- building the tables of features
def trade_rows(name: str, cal: list[str], daily: Daily, nifty: pd.Series, sectors: dict, members: dict,
               oi: FutOI, fin: dict, times: dict) -> pd.DataFrame:
    from .backtest_s1_v4 import SLIPPAGE
    from .backtest_s1_v10 import net_of
    from .option_engine import TICK, premium_vwap
    from .peak_study import result_quality
    _start, _end, tag = WINDOWS[name]
    t = pd.read_csv(RES / f"S1_v10_trades{tag}.csv")
    vw = t[(t["entry"] == "vwap") & (t["e1_excluded"].fillna("") == "")].set_index(["symbol", "day0"])["e1_net_pct"]
    t = t[(t["entry"] == "open") & (t["e1_excluded"].fillna("") == "")].sort_values(["day0", "symbol"])
    pos = {d: k for k, d in enumerate(cal)}
    opt, rows = OptDay(), []
    for r in t.itertuples():
        i = pos.get(r.day0)
        if i is None:
            log.warning("%s %s: day 0 not in the NIFTY calendar", r.symbol, r.day0)
            continue
        ftime = times.get((r.symbol, r.filed))
        slot, base = filing_slot(cal, i, r.filed, ftime)
        df = daily.get(r.symbol)
        f = stock_features(df, cal, i, base)
        nf = market_features(nifty, cal, i, r.day0, base)
        b = beta(df["Close"] if df is not None else None, nifty, cal, base)
        q = result_quality(fin, r.symbol, r.filed)
        o = opt.get(r.day0, r.symbol, r.expiry, float(r.strike), r.side)
        oo, oh, ol, oc_ = ((_num(o.OpnPric), _num(o.HghPric), _num(o.LwPric), _num(o.ClsPric)) if o is not None
                           else (math.nan,) * 4)
        lot = int(r.lot)
        same = math.nan                                  # VWAP entry on the SAME contract, same 15:20 exit
        if o is not None:
            v = premium_vwap(_num(o.TtlTrfVal), _num(o.TtlTradgVol), _num(o.NewBrdLotQty) or lot, float(r.strike),
                             ol, oh)
            if v is not None:
                fill = round(v + TICK, 2)
                slip = SLIPPAGE.get(r.category, SLIPPAGE["unknown"])
                same = round(net_of(r.side, fill, float(r.e1_exit_price), lot, slip)[2] / (fill * lot) * 100, 3)
        sign = -1 if r.side == "PE" else 1                       # the fade's direction: puts gain when the stock falls
        spot = float(r.spot_prev_close)
        otm = (spot - float(r.strike)) / spot * 100 if r.side == "PE" else (float(r.strike) - spot) / spot * 100
        so = spot * (1 + f["gap"] / 100) if f["gap"] == f["gap"] else math.nan
        otm_open = ((so - float(r.strike)) / so * 100 if r.side == "PE" else (float(r.strike) - so) / so * 100) \
            if so == so else math.nan
        best = ((f["s_open"] - f["s_low"]) if r.side == "PE" else (f["s_high"] - f["s_open"])) / f["s_open"] * 100 \
            if f["s_open"] > 0 else math.nan                     # the stock's best move in the bet's direction
        fade = sign * f["oc"] if f["oc"] == f["oc"] else math.nan
        rows.append({
            "window": name, "side": r.side, "symbol": r.symbol, "filed": r.filed, "filed_time": ftime, "day0": r.day0,
            "filing": slot, "special": SPECIAL_OUT.get(r.day0) or SPECIAL_KEPT.get(r.day0) or "",
            "excluded": "special session" if r.day0 in SPECIAL_OUT else "",
            "category": r.category, "np_yoy": r.np_yoy, "np_qoq": r.np_qoq, "rev_yoy": r.rev_yoy,
            "eps_yoy": q.get("eps_yoy"), "eps_qoq": q.get("eps_qoq"), "loss_quarter": q.get("loss_quarter"),
            "strike": r.strike, "expiry": r.expiry, "lot": lot, "entry": r.entry_price, "premium_rs": r.premium_rs,
            "opt_open": oo, "opt_high": oh, "opt_low": ol, "opt_close": oc_,
            "peak_pct": pct(oh, r.entry_price), "dip_pct": pct(ol, r.entry_price),
            "net_pct": r.e1_net_pct, "net_rs": r.e1_net, "vwap_net_pct": same,
            "vwap_walk_net_pct": vw.get((r.symbol, r.day0), math.nan),
            "loser_class": loser_class(pct(oh, r.entry_price), r.e1_net_pct),
            **f, "stock_fade_pct": fade, "stock_best_pct": best, "backtest_stock_oc_signed": r.stock_oc_signed_pct,
            **nf, "beta": b,
            "stock_fade_net_nifty": sign * (f["oc"] - nf["n_oc"]) if fade == fade else math.nan,
            "stock_fade_net_beta": sign * (f["oc"] - b * nf["n_oc"]) if fade == fade and b == b else math.nan,
            "sector_cc": sector_cc(r.symbol, cal, i, daily, sectors, members),
            "pre5_net": f["pre5"] - nf["n_pre5"], "pre20_net": f["pre20"] - nf["n_pre20"],
            "pre_entry_net": f["pre_entry"] - nf["n_pre_entry"],
            "oi5": oi.change(r.symbol, cal, base), "otm_pct": otm, "otm_open_pct": otm_open,
            "dte": sum(1 for d in cal[i + 1:] if d <= r.expiry) if r.expiry <= cal[-1] else math.nan,
            "period": r.period})
        sc = rows[-1]["sector_cc"]
        rows[-1]["stock_fade_net_sector"] = sign * (f["cc"] - sc) if (f["cc"] == f["cc"] and sc == sc) else math.nan
    out = pd.DataFrame(rows)
    g = out.groupby("day0")["net_pct"]
    out["n_same_day"], out["won_same_day"] = g.transform("size"), g.transform(lambda s: int((s > 0).sum()))
    return out


def filing_rows(name: str, cal: list[str], daily: Daily, nifty: pd.Series, results: list, fin: dict) -> pd.DataFrame:
    """Q6 / Q4 extension: every results filing of an F&O stock with day 0 in the window, one per stock and day 0 (the
    earliest), with the filing's numbers where data/financials.json has them."""
    from .backtest_s1_v2 import day0_index
    from .backtest_s1_v10 import Bhav
    from .event_screens import num_or_none
    from .peak_study import result_quality
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
        slot, base = filing_slot(cal, i, d, tm)
        df = daily.get(sym)
        f = stock_features(df, cal, i, base)
        nf = market_features(nifty, cal, i, sess[j], base)
        b = beta(df["Close"] if df is not None else None, nifty, cal, base)
        q = result_quality(fin, sym, d)
        rows.append({"window": name, "symbol": sym, "filed": d, "filed_time": tm, "day0": sess[j], "filing": slot,
                     "excluded": "special session" if sess[j] in SPECIAL_OUT else "",
                     "np_yoy": num_or_none(q.get("net_profit_yoy")), "np_qoq": num_or_none(q.get("net_profit_qoq")),
                     "rev_yoy": num_or_none(q.get("revenue_yoy")), **f, **nf, "beta": b,
                     "pre5_net": f["pre5"] - nf["n_pre5"], "pre20_net": f["pre20"] - nf["n_pre20"],
                     "oc_net": f["oc"] - nf["n_oc"], "cc_net": f["cc"] - nf["n_cc"],
                     "full_net": f["full"] - nf["n_full"], "pre_entry_net": f["pre_entry"] - nf["n_pre_entry"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- tables
def stats(v: pd.Series, dates: pd.Series) -> dict:
    from .stats import clustered_t
    v = pd.to_numeric(v, errors="coerce")
    m = v.notna()
    v, dates = v[m], dates[m]
    return {"n": int(len(v)), "dates": int(dates.nunique()), "mean": round(v.mean(), 2) if len(v) else None,
            "median": round(v.median(), 2) if len(v) else None,
            "hit_pct": round((v > 0).mean() * 100, 1) if len(v) else None,
            "t": clustered_t(v, dates) if len(v) > 1 else None}


BUCKETS = {
    # name: (column, side or None, cuts, labels); cuts None = categorical
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
    "Filing time": ("filing", None, None, SLOTS),
    "Reaction before entry": ("pre_entry", None, [-2, 1.9999], ["<= -2 %", "-2 to +2 %", ">= +2 %"]),
}
QUESTION_OF = {"NIFTY": "Q2", "Pre-run": "Q3", "Day-0 gap": "Q3", "Place": "Q3", "NP": "Q4", "Revenue": "Q4",
               "EPS": "Q7", "Volume": "Q7", "Futures": "Q7", "Strike": "Q7", "Sessions": "Q7", "Sector": "Q7",
               "Filing": "Q7", "Reaction": "Q7"}


def compare(f: pd.DataFrame) -> pd.DataFrame:
    """Every bucket of every BUCKETS entry, per side: per window, the bucket vs the rest of its side (date-clustered t
    of the difference), for the net % (open entry), the same-contract VWAP entry and the stock's own fade; the pooled
    t = (t1 + t2) / sqrt(2) and the consistency guard (consistent / STRONG)."""
    from .stats import clustered_diff_t
    rows = []
    for name, (col, only, cuts, labels) in BUCKETS.items():
        q = next(v for k, v in QUESTION_OF.items() if name.startswith(k))
        for side in (("PE", "CE") if only is None else (only,)):
            s = f[f["side"] == side].copy()
            s["b"] = s[col].where(s[col].isin(labels)) if cuts is None else s[col].map(lambda x: bucket(x, cuts, labels))
            for lab in labels:
                row = {"question": q, "measure": name, "side": side, "bucket": lab}
                ts = {"net_pct": [], "vwap_net_pct": [], "stock_fade_pct": []}
                for w in WINDOWS:
                    sw = s[s["window"] == w]
                    inb, rest = sw[sw["b"] == lab], sw[(sw["b"] != lab) & sw["b"].notna()]
                    ok = len(inb) > 1 and len(rest) > 1
                    for k in ts:
                        ts[k].append(clustered_diff_t(inb[k], inb["day0"], rest[k], rest["day0"]) if ok else None)
                    d = inb["net_pct"].mean() - rest["net_pct"].mean() if ok else math.nan
                    row.update({
                        f"n {w}": len(inb), f"dates {w}": int(inb["day0"].nunique()),
                        f"mean {w}": round(inb["net_pct"].mean(), 1) if len(inb) else None,
                        f"rest {w}": round(rest["net_pct"].mean(), 1) if len(rest) else None,
                        f"median {w}": round(inb["net_pct"].median(), 1) if len(inb) else None,
                        f"hit % {w}": round((inb["net_pct"] > 0).mean() * 100, 0) if len(inb) else None,
                        f"t {w}": ts["net_pct"][-1],
                        f"detectable diff {w}": round(2 * abs(d / ts["net_pct"][-1]), 0)
                        if ok and ts["net_pct"][-1] not in (None, 0) else None,
                        f"vwap mean {w}": round(inb["vwap_net_pct"].mean(), 1) if len(inb) else None,
                        f"stock fade {w}": round(inb["stock_fade_pct"].mean(), 2) if len(inb) else None,
                        f"stock fade rest {w}": round(rest["stock_fade_pct"].mean(), 2) if len(rest) else None})
                t1, t2 = ts["net_pct"]
                pt, pv, ps = (pooled_t(*ts[k]) for k in ("net_pct", "vwap_net_pct", "stock_fade_pct"))
                enough = all(row[f"n {w}"] >= MIN_N and row[f"dates {w}"] >= MIN_DATES for w in WINDOWS)
                same = t1 is not None and t2 is not None and np.sign(t1) == np.sign(t2) != 0
                consistent = bool(enough and same and min(abs(t1), abs(t2)) >= MIN_T_EACH and abs(pt) >= MIN_T)
                s1, s2 = ts["stock_fade_pct"]
                stock_cons = bool(enough and s1 is not None and s2 is not None and np.sign(s1) == np.sign(s2) != 0
                                  and min(abs(s1), abs(s2)) >= MIN_T_EACH and abs(ps) >= MIN_T)
                row.update({"pooled t": pt, "vwap pooled t": pv, "stock fade pooled t": ps,
                            "enough both (N>=30, dates>=15)": enough, "verdict": "consistent" if consistent else "",
                            "only with the open entry": "flag" if consistent and (pv is None or np.sign(pv) != np.sign(pt)
                                                                                    or abs(pv) < MIN_T_EACH) else "",
                            "stock fade verdict": "consistent" if stock_cons else ""})
                rows.append(row)
    out = pd.DataFrame(rows)
    z = NormalDist().inv_cdf(1 - 0.025 / max(1, len(out)))
    out.loc[(out["verdict"] == "consistent") & (out["pooled t"].abs() >= z), "verdict"] = "STRONG"
    out.loc[(out["stock fade verdict"] == "consistent") & (out["stock fade pooled t"].abs() >= z),
            "stock fade verdict"] = "STRONG"
    out.attrs["z_bonferroni"] = round(z, 2)
    return out


def coverage(f: pd.DataFrame, fl: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for w in WINDOWS:
        a, b = f[f["window"] == w], fl[fl["window"] == w]
        rows += [
            {"window": w, "item": "fade trades (open entry, same-day exit)", "count": len(a)},
            {"window": w, "item": "  left out: special session (Muhurat / short)", "count": int((a["excluded"] != "").sum())},
            {"window": w, "item": "  kept but flagged: full special session / budget day",
             "count": int(a["day0"].isin(SPECIAL_KEPT).sum())},
            {"window": w, "item": "  no NIFTY day-0 open", "count": int(a["n_oc"].isna().sum())},
            {"window": w, "item": "  no stock day-0 prices (eod2)", "count": int(a["oc"].isna().sum())},
            {"window": w, "item": "  a feature blanked by a > 20 % one-day move", "count": int((a["ca_blank"].fillna("") != "").sum())},
            {"window": w, "item": "  no beta", "count": int(a["beta"].isna().sum())},
            {"window": w, "item": "  no same-contract VWAP", "count": int(a["vwap_net_pct"].isna().sum())},
            *({"window": w, "item": f"  filing slot: {s}", "count": int((a["filing"] == s).sum())}
              for s in SLOTS + ["time unknown"]),
            {"window": w, "item": "results filings of F&O stocks (Q6)", "count": len(b)},
            {"window": w, "item": "  left out: special session", "count": int((b["excluded"] != "").sum())},
            {"window": w, "item": "  with all three numbers (Q4 curves)",
             "count": int(b[["np_yoy", "np_qoq", "rev_yoy"]].notna().all(axis=1).sum())},
            {"window": w, "item": "  filed in session day -1", "count": int((b["filing"] == SLOTS[1]).sum())}]
    return pd.DataFrame(rows)


def loser_anatomy(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for w in WINDOWS:
        for side in ("PE", "CE"):
            s = f[(f["window"] == w) & (f["side"] == side)]
            losers = s[s["net_pct"] < 0]
            lost = losers["net_rs"].sum()
            row = {"window": w, "side": side, "trades": len(s), "losers": len(losers),
                   "losers %": round(len(losers) / len(s) * 100, 1) if len(s) else None}
            for c in ("never up", "round trip", "other"):
                g = losers[losers["loser_class"] == c]
                row[f"{c}: n"] = len(g)
                row[f"{c}: share of losers %"] = round(len(g) / len(losers) * 100, 1) if len(losers) else None
                row[f"{c}: share of rupees lost %"] = round(g["net_rs"].sum() / lost * 100, 1) if lost else None
                row[f"{c}: mean net %"] = round(g["net_pct"].mean(), 1) if len(g) else None
                row[f"{c}: stock faded %"] = round((g["stock_fade_pct"] > 0).mean() * 100, 1) if len(g) else None
                row[f"{c}: stock best move % (median)"] = round(g["stock_best_pct"].median(), 2) if len(g) else None
                row[f"{c}: strike OTM at open % (median)"] = round(g["otm_open_pct"].median(), 2) if len(g) else None
                row[f"{c}: sessions to expiry (median)"] = g["dte"].median() if len(g) else None
            row["never up: option high <= entry (n)"] = int((losers["peak_pct"] <= 0).sum())
            win = s[s["net_pct"] >= 0]
            row["winners: stock best move % (median)"] = round(win["stock_best_pct"].median(), 2) if len(win) else None
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
                                 "median stock best move %": round(g["stock_best_pct"].median(), 2) if len(g) else None,
                                 "median strike OTM at open %": round(g["otm_open_pct"].median(), 2) if len(g) else None,
                                 "median sessions to expiry": g["dte"].median() if len(g) else None})
    return pd.DataFrame(rows)


def fade_vs_market(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for w in WINDOWS:
        for side in ("PE", "CE", "all"):
            s = f[f["window"] == w] if side == "all" else f[(f["window"] == w) & (f["side"] == side)]
            for col, lab in (("stock_fade_pct", "stock fade, raw (open->close)"),
                             ("stock_fade_net_nifty", "stock fade net of NIFTY, beta 1 (open->close)"),
                             ("stock_fade_net_beta", "stock fade net of beta x NIFTY (open->close)"),
                             ("stock_fade_net_sector", "stock fade net of its sector (close->close)"),
                             ("net_pct", "option net % of premium (open entry)")):
                rows.append({"window": w, "side": side, "measure": lab, **stats(s[col], s["day0"])})
            sign = s["side"].map({"PE": -1, "CE": 1})
            rows.append({"window": w, "side": side, "measure": "the market's part: sign x beta x NIFTY open->close",
                         **stats(sign * s["beta"] * s["n_oc"], s["day0"])})
            rows.append({"window": w, "side": side, "measure": "beta (250 sessions)", **stats(s["beta"], s["day0"])})
    return pd.DataFrame(rows)


def run_done_opposite(fl: pd.DataFrame) -> pd.DataFrame:
    """Q6 on every filing: reversal = -sign(pre-run) x day-0 reaction, by run size."""
    rows = []
    react = {"oc": "day-0 open->close", "full": "close before filing -> day-0 close",
             "oc_net": "day-0 open->close, net of NIFTY", "full_net": "close before filing -> day-0 close, net of NIFTY"}
    for w in WINDOWS:
        s = fl[fl["window"] == w]
        for pre in ("pre5", "pre20", "pre5_net", "pre20_net"):
            for rc in (("oc", "full") if not pre.endswith("_net") else ("oc_net", "full_net")):
                for lab, lo, hi in (("run < 3 %", 0, 3), ("run 3-8 %", 3, 8), ("run > 8 %", 8, 1e9)):
                    g = s[(s[pre].abs() >= lo) & (s[pre].abs() < hi)]
                    rv = pd.Series([reversal(a, b) for a, b in zip(g[pre], g[rc])], index=g.index)
                    st = stats(rv, g["day0"])
                    rows.append({"window": w, "pre-run": pre, "reaction": react[rc], "run size": lab, **st,
                                 "moved opposite %": round((rv > 0).sum() / rv.notna().sum() * 100, 1)
                                 if rv.notna().sum() else None})
    return pd.DataFrame(rows)


CURVES = {
    "NP YoY %": ("np_yoy", [-50, -25, -10, 0, 10, 25, 50, 100],
                 ["< -50", "-50 to -25", "-25 to -10", "-10 to 0", "0 to 10", "10 to 25", "25 to 50", "50 to 100",
                  "> 100"]),
    "NP QoQ %": ("np_qoq", [-30, -10, 0, 10, 30], ["< -30", "-30 to -10", "-10 to 0", "0 to 10", "10 to 30", "> 30"]),
    "Revenue YoY %": ("rev_yoy", [0, 10, 20], ["< 0", "0 to 10", "10 to 20", "> 20"]),
}


def number_curves(fl: pd.DataFrame) -> pd.DataFrame:
    """Q4 extension: every filing with numbers, the stock's day-0 open->close net of NIFTY and its reaction before entry,
    by bins over each number's whole range (a fade = good numbers fall on day 0, bad numbers rise)."""
    rows = []
    for name, (col, cuts, labels) in CURVES.items():
        for w in WINDOWS:
            s = fl[(fl["window"] == w) & fl[col].notna()].copy()
            s["b"] = s[col].map(lambda x: bucket(x - 1e-9, cuts, labels))        # bins are lower-open, upper-closed
            for lab in labels:
                g = s[s["b"] == lab]
                a, r = stats(g["oc_net"], g["day0"]), stats(g["pre_entry_net"], g["day0"])
                rows.append({"number": name, "window": w, "bin": lab, "filings": a["n"], "dates": a["dates"],
                             "reaction before entry, net of NIFTY %": r["mean"], "t (before entry)": r["t"],
                             "day-0 open->close, net of NIFTY %": a["mean"], "t (day 0)": a["t"],
                             "day 0 up %": a["hit_pct"]})
    return pd.DataFrame(rows)


def examples(f: pd.DataFrame) -> pd.DataFrame:
    e = f[f["symbol"].isin(EXAMPLES)].sort_values(["symbol", "day0"]).copy()

    def reading(r) -> str:
        fade = "nan" if r.stock_fade_pct != r.stock_fade_pct else \
            ("faded" if r.stock_fade_pct > 0 else "moved WITH the numbers")
        bits = [f"{'put' if r.side == 'PE' else 'call'} {r.net_pct:+.0f} %", f"stock {fade} ({r.oc:+.1f} % open->close)",
                f"NIFTY {r.n_oc:+.1f} % open->close", f"stock {r.pre20:+.1f} % in the 20 sessions before "
                f"({r.dd52:+.0f} % from its 52-week high)", f"option peak {r.peak_pct:+.0f} %, dip {r.dip_pct:+.0f} %",
                f"{r.won_same_day} of {r.n_same_day} fade trades won that day"]
        return "; ".join(bits)
    e["reading"] = [reading(r) for r in e.itertuples()]
    keep = ["symbol", "day0", "side", "filing", "np_yoy", "np_qoq", "rev_yoy", "entry", "net_pct", "peak_pct", "dip_pct",
            "loser_class", "oc", "stock_fade_pct", "n_oc", "beta", "stock_fade_net_beta", "pre5", "pre20", "pre20_net",
            "dd52", "gap", "pre_entry", "n_same_day", "won_same_day", "reading"]
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
    times: dict = {}
    for sym, d, tm in res:
        if tm and ((sym, d) not in times or tm < times[(sym, d)]):
            times[(sym, d)] = tm
    f = pd.concat([trade_rows(w, cal, daily, nifty, sectors, members, oi, fin, times) for w in WINDOWS],
                  ignore_index=True)
    log.info("trade features done: %d rows", len(f))
    fl = pd.concat([filing_rows(w, cal, daily, nifty, res, fin) for w in WINDOWS], ignore_index=True)
    log.info("filing features done: %d rows", len(fl))
    return f, fl


def write(f: pd.DataFrame, fl: pd.DataFrame, answers: str | None = None) -> None:
    import xlsxwriter
    from .backtest_s1_v2 import md
    RES.mkdir(parents=True, exist_ok=True)
    f.to_csv(RES / "S1_v10_fade_diag_features.csv", index=False)
    fl.to_csv(RES / "S1_v10_fade_diag_filings.csv", index=False)
    fk = f[f["excluded"].fillna("") == ""]
    flk = fl[fl["excluded"].fillna("") == ""]
    cmp_ = compare(fk)
    z = cmp_.attrs["z_bonferroni"]
    tables = [
        ("Coverage", "Coverage: what was counted, left out or blanked", coverage(f, fl)),
        ("Q1 Loser anatomy", "Q1 · Losers: never up (peak < +10 %), round trip (peak >= +30 %, then a loss), other",
         loser_anatomy(fk)),
        ("Q1 Stock vs option", "Q1 · Did the stock fade? Did the option win? (2x2)", two_by_two(fk)),
        ("Q2 Fade vs market", "Q2 · The stock's fade: raw, net of NIFTY 50 (beta 1 and beta), net of its sector",
         fade_vs_market(fk)),
        ("Buckets (Q2-Q4, Q7)", "Q2-Q4, Q7 · Every bucket vs the rest of its side (net % of premium, open entry)", cmp_),
        ("Q4 Numbers, all filings", "Q4 · All filings with numbers: the stock's day-0 move by NP YoY / NP QoQ / revenue "
                                    "YoY bin (a fade = good numbers fall, bad numbers rise)", number_curves(flk)),
        ("Q6 Run done->opposite", "Q6 · All results filings of F&O stocks: does day 0 move opposite to the pre-run?",
         run_done_opposite(flk)),
        ("Q5 Your 9 stocks", "Q5 · The user's example stocks: every fade trade (picked with hindsight: illustrations)",
         examples(fk)),
    ]
    n_cons = int((cmp_["verdict"] != "").sum())
    head = ("Descriptive only (strategies/S1_v10_fade_diagnostics.md and its 2026-10-18 addendum). Not out of sample. "
            f"{len(cmp_)} bucket tests were run; by chance alone about {chance_consistent(len(cmp_))} would come out "
            f"'consistent' (N >= 30 and >= 15 dates in both windows, same sign, |t| >= 1 in each, |pooled t| >= 2); "
            f"STRONG needs |pooled t| >= {z} (Bonferroni 5 % for {len(cmp_)} tests). Found: {n_cons} consistent, "
            f"{int((cmp_['verdict'] == 'STRONG').sum())} STRONG.")
    counts = (f"Fade trades: {len(fk)} ({', '.join(f'{w} {int((fk.window == w).sum())}' for w in WINDOWS)}); "
              f"results filings (Q6): {len(flk)} ({', '.join(f'{w} {int((flk.window == w).sum())}' for w in WINDOWS)}).")
    text = ["# S1 v10 fade · diagnostics\n", head + "\n", counts + "\n"]
    if answers:
        text += ["## Answers (verified)\n", answers + "\n"]
    stand = cmp_[(cmp_["verdict"] != "") | (cmp_["stock fade verdict"] != "")]
    text += ["## Buckets that pass the guard (option net % or the stock's own fade)\n",
             md(stand) if len(stand) else "None.\n"]
    for _sheet, title, df in tables:
        text += [f"## {title}\n", md(df)]
    (RES / "S1_v10_fade_diagnostics.md").write_text("\n".join(text), encoding="utf-8")

    wb = xlsxwriter.Workbook(RES / "S1_v10_fade_diagnostics.xlsx")
    F = lambda **k: wb.add_format({"font_name": "Arial", "font_size": 10, **k})         # noqa: E731
    H = F(bold=True, font_color="#FFFFFF", bg_color="#1F3864", text_wrap=True, align="center", valign="vcenter", border=1)
    yes = F(bold=True, bg_color="#E2F0E4")
    note = F(italic=True, font_size=9, font_color="#595959", text_wrap=True)
    num = F(num_format="0.0;[Red]-0.0")

    def table(ws, r0, df, wide=None):
        ws.set_row(r0, 54)
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
                    ws.write(r0 + i, c, str(v), yes if v in ("consistent", "STRONG") else F())
        return r0 + len(df) + 2

    ws = wb.add_worksheet("Answers")
    ws.set_column(0, 0, 140)
    ws.write(0, 0, "S1 v10 fade · diagnostics: answers to your questions", F(bold=True, font_size=13))
    ws.write(1, 0, head, note)
    ws.set_row(1, 40)
    ws.write(2, 0, counts, note)
    for k, line in enumerate((answers or "Answers are added after the verification run.").splitlines()):
        ws.write(4 + k, 0, line, F(text_wrap=True, valign="top", bold=line.startswith("Q")))
    wide = {"measure": 30, "bucket": 16, "reading": 120, "pre-run": 10, "run size": 10, "item": 50, "number": 14}
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
