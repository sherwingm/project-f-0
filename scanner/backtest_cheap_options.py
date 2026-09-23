"""Backtest of cheap, near-expiry stock options, from NSE's own F&O bhavcopies. Prints numbers only.

    python -m scanner.backtest_cheap_options --months 12 --max-premium 2 --dte 3 7 --out data/backtest_cheap.csv

For every session in the window, every stock option in that day's bhavcopy with 0 < ClsPric <= max-premium
and dte-min..dte-max sessions to expiry becomes one row: date, symbol, contract, strike, premium, spot
(UndrlygPric), sessions to expiry, lot size, volume, OI, and the scanner's label for the stock that day
(scanner.classify on that day's futures OI/PCR from the bhavcopy plus eod2 price change and volume ratio).
One lot is bought at the close + 1 tick; cost = entry x lot + buy-leg charges (server/charges.py). Outcomes:
    (a) exit   sell at the option's close `--hold` (3) sessions later - 1 tick, less sell-leg charges. A sale that
               would not cover its own charges is not made: payoff 0.
    (b) expiry hold to expiry: intrinsic value from the expiry-day underlying close (UndrlygPric in that day's
               bhavcopy, else eod2's close) less STT on exercise. Physical-settlement delivery costs are not modelled.
    net = payoff - cost; multiple = payoff / cost.
Needs a machine that can reach nsearchives.nseindia.com. Bhavcopies are cached under data/cache/ and fetched
at most once a second.
"""
from __future__ import annotations

import argparse
import bisect
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd

from server import charges as ch

from .binomial import binomial_line
from .build import ROOT
from .classify import BEARISH, BULLISH, UNCLASSIFIED, classify
from .equity import INDEX_FILE, equity_metrics_one, load_symbol
from .nse_fo import BhavcopyUnavailable, download_fo_bhavcopy, fo_metrics
from .universe import fetch_fo_lots

log = logging.getLogger("backtest")
TICK = 0.05
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


@dataclass
class Inputs:
    sessions: list[date]                           # trading calendar, sorted
    bhav: Callable[[date], pd.DataFrame | None]    # that session's F&O bhavcopy (STO/STF rows are enough)
    equity: Callable[[str], pd.DataFrame | None]   # eod2 frame per symbol: Date index, Close and Volume
    lots: dict[str, int]                           # fallback lot sizes when the bhavcopy has no NewBrdLotQty


def sessions_to(cal: list[date], d: date, e: date) -> int:
    """Sessions after d up to and including e (expiry day = 0 sessions away); weekdays past the calendar's end."""
    n = bisect.bisect_right(cal, min(e, cal[-1])) - bisect.bisect_right(cal, d)
    x = cal[-1] + timedelta(days=1)
    while x <= e:
        n += x.weekday() < 5
        x += timedelta(days=1)
    return n


def contract_name(sym: str, expiry: date, strike: float, typ: str) -> str:
    k = int(strike) if float(strike).is_integer() else strike
    return f"{sym}{expiry:%y}{MONTHS[expiry.month - 1]}{k}{typ}"


def run(inp: Inputs, start: date, end: date, max_premium: float = 2.0, dte: tuple[int, int] = (3, 7), hold: int = 3,
        tick: float = TICK, min_volume: int = 0) -> pd.DataFrame:
    cal = inp.sessions
    pos = {d: i for i, d in enumerate(cal)}
    prices: OrderedDict = OrderedDict()                   # small LRU of {contract key: close} per session
    expiry_spot: dict[date, dict[str, float]] = {}
    frames: dict[str, pd.DataFrame | None] = {}
    rows: list[dict] = []

    def closes_on(day: date) -> dict | None:
        if day in prices:
            prices.move_to_end(day)
            return prices[day]
        b = inp.bhav(day)
        m = None
        if b is not None:
            s = b[b["FinInstrmTp"] == "STO"]
            m = {(t, _d(x), float(k), o): float(c) for t, x, k, o, c in
                 zip(s["TckrSymb"], s["XpryDt"], s["StrkPric"], s["OptnTp"], s["ClsPric"])}
        prices[day] = m
        if len(prices) > 12:
            prices.popitem(last=False)
        return m

    def spot_at_expiry(sym: str, e: date) -> float | None:
        if e not in expiry_spot:
            b = inp.bhav(e) if e in pos else None
            expiry_spot[e] = {} if b is None else \
                b[b["UndrlygPric"] > 0].groupby("TckrSymb")["UndrlygPric"].first().astype(float).to_dict()
        v = expiry_spot[e].get(sym)
        if v is None:                                    # no bhavcopy for that day: eod2's close
            f = frame(sym)
            ts = pd.Timestamp(e)
            if f is not None and ts in f.index:
                v = float(f.loc[ts, "Close"])
        return v

    def frame(sym: str):
        if sym not in frames:
            try:
                frames[sym] = inp.equity(sym)
            except Exception as exc:  # noqa: BLE001
                log.warning("%s: no eod2 data (%s)", sym, exc)
                frames[sym] = None
        return frames[sym]

    days = [d for d in cal if start <= d <= end]
    for n_day, d in enumerate(days, 1):
        b = inp.bhav(d)
        if b is None:
            continue
        sto = b[b["FinInstrmTp"] == "STO"]
        cheap = sto[(sto["ClsPric"] > 0) & (sto["ClsPric"] <= max_premium) & (sto["TtlTradgVol"] >= min_volume)]
        if cheap.empty:
            continue
        exps = {x: sessions_to(cal, d, _d(x)) for x in cheap["XpryDt"].unique()}
        cheap = cheap[cheap["XpryDt"].map(exps).between(dte[0], dte[1])]
        if cheap.empty:
            continue
        fo = {r["symbol"]: r for r in fo_metrics(b).to_dict("records")}
        labels: dict[str, str] = {}
        i = pos[d]
        exit_day = cal[i + hold] if i + hold < len(cal) else None
        exit_closes = closes_on(exit_day) if exit_day else None
        has_lot = "NewBrdLotQty" in cheap.columns
        for r in cheap.to_dict("records"):
            sym, e, k, typ = r["TckrSymb"], _d(r["XpryDt"]), float(r["StrkPric"]), r["OptnTp"]
            if sym not in labels:
                labels[sym] = _label(sym, d, frame(sym), fo.get(sym))
            lot = int(r["NewBrdLotQty"]) if has_lot and pd.notna(r.get("NewBrdLotQty")) and r["NewBrdLotQty"] > 0 else inp.lots.get(sym)
            if not lot:
                continue
            premium = float(r["ClsPric"])
            entry = round(premium + tick, 2)
            cost = entry * lot + ch.leg(typ, "BUY", lot, entry)["total"]
            row = {"date": d.isoformat(), "symbol": sym, "contract": contract_name(sym, e, k, typ), "type": typ, "strike": k,
                   "expiry": e.isoformat(), "premium": premium, "spot": float(r["UndrlygPric"]) if r["UndrlygPric"] > 0 else None,
                   "dte": exps[r["XpryDt"]], "lot": lot, "volume": int(r["TtlTradgVol"]), "oi": int(r["OpnIntrst"]),
                   "label": labels[sym], "entry_price": entry, "cost": round(cost, 2)}
            # (a) sell `hold` sessions later at that close - 1 tick
            xc = exit_closes.get((sym, e, k, typ)) if exit_closes is not None else None
            if exit_day is None or xc is None:
                row.update({"exit_date": exit_day.isoformat() if exit_day else None, "exit_close": None,
                            "exit_payoff": None, "exit_net": None, "exit_multiple": None})
            else:
                sell = max(0.0, round(xc - tick, 2))
                proceeds = sell * lot - (ch.leg(typ, "SELL", lot, sell)["total"] if sell > 0 else 0.0)
                payoff = max(0.0, proceeds)
                row.update({"exit_date": exit_day.isoformat(), "exit_close": xc, "exit_payoff": round(payoff, 2),
                            "exit_net": round(payoff - cost, 2), "exit_multiple": round(payoff / cost, 4)})
            # (b) hold to expiry: intrinsic from the expiry-day underlying close, less exercise STT
            s_exp = spot_at_expiry(sym, e) if e <= cal[-1] else None
            if s_exp is None:
                row.update({"expiry_spot": None, "intrinsic": None, "expiry_payoff": None, "expiry_net": None, "expiry_multiple": None})
            else:
                intrinsic = max(0.0, s_exp - k) if typ == "CE" else max(0.0, k - s_exp)
                payoff = intrinsic * lot - ch.exercise(lot, intrinsic)["total"]
                row.update({"expiry_spot": s_exp, "intrinsic": round(intrinsic, 2), "expiry_payoff": round(payoff, 2),
                            "expiry_net": round(payoff - cost, 2), "expiry_multiple": round(payoff / cost, 4)})
            rows.append(row)
        if n_day % 20 == 0:
            log.info("%s: %d of %d sessions, %d contracts so far", d, n_day, len(days), len(rows))
    return pd.DataFrame(rows)


def _label(sym: str, d: date, frame: pd.DataFrame | None, fo: dict | None) -> str:
    if frame is None:
        return UNCLASSIFIED
    m = equity_metrics_one(sym, frame, as_of=pd.Timestamp(d))
    if not m or m["date"] != d.isoformat():
        return UNCLASSIFIED
    fo = fo or {}
    clean = lambda v: None if v is None or pd.isna(v) else float(v)
    return classify({**m, "oi_change_pct": clean(fo.get("oi_change_pct")), "pcr": clean(fo.get("pcr"))})["label"]


def _d(x) -> date:
    if isinstance(x, date) and not isinstance(x, datetime):
        return x
    return pd.Timestamp(x).date()


# ---------------------------------------------------------------- summary
OUTCOMES = (("exit", "(a) sell at the option's close {hold} sessions later - 1 tick, net of charges"),
            ("expiry", "(b) hold to expiry: intrinsic from the expiry-day underlying close, net of charges and exercise STT"))


def groups(df: pd.DataFrame, dte: tuple[int, int]) -> list[tuple[str, pd.Series]]:
    ce, pe = df["type"] == "CE", df["type"] == "PE"
    g = [("all cheap calls", ce), ("all cheap calls traded that day (volume > 0)", ce & (df["volume"] > 0)),
         ("calls on Bullish-labelled stocks", ce & (df["label"] == BULLISH)),
         ("all cheap puts", pe), ("puts on Bearish-labelled stocks", pe & (df["label"] == BEARISH))]
    g += [(f"calls, {k} sessions to expiry", ce & (df["dte"] == k)) for k in range(dte[0], dte[1] + 1)]
    g += [(f"puts, {k} sessions to expiry", pe & (df["dte"] == k)) for k in range(dte[0], dte[1] + 1)]
    return g


def summarise(df: pd.DataFrame, dte: tuple[int, int]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for key, _ in OUTCOMES:
        rows = []
        for name, mask in groups(df, dte) if len(df) else []:
            sub = df[mask & df[f"{key}_net"].notna()]
            n = len(sub)
            wins = int((sub[f"{key}_net"] > 0).sum())
            mult = sub[f"{key}_multiple"]
            rows.append({"group": name, "count": n, "wins": wins, "pct_positive": round(wins / n * 100, 2) if n else None,
                         "mean_multiple": round(float(mult.mean()), 4) if n else None,
                         "median_multiple": round(float(mult.median()), 4) if n else None,
                         "best_multiple": round(float(mult.max()), 4) if n else None,
                         "worst_multiple": round(float(mult.min()), 4) if n else None,
                         "net_per_1000": round(float(sub[f"{key}_net"].sum() / sub["cost"].sum() * 1000), 2) if n else None,
                         "binomial": binomial_line(wins, n)})
        out[key] = rows
    return out


def print_table(summary: dict[str, list[dict]], hold: int, header: str = "") -> None:
    if header:
        print(header)
    for key, title in OUTCOMES:
        print()
        print(title.format(hold=hold))
        print(f"{'group':<46}{'count':>8}{'net>0 %':>9}{'mean x':>9}{'median x':>10}{'best x':>9}{'worst x':>9}{'net per Rs1,000':>17}")
        for r in summary[key]:
            f = lambda v, w, p=2: f"{v:>{w}.{p}f}" if v is not None else f"{'-':>{w}}"
            print(f"{r['group']:<46}{r['count']:>8}{f(r['pct_positive'], 9)}{f(r['mean_multiple'], 9, 3)}"
                  f"{f(r['median_multiple'], 10, 3)}{f(r['best_multiple'], 9, 2)}{f(r['worst_multiple'], 9, 3)}{f(r['net_per_1000'], 17)}")
            print(f"    {r['binomial']}")


# ---------------------------------------------------------------- inputs from the network / caches
class NseInputs:
    """Real inputs: eod2's NIFTY 50 dates as the calendar (extended with any later sessions NSE has a bhavcopy
    for), bhavcopies from data/cache or NSE (one download a second), eod2 frames, NSE's current lot sizes."""

    def __init__(self, eod2_dir: Path, cache_dir: Path, today: date | None = None):
        self.eod2_dir, self.cache_dir = eod2_dir, cache_dir
        self._last_download = 0.0
        self._cache: OrderedDict = OrderedDict()
        self.missing: list[date] = []
        idx = _read_index(eod2_dir)
        cal = [d.date() for d in idx.index]
        today = today or date.today()
        x = cal[-1] + timedelta(days=1)
        while x < today:                          # sessions after eod2's last date that NSE has published
            if x.weekday() < 5 and self.bhav(x, probe=True) is not None:
                cal.append(x)
            x += timedelta(days=1)
        self.sessions = cal
        self.eod2_last = idx.index[-1].date()
        self.lots = fetch_fo_lots(cache_path=cache_dir / "fo_universe.txt")

    def bhav(self, day: date, probe: bool = False) -> pd.DataFrame | None:
        if day in self._cache:
            self._cache.move_to_end(day)
            return self._cache[day]
        cached = (self.cache_dir / f"fo_bhavcopy_{day:%Y%m%d}.csv").exists()
        if not cached:
            wait = 1.0 - (time.monotonic() - self._last_download)
            if wait > 0:
                time.sleep(wait)
            self._last_download = time.monotonic()
        try:
            df = download_fo_bhavcopy(day, cache_dir=self.cache_dir)
            df = df[df["FinInstrmTp"].isin(["STO", "STF"])].reset_index(drop=True)
        except BhavcopyUnavailable as exc:
            if not probe:                         # a probed weekday with no file is a holiday, not a gap
                log.warning("%s: %s", day, exc)
                self.missing.append(day)
            df = None
        self._cache[day] = df
        if len(self._cache) > 8:
            self._cache.popitem(last=False)
        return df

    def equity(self, sym: str) -> pd.DataFrame | None:
        return load_symbol(sym, self.eod2_dir)


def _read_index(eod2_dir: Path) -> pd.DataFrame:
    path = eod2_dir / f"{INDEX_FILE}.csv"
    if not path.exists():
        from .equity import index_closes
        index_closes(eod2_dir, pd.Timestamp.today())      # downloads and caches the file
    df = pd.read_csv(path, usecols=["Date", "Close"], parse_dates=["Date"])
    return df[df["Close"] > 0].set_index("Date").sort_index()


def main() -> None:
    ap = argparse.ArgumentParser(description="Backtest cheap near-expiry stock options from NSE bhavcopies (numbers only)")
    ap.add_argument("--months", type=int, default=12)
    ap.add_argument("--max-premium", type=float, default=2.0)
    ap.add_argument("--dte", type=int, nargs=2, default=[3, 7], metavar=("MIN", "MAX"), help="sessions to expiry, inclusive")
    ap.add_argument("--hold", type=int, default=3, help="sessions until the outcome (a) exit")
    ap.add_argument("--min-volume", type=int, default=0, help="only contracts that traded at least this many that day")
    ap.add_argument("--tick", type=float, default=TICK)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "backtest_cheap.csv")
    ap.add_argument("--eod2-dir", type=Path, default=ROOT / "data" / "eod2")
    ap.add_argument("--cache-dir", type=Path, default=ROOT / "data" / "cache")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    inp = NseInputs(a.eod2_dir, a.cache_dir)
    end = inp.eod2_last                                   # labels need eod2 price/volume for the day
    start = (pd.Timestamp(end) - pd.DateOffset(months=a.months)).date() + timedelta(days=1)
    log.info("window %s to %s (%d sessions); calendar runs to %s", start, end,
             sum(start <= d <= end for d in inp.sessions), inp.sessions[-1])
    df = run(Inputs(inp.sessions, inp.bhav, inp.equity, inp.lots), start, end, a.max_premium, tuple(a.dte), a.hold, a.tick, a.min_volume)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    header = (f"Cheap stock options: ClsPric <= Rs {a.max_premium:g}, {a.dte[0]}-{a.dte[1]} sessions to expiry, "
              f"{start} to {end}; one lot bought at the close + {a.tick:g}. {len(df)} contracts -> {a.out}"
              + (f"; no bhavcopy for {len(inp.missing)} session(s): {', '.join(map(str, inp.missing[:8]))}" if inp.missing else ""))
    print_table(summarise(df, tuple(a.dte)), a.hold, header)


if __name__ == "__main__":
    main()
