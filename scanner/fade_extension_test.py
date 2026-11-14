"""S1 fade · the extension window (day 0 = 9-21 Oct 2026) on 1-minute candles, and the earlier window + extension together (numbers only).

    python -m scanner.fade_extension_test

strategies/S1_extension_oct2026.md. Same rule as the earlier minute test: entry 09:16 open + 1 tick, price >= Rs 2, lot Rs 600-8,000, exit v12 (live) and v10.
"""
from __future__ import annotations

import pandas as pd

from . import fade_stop_trail as fst
from .backtest_s1_v2 import md
from .build import ROOT
from .fade_cheap_dte import V12
from .fade_entry_time import run_min
from .fade_novolume_test import V10
from .fade_realistic_studies import TICK_CHANGE
from .fastio import read_table
from .stats import clustered_t

RES = ROOT / "data" / "results"


def main() -> None:
    picks = pd.read_csv(RES / "S1_fade_extension_picks.csv")
    mins = read_table(RES / "S1_v10_bandfadeext_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    mins["d"] = mins["ts"].str[:10]
    by = {k: g.sort_values("ts") for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
    rows = []
    for p in picks.itertuples():
        g = by.get((p.symbol, p.day0, p.side, float(p.strike)))
        rec = {"symbol": p.symbol, "day0": p.day0, "side": p.side, "lot": int(p.lot)}
        if g is None:
            rows.append({**rec, "why": "no candles"})
            continue
        c = g[(g["d"] == p.day0) & (g["t"] >= "09:16") & (g["t"] <= "15:19")].reset_index(drop=True)
        first = c[c["t"] == "09:16"]
        if first.empty:
            rows.append({**rec, "why": "no 09:16 candle"})
            continue
        tick = 0.05 if p.day0 < TICK_CHANGE else 0.01
        e = round(float(first["o"].iloc[0]) + tick, 2)
        if e < 2 or not 600 <= e * p.lot <= 8000:
            rows.append({**rec, "why": f"entry {e} outside the live price/lot band"})
            continue
        sell, at = fst.walk(c, e, tick, V12, 1)
        last = len(c) - 1 if at is None else at
        held, after = c.iloc[: last + 1], c.iloc[last + 1:]
        pct = lambda x: (float(x) / e - 1) * 100
        rows.append({**rec, "entry": e, "v12": run_min(c, e, p.lot, p.side, p.day0, V12), "v10": run_min(c, e, p.lot, p.side, p.day0, V10),
                     "held_max_up": pct(held["h"].max()), "held_max_dip": pct(held["l"].min()),
                     "after_peak": pct(after["h"].max()) if len(after) else None, "day_high": pct(c["h"].max()), "why": ""})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "S1_fade_extension_trades.csv", index=False)
    ok = df[df["why"] == ""].copy()
    out = [f"## Extension window, day 0 = 9-21 Oct 2026: {len(df)} fade picks, {len(ok)} buyable at 09:16 on minute candles\n"]
    if len(ok):
        net = lambda col: ok[col] / 100 * ok["entry"] * ok["lot"]
        tab = [{"exit": v, "n": len(ok), "win %": round((ok[v] > 0).mean() * 100, 1), "mean %": round(ok[v].mean(), 2), "median %": round(ok[v].median(), 1),
                "total Rs": round(net(v).sum()), "t": None if len(ok) < 2 else round(clustered_t(ok[v].values, ok["day0"].values) or 0, 2)} for v in ("v12", "v10")]
        mx = pd.DataFrame([{"measure": lab, "mean %": round(ok[c].mean(), 1), "median %": round(ok[c].median(), 1),
                            ">= +50 %": int((ok[c] >= 50).sum()), ">= +100 %": int((ok[c] >= 100).sum()), ">= +200 %": int((ok[c] >= 200).sum())}
                           for c, lab in (("held_max_up", "max up while held"), ("day_high", "highest price of the day"), ("after_peak", "peak after the v12 sale"))])
        out += ["Max up first (candle highs, % of entry):\n", md(mx), "\nBooked result:\n", md(pd.DataFrame(tab)) + "\n",
                f"Held max dip mean {ok.held_max_dip.mean():.0f} %, median {ok.held_max_dip.median():.0f} %.\n"]
    nb = df[df["why"] != ""]
    if len(nb):
        out.append("Not testable:\n\n" + md(nb[["symbol", "day0", "side", "why"]]) + "\n")
    old = pd.read_csv(RES / "S1_fade_minutes_retest_trades.csv")
    old = old[old.lot_ok & (old.entry_B >= 2)]
    comb = pd.concat([old[["day0", "v12_net_pct", "v10_net_pct"]].rename(columns={"v12_net_pct": "v12", "v10_net_pct": "v10"}), ok[["day0", "v12", "v10"]]])
    ct = [{"set": nm, "n": len(d), "v12 mean %": round(d.v12.mean(), 2), "v12 win %": round((d.v12 > 0).mean() * 100, 1),
           "v12 t": round(clustered_t(d.v12.values, d.day0.values) or 0, 2), "v10 mean %": round(d.v10.mean(), 2)}
          for nm, d in (("earlier window (Oct 2024 - Sep 2026)", comb.iloc[: len(old)]), ("extension only", ok), ("earlier + extension", comb))]
    out.append("Earlier window and extension together:\n\n" + md(pd.DataFrame(ct)) + "\n")
    rep = "# S1 fade · extension to Oct 2026 on minute candles\n\nNumbers only. Pre-registered: strategies/S1_extension_oct2026.md.\n\n" + "\n".join(out)
    (RES / "S1_extension_oct2026.md").write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
