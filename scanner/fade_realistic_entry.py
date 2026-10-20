"""S1 fade · the backtest re-run with a realistic entry (09:16 candle open + 1 tick) beside the old one.

    python -m scanner.fade_realistic_entry

strategies/S1_fade_realistic_entry.md fixes every choice. Writes data/results/S1_fade_realistic_entry.md and _trades.csv.
"""
from __future__ import annotations

import pandas as pd

from server import charges as ch

from .backtest_s1_v2 import md
from .build import ROOT
from .stats import clustered_t

RES = ROOT / "data" / "results"
TICK_CHANGE = "2025-11-03"


def trade(m: pd.DataFrame, r, entry: float, stop_from: str, tick: float) -> dict:
    """v10 (15:19 close - tick) and v11 (-20 % stop from stop_from, else v10) for one entry price."""
    m = m[(m["t"] >= "09:15") & (m["t"] <= "15:19")]
    lot = int(r.lot)

    def net(sell: float) -> float:
        c = ch.leg(r.side, "BUY", lot, entry)["total"] + ch.leg(r.side, "SELL", lot, sell)["total"]
        return (sell - entry) * lot - c

    v10_sell = max(tick, round(float(m["c"].iloc[-1]) - tick, 2))
    stop = 0.80 * entry
    hit = m[(m["l"] <= stop + 1e-9) & (m["t"] >= stop_from)]
    v11_sell, when = v10_sell, ""
    if not hit.empty:
        row = hit.iloc[0]
        v11_sell, when = max(tick, round(min(stop, float(row["o"])) - tick, 2)), row["t"]
    return {"v10_net": round(net(v10_sell), 2), "v11_net": round(net(v11_sell), 2), "stop_time": when,
            "premium": round(entry * lot, 2),
            "first_close_pct": round((float(m["c"].iloc[0]) / entry - 1) * 100, 1)}


def stats(g: pd.DataFrame, col: str) -> dict:
    if g.empty:
        return {"n": 0}
    pct = g[col] / g["premium"] * 100
    return {"n": len(g), "win %": round((g[col] > 0).mean() * 100, 1), "mean %": round(pct.mean(), 2),
            "median %": round(pct.median(), 2), "total Rs": round(g[col].sum()),
            "t": clustered_t(pct, g["day0"]) if len(g) > 1 else None}


def main() -> None:
    c = pd.read_csv(RES / "S1_v10_bandv10_contracts.csv")
    mins = pd.read_csv(RES / "S1_v10_bandv10_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    by = {k: g.sort_values("ts").reset_index(drop=True) for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
    rows = []
    for r in c.itertuples():
        m = by.get((r.symbol, r.day0, r.side, float(r.strike)))
        if m is None or m[(m["t"] >= "09:15") & (m["t"] <= "15:19")].empty:
            continue
        tick = 0.05 if r.day0 < TICK_CHANGE else 0.01
        a = trade(m, r, float(r.entry_price), "09:16", tick)
        c16 = m[m["t"] == "09:16"]
        base = {"symbol": r.symbol, "day0": r.day0, "side": r.side, "lot": int(r.lot), "entry_A": float(r.entry_price),
                "old_e1_net": float(r.e1_net)}
        row = {**base, **{f"A_{k}": v for k, v in a.items()}}
        if c16.empty:
            row["B_excluded"] = "no_0916_candle"
        else:
            eb = round(float(c16["o"].iloc[0]) + tick, 2)
            b = trade(m, r, eb, "09:17", tick)
            row.update({"entry_B": eb, "B_excluded": "", **{f"B_{k}": v for k, v in b.items()},
                        "B_rule_fail": bool(eb < 2 or not (600 <= eb * int(r.lot) <= 8000))})
        rows.append(row)
    t = pd.DataFrame(rows)
    t["window"] = t["day0"].map(lambda d: "Oct24-Oct25" if d < "2025-11-03" else "Nov25-Sep26")
    t.to_csv(RES / "S1_fade_realistic_entry_trades.csv", index=False)
    ok = t[t["B_excluded"] == ""].copy()

    def st(df, e, x):
        g = df[["day0", f"{e}_premium", f"{e}_{x}_net"]].rename(columns={f"{e}_premium": "premium", f"{e}_{x}_net": "net"})
        return stats(g, "net")

    main_tab = pd.DataFrame([{"entry": e, "exit": x, **st(ok, e, x)} for e in ("A", "B") for x in ("v10", "v11")])
    main_tab["entry"] = main_tab["entry"].map({"A": "A old (backtest open)", "B": "B new (09:16 open + tick)"})
    win_tab = pd.DataFrame([{"window": w, "exit": x, **st(ok[ok["window"] == w], "B", x)}
                            for w in ("Oct24-Oct25", "Nov25-Sep26") for x in ("v10", "v11")])
    ok["B_rule_fail"] = ok["B_rule_fail"].astype(bool)
    passr = ok[~ok["B_rule_fail"]]
    rule_tab = pd.DataFrame([
        {"set": "all B trades", **st(ok, "B", "v11"), "exit": "v11"},
        {"set": "fail the rules at B (fill < 2 or lot Rs outside 600-8000)", **st(ok[ok["B_rule_fail"]], "B", "v11"), "exit": "v11"},
        {"set": "B trades that pass the rules", **st(passr, "B", "v11"), "exit": "v11"},
        {"set": "B trades that pass the rules", **st(passr, "B", "v10"), "exit": "v10"}])
    big_loss = ok[(ok["A_v11_net"] / ok["A_premium"] * 100).between(-85, -30)]
    pop = ok[ok["A_first_close_pct"] >= 20]
    big_win = ok[ok["A_v11_net"] / ok["A_premium"] * 100 >= 300]
    cmp_tab = pd.DataFrame([
        {"group (picked under A)": "lost -30..-85 % under A (v11)", "n": len(big_loss),
         "A mean %": round((big_loss["A_v11_net"] / big_loss["A_premium"] * 100).mean(), 1),
         "B mean %": round((big_loss["B_v11_net"] / big_loss["B_premium"] * 100).mean(), 1)},
        {"group (picked under A)": "first candle closed >= +20 % over A entry", "n": len(pop),
         "A mean %": round((pop["A_v11_net"] / pop["A_premium"] * 100).mean(), 1),
         "B mean %": round((pop["B_v11_net"] / pop["B_premium"] * 100).mean(), 1)},
        {"group (picked under A)": "won >= +300 % under A (v11)", "n": len(big_win),
         "A mean %": round((big_win["A_v11_net"] / big_win["A_premium"] * 100).mean(), 1),
         "B mean %": round((big_win["B_v11_net"] / big_win["B_premium"] * 100).mean(), 1)}])
    move = (ok["entry_B"] / ok["entry_A"] - 1) * 100
    dist = pd.DataFrame([{"B entry vs A entry": "median", "%": round(move.median(), 1)},
                         {"B entry vs A entry": "share B > A by 20 %+", "%": round((move >= 20).mean() * 100, 1)},
                         {"B entry vs A entry": "share B < A by 20 %+", "%": round((move <= -20).mean() * 100, 1)},
                         {"B entry vs A entry": "share within +-5 %", "%": round((move.abs() <= 5).mean() * 100, 1)}])
    text = "\n".join([
        "# S1 fade · the backtest with a realistic entry (09:16 candle open + 1 tick)\n",
        "Pre-registered: strategies/S1_fade_realistic_entry.md. Descriptive; nothing live changes. Same "
        f"{len(ok)} contracts for A and B ({len(t) - len(ok)} excluded: no 09:16 candle). Same exit code for both; real "
        "charges, no extra % slippage. t is date-clustered.\n",
        "## A (old entry) vs B (new entry), v10 and v11 exits\n\n" + md(main_tab),
        "## B by window\n\n" + md(win_tab),
        "## B and the rules (fill >= Rs 2, one lot Rs 600-8,000)\n\n" + md(rule_tab),
        "## The odd trades of the old entry, under B\n\n" + md(cmp_tab),
        "## How far B is from A\n\n" + md(dist),
    ])
    (RES / "S1_fade_realistic_entry.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
