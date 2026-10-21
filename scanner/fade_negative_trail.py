"""S1 fade · "negative trailing" stops: step the stop down at -20 %, then trail or reset (numbers only).

    python -m scanner.fade_negative_trail

strategies/S1_fade_negative_trail.md fixes every choice. Writes data/results/S1_fade_negative_trail.md.
"""
from __future__ import annotations

import pandas as pd

from server import charges as ch

from .backtest_s1_v2 import md
from .build import ROOT
from .fade_stop_trail import SPLIT
from .stats import clustered_t

RES = ROOT / "data" / "results"


def sell_price(c: pd.DataFrame, e: float, tick: float, v: str) -> float:
    o, h, l, cl, t = (c[k].to_numpy() for k in ("o", "h", "l", "c", "t"))
    floor = {"N2-30": 0.70, "N2-35": 0.65, "N2-40": 0.60, "v11": 0.80}.get(v)
    level, stepped, reset, peak = None, False, False, None
    for i in range(len(c)):
        if t[i] < "09:17":
            continue
        if floor is not None:                                    # plain stop (ladder to a floor = a stop at the floor)
            if l[i] <= floor * e + 1e-9:
                return max(tick, round(min(floor * e, o[i]) - tick, 2))
            continue
        if v == "v10":
            continue
        if level is not None and l[i] <= level + 1e-9:
            return max(tick, round(min(level, o[i]) - tick, 2))
        if not stepped and l[i] <= 0.80 * e + 1e-9:
            stepped, level, peak = True, 0.75 * e, h[i]
            continue
        if stepped:
            if v.startswith("N3") and not reset and h[i] >= e - 1e-9:
                reset, level, peak = True, e, h[i]
                continue
            peak = max(peak, h[i])
            if v == "N1":
                level = max(0.75 * e, 0.95 * peak)
            elif v == "N3b" and reset:
                level = max(e, 0.95 * peak)
    return max(tick, round(cl[-1] - tick, 2))


def main() -> None:
    t = pd.read_csv(RES / "S1_fade_realistic_entry_trades.csv")
    t = t[t["B_excluded"].fillna("") == ""].reset_index(drop=True)
    con = pd.read_csv(RES / "S1_v10_bandv10_contracts.csv")
    strike = {(r.symbol, r.day0, r.side): float(r.strike) for r in con.itertuples()}
    mins = pd.read_csv(RES / "S1_v10_bandv10_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    by = {k: g.sort_values("ts") for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
    vs = ["v11", "v10", "N1", "N2-30", "N2-35", "N2-40", "N3a", "N3b"]
    out = {v: [] for v in vs}
    for r in t.itertuples():
        g = by[(r.symbol, r.day0, r.side, strike[(r.symbol, r.day0, r.side)])]
        c = g[(g["t"] >= "09:16") & (g["t"] <= "15:19")].reset_index(drop=True)
        tick, e, lot = (0.05 if r.day0 < SPLIT else 0.01), float(r.entry_B), int(r.lot)
        for v in vs:
            s = sell_price(c, e, tick, v)
            net = (s - e) * lot - ch.leg(r.side, "BUY", lot, e)["total"] - ch.leg(r.side, "SELL", lot, s)["total"]
            out[v].append(net / (e * lot) * 100)
    res = pd.DataFrame(out)
    res["day0"] = t["day0"]
    tr, te = res[res["day0"] < SPLIT], res[res["day0"] >= SPLIT]
    rows = []
    for v in vs:
        d = te[v] - te["v11"]
        rows.append({"variant": v, "train mean %": round(tr[v].mean(), 2), "test mean %": round(te[v].mean(), 2),
                     "test t": clustered_t(te[v], te["day0"]), "test diff vs v11": round(d.mean(), 2),
                     "diff t": clustered_t(d, te["day0"]) if d.abs().sum() else None, "all mean %": round(res[v].mean(), 2),
                     "all t": clustered_t(res[v], res["day0"]), "win %": round((res[v] > 0).mean() * 100, 1),
                     "worst %": round(res[v].min(), 1)})
    tab = pd.DataFrame(rows)
    cand = tab[~tab["variant"].isin(["v11", "v10"])].sort_values("train mean %", ascending=False)
    best = cand.iloc[0]
    passed = bool(best["test mean %"] > 0 and best["test diff vs v11"] > 0 and (best["diff t"] or 0) >= 2)
    text = "\n".join([
        "# S1 fade · negative trailing stops (step down at -20 %, then trail or reset), realistic entry\n",
        f"Pre-registered: strategies/S1_fade_negative_trail.md. {len(t)} trades; train before {SPLIT} ({len(tr)}), test "
        f"from it ({len(te)}). Net % of premium after charges; t date-clustered.\n",
        f"## The test: **{'PASS' if passed else 'FAIL'}**\n\nTrain winner: **{best['variant']}**: test mean "
        f"{best['test mean %']} %, vs v11 {best['test diff vs v11']:+} points (t {best['diff t']}).\n",
        "## All variants\n\n" + md(tab),
        "\nN1 = step to -25 % then trail 5 % below the peak; N2-x = ladder to a floor (= a stop at -x %); N3a = step to "
        "-25 %, break-even once back at the buy price, then hold; N3b = the same, then trail 5 % below the peak.\n",
    ])
    (RES / "S1_fade_negative_trail.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
