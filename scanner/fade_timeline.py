"""S1 v10 fade · intraday timeline and stop-loss study 2025-2026 (descriptive; strategies/S1_v10_stoploss_study_2025_26.md).

    python -m scanner.fade_timeline --fetch     # day-0 1-minute stock candles via the live server -> data/cache/intraday/
    python -m scanner.fade_timeline             # the study -> data/results/S1_v10_stoploss_study.md and .xlsx

Option minute prices for expired contracts are not available (NSE's free files: the day's OHLC only; Kotak's history
cannot look up expired contracts), so each trade's option path is a PROXY built from the stock's 1-minute candles:
P(t) = O + b x (S(t) - S0), b = s x (option high - option low) / (stock high - stock low), s = -1 puts, +1 calls.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .build import ROOT
from .option_engine import TICK

log = logging.getLogger("fade_timeline")
IST = timezone(timedelta(hours=5, minutes=30))
CACHE = ROOT / "data" / "cache" / "intraday"
LIVE_URL = "https://fo-scanner.onrender.com"
SELL_AT = "15:20"
FLOOR = 0.05


@dataclass(frozen=True)
class Exit:
    name: str
    label: str
    sl: float | None = None          # sell when the proxy low <= sl x entry
    tp: float | None = None          # sell when the proxy high >= tp x entry
    trail: float | None = None       # once above the entry: sell when the proxy low <= trail x the highest value so far
    sl_from: str = "09:15"           # the stop is armed from this minute


EXITS = (
    Exit("same_day", "Same day 15:20, no stop (the live rule)"),
    Exit("sl20", "Stop -20 %", sl=0.80), Exit("sl30", "Stop -30 %", sl=0.70), Exit("sl40", "Stop -40 %", sl=0.60),
    Exit("tp30", "Target +30 %", tp=1.30), Exit("tp50", "Target +50 %", tp=1.50), Exit("tp100", "Target +100 %", tp=2.00),
    Exit("sl20_tp30", "Stop -20 % + target +30 %", sl=0.80, tp=1.30),
    Exit("sl20_tp50", "Stop -20 % + target +50 %", sl=0.80, tp=1.50),
    Exit("sl30_tp50", "Stop -30 % + target +50 %", sl=0.70, tp=1.50),
    Exit("trail25", "Trail 25 % below the highest value", trail=0.75),
    Exit("sl20_from0945", "Stop -20 % armed from 09:45", sl=0.80, sl_from="09:45"),
)


# ---------------------------------------------------------------- pure rules
def hm(ts: int) -> str:
    return datetime.fromtimestamp(ts, IST).strftime("%H:%M")


def stock_bars(candles: list[dict]) -> list[tuple[str, float, float, float, float]]:
    """(HH:MM, open, high, low, close) from 09:15 to 15:29, in time order."""
    out = [(hm(c["time"]), c["open"], c["high"], c["low"], c["close"]) for c in sorted(candles, key=lambda c: c["time"])]
    return [b for b in out if "09:15" <= b[0] <= "15:29"]


def proxy(bars, side: str, o_open: float, o_high: float, o_low: float):
    """The proxy option path [(HH:MM, open, high, low, close)], or None when the stock did not move."""
    if not bars or not o_open or o_open <= 0:
        return None
    s_hi, s_lo = max(b[2] for b in bars), min(b[3] for b in bars)
    if s_hi <= s_lo:
        return None
    b = (-1 if side == "PE" else 1) * (o_high - o_low) / (s_hi - s_lo)
    s0 = bars[0][1]
    f = lambda s: max(FLOOR, o_open + b * (s - s0))                     # noqa: E731
    return [(t, f(op), max(f(h), f(lo)), min(f(h), f(lo)), f(cl)) for t, op, h, lo, cl in bars]


def proxy_range(bars, side: str, o_high: float, o_low: float):
    """Proxy B (addendum): the option's real day range laid onto the stock's: the real high at the stock's low (puts) or
    high (calls), the real low at the other extreme."""
    if not bars or o_high is None or o_low is None:
        return None
    s_hi, s_lo = max(b[2] for b in bars), min(b[3] for b in bars)
    if s_hi <= s_lo:
        return None
    f = (lambda x: (s_hi - x) / (s_hi - s_lo)) if side == "PE" else (lambda x: (x - s_lo) / (s_hi - s_lo))
    g = lambda x: max(FLOOR, o_low + (o_high - o_low) * f(x))          # noqa: E731
    return [(t, g(op), max(g(h), g(lo)), min(g(h), g(lo)), g(cl)) for t, op, h, lo, cl in bars]


def sell_value(path) -> tuple[str, float]:
    """The value at 15:20: the open of the 15:20 minute (else the last minute before it)."""
    at = next((p for p in path if p[0] == SELL_AT), None)
    if at is not None:
        return SELL_AT, at[1]
    before = [p for p in path if p[0] < SELL_AT]
    return (before[-1][0], before[-1][4]) if before else (path[-1][0], path[-1][4])


def run_exit(path, entry: float, ex: Exit) -> tuple[float, str, str]:
    """(exit price, reason, HH:MM). Minutes before 15:20 are checked in order; within a minute the stop is assumed to
    come before the target (the cautious order). Stops and targets fill at their level; the trail at its level."""
    peak = entry
    for t, _op, hi, lo, _cl in path:
        if t >= SELL_AT:
            break
        if ex.sl and t >= ex.sl_from and lo <= ex.sl * entry:
            return ex.sl * entry, "stop", t
        if ex.trail and peak > entry and lo <= ex.trail * peak:
            return ex.trail * peak, "trail", t
        if ex.tp and hi >= ex.tp * entry:
            return ex.tp * entry, "target", t
        peak = max(peak, hi)
    t, v = sell_value(path)
    return v, "15:20", t


def timeline(path, entry: float) -> dict:
    pk = max(path, key=lambda p: p[2])
    dp = min(path, key=lambda p: p[3])
    first = lambda cond: next((p[0] for p in path if cond(p)), None)     # noqa: E731
    t20, v20 = sell_value(path)
    return {"peak": pk[2], "peak_time": pk[0], "peak_pct": (pk[2] / entry - 1) * 100,
            "dip": dp[3], "dip_time": dp[0], "dip_pct": (dp[3] / entry - 1) * 100,
            "peak_first": path.index(pk) < path.index(dp) or (path.index(pk) == path.index(dp)),
            "touch_m20": first(lambda p: p[3] <= 0.80 * entry), "touch_p30": first(lambda p: p[2] >= 1.30 * entry),
            "touch_p50": first(lambda p: p[2] >= 1.50 * entry), "proxy_1520": v20}


def minutes_after_open(t: str | None) -> float | None:
    if t is None:
        return None
    h, m = (int(x) for x in t.split(":"))
    return (h * 60 + m) - (9 * 60 + 15)


def half_hour(t: str) -> str:
    h, m = (int(x) for x in t.split(":"))
    m0 = 0 if m < 30 else 30
    return f"{h:02d}:{m0:02d}"


# ---------------------------------------------------------------- data
def trades(tag: str = "") -> pd.DataFrame:
    t = pd.read_csv(ROOT / "data" / "results" / f"S1_v10_trades{tag}.csv")
    return t[(t["entry"] == "open") & (t["e1_excluded"].fillna("") == "")].sort_values(["day0", "symbol"]).reset_index(drop=True)


def cache_file(sym: str, day: str, cache: Path = CACHE) -> Path:
    return cache / f"{sym}_{day}.json"


def fetch(t: pd.DataFrame, url: str = LIVE_URL, cache: Path = CACHE, pause: float = 0.3) -> dict:
    import requests
    cache.mkdir(parents=True, exist_ok=True)
    done = failed = 0
    for sym, day in sorted(set(zip(t["symbol"], t["day0"]))):
        f = cache_file(sym, day, cache)
        if f.exists():
            continue
        for attempt in range(3):
            try:
                r = requests.get(f"{url}/api/history/{sym}", params={"day": day, "tf": 1}, timeout=150)
                if r.status_code == 503:
                    raise RuntimeError("market hours: the server refuses history now")
                r.raise_for_status()
                body = r.json()
                f.write_text(json.dumps(body), encoding="utf-8")
                done += 1
                break
            except RuntimeError:
                raise
            except Exception as exc:  # noqa: BLE001 - retry, then count
                log.warning("%s %s attempt %d: %s", sym, day, attempt + 1, exc)
                time.sleep(5)
        else:
            failed += 1
        time.sleep(pause)
        if (done + failed) % 25 == 0:
            log.info("%d fetched, %d failed", done, failed)
    return {"fetched": done, "failed": failed}


def option_ohlc(day: str, sym: str, expiry: str, strike: float, side: str) -> tuple[float, float, float, float] | None:
    p = pd.read_csv(ROOT / "data" / "cache" / f"fo_prices_{day.replace('-', '')}.csv",
                    usecols=["TckrSymb", "XpryDt", "StrkPric", "OptnTp", "OpnPric", "HghPric", "LwPric", "ClsPric"])
    m = p[(p["TckrSymb"].astype(str).str.strip() == sym) & (p["XpryDt"].astype(str).str[:10] == expiry)
          & (p["StrkPric"] == strike) & (p["OptnTp"] == side)]
    if m.empty:
        return None
    r = m.iloc[0]
    return float(r["OpnPric"]), float(r["HghPric"]), float(r["LwPric"]), float(r["ClsPric"])


# ---------------------------------------------------------------- the study
def study(t: pd.DataFrame, kind: str = "A", cache: Path = CACHE) -> tuple[pd.DataFrame, dict]:
    from .backtest_s1_v4 import SLIPPAGE
    from .backtest_s1_v10 import net_of
    rows, excl = [], {"no_minute_history": 0, "stock_did_not_move": 0, "no_option_prices": 0}
    for r in t.itertuples():
        f = cache_file(r.symbol, r.day0, cache)
        body = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        bars = stock_bars(body.get("candles") or [])
        if len(bars) < 30:
            excl["no_minute_history"] += 1
            continue
        ohlc = option_ohlc(r.day0, r.symbol, r.expiry, float(r.strike), r.side)
        if ohlc is None:
            excl["no_option_prices"] += 1
            continue
        path = proxy(bars, r.side, ohlc[0], ohlc[1], ohlc[2]) if kind == "A" else \
            proxy_range(bars, r.side, ohlc[1], ohlc[2])
        if path is None:
            excl["stock_did_not_move"] += 1
            continue
        entry, lot = float(r.entry_price), int(r.lot)
        slip = SLIPPAGE.get(r.category, SLIPPAGE["unknown"])
        tl = timeline(path, entry)
        row = {"day0": r.day0, "symbol": r.symbol, "side": r.side, "category": r.category, "strike": r.strike,
               "expiry": r.expiry, "lot": lot, "entry": entry, "opt_open": ohlc[0], "opt_high": ohlc[1], "opt_low": ohlc[2],
               "opt_close": ohlc[3], "period": r.period, **tl,
               "calib_open_err_pct": abs(path[0][1] - ohlc[0]) / entry * 100,
               "calib_close_err_pct": abs(tl["proxy_1520"] - ohlc[3]) / entry * 100,
               "calib_high_err_pct": abs(max(p[2] for p in path) - ohlc[1]) / entry * 100,
               "calib_low_err_pct": abs(min(p[3] for p in path) - ohlc[2]) / entry * 100,
               "real_close_net": float(r.e1_net), "real_close_net_pct": float(r.e1_net_pct)}
        for ex in EXITS:
            px, why, when = run_exit(path, entry, ex)
            px = max(0.0, round(px - TICK, 2)) if why == "15:20" else round(px, 2)
            _c, _s, net = net_of(r.side, entry, px, lot, slip)
            row[f"{ex.name}_net"], row[f"{ex.name}_pct"] = net, net / (entry * lot) * 100
            row[f"{ex.name}_why"], row[f"{ex.name}_time"] = why, when
        rows.append(row)
    return pd.DataFrame(rows), excl


def exact_levels(t: pd.DataFrame) -> pd.DataFrame:
    """Added after the proxy results were seen (2026-10-18), with NO proxy: a single stop or a single target depends only
    on whether the option's REAL day low / high crossed its level, not on when, so it is computed from the bhavcopy's
    real high / low / close. Fills at the level (optimistic in a fast move); otherwise the real close - 1 tick."""
    from .backtest_s1_v4 import SLIPPAGE
    from .backtest_s1_v10 import net_of
    from .stats import clustered_t
    o = [option_ohlc(r.day0, r.symbol, r.expiry, float(r.strike), r.side) for r in t.itertuples()]
    hi, lo = [x[1] for x in o], [x[2] for x in o]
    entry, close = t["entry_price"].astype(float).tolist(), t["e1_exit_price"].astype(float).tolist()

    def row(label, px, hit):
        nets = [net_of(r.side, r.entry_price, max(0.0, round(x, 2)), int(r.lot), SLIPPAGE.get(r.category, SLIPPAGE["unknown"]))[2]
                for r, x in zip(t.itertuples(), px)]
        pct = pd.Series(nets) / (t["entry_price"] * t["lot"]).values * 100
        hit = pd.Series(hit)
        moved = pd.Series([(c / e - 1) * 100 for c, e in zip(close, entry)])
        return {"exit": label, "n": len(pct), "mean_pct": round(pct.mean(), 2), "median_pct": round(pct.median(), 2),
                "hit_pct": round((pct > 0).mean() * 100, 1), "t": clustered_t(pct, t["day0"]), "total_rs": round(sum(nets)),
                "trades the level fired on (%)": round(hit.mean() * 100, 1) if hit.any() else 0.0,
                "those trades' real 15:20 result (%)": round(moved[hit.values].mean(), 1) if hit.any() else None}

    rows = [row("Same day 15:20, no stop (real close)", close, [False] * len(t))]
    for sl in (0.80, 0.70, 0.60, 0.50):
        h = [lo_ <= sl * e for lo_, e in zip(lo, entry)]
        rows.append(row(f"Stop {round((sl - 1) * 100)} %", [sl * e if x else c for x, e, c in zip(h, entry, close)], h))
    for tp in (1.30, 1.50, 2.00):
        h = [hi_ >= tp * e for hi_, e in zip(hi, entry)]
        rows.append(row(f"Target +{round((tp - 1) * 100)} %", [tp * e if x else c for x, e, c in zip(h, entry, close)], h))
    return pd.DataFrame(rows)


def summarise(s: pd.DataFrame, name: str) -> dict:
    from .stats import clustered_t
    r = s[f"{name}_pct"].astype(float)
    return {"n": len(s), "mean_pct": round(r.mean(), 2), "median_pct": round(r.median(), 2),
            "hit_pct": round((r > 0).mean() * 100, 1), "t": clustered_t(r, s["day0"]) if len(s) > 1 else None,
            "total_rs": round(s[f"{name}_net"].sum())}


def main() -> None:
    ap = argparse.ArgumentParser(description="S1 v10 fade: intraday timeline and stop-loss study 2025-26 (descriptive)")
    ap.add_argument("--fetch", action="store_true", help="fetch the day-0 1-minute stock candles through the live server")
    ap.add_argument("--url", default=LIVE_URL)
    ap.add_argument("--tag", default="", help="the backtest's output suffix, e.g. _2022_24")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    t = trades(a.tag)
    if a.fetch:
        print(fetch(t, a.url))
        return
    write({k: study(t, k) for k in ("A", "B")}, len(t), exact=exact_levels(t), tag=a.tag)


# ---------------------------------------------------------------- report
def write(res: dict, n_all: int, out_dir: Path = ROOT / "data" / "results", exact: pd.DataFrame | None = None,
          tag: str = "") -> None:
    """res = {"A": (trades, exclusions), "B": (...)}: the report (md) and the workbook (xlsx), both proxies side by side."""
    import xlsxwriter
    from .backtest_s1_v2 import md
    out_dir.mkdir(parents=True, exist_ok=True)
    names = {"A": "Proxy A (pre-registered)", "B": "Proxy B (range-anchored, addendum)"}
    head = ("Descriptive only: no rule changes. NOT real option minute prices: proxies from the stock's 1-minute candles "
            "(strategies/S1_v10_stoploss_study_2025_26.md and its addendum). Not out of sample, and 12 exits are compared, so "
            "the best one looks better than it is. Stops and targets fill at their level (optimistic). Read a stop level only "
            "where proxies A and B agree.")
    sa = res["A"][0]
    tl = {"trades": len(sa), "peak came before the dip (%)": round(sa["peak_first"].mean() * 100, 1),
          "median peak time": sa["peak_time"].sort_values().iloc[len(sa) // 2] if len(sa) else None,
          "median dip time": sa["dip_time"].sort_values().iloc[len(sa) // 2] if len(sa) else None,
          "peak in the first 30 minutes (%)": round((sa["peak_time"] < "09:45").mean() * 100, 1),
          "dip in the first 30 minutes (%)": round((sa["dip_time"] < "09:45").mean() * 100, 1)}
    buckets = sorted(set(sa["peak_time"].map(half_hour)) | set(sa["dip_time"].map(half_hour)))
    tb = pd.DataFrame([{"half-hour": b, "peaks (%)": round((sa["peak_time"].map(half_hour) == b).mean() * 100, 1),
                        "dips (%)": round((sa["dip_time"].map(half_hour) == b).mean() * 100, 1)} for b in buckets])
    sections, tables = [], {}
    for k, (s_, excl) in res.items():
        s_.to_csv(out_dir / f"S1_v10_stoploss_study_trades{tag}_{k}.csv", index=False)
        ex_all = pd.DataFrame([{"exit": e.label, **summarise(s_, e.name)} for e in EXITS])
        ex_side = pd.DataFrame([{"side": sd, "exit": e.label, **summarise(s_[s_.side == sd], e.name)}
                                for sd in ("PE", "CE") for e in EXITS])
        periods = sorted(s_["period"].unique())
        ex_per = pd.DataFrame([{"exit": e.label, **{p: round(s_[s_.period == p][f"{e.name}_pct"].mean(), 1) for p in periods}}
                               for e in EXITS])
        calib = {c: round(s_[c].median(), 1) for c in ("calib_open_err_pct", "calib_close_err_pct", "calib_high_err_pct",
                                                       "calib_low_err_pct")}
        m20 = s_["touch_m20"].map(minutes_after_open).dropna()
        p30 = s_["touch_p30"].map(minutes_after_open).dropna()
        lv = {"touched -20 % (%)": round(s_["touch_m20"].notna().mean() * 100, 1),
              "median minutes to -20 %": None if m20.empty else round(m20.median(), 0),
              "touched +30 % (%)": round(s_["touch_p30"].notna().mean() * 100, 1),
              "median minutes to +30 %": None if p30.empty else round(p30.median(), 0),
              "touched +50 % (%)": round(s_["touch_p50"].notna().mean() * 100, 1),
              "touched +30 % and sold below entry at 15:20 (%)":
                  round((s_["touch_p30"].notna() & (s_["same_day_pct"] < 0)).mean() * 100, 1)}
        tables[k] = (ex_all, ex_side, ex_per, calib, lv, excl)
        sections += [f"## {names[k]}\n",
                     f"Trades {len(s_)} of {n_all}; excluded {excl}. Calibration, median absolute error in % of the entry: "
                     f"09:15 vs real open {calib['calib_open_err_pct']}, 15:20 vs real close {calib['calib_close_err_pct']}, "
                     f"high {calib['calib_high_err_pct']}, low {calib['calib_low_err_pct']}. Same-day exit at the REAL close: "
                     f"mean {round(s_['real_close_net_pct'].mean(), 2)} %.\n",
                     "### Price levels touched\n\n" + md(pd.DataFrame([lv])),
                     "### Exits compared (net % of premium after charges and slippage)\n\n" + md(ex_all),
                     "### By side\n\n" + md(ex_side), "### Mean net % by half-year\n\n" + md(ex_per)]
    ex_note = ("Added after the proxy results were seen: computed from the option's REAL day high / low / close, no proxy. "
               "A single stop or target only depends on whether the real low / high crossed it. Fills at the level "
               "(optimistic in a fast move). The proxies put the same-day exit far above the real close (both miss the "
               "fall in option value after results and time decay), so their absolute levels are not reliable.")
    exact_md = [] if exact is None else [f"## Exact check on real prices: single stops and targets (all {n_all} trades)\n",
                                         ex_note + "\n", md(exact)]
    years = f"{s_['day0'].min()[:4]}-{s_['day0'].max()[:4]}" if len(s_) else ""
    text = "\n".join([f"# S1 v10 fade · intraday timeline and stop-loss study {years}\n", head + "\n"] + exact_md + [
                      "## Timeline (the same under both proxies: it follows the stock's own low and high)\n\n"
                      + md(pd.DataFrame([tl])),
                      "### When the peak and the dip happen (share of trades by half-hour)\n\n" + md(tb)] + sections)
    (out_dir / f"S1_v10_stoploss_study{tag}.md").write_text(text, encoding="utf-8")

    wb = xlsxwriter.Workbook(out_dir / f"S1_v10_stoploss_study{tag}.xlsx")
    F = lambda **kw: wb.add_format({"font_name": "Arial", "font_size": 10, **kw})        # noqa: E731
    H = F(bold=True, font_color="#FFFFFF", bg_color="#1F3864", text_wrap=True, align="center", valign="vcenter", border=1)
    note = F(italic=True, font_size=9, font_color="#595959")
    num = F(num_format="0.0;[Red]-0.0")

    def table(ws, r0, df, widths=None):
        ws.set_row(r0, 40)
        for c, h in enumerate(df.columns):
            ws.write(r0, c, str(h), H)
            ws.set_column(c, c, (widths or {}).get(c, 13))
        for i, row in enumerate(df.itertuples(index=False), 1):
            for c, v in enumerate(row):
                if v is None or (isinstance(v, float) and math.isnan(v)):
                    ws.write_blank(r0 + i, c, None)
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    ws.write_number(r0 + i, c, float(v), num)
                else:
                    ws.write(r0 + i, c, str(v), F())
        return r0 + len(df) + 2

    if exact is not None:
        we = wb.add_worksheet("Exact (real prices)")
        we.write(0, 0, f"Single stops and targets on REAL option prices (no proxy), {n_all} trades", F(bold=True, font_size=13))
        we.write(1, 0, ex_note, note)
        table(we, 3, exact, {0: 36, 7: 16, 8: 18})
    ws = wb.add_worksheet("Timeline")
    ws.write(0, 0, f"S1 v10 fade {years}: when the peak and the dip happen", F(bold=True, font_size=13))
    ws.write(1, 0, head, note)
    r = table(ws, 3, pd.DataFrame([{"measure": a_, "value": b_} for a_, b_ in tl.items()]), {0: 40})
    table(ws, r, tb)
    for k in res:
        ex_all, ex_side, ex_per, calib, lv, excl = tables[k]
        w = wb.add_worksheet(f"Exits {k}")
        w.write(0, 0, f"{names[k]}: exits compared on the same trades", F(bold=True, font_size=13))
        w.write(1, 0, f"Calibration (median abs error, % of entry): open {calib['calib_open_err_pct']}, close "
                f"{calib['calib_close_err_pct']}, high {calib['calib_high_err_pct']}, low {calib['calib_low_err_pct']}. "
                f"Excluded {excl}.", note)
        r = table(w, 3, pd.DataFrame([{"measure": a_, "value": b_} for a_, b_ in lv.items()]), {0: 44})
        r = table(w, r, ex_all, {0: 38})
        w.write(r, 0, "By side", F(bold=True))
        r = table(w, r + 1, ex_side, {1: 38})
        w.write(r, 0, "Mean net % by half-year", F(bold=True))
        table(w, r + 1, ex_per, {0: 38})
    s_ = res["B"][0]
    keep = ["day0", "symbol", "side", "lot", "entry", "opt_open", "opt_high", "opt_low", "opt_close", "peak_time", "dip_time",
            "peak_first", "touch_m20", "touch_p30", "touch_p50", "real_close_net_pct"] + [f"{e.name}_pct" for e in EXITS]
    w = wb.add_worksheet("Trades (proxy B)")
    table(w, 0, s_[keep].assign(peak_first=s_["peak_first"].map({True: "peak", False: "dip"})), {1: 13})
    w.freeze_panes(1, 2)
    wb.close()
    print(text)


if __name__ == "__main__":
    main()
