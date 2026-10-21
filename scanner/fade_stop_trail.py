"""S1 fade · wider stops, a 1-minute wait, trailing stops and re-entry, on the realistic entry (numbers only).

    python -m scanner.fade_stop_trail

strategies/S1_fade_stop_trail_study.md fixes every choice: entry B (09:16 open + 1 tick), 1-minute candles to 15:19,
pick the best variant on train (before 2025-11-03), test it against v11 on the rest. Writes
data/results/S1_fade_stop_trail.md and _variants.csv.
"""
from __future__ import annotations

import pandas as pd

from server import charges as ch

from .backtest_s1_v2 import md
from .build import ROOT
from .stats import clustered_t

RES = ROOT / "data" / "results"
SPLIT = "2025-11-03"


def variants() -> list[dict]:
    v = [{"name": "no stop", "S": None, "mode": "touch", "start": "09:17", "A": None, "D": None, "re": False, "rules": 0}]
    for s in (20, 25, 28, 30, 35, 40, 50):
        for mode in ("touch", "wait1m"):
            for start in ("09:17", "09:30", "10:00"):
                v.append({"name": f"stop {s} {mode} from {start}", "S": s, "mode": mode, "start": start, "A": None,
                          "D": None, "re": False, "rules": 1 + (mode != "touch") + (start != "09:17")})
    for base in (None, 20, 30):
        for a in (0, 20, 50):
            for d in (15, 20, 30):
                v.append({"name": f"{'no stop' if base is None else f'stop {base}'} + trail A{a} D{d}", "S": base,
                          "mode": "touch", "start": "09:17", "A": a, "D": d, "re": False, "rules": 2 + (base is not None)})
    v.append({"name": "v11 + re-entry", "S": 20, "mode": "touch", "start": "09:17", "A": None, "D": None, "re": True, "rules": 2})
    return v


def walk(c: pd.DataFrame, entry: float, tick: float, v: dict, i0: int) -> tuple[float, int | None]:
    """Sell price and the index of the selling candle (None = held to 15:19), from candle i0 on."""
    o, h, l, cl, t = c["o"].to_numpy(), c["h"].to_numpy(), c["l"].to_numpy(), c["c"].to_numpy(), c["t"].to_numpy()
    stop = entry * (1 - v["S"] / 100) if v["S"] else None
    active, peak, n = v["A"] == 0, None, len(c)
    for i in range(i0, n):
        if stop is not None and t[i] >= v["start"]:
            if v["mode"] == "touch" and l[i] <= stop + 1e-9:
                return max(tick, round(min(stop, o[i]) - tick, 2)), i
            if v["mode"] == "wait1m" and cl[i] <= stop + 1e-9 and i + 1 < n:
                return max(tick, round(o[i + 1] - tick, 2)), i + 1
        if v["A"] is not None:
            if active and peak is not None:
                lvl = peak * (1 - v["D"] / 100)
                if l[i] <= lvl + 1e-9:
                    return max(tick, round(min(lvl, o[i]) - tick, 2)), i
            if not active and h[i] >= entry * (1 + v["A"] / 100) - 1e-9:
                active = True
            if active:
                peak = h[i] if peak is None else max(peak, h[i])
    return max(tick, round(cl[-1] - tick, 2)), None


def one(c: pd.DataFrame, r, v: dict) -> float:
    lot, side, tick = int(r.lot), r.side, (0.05 if r.day0 < SPLIT else 0.01)

    def net(buy: float, sell: float) -> float:
        return (sell - buy) * lot - ch.leg(side, "BUY", lot, buy)["total"] - ch.leg(side, "SELL", lot, sell)["total"]
    e = float(r.entry_B)
    i0 = int((c["t"] < "09:17").sum())
    sell, at = walk(c, e, tick, v, i0)
    total = net(e, sell)
    if v["re"] and at is not None:
        cl, t = c["c"].to_numpy(), c["t"].to_numpy()
        for j in range(at + 1, len(c) - 1):
            if t[j] >= "15:00":
                break
            if cl[j] >= e - 1e-9:
                e2 = round(float(c["o"].iloc[j + 1]) + tick, 2)
                s2, _ = walk(c, e2, tick, {"S": 20, "mode": "touch", "start": "00:00", "A": None}, j + 2)
                total += net(e2, s2)
                break
    return round(total / (e * lot) * 100, 3)


def main() -> None:
    t = pd.read_csv(RES / "S1_fade_realistic_entry_trades.csv")
    t = t[t["B_excluded"].fillna("") == ""].reset_index(drop=True)
    con = pd.read_csv(RES / "S1_v10_bandv10_contracts.csv")
    strike = {(r.symbol, r.day0, r.side): float(r.strike) for r in con.itertuples()}
    mins = pd.read_csv(RES / "S1_v10_bandv10_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    by = {k: g.sort_values("ts") for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
    cs = []
    for r in t.itertuples():
        g = by[(r.symbol, r.day0, r.side, strike[(r.symbol, r.day0, r.side)])]
        cs.append(g[(g["t"] >= "09:16") & (g["t"] <= "15:19")].reset_index(drop=True))
    vs = variants()
    res = pd.DataFrame({v["name"]: [one(c, r, v) for c, r in zip(cs, t.itertuples())] for v in vs})
    res["day0"], res["half"] = t["day0"], t["day0"].map(lambda d: "train" if d < SPLIT else "test")
    res.to_csv(RES / "S1_fade_stop_trail_trades.csv", index=False)
    base = "stop 20 touch from 09:17"
    tr, te = res[res["half"] == "train"], res[res["half"] == "test"]

    def row(v):
        n = v["name"]
        d = te[n] - te[base]
        return {"variant": n, "train mean %": round(tr[n].mean(), 2), "train t": clustered_t(tr[n], tr["day0"]),
                "test mean %": round(te[n].mean(), 2), "test t": clustered_t(te[n], te["day0"]),
                "test win %": round((te[n] > 0).mean() * 100, 1), "test worst %": round(te[n].min(), 1),
                "test diff vs v11": round(d.mean(), 2), "diff t": clustered_t(d, te["day0"]) if d.abs().sum() else None,
                "all mean %": round(res[n].mean(), 2), "rules": v["rules"]}
    tab = pd.DataFrame([row(v) for v in vs]).sort_values(["train mean %", "rules"], ascending=[False, True])
    tab.to_csv(RES / "S1_fade_stop_trail_variants.csv", index=False)
    best = tab.iloc[0]
    passed = bool(best["test mean %"] > 0 and best["test diff vs v11"] > 0 and (best["diff t"] or 0) >= 2)
    fam = lambda s: "re-entry" if "re-entry" in s else "trailing" if "trail" in s else "stop width"   # noqa: E731
    tab["family"] = tab["variant"].map(fam)
    fam_best = tab.groupby("family", sort=False).head(1)
    v11 = tab[tab["variant"] == base]
    cols = ["variant", "train mean %", "train t", "test mean %", "test t", "test win %", "test worst %",
            "test diff vs v11", "diff t", "all mean %"]
    text = "\n".join([
        "# S1 fade · wider stops, a 1-minute wait, trailing stops and re-entry (realistic entry)\n",
        f"Pre-registered: strategies/S1_fade_stop_trail_study.md. {len(t)} trades, entry = 09:16 open + 1 tick; "
        f"train = before {SPLIT} ({len(tr)}), test = from {SPLIT} ({len(te)}). Net % of premium after real charges; "
        f"t date-clustered. {len(vs)} variants.\n",
        f"## The test: **{'PASS' if passed else 'FAIL'}**\n\nTrain winner: **{best['variant']}**. On test: mean "
        f"{best['test mean %']} % (t {best['test t']}); vs v11 {best['test diff vs v11']:+} points (t {best['diff t']}). "
        "Pass needs test mean > 0 and the difference to v11 > 0 with t >= 2.\n",
        "## v11 (baseline)\n\n" + md(v11[cols]),
        "## Best of each family on train, shown on test\n\n" + md(fam_best[["family"] + cols]),
        "## Top 15 on train\n\n" + md(tab.head(15)[cols]),
        "## Stop width only (touch, from 09:17)\n\n" + md(tab[tab["variant"].str.match(r"^(stop \d+ touch from 09:17|no stop)$")]
                                                          .sort_values("variant")[cols]),
        "\nAll variants: data/results/S1_fade_stop_trail_variants.csv.\n",
    ])
    (RES / "S1_fade_stop_trail.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
