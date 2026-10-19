"""S1 v10 fade · Rs 0.50-1 band: +20 % target with a trailing stop on 1-minute prices (numbers only).

    python -m scanner.fade_band050 pick      # the contracts -> data/results/S1_v10_band050_contracts.csv
    (GitHub: index_data.fetch_band_minutes)  # their day-0 minute candles -> S1_v10_band050_minutes.csv
    python -m scanner.fade_band050 run       # +20 %: choose on 2025, test once on 2026 -> S1_v10_band050_trail.md
    python -m scanner.fade_band050 run100    # +100 % (addendum 2): -> S1_v10_band050_t100.md

strategies/S1_v10_band050_trail.md fixes every choice.
"""
from __future__ import annotations

import math
import sys
from collections import Counter

import pandas as pd

from server import charges as ch

from .backtest_s1_v2 import md
from .backtest_s1_v10 import BAND, MIN_CONTRACTS, TICK, quotes_of, start_strike
from .build import ROOT
from .stats import clustered_t

RES, CACHE = ROOT / "data" / "results", ROOT / "data" / "cache"
CONTRACTS, MINUTES = RES / "S1_v10_band050_contracts.csv", RES / "S1_v10_band050_minutes.csv"
LO, HI, TARGET = 0.50, 1.00, 0.20
BASE = ("baseline 15:20", None, None, "before")
# (name, trail, target, mode): "before" = trailing stop until the target, sold at the target; "after" = no stop until
# the target is reached, then a trailing stop from the peak (addendum 2)
VARIANTS = {"run": (BASE, *((f"R{int(x * 100)}", x, 0.20, "before") for x in (0.10, 0.20, 0.30))),
            "run100": (BASE, *((f"A{int(x * 100)}", x, 1.00, "before") for x in (0.10, 0.20, 0.30)),
                       *((f"B{int(x * 100)}", x, 1.00, "after") for x in (0.10, 0.20, 0.30)))}
OUT = {"run": ("S1_v10_band050_trail.md", "S1_v10_band050_trades.csv", "+20 % target with a trailing stop"),
       "run100": ("S1_v10_band050_t100.md", "S1_v10_band050_t100_trades.csv",
                  "+100 % target, trailing stop before it (A) or after it (B)")}
CHOOSE, TEST = ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-09-25")


# ---------------------------------------------------------------- the contracts
def pick() -> None:
    sig = pd.read_csv(RES / "S1_v10_trades_floor0p05.csv")
    sig = sig[sig["entry"] == "open"].drop_duplicates(["symbol", "day0", "side"])
    rows, fun = [], Counter(signals=len(sig))
    for d0, g in sig.groupby("day0"):
        p = pd.read_csv(CACHE / f"fo_prices_{d0.replace('-', '')}.csv")
        for r in g.itertuples():
            qs = quotes_of(p, r.symbol, r.expiry, r.side)
            ks = sorted(qs)
            k0 = start_strike(ks, r.spot_prev_close, r.side)
            if k0 is None:
                fun["no_strikes"] += 1
                continue
            i = ks.index(k0)
            path = ks[: i + 1][::-1] if r.side == "PE" else ks[i:]
            k = next((k for k in path if qs[k].contracts >= MIN_CONTRACTS and qs[k].open == qs[k].open
                      and LO <= qs[k].open + TICK < HI), None)
            if k is None:
                fun["no_liquid_strike_in_band"] += 1
                continue
            q = qs[k]
            cost = (q.open + TICK) * q.lot
            if not BAND[0] <= cost <= BAND[1]:
                fun["lot_outside_600_8000"] += 1
                continue
            fun["picked"] += 1
            rows.append({"symbol": r.symbol, "day0": d0, "side": r.side, "expiry": r.expiry, "strike": k,
                         "lot": q.lot, "bhav_open": q.open, "bhav_high": q.high, "bhav_low": q.low, "bhav_close": q.close,
                         "contracts_day0": q.contracts, "spot_prev_close": r.spot_prev_close,
                         "category": r.category, "np_yoy": r.np_yoy})
    pd.DataFrame(rows).to_csv(CONTRACTS, index=False)
    print(dict(fun), "->", CONTRACTS)


# ---------------------------------------------------------------- the exits on minute candles
def up_tick(x: float) -> float:
    return round(math.ceil(round(x / TICK, 6)) * TICK, 2)


def down_tick(x: float) -> float:
    return round(math.floor(round(x / TICK, 6)) * TICK, 2)


def simulate(m: pd.DataFrame, trail: float | None, target_pct: float | None = TARGET, mode: str = "before") -> dict | None:
    """One trade on its day-0 minutes (time-sorted rows with t, o, h, l, c). None if there is no entry minute."""
    m = m[(m["t"] >= "09:15") & (m["t"] <= "15:19")]
    first = m[m["t"] <= "09:20"]
    if first.empty:
        return None
    e_row = first.iloc[0]
    entry = round(float(e_row["c"]) + 2 * TICK, 2)
    target = up_tick(entry * (1 + (target_pct or 0.0)))
    peak, armed = entry, mode == "before"
    for r in m[m["t"] > e_row["t"]].itertuples():
        if trail is None:
            continue
        if armed:
            stop = peak * (1 - trail)
            if r.l <= stop:
                px = down_tick(min(stop, r.o)) - 2 * TICK
                return {"entry": entry, "exit": round(max(TICK, px), 2), "reason": "stop", "at": r.t}
            if mode == "before" and r.h >= target + TICK - 1e-9:
                return {"entry": entry, "exit": target, "reason": "target", "at": r.t}
            peak = max(peak, float(r.h))
        elif r.h >= target + TICK - 1e-9:                    # "after": the target arms the trailing stop
            armed, peak = True, float(r.h)
    last = m.iloc[-1]
    return {"entry": entry, "exit": round(max(0.0, float(last["c"]) - 2 * TICK), 2), "reason": "15:20", "at": last["t"]}


def stats(g: pd.DataFrame) -> dict:
    if not len(g):
        return {"n": 0}
    r = g["net_pct"]
    cum = g.sort_values(["day0", "symbol"])["net"].cumsum()
    out = {"n": len(g), "win_pct": round((g["net"] > 0).mean() * 100, 1), "mean_pct": round(r.mean(), 2),
           "median_pct": round(r.median(), 2), "total_rs": round(g["net"].sum()),
           "max_dd_rs": round(float((cum.cummax().clip(lower=0) - cum).max())),
           "t": clustered_t(r, g["day0"]) if len(g) > 1 else None}
    for why in ("target", "stop", "15:20"):
        out[f"{why}_pct"] = round((g["reason"] == why).mean() * 100, 1)
    return out


def run(kind: str = "run") -> None:
    variants = VARIANTS[kind]
    md_name, csv_name, title = OUT[kind]
    c = pd.read_csv(CONTRACTS)
    mins = pd.read_csv(MINUTES)
    mins["t"] = mins["ts"].str[11:16]
    by = {k: g.sort_values("ts") for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
    rows, fun = [], Counter(contracts=len(c))
    for r in c.itertuples():
        m = by.get((r.symbol, r.day0, r.side, float(r.strike)))
        if m is None or m.empty:
            fun["no_minute_candles"] += 1
            continue
        done = True
        for name, trail, tgt, mode in variants:
            s = simulate(m, trail, tgt, mode)
            if s is None:
                done = False
                break
            lot = int(r.lot)
            charges = ch.leg(r.side, "BUY", lot, s["entry"])["total"] + (
                ch.leg(r.side, "SELL", lot, s["exit"])["total"] if s["exit"] > 0 else 0.0)
            net = round((s["exit"] - s["entry"]) * lot - charges, 2)
            rows.append({"variant": name, "symbol": r.symbol, "day0": r.day0, "side": r.side, "strike": r.strike,
                         "lot": lot, **s, "charges": round(charges, 2), "net": net,
                         "net_pct": round(net / (s["entry"] * lot) * 100, 3)})
        fun["simulated" if done else "no_entry_minute"] += 1
    t = pd.DataFrame(rows)
    t.to_csv(RES / csv_name, index=False)
    win = lambda a, b: t[(t["day0"] >= a) & (t["day0"] <= b)]                         # noqa: E731
    choose, test = win(*CHOOSE), win(*TEST)
    tab = lambda df: pd.DataFrame([{"variant": n, **stats(df[df["variant"] == n])} for n, *_ in variants])  # noqa: E731
    ct, tt = tab(choose), tab(test)
    cand = ct[ct["variant"] != "baseline 15:20"].copy()
    cand["trail"], cand["letter"] = cand["variant"].str[1:].astype(int), cand["variant"].str[0]
    chosen = cand.sort_values(["total_rs", "trail", "letter"], ascending=[False, False, True]).iloc[0]["variant"]
    tr = tt.set_index("variant")
    res, base = tr.loc[chosen], tr.loc["baseline 15:20"]
    crit = {"total net Rs > 0 on 2026": bool(res["total_rs"] > 0),
            "mean net % > 0 with t >= 2 on 2026": bool(res["mean_pct"] > 0 and (res["t"] or 0) >= 2),
            "beats the 15:20 baseline's total on 2026": bool(res["total_rs"] > base["total_rs"])}
    passed = all(crit.values())
    verdict = (f"**Verdict: {chosen} (chosen on 2025) {'passes' if passed else 'does not pass'} on 2026.** "
               f"On the {int(res['n'])} trades of 2026 it made Rs {int(res['total_rs']):,} (mean {res['mean_pct']:+.1f} % a trade, "
               f"t {res['t']}, win rate {res['win_pct']} %) against Rs {int(base['total_rs']):,} for the 15:20 exit. "
               + ("The same rule is next tested on the Rs 1-2 band under its own pre-registration."
                  if passed else "Under the pre-registration, the Rs 1-2 step is not run on this rule."))
    text = "\n".join([
        "# S1 v10 fade · Rs 0.50-1 band: +20 % target with a trailing stop, 1-minute prices\n",
        "Numbers only. Pre-registered: strategies/S1_v10_band050_trail.md. Entry: the 09:15 minute's close + 2 ticks. "
        f"Target: entry x {1 + (variants[1][2] or 0):.2f}, filled at the first minute whose high >= target + 1 tick"
        + ("; in B variants the target is not sold but arms the trailing stop from that minute's high. " if kind == "run100" else ". ")
        + "Trailing stop: peak x (1 - trail) "
        "against each minute's low before the peak updates, filled at min(stop, open) - 2 ticks; stop first when both touch "
        "in a minute. Else the 15:19 minute's close - 2 ticks. Real charges. Net % of the lot value at entry. t "
        "date-clustered. Trades: data/results/S1_v10_band050_trades.csv.\n",
        verdict + "\n",
        "## Pass criterion (2026, the chosen rule)\n\n" + "\n".join(f"- {k}: **{'yes' if v else 'no'}**" for k, v in crit.items()) + "\n",
        f"## Choose: 2025 (chosen: {chosen}, highest total net Rs)\n\n" + md(ct),
        "## Test: 2026 (only the chosen rule counts; the others for information)\n\n" + md(tt),
        "## Funnel\n\n" + md(pd.DataFrame([dict(fun)])),
    ])
    (RES / md_name).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    pick() if sys.argv[1] == "pick" else run(sys.argv[1])
