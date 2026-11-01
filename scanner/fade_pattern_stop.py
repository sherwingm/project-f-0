"""S1 v12 fade · on "Nifty up yesterday + gap down" days, does a wider stop help? 09:16 buy and four indicator entries (numbers only)

    python -m scanner.fade_pattern_stop

On those days the fade is often right but early: the −20 % stop is hit before the move. Same 73 pattern trades as
scanner.fade_pattern_entry_more. Stop −20 % (v12), −25 %, −30 %, −40 % or none; everything else as v12 (touch from
09:17, 2 % trail once +10 %, else 15:19), real charges. Five entries: the 09:16 buy (09:16 open + 1 tick) and the
four indicator rules picked in the last two studies (first traded candle after the sign). 20 new pairs, so a wider stop
counts only if it beats the −20 % stop with the same entry in BOTH halves and the per-trade gain has a date-clustered
t of at least 2. The other days are shown as a control (a pattern-only stop would not touch them).
Writes data/results/S1_fade_pattern_stop.xlsx.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment

from .fade_indicators import RES, V12, net_pct
from .fade_indicators_xlsx import GOOD, F, FB, sheet
from .fade_market_pattern import market
from .fade_pattern_entry_more import FIRST, LAST, all_signs
from .fade_stop_trail import SPLIT, walk
from .stats import clustered_t

STOPS = [20, 25, 30, 40, None]
ENTRIES = {
    "09:16 buy (live rule)": None,
    "RSI back above 30 + above EMA 50": ("opt RSI back above 30 (after < 30)", "opt above EMA 50"),
    "range high + Nifty RSI + after 12:30": ("opt above the 09:15 – 09:29 range high", "Nifty RSI with the trade", "clock 12:30 or later"),
    "EMA 9 + Supertrend 7×2 turned up + crossed VWAP": ("opt above EMA 9", "opt Supertrend 7×2 just turned up", "opt just crossed above VWAP"),
    "Supertrend 7×2 turned up + stock past VWAP": ("opt Supertrend 7×2 just turned up", "stock past VWAP with the trade"),
}


def stop_name(s: int | None) -> str:
    return "no stop" if s is None else f"stop −{s} %"


def buy_at(c: pd.DataFrame, sg: dict, signs: tuple[str, ...]) -> int | None:
    """Candle index of the buy: the first traded candle after the first minute 09:17 – 15:00 where every sign is true."""
    tt, n = c["t"].to_numpy(), len(c)
    m = (tt >= FIRST) & (tt <= LAST)
    m[n - 2:] = False
    for s in signs:
        m &= sg[s][1] if s in sg else False
    idx = np.flatnonzero(m)
    if not len(idx):
        return None
    vol, k = c["volume"].to_numpy(), int(idx[0]) + 1
    while k < n - 1 and vol[k] == 0:
        k += 1
    return k if vol[k] > 0 else None


def run(f: pd.DataFrame) -> pd.DataFrame:
    pre_, _, _ = all_signs(f)
    rows = []
    for r, _, c, e0, sg in pre_:
        tick, lot, side = (0.05 if r.day0 < SPLIT else 0.01), int(r.lot), r.side
        h, lo = c["h"].to_numpy(), c["l"].to_numpy()
        for name, signs in ENTRIES.items():
            if signs is None:
                k, e = int((c["t"] < "09:17").sum()), e0                    # as v12: buy at 09:16, exits checked from 09:17
            else:
                k = buy_at(c, sg, signs)
                if k is None:
                    continue
                e = max(tick, round(float(c["o"].iloc[k]) + tick, 2))
            row = {"day0": r.day0, "half": r.half, "pattern": r.pattern, "symbol": r.symbol, "side": side, "entry": name,
                   "buy at": c["t"].iloc[k - 1 if signs is None else k], "buy price": e}
            for s in STOPS:
                sell, at = walk(c, e, tick, V12 | {"S": s}, k)
                rs, p = net_pct(side, lot, e, sell)
                end = (len(c) - 1 if at is None else at) + 1
                nm = stop_name(s)
                row[f"{nm} · net %"], row[f"{nm} · net Rs"] = p, rs
                row[f"{nm} · exit"] = "15:19" if at is None else ("below the buy" if sell < e else "trail")
                row[f"{nm} · max up held %"] = (h[k:end].max() / e - 1) * 100
                row[f"{nm} · max dip held %"] = (lo[k:end].min() / e - 1) * 100
            rows.append(row)
    return pd.DataFrame(rows)


def table(d: pd.DataFrame, n_pattern: dict) -> pd.DataFrame:
    out = []
    for name in ENTRIES:
        for pat, lab in ((True, "pattern days"), (False, "other days")):
            g = d[(d["entry"] == name) & (d["pattern"] == pat)]
            b = g[f"{stop_name(20)} · net %"]
            for s in STOPS:
                nm = stop_name(s)
                x = g[f"{nm} · net %"]
                diff = x - b
                o, n = g["half"] == "train", g["half"] == "test"
                row = {"days": lab, "entry": name, "stop": nm, "trades": len(g), "fail %": (x < 0).mean() * 100,
                       "mean net %": x.mean(), "median net %": x.median(), "total Rs": g[f"{nm} · net Rs"].sum(),
                       "exits below the buy %": (g[f"{nm} · exit"] == "below the buy").mean() * 100,
                       "median max up held %": g[f"{nm} · max up held %"].median(),
                       "median max dip held %": g[f"{nm} · max dip held %"].median(),
                       "older half mean net %": x[o].mean(), "newer half mean net %": x[n].mean(),
                       "gain vs −20 % stop, same entry %": diff.mean(),
                       "older half gain %": diff[o].mean(), "newer half gain %": diff[n].mean(),
                       "gain t (date-clustered)": clustered_t(diff.to_numpy(), g["day0"].to_numpy()) if s != 20 else None}
                if pat:
                    for h, lab2 in (("train", "older"), ("test", "newer")):
                        row[f"{lab2} half per pattern trade %"] = x[g["half"] == h].sum() / n_pattern[h]
                row["passes"] = "yes" if (s != 20 and pat and row["older half gain %"] > 0 and row["newer half gain %"] > 0
                                          and (row["gain t (date-clustered)"] or 0) >= 2) else "no"
                out.append(row)
    return pd.DataFrame(out)


def write(path, d: pd.DataFrame, t: pd.DataFrame) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    p = t[t["days"] == "pattern days"]
    base = p[(p["entry"] == "09:16 buy (live rule)") & (p["stop"] == stop_name(20))].iloc[0]
    lines = [("S1 v12 fade · Nifty up yesterday + gap down days: does a wider stop help?", FB),
             (f"{int(base['trades'])} pattern trades. Live rule (09:16 buy, −20 % stop): fail {base['fail %']:.0f} %, mean {base['mean net %']:+.2f} %, "
              f"median {base['median net %']:+.2f} %, total ₹{base['total Rs']:,.0f}. Stops −25 / −30 / −40 % and none, all else v12, real charges; "
              "the 09:16 buy and four indicator entries from the last studies (they buy at the first traded candle after the sign).", F),
             ("A wider stop counts only if it beats the −20 % stop with the same entry in BOTH halves and the per-trade gain has a date-clustered "
              f"t ≥ 2 (20 pairs tested). Passing: {int((p['passes'] == 'yes').sum())} of 20.", F), ("", F)]
    for name in ENTRIES:
        lines.append((name, FB))
        for _, r in p[p["entry"] == name].iterrows():
            g = "" if r["stop"] == stop_name(20) else (f"; vs −20 %: {r['gain vs −20 % stop, same entry %']:+.2f} % a trade (older {r['older half gain %']:+.2f}, "
                                                     f"newer {r['newer half gain %']:+.2f}, t {r['gain t (date-clustered)']:.2f})")
            lines.append((f"   {r['stop']}: {int(r['trades'])} trades, fail {r['fail %']:.0f} %, mean {r['mean net %']:+.2f} %, median {r['median net %']:+.1f} %, "
                          f"₹{r['total Rs']:,.0f}, exits below the buy {r['exits below the buy %']:.0f} %, median max dip held {r['median max dip held %']:.0f} %"
                          f"{g}{'  → PASSES' if r['passes'] == 'yes' else ''}", F))
    lines += [("", F), ("Research only: nothing live changes. Sheets: Results (pattern and other days) · Trades (each pattern trade, each entry, every stop).", F)]
    for i, (txt, font) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=txt)
        c.font = font
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 170
    sheet(wb, "Results", t, "Each entry × stop. Pattern days first; other days = the same entry and stop on every other trade (control). "
          "Green = passes (beats −20 % in both halves, t ≥ 2).")
    w = wb["Results"]
    for i, v in enumerate(t["passes"], 3):
        if v == "yes":
            for j in range(1, len(t.columns) + 1):
                w.cell(row=i, column=j).fill = GOOD
    pt = d[d["pattern"]].drop(columns=["pattern"]).sort_values(["entry", "day0", "symbol"])
    pt["half"] = pt["half"].map({"train": "older", "test": "newer"})
    sheet(wb, "Trades", pt, "Every pattern trade for each entry: the buy and, per stop, net %, net ₹, how it exited, max up and max dip while held.")
    wb.save(path)


def main() -> None:
    t = pd.read_feather(RES / "S1_fade_market_direction_trades.feather").sort_values("day0").reset_index(drop=True)
    f = market(t)
    f["pattern"] = (f["nifty prev day %"] > 0) & (f["nifty gap %"] < 0)
    d = run(f)
    n_pattern = f[f["pattern"]]["half"].value_counts().to_dict()
    tab = table(d, n_pattern)
    write(RES / "S1_fade_pattern_stop.xlsx", d, tab)
    pd.set_option("display.width", 300)
    cols = ["days", "entry", "stop", "trades", "fail %", "mean net %", "median net %", "total Rs", "exits below the buy %",
            "older half gain %", "newer half gain %", "gain t (date-clustered)", "passes"]
    print(tab[cols].round(2).to_string())


if __name__ == "__main__":
    main()
