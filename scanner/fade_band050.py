"""S1 v10 fade · cheap-option bands: targets with trailing stops on 1-minute prices (numbers only).

    python -m scanner.fade_band050 pick      # Rs 0.50-1 contracts -> data/results/S1_v10_band050_contracts.csv
    python -m scanner.fade_band050 pick12    # Rs 1-2 contracts -> data/results/S1_v10_band12_contracts.csv
    (GitHub: index_data.fetch_band_minutes [12])  # day-0 minute candles -> S1_v10_band050 / band12 _minutes.csv
    python -m scanner.fade_band050 run       # Rs 0.50-1, +20 %: choose on 2025, test on 2026 -> S1_v10_band050_trail.md
    python -m scanner.fade_band050 run100    # Rs 0.50-1, +100 % (addendum 2) -> S1_v10_band050_t100.md
    python -m scanner.fade_band050 run12     # Rs 1-2, all nine exits, real ticks -> S1_v10_band12_trail.md

strategies/S1_v10_band050_trail.md and S1_v10_band12_trail.md fix every choice.
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
TARGET = 0.20
FILES = {"050": (RES / "S1_v10_band050_contracts.csv", RES / "S1_v10_band050_minutes.csv", 0.50, 1.00),
         "12": (RES / "S1_v10_band12_contracts.csv", RES / "S1_v10_band12_minutes.csv", 1.00, 2.00)}
TICK_CHANGE = "2025-11-03"                                       # NSE stock-option tick Rs 0.05 -> Rs 0.01 (audit)


def costs_old(day0: str) -> tuple[float, float]:
    """(tick, cost a side): the Rs 0.50-1 studies' model, 2 ticks of Rs 0.05 throughout."""
    return TICK, 2 * TICK


def costs_real(day0: str) -> tuple[float, float]:
    """S1_v10_band12_trail.md's primary: Rs 0.10 a side before the tick change, Rs 0.04 from it (tick Rs 0.01)."""
    return (TICK, 2 * TICK) if day0 < TICK_CHANGE else (0.01, 0.04)


def costs_optimistic(day0: str) -> tuple[float, float]:
    return (TICK, 2 * TICK) if day0 < TICK_CHANGE else (0.01, 0.02)
BASE = ("baseline 15:20", None, None, "before")
# (name, trail, target, mode): "before" = trailing stop until the target, sold at the target; "after" = no stop until
# the target is reached, then a trailing stop from the peak (addendum 2)
VARIANTS = {"run": (BASE, *((f"R{int(x * 100)}", x, 0.20, "before") for x in (0.10, 0.20, 0.30))),
            "run100": (BASE, *((f"A{int(x * 100)}", x, 1.00, "before") for x in (0.10, 0.20, 0.30)),
                       *((f"B{int(x * 100)}", x, 1.00, "after") for x in (0.10, 0.20, 0.30)))}
VARIANTS["run12"] = (BASE, *VARIANTS["run"][1:], *VARIANTS["run100"][1:])
OUT = {"run": ("S1_v10_band050_trail.md", "S1_v10_band050_trades.csv", "+20 % target with a trailing stop"),
       "run100": ("S1_v10_band050_t100.md", "S1_v10_band050_t100_trades.csv",
                  "+100 % target, trailing stop before it (A) or after it (B)"),
       "run12": ("S1_v10_band12_trail.md", "S1_v10_band12_trades.csv",
                 "+20 % (R) and +100 % (A, B) targets with trailing stops, real ticks")}
BAND_OF = {"run": "050", "run100": "050", "run12": "12"}
COSTS = {"run": costs_old, "run100": costs_old, "run12": costs_real}
CHOOSE, TEST = ("2025-01-01", "2025-12-31"), ("2026-01-01", "2026-09-25")


# ---------------------------------------------------------------- the contracts
def pick(band: str = "050") -> None:
    contracts, _, lo, hi = FILES[band]
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
                      and lo <= qs[k].open + TICK < hi), None)
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
    pd.DataFrame(rows).to_csv(contracts, index=False)
    print(dict(fun), "->", contracts)


# ---------------------------------------------------------------- the exits on minute candles
def up_tick(x: float, tick: float = TICK) -> float:
    return round(math.ceil(round(x / tick, 6)) * tick, 2)


def down_tick(x: float, tick: float = TICK) -> float:
    return round(math.floor(round(x / tick, 6)) * tick, 2)


def simulate(m: pd.DataFrame, trail: float | None, target_pct: float | None = TARGET, mode: str = "before",
             tick: float = TICK, cost: float = 2 * TICK) -> dict | None:
    """One trade on its day-0 minutes (time-sorted rows with t, o, h, l, c). None if there is no entry minute."""
    m = m[(m["t"] >= "09:15") & (m["t"] <= "15:19")]
    first = m[m["t"] <= "09:20"]
    if first.empty:
        return None
    e_row = first.iloc[0]
    entry = round(float(e_row["c"]) + cost, 2)
    target = up_tick(entry * (1 + (target_pct or 0.0)), tick)
    peak, armed = entry, mode == "before"
    for r in m[m["t"] > e_row["t"]].itertuples():
        if trail is None:
            continue
        if armed:
            stop = peak * (1 - trail)
            if r.l <= stop:
                px = down_tick(min(stop, r.o), tick) - cost
                return {"entry": entry, "exit": round(max(tick, px), 2), "reason": "stop", "at": r.t}
            if mode == "before" and r.h >= target + tick - 1e-9:
                return {"entry": entry, "exit": target, "reason": "target", "at": r.t}
            peak = max(peak, float(r.h))
        elif r.h >= target + tick - 1e-9:                    # "after": the target arms the trailing stop
            armed, peak = True, float(r.h)
    last = m.iloc[-1]
    return {"entry": entry, "exit": round(max(0.0, float(last["c"]) - cost), 2), "reason": "15:20", "at": last["t"]}


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


def trades(kind: str, costs) -> tuple[pd.DataFrame, Counter]:
    """Every contract under every exit of `kind`, priced with `costs(day0) -> (tick, cost a side)`."""
    variants = VARIANTS[kind]
    contracts, minutes, *_ = FILES[BAND_OF[kind]]
    c = pd.read_csv(contracts)
    mins = pd.read_csv(minutes)
    mins["t"] = mins["ts"].str[11:16]
    by = {k: g.sort_values("ts") for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
    rows, fun = [], Counter(contracts=len(c))
    for r in c.itertuples():
        m = by.get((r.symbol, r.day0, r.side, float(r.strike)))
        if m is None or m.empty:
            fun["no_minute_candles"] += 1
            continue
        done = True
        tick, cost = costs(r.day0)
        for name, trail, tgt, mode in variants:
            s = simulate(m, trail, tgt, mode, tick, cost)
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
    return pd.DataFrame(rows), fun


def run(kind: str = "run") -> None:
    variants = VARIANTS[kind]
    md_name, csv_name, title = OUT[kind]
    t, fun = trades(kind, COSTS[kind])
    t.to_csv(RES / csv_name, index=False)
    win = lambda a, b: t[(t["day0"] >= a) & (t["day0"] <= b)]                         # noqa: E731
    choose, test = win(*CHOOSE), win(*TEST)
    tab = lambda df: pd.DataFrame([{"variant": n, **stats(df[df["variant"] == n])} for n, *_ in variants])  # noqa: E731
    ct, tt = tab(choose), tab(test)
    cand = ct[ct["variant"] != "baseline 15:20"].copy()
    cand["trail"], cand["letter"] = (cand["variant"].str[1:].astype(int),
                                      cand["variant"].str[0].map({"R": 0, "A": 1, "B": 2}))
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
               + ("" if kind == "run12" else
                  "The same rule is next tested on the Rs 1-2 band under its own pre-registration." if passed
                  else "Under the pre-registration, the Rs 1-2 step is not run on this rule."))
    sens = []
    if kind == "run12":
        for label, fn in (("old: Rs 0.10 a side throughout", costs_old),
                          ("optimistic: Rs 0.02 a side from 2025-11-03", costs_optimistic)):
            st, _ = trades(kind, fn)
            for wname, (a, b) in (("2025", CHOOSE), ("2026", TEST)):
                g = st[(st["day0"] >= a) & (st["day0"] <= b)]
                sens.append(f"## Sensitivity ({label}), {wname} (not judged)\n\n"
                            + md(pd.DataFrame([{"variant": n, **stats(g[g["variant"] == n])} for n, *_ in variants])))
    text = "\n".join([
        f"# S1 v10 fade · Rs {FILES[BAND_OF[kind]][2]:.2f}-{FILES[BAND_OF[kind]][3]:.0f} band: {title}, 1-minute prices\n",
        f"Numbers only. Pre-registered: strategies/{'S1_v10_band12_trail.md' if kind == 'run12' else 'S1_v10_band050_trail.md'}. "
        + ("Cost a side: Rs 0.10 before 2025-11-03, Rs 0.04 from it (tick Rs 0.05 -> Rs 0.01). " if kind == "run12"
           else "Cost a side: 2 ticks of Rs 0.05. ")
        + "Entry: the 09:15 minute's close + cost. "
        f"Target: entry x {1 + (variants[1][2] or 0):.2f}" + (" (R) or x 2.00 (A, B)" if kind == "run12" else "")
        + ", filled at the first minute whose high >= target + 1 tick"
        + ("; in B variants the target is not sold but arms the trailing stop from that minute's high. "
           if kind != "run" else ". ")
        + "Trailing stop: peak x (1 - trail) against each minute's low before the peak updates, filled at min(stop, "
        "open) rounded down to the tick - cost; stop first when both touch in a minute. Else the 15:19 minute's close "
        f"- cost. Real charges. Net % of the lot value at entry. t date-clustered. Trades: data/results/{csv_name}.\n",
        verdict + "\n",
        "## Pass criterion (2026, the chosen rule)\n\n" + "\n".join(f"- {k}: **{'yes' if v else 'no'}**" for k, v in crit.items()) + "\n",
        f"## Choose: 2025 (chosen: {chosen}, highest total net Rs)\n\n" + md(ct),
        "## Test: 2026 (only the chosen rule counts; the others for information)\n\n" + md(tt),
        "## Funnel\n\n" + md(pd.DataFrame([dict(fun)])),
        *sens,
    ])
    (RES / md_name).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    {"pick": lambda: pick("050"), "pick12": lambda: pick("12")}.get(sys.argv[1], lambda: run(sys.argv[1]))()
