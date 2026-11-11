"""S1 fade · v12 on minute candles: max up / max dip while held and after the sale (numbers only, descriptive).

    python -m scanner.fade_v12_maxup

The live-rule fade trades with 1-minute candles (Oct 2024 - Sep 2026): entry = 09:16 open + 1 tick, price >= Rs 2, lot Rs 600-8,000, exit = v12
(-20 % stop from 09:17, 2 % trail once +10 %, else the 15:19 close). All figures are % of the entry fill, from candle highs / lows (an upper bound on what
a bid could pay; the live account's own recorded peak is the better measure). After the sale = the rest of day 0 to 15:19, and where the carry set
(S1_v10_bandcarry_minutes) has the contract, the later sessions up to its expiry.
"""
from __future__ import annotations

import pandas as pd

from . import fade_stop_trail as fst
from .backtest_s1_v2 import md
from .build import ROOT
from .fade_cheap_dte import V12
from .fade_realistic_studies import SETS, TICK_CHANGE
from .fastio import read_table

RES = ROOT / "data" / "results"


def main() -> None:
    mp = pd.read_csv(RES / "S1_nbr_fade_map.csv").drop_duplicates(["symbol", "day0", "side"])
    pk = pd.concat([read_table(RES / f"S1_v10_{s}_minutes.csv") for s in SETS]).drop_duplicates(["symbol", "day0", "side", "strike", "ts"])
    pk["t"] = pk["ts"].str[11:16]
    pk["d"] = pk["ts"].str[:10]
    by = {k: g.sort_values("ts") for k, g in pk.groupby(["symbol", "day0", "side", "strike"])}
    carry = read_table(RES / "S1_v10_bandcarry_minutes.csv")
    carry["d"] = carry["ts"].str[:10]
    cby = {k: g.sort_values("ts") for k, g in carry.groupby(["symbol", "day0", "side", "strike"])}
    lots = {}
    for s in SETS:
        c = pd.read_csv(RES / f"S1_v10_{s}_contracts.csv")
        lots.update({(r.symbol, r.day0, r.side, float(r.strike)): int(r.lot) for r in c.itertuples()})
    rows = []
    for p in mp.itertuples():
        key = (p.symbol, p.day0, p.side, float(p.pick_strike))
        g, lot = by.get(key), lots.get(key)
        if g is None or not lot:
            continue
        c = g[(g["d"] == p.day0) & (g["t"] >= "09:16") & (g["t"] <= "15:19")].reset_index(drop=True)
        first = c[c["t"] == "09:16"]
        if first.empty:
            continue
        tick = 0.05 if p.day0 < TICK_CHANGE else 0.01
        e = round(float(first["o"].iloc[0]) + tick, 2)
        if e < 2 or not 600 <= e * lot <= 8000:
            continue
        sell, at = fst.walk(c, e, tick, V12, 1)
        last = len(c) - 1 if at is None else at
        held = c.iloc[: last + 1]
        after = c.iloc[last + 1:]
        reason = "15:19 close" if at is None else ("stop" if sell <= e * 0.8 + 1e-9 else "trail")
        pct = lambda x: (float(x) / e - 1) * 100
        rec = {"symbol": p.symbol, "day0": p.day0, "side": p.side, "entry": e, "sell": sell, "reason": reason,
               "net_pct": round((sell / e - 1) * 100, 1), "held_max_up": pct(held["h"].max()), "held_max_dip": pct(held["l"].min()),
               "held_minutes": last,
               "after_peak": pct(after["h"].max()) if len(after) else None, "after_low": pct(after["l"].min()) if len(after) else None,
               "close_1519": pct(c["c"].iloc[-1]), "day_high": pct(c["h"].max())}
        cg = cby.get(key)
        if cg is not None:
            later = cg[cg["d"] > p.day0]
            if len(later):
                rec["later_days_peak"] = pct(later["h"].max())
                rec["later_days"] = later["d"].nunique()
        rows.append(rec)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "S1_fade_v12_maxup_trades.csv", index=False)

    def st(g: pd.DataFrame, lab: str) -> dict:
        a = g["after_peak"].dropna()
        return {"group": lab, "n": len(g), "held max up mean / median": f"{g.held_max_up.mean():.0f} / {g.held_max_up.median():.0f}",
                "held max dip mean / median": f"{g.held_max_dip.mean():.0f} / {g.held_max_dip.median():.0f}",
                "after-sale peak mean / median": f"{a.mean():.0f} / {a.median():.0f}" if len(a) else "-",
                "15:19 close mean / median": f"{g.close_1519.mean():.0f} / {g.close_1519.median():.0f}",
                "day high mean / median": f"{g.day_high.mean():.0f} / {g.day_high.median():.0f}",
                "v12 price change before charges, mean / median": f"{g.net_pct.mean():.1f} / {g.net_pct.median():.1f}"}
    tab = [st(df, "all v12 trades")] + [st(df[df.reason == r], f"sold by: {r}") for r in ("stop", "trail", "15:19 close")]
    tab += [st(df[df.side == s], f"side {s}") for s in ("PE", "CE")]
    thr = pd.DataFrame([{"level": f">= {t} %", "held max up": int((df.held_max_up >= t).sum()),
                         "after-sale peak": int((df.after_peak.dropna() >= t).sum()), "day high": int((df.day_high >= t).sum())} for t in (25, 50, 100)])
    later = df.dropna(subset=["later_days_peak"])
    rep = (f"# S1 fade · v12 max up / max dip while held and after the sale (minute candles)\n\nNumbers only, descriptive. {len(df)} fade trades, entry 09:16 open + 1 tick. "
           "All as % of the entry fill, from candle highs and lows (upper bounds on a bid).\n\n" + md(pd.DataFrame(tab)) +
           "\n\nTrades reaching a level (of " + str(len(df)) + "):\n\n" + md(thr) +
           (f"\n\nLater sessions (carry candles exist for {len(later)} trades, {later.later_days.median():.0f} later days on median): peak after day 0 mean "
            f"{later.later_days_peak.mean():.0f} %, median {later.later_days_peak.median():.0f} %; >= 100 % in {int((later.later_days_peak >= 100).sum())} trades.\n"))
    (RES / "S1_fade_v12_maxup.md").write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
