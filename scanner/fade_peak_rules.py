"""S1 fade peak study, phase C: the frozen rule (R2 stall 20) and the other phase-B rules vs v12 on the TEST half.

    python -m scanner.fade_peak_rules

strategies/S1_fade_peak_patterns.md (addendum 2026-10-22). The walker and rule texts below are copied word for word
from phase B's rules.py (train pack only); here they run once on day 0 from 2025-11-03 with the tick at Rs 0.01.
Writes data/results/S1_fade_peak_rules_test.md and _trades.csv.

Phase B docstring follows (kept for the record):

    cd C:\\Users\\sherw\\project-f-0
    set PYTHONPATH=C:\\Users\\sherw\\project-f-0
    python <scratchpad>\\pattern_train\\work\\rules.py

Reads only pattern_train/trades.csv and pattern_train/option_minutes.csv (day0 Oct 2024 - Oct 2025).
Writes rules_per_trade.csv next to this script. Nothing in the repo is touched.

The rule texts in RULES are written before the first run and are meant to be frozen word for word.
Parameters come from the phase-A findings, not from a search on this data.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from server import charges as ch
from scanner.stats import clustered_t

TICK = 0.01            # test dates are all from 2025-11-03 (Rs 0.01 tick)
STOP = 0.20            # -20 % stop
ARM = 0.10             # trail / signals switch on once a candle high >= 1.10 x entry
EPS = 1e-9

COMMON = (
    "COMMON FRAME (all rules, identical to v12). Buy at entry = the 09:16 candle open + 1 tick. Work through the "
    "1-minute candles from 09:17 to 15:19 in order, using only the current and earlier candles. Tick = Rs 0.05 "
    "(Rs 0.01 from 2025-11-03). Every sell price is floored at 1 tick. Within each candle the checks run in this "
    "order: (0) a sell signalled at the previous candle's close is filled at this candle's open - 1 tick; "
    "(1) STOP: if the candle's low <= 0.80 x entry, sell at min(0.80 x entry, the candle's open) - 1 tick; "
    "(2) the rule's resting price level L, if it has one and is armed: if the low <= L, sell at min(L, open) - 1 tick; "
    "(3) ARMING: the rule is armed from the first candle (09:17 on) whose high >= 1.10 x entry; H = the highest high "
    "from the arming candle up to and including the PREVIOUS candle (so at the arming candle itself there is no L "
    "yet), updated after steps 1-2; (4) close signals, if the rule has any, are read at the candle's close and sold "
    "at the next candle's open - 1 tick (a signal on the 15:19 candle sells at the 15:19 close - 1 tick). "
    "If nothing has sold by 15:19, sell at the 15:19 close - 1 tick."
)

RULES = {
    "v12": "BASELINE v12. L = 0.98 x H.",
    "R1 range trail": (
        "R1 RANGE TRAIL (gap scaled by recent 1-minute range). Like v12 but L = H x (1 - g), where "
        "g = max(0.02, 3 x A) and A = the mean of (high - low) / close over the 10 candles before the current candle "
        "(counting from the 09:15 candle; fewer if fewer exist). No close signals."),
    "R2 stall 20": (
        "R2 STALL 20. No resting level L. After arming, count consecutive candles whose high is not above the "
        "running high (the running high starts as the arming candle's high; a candle whose high is above it becomes "
        "the new running high and resets the count to 0). When the count reaches 20 at a candle's close, sell at the "
        "next candle's open - 1 tick. Stop and 15:19 as in the common frame."),
    "R3 half-profit floor": (
        "R3 HALF-PROFIT FLOOR. L = entry + 0.5 x (H - entry): once armed, sell when the price gives back half of the "
        "best open gain (best = H, the highest high of earlier candles since arming). No close signals."),
    "R4 half-profit + wick top": (
        "R4 HALF-PROFIT FLOOR + WICK TOP. R3, plus one close signal: if an armed candle makes a new high (its high "
        "> H, or it is the arming candle) and its close <= 0.90 x its own high, sell at the next candle's open "
        "- 1 tick."),
    "R5 hold to close": (
        "R5 HOLD. The -20 % stop only: no trail, no signals; otherwise sell at the 15:19 close - 1 tick."),
}

WHY = {
    "R1 range trail": "v12's 2 % gap fires within 1-2 min of switch-on because 1-min candles range ~6.4 % at "
                      "09:17-09:30 (2.2 % at 09:31-10:30, 0.4 % later). 3 x 6.4 % ~ 19 %, the median gap live 40-100 % "
                      "peaks needed (18.6 %); 10 candles ~ the 09:17-09:30 window the 6.4 % was measured on; floor = "
                      "v12's 2 %.",
    "R2 stall 20": "No-new-high-for-N says the peak is in ~50 % (N=10) to ~52-60 % (N=30) of the time; the "
                   "exploratory N=20 variant was the best timing exit (+3.60 vs v12, t 0.55, optimistic).",
    "R3 half-profit floor": "Pullbacks grow with the peak (needed gap median 18.6 % for 40-100 % peaks, 38.3 % for "
                            ">= 100 %). A half-profit floor's gap is 0.5(H-e)/H: ~4.5 % at +10 %, 17 % at +50 %, 25 % at "
                            "+100 %, 33 % at +200 %, close to those medians.",
    "R4 half-profit + wick top": "A new-high candle closing >= 10 % below its high is the day's peak 35-50 % of the time "
                                 "vs 9-13 % for other new highs; selling at the next open keeps a median 87.5 % (live) "
                                 "of the peak gain when it is the peak.",
    "R5 hold to close": "Big peaks come late (median 220 min, 11/28 live after 14:00); late peakers close at 0.84 x "
                        "the day high; v12 sells in the noisy first minutes. Exploratory hold: +2.46 vs v12.",
}


def net_rs(r, buy: float, sell: float) -> float:
    q = int(r.qty)
    return (sell - buy) * q - ch.leg(r.side, "BUY", q, buy)["total"] - ch.leg(r.side, "SELL", q, sell)["total"]


# ----------------------------------------------------------------------------------------------------------- walk
def walk(rule: str, c: pd.DataFrame, e: float, tick: float = TICK):
    """Return (sell price, exit kind, sell time). c = candles 09:15 (if present) .. 15:19."""
    o, h, l, cl, tt = (c[k].to_numpy(dtype=float if k != "t" else object) for k in ("o", "h", "l", "c", "t"))
    rng = (h - l) / np.where(cl > 0, cl, np.nan)
    start = int((tt < "09:17").sum())                    # first decision candle = 09:17
    n = len(c)
    stop = e * (1 - STOP)
    armed, H, stall, pending = False, None, 0, None

    def px(x):
        return max(tick, round(x - tick, 2))

    for i in range(start, n):
        if pending is not None:                          # (0) close signal from the previous candle
            return px(o[i]), pending, tt[i]
        if rule != "none" and l[i] <= stop + EPS:         # (1) stop
            return px(min(stop, o[i])), "stop", tt[i]
        # (2) resting level
        if armed and H is not None:
            L = None
            if rule == "v12":
                L = 0.98 * H
            elif rule == "R1 range trail":
                a = rng[max(0, i - 10):i]
                a = a[~np.isnan(a)]
                A = float(a.mean()) if len(a) else 0.0
                L = H * (1 - max(0.02, 3 * A))
            elif rule in ("R3 half-profit floor", "R4 half-profit + wick top"):
                L = e + 0.5 * (H - e)
            if L is not None and l[i] <= L + EPS:
                return px(min(L, o[i])), "level", tt[i]
        # (3) arming and running high
        new_high = False
        if not armed:
            if h[i] >= e * (1 + ARM) - EPS:
                armed, H, stall, new_high = True, h[i], 0, True
        else:
            if h[i] > H + EPS:
                H, stall, new_high = h[i], 0, True
            else:
                stall += 1
        # (4) close signals
        if armed:
            if rule == "R2 stall 20" and stall >= 20:
                pending = "stall"
            if rule == "R4 half-profit + wick top" and new_high and cl[i] <= 0.90 * h[i] + EPS:
                pending = "wick"
            if pending is not None and i == n - 1:
                return px(cl[i]), pending, tt[i]
    return px(cl[-1]), "close", tt[-1]



from scanner.backtest_s1_v2 import md
from scanner.build import ROOT

RES = ROOT / "data" / "results"
SPLIT = "2025-11-03"
SETS = ("bandv10", "band12", "band12q4", "band050", "band050q4")


def load():
    c = pd.read_csv(RES / "S1_fade_cheap_dte_trades.csv")
    live = c[(c.entry_B >= 2) & c.lot_ok].copy()
    live["qty"], live["group"] = live["lot"], "live"
    ref = pd.read_csv(RES / "S1_refused_listing_price_trades.csv")
    ref["qty"], ref["group"] = ref["lots"] * ref["lot"], "refused"
    cols = ["group", "set", "symbol", "day0", "side", "strike", "qty", "entry_B"]
    t = pd.concat([live[cols], ref[cols]], ignore_index=True)
    t = t[t["day0"] >= SPLIT].reset_index(drop=True)
    keys = set(zip(t.symbol, t.day0, t.side, t.strike.astype(float)))
    by = {}
    for s in SETS:
        m = pd.read_csv(RES / f"S1_v10_{s}_minutes.csv")
        m["t"] = m["ts"].str[11:16]
        for k, g in m.groupby(["symbol", "day0", "side", "strike"]):
            if k in keys and k not in by:
                g = g.sort_values("ts")
                by[k] = g[(g["t"] >= "09:15") & (g["t"] <= "15:19")].reset_index(drop=True)
    return t, [by[(r.symbol, r.day0, r.side, float(r.strike))] for r in t.itertuples()]


def main() -> None:
    t, cs = load()
    rows = []
    for r, c in zip(t.itertuples(), cs):
        e = float(r.entry_B)
        d16 = c[c["t"] >= "09:16"]
        peak = float(d16["h"].max()) / e - 1
        row = {"group": r.group, "symbol": r.symbol, "day0": r.day0, "side": r.side, "strike": r.strike,
               "qty": int(r.qty), "entry": e, "peak_pct": peak * 100}
        for nm in RULES:
            s, kind, at = walk(nm, c, e, TICK)
            nr = net_rs(r, e, s)
            row.update({f"{nm}|sell": s, f"{nm}|kind": kind, f"{nm}|at": at, f"{nm}|rs": round(nr, 2),
                        f"{nm}|pct": nr / (e * int(r.qty)) * 100})
        rows.append(row)
    R = pd.DataFrame(rows)
    R.to_csv(RES / "S1_fade_peak_rules_test_trades.csv", index=False)
    out = []
    for grp in ("live", "refused"):
        G = R[R["group"] == grp]
        big = G[G["peak_pct"] >= 40]
        for nm in RULES:
            p, rs = G[f"{nm}|pct"], G[f"{nm}|rs"]
            d = p - G["v12|pct"]
            srt = p.sort_values(ascending=False)
            out.append({"group": grp, "rule": nm, "n": len(G), "win %": round((rs > 0).mean() * 100, 1),
                        "mean %": round(p.mean(), 2), "median %": round(p.median(), 2), "total Rs": round(rs.sum()),
                        "diff vs v12": round(d.mean(), 2),
                        "diff t": clustered_t(d, G["day0"]) if d.abs().sum() > 0 else None,
                        "better/worse/same": f"{(d > 1e-6).sum()}/{(d < -1e-6).sum()}/{(d.abs() <= 1e-6).sum()}",
                        "mean w/o best 3": round(srt.iloc[3:].mean(), 2),
                        f"mean % on peak >= 40 %": round(big[f"{nm}|pct"].mean(), 2),
                        "kept (mean net / mean peak, peak >= 40 %)": round(big[f"{nm}|pct"].mean() / big["peak_pct"].mean(), 3)})
    T = pd.DataFrame(out)
    r2 = T[(T.group == "live") & (T.rule == "R2 stall 20")].iloc[0]
    passed = bool(r2["mean %"] > 0 and r2["diff vs v12"] > 0 and (r2["diff t"] or 0) >= 2)
    nl = chr(10)
    text = nl.join([
        "# S1 fade · peak-pattern study, phase C: the frozen rule on the test half" + nl,
        f"strategies/S1_fade_peak_patterns.md (addendum 2026-10-22). Test = day 0 from {SPLIT}: "
        f"{(R.group == 'live').sum()} live trades (1 lot), {(R.group == 'refused').sum()} refused (max lots under Rs 8,000). "
        "Same walker as phase B, tick Rs 0.01, real charges." + nl,
        f"## Frozen rule R2 stall 20 (live set): **{'PASS' if passed else 'FAIL'}**" + nl + nl
        + f"mean {r2['mean %']} %, vs v12 {r2['diff vs v12']:+} points (t {r2['diff t']}). Pass needs mean > 0 and the "
        "difference > 0 with t >= 2. R4 and the others are descriptive." + nl,
        "## Live set" + nl + nl + md(T[T.group == "live"].drop(columns=["group"])),
        "## Refused set" + nl + nl + md(T[T.group == "refused"].drop(columns=["group"])),
    ])
    (RES / "S1_fade_peak_rules_test.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
