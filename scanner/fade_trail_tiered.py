"""S1 fade · a trail that widens once the gain passes +40 % (numbers only).

    python -m scanner.fade_trail_tiered

strategies/S1_fade_trail_tiered.md fixes every choice. Entry B (09:16 open + 1 tick), 1-minute candles 09:17-15:19,
the -20 % stop, a trail on at +10 % whose gap is G1 below entry x (1 + T) and G2 above it. Writes
data/results/S1_fade_trail_tiered.md and _variants.csv.
"""
from __future__ import annotations

import pandas as pd

from server import charges as ch

from .backtest_s1_v2 import md
from .build import ROOT
from .fade_stop_trail import SPLIT
from .stats import clustered_t

RES = ROOT / "data" / "results"
SETS = ("bandv10", "band12", "band12q4", "band050", "band050q4")


def sell(c: pd.DataFrame, e: float, tick: float, g1: float | None, g2: float | None, thr: float = 0.40,
         ratchet: bool = False, stop_on: bool = True) -> tuple[float, str, str]:
    """(sell price, how, time). g1 None = no trail (v11 / v10)."""
    o, h, l, cl, t = (c[k].to_numpy() for k in ("o", "h", "l", "c", "t"))
    stop, active, peak, level = 0.80 * e, False, None, None
    for i in range(len(c)):
        if t[i] < "09:17":
            continue
        if stop_on and l[i] <= stop + 1e-9:
            return max(tick, round(min(stop, o[i]) - tick, 2)), "stop", t[i]
        if g1 is None:
            continue
        if active and peak is not None:
            gap = g1 if peak < e * (1 + thr) - 1e-9 else g2
            lv = peak * (1 - gap)
            level = max(level, lv) if (ratchet and level is not None) else lv
            if l[i] <= level + 1e-9:
                return max(tick, round(min(level, o[i]) - tick, 2)), "trail", t[i]
        if not active and h[i] >= e * 1.10 - 1e-9:
            active = True
        if active:
            peak = h[i] if peak is None else max(peak, h[i])
    return max(tick, round(cl[-1] - tick, 2)), "15:19", t[-1]


def variants() -> list[dict]:
    v = [dict(name="v12: gap 2 % (live)", g1=0.02, g2=0.02), dict(name="gap 5 % flat (shadow tag)", g1=0.05, g2=0.05),
         dict(name="v11: stop only", g1=None, g2=None), dict(name="v10: no stop", g1=None, g2=None, stop_on=False)]
    for g1 in (0.02, 0.05):
        for g2 in (0.10, 0.15, 0.20):
            v.append(dict(name=f"gap {g1:.0%} -> {g2:.0%} past +40 %", g1=g1, g2=g2, grid=True))
    for thr in (0.30, 0.60):
        for g1, g2 in ((0.02, 0.15), (0.05, 0.15)):
            v.append(dict(name=f"gap {g1:.0%} -> {g2:.0%} past +{thr:.0%}", g1=g1, g2=g2, thr=thr))
    for g1, g2 in ((0.02, 0.15), (0.05, 0.15)):
        v.append(dict(name=f"gap {g1:.0%} -> {g2:.0%} past +40 %, ratchet", g1=g1, g2=g2, ratchet=True))
    return v


def run(trades: pd.DataFrame, by: dict, vs: list[dict]) -> pd.DataFrame:
    out = {}
    for v in vs:
        pct, how, rs = [], [], []
        for r in trades.itertuples():
            c = by[(r.symbol, r.day0, r.side, float(r.strike))]
            tick, e, q = (0.05 if r.day0 < SPLIT else 0.01), float(r.entry_B), int(r.qty)
            s, hw, _ = sell(c, e, tick, v["g1"], v["g2"], v.get("thr", 0.40), v.get("ratchet", False), v.get("stop_on", True))
            net = (s - e) * q - ch.leg(r.side, "BUY", q, e)["total"] - ch.leg(r.side, "SELL", q, s)["total"]
            pct.append(round(net / (e * q) * 100, 3)); rs.append(round(net, 2)); how.append(hw)
        out[v["name"]] = (pct, rs, how)
    return out


def table(trades: pd.DataFrame, res: dict, label: str) -> pd.DataFrame:
    rows = []
    base = pd.Series(res["v12: gap 2 % (live)"][0], index=trades.index)
    tr, te = trades["day0"] < SPLIT, trades["day0"] >= SPLIT
    big = trades["peak"] >= 40
    for name, (pct, rs, how) in res.items():
        p, r, hw = pd.Series(pct, index=trades.index), pd.Series(rs, index=trades.index), pd.Series(how, index=trades.index)
        d = p - base
        rows.append({"set": label, "exit": name, "n": len(p), "win %": round((r > 0).mean() * 100, 1),
                     "mean %": round(p.mean(), 2), "total Rs": round(r.sum()), "t": clustered_t(p, trades["day0"]),
                     "train mean %": round(p[tr].mean(), 2), "test mean %": round(p[te].mean(), 2),
                     "test diff vs v12": round(d[te].mean(), 2),
                     "diff t": clustered_t(d[te], trades.loc[te, "day0"]) if d[te].abs().sum() else None,
                     "stop / trail / 15:19": f"{(hw == 'stop').sum()} / {(hw == 'trail').sum()} / {(hw == '15:19').sum()}",
                     f"kept on {int(big.sum())} trades peaking >= +40 %": round(p[big].mean(), 1)})
    return pd.DataFrame(rows)


def main() -> None:
    by = {}
    for s in SETS:
        m = pd.read_csv(RES / f"S1_v10_{s}_minutes.csv")
        m["t"] = m["ts"].str[11:16]
        for k, g in m.groupby(["symbol", "day0", "side", "strike"]):
            if k not in by:
                g = g.sort_values("ts")
                by[k] = g[(g["t"] >= "09:16") & (g["t"] <= "15:19")].reset_index(drop=True)
    c = pd.read_csv(RES / "S1_fade_cheap_dte_trades.csv")
    live = c[(c["entry_B"] >= 2) & c["lot_ok"]].copy()
    live["qty"] = live["lot"]
    ref = pd.read_csv(RES / "S1_refused_listing_price_trades.csv")
    ref["qty"] = ref["lots"] * ref["lot"]
    for df in (live, ref):
        df["peak"] = [(by[(r.symbol, r.day0, r.side, float(r.strike))]["h"].max() / r.entry_B - 1) * 100
                      for r in df.itertuples()]
    vs = variants()
    t_live = table(live, run(live, by, vs), "live fade set (B >= Rs 2)")
    sets = {"refused, listing Rs 2-7": ref[(ref.listing_close >= 2) & (ref.listing_close < 7)],
            "refused, listing Rs 2-10": ref[(ref.listing_close >= 2) & (ref.listing_close < 10)]}
    others = [table(df, run(df, by, vs), k) for k, df in sets.items()]
    allv = pd.concat([t_live] + others)
    allv.to_csv(RES / "S1_fade_trail_tiered_variants.csv", index=False)
    grid = t_live[t_live["exit"].isin([v["name"] for v in vs if v.get("grid")])].sort_values("train mean %", ascending=False)
    best = grid.iloc[0]
    passed = bool(best["test mean %"] > 0 and best["test diff vs v12"] > 0 and (best["diff t"] or 0) >= 2)
    cols = ["exit", "n", "win %", "mean %", "total Rs", "t", "train mean %", "test mean %", "test diff vs v12", "diff t",
            "stop / trail / 15:19"]
    kept = [k for k in t_live.columns if k.startswith("kept on")][0]
    text = "\n".join([
        "# S1 fade · a trail that widens once the gain passes +40 % (realistic entry)\n",
        "Pre-registered: strategies/S1_fade_trail_tiered.md. Entry 09:16 open + 1 tick; -20 % stop; trail on at +10 %, gap "
        "G1 below +40 % and G2 above; real charges; t date-clustered; train before 2025-11-03, test from it.\n",
        f"## The test (live fade set): **{'PASS' if passed else 'FAIL'}**\n\nTrain winner: **{best['exit']}**: test mean "
        f"{best['test mean %']} %, vs v12 {best['test diff vs v12']:+} points (t {best['diff t']}).\n",
        "## Live fade set (B >= Rs 2, 1 lot)\n\n" + md(t_live[cols + [kept]]),
    ] + [f"## {k} (max lots under Rs 8,000)\n\n" + md(o[cols + [[x for x in o.columns if x.startswith('kept on')][0]]])
         for k, o in zip(sets, others)])
    (RES / "S1_fade_trail_tiered.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
