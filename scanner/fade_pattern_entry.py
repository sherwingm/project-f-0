"""S1 v12 fade · on "Nifty up yesterday + gap down" days, enter when the option's own indicators turn good, any time (numbers only)

    python -m scanner.fade_pattern_entry

On those days the fade is often right but early: the −20 % stop is hit before the move. Test: instead of buying at 09:16,
wait on the option's 1-minute candles for a good sign (RSI 14, close above EMA 50 / 100 / 200, Supertrend 10 × 3), any
minute from 09:17 to 15:00; buy at the next candle's open + 1 tick; v12 exit (−20 % stop by touch, 2 % trail once +10 %,
else 15:19), real charges. Every single sign and every combination of 2 and 3 signs. The same rule on all other days is
shown as a control: a rule that only helps on the pattern days is more believable than one that helps everywhere.
With ~70 trades and ~60 rules, the best rule partly wins by luck: a rule counts only if it beats the 09:16 buy on the same
trades in BOTH halves. Writes data/results/S1_fade_pattern_entry.xlsx.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment

from .fade_indicators import RES, V12, minute_book, net_pct, rsi, supertrend
from .fade_indicators_xlsx import F, FB, sheet
from .fade_market_pattern import market
from .fade_stop_trail import SPLIT, walk

FIRST, LAST = "09:17", "15:00"


def signs(c: pd.DataFrame) -> dict[str, np.ndarray]:
    cl = c["c"]
    r = rsi(cl)
    st = supertrend(c["h"], c["l"], cl)
    s = {"RSI > 50": r > 50, "RSI back above 30 (after < 30)": (r < 30).cummax() & (r > 30)}
    for n in (50, 100, 200):
        s[f"above EMA {n}"] = cl > cl.ewm(span=n, adjust=False).mean()
    s["Supertrend up"] = st > 0
    s["Supertrend just turned up"] = (st > 0) & (st.shift(1) < 0)
    return {k: v.fillna(False).to_numpy(bool) for k, v in s.items()}


def rules(names: list[str]) -> list[tuple[str, ...]]:
    out = []
    for k in (1, 2, 3):
        for combo in combinations(names, k):
            if sum(x.startswith("RSI") for x in combo) > 1 or sum(x.startswith("Supertrend") for x in combo) > 1:
                continue                                                # same family twice says nothing new
            out.append(combo)
    return out


def run(f: pd.DataFrame, book: dict) -> tuple[pd.DataFrame, list[tuple[str, ...]]]:
    names, rl, rows = None, None, []
    for r in f.itertuples():
        c = book.get((r.symbol, r.day0, r.side, float(r.strike)))
        if c is None:
            continue
        c = c[c["t"] <= "15:19"].reset_index(drop=True)
        tick, lot, side = (0.05 if r.day0 < SPLIT else 0.01), int(r.lot), r.side
        e0 = float(f.at[r.Index, "entry 09:16+tick"])
        s0, _ = walk(c, e0, tick, V12, int((c["t"] < "09:17").sum()))
        b_rs, b_pct = net_pct(side, lot, e0, s0)
        row = {"day0": r.day0, "symbol": r.symbol, "side": side, "half": r.half, "pattern": r.pattern,
               "09:16 net %": b_pct, "09:16 net Rs": b_rs}
        sg = signs(c)
        if names is None:
            names = list(sg)
            rl = rules(names)
        tt = c["t"].to_numpy()
        ok_time = (tt >= FIRST) & (tt <= LAST)
        ok_time[len(c) - 2:] = False
        for combo in rl:
            m = ok_time.copy()
            for x in combo:
                m &= sg[x]
            idx = np.flatnonzero(m)
            key = " + ".join(combo)
            if not len(idx):
                row[f"{key} · at"], row[f"{key} · net %"], row[f"{key} · net Rs"] = None, None, None
                continue
            j = int(idx[0])
            e = max(tick, round(float(c["o"].iloc[j + 1]) + tick, 2))
            s, _ = walk(c, e, tick, V12, j + 1)
            rs_, p = net_pct(side, lot, e, s)
            row[f"{key} · at"], row[f"{key} · net %"], row[f"{key} · net Rs"] = tt[j + 1], p, rs_
        rows.append(row)
    return pd.DataFrame(rows), rl


def summary(d: pd.DataFrame, rl: list[tuple[str, ...]]) -> pd.DataFrame:
    pt, ot = d[d["pattern"]], d[~d["pattern"]]
    out = [{"entry rule": "09:16 open + 1 tick (live rule)", "signs": 0, "trades taken": len(pt), "no sign by 15:00": 0,
            "median entry time": "09:16", "fail %": (pt["09:16 net %"] < 0).mean() * 100, "mean net %": pt["09:16 net %"].mean(),
            "median net %": pt["09:16 net %"].median(), "total Rs": pt["09:16 net Rs"].sum(),
            "same trades at 09:16: mean net %": pt["09:16 net %"].mean(), "same trades at 09:16: total Rs": pt["09:16 net Rs"].sum(),
            "older half mean net %": pt.loc[pt.half == "train", "09:16 net %"].mean(), "older half at 09:16 %": pt.loc[pt.half == "train", "09:16 net %"].mean(),
            "newer half mean net %": pt.loc[pt.half == "test", "09:16 net %"].mean(), "newer half at 09:16 %": pt.loc[pt.half == "test", "09:16 net %"].mean(),
            "other days: mean net %": ot["09:16 net %"].mean(), "other days at 09:16 %": ot["09:16 net %"].mean()}]
    for combo in rl:
        key = " + ".join(combo)
        k = pt[pt[f"{key} · net %"].notna()]
        o = ot[ot[f"{key} · net %"].notna()]
        tr, te = k[k.half == "train"], k[k.half == "test"]
        times = pd.to_datetime(k[f"{key} · at"], format="%H:%M")
        out.append({"entry rule": key, "signs": len(combo), "trades taken": len(k), "no sign by 15:00": len(pt) - len(k),
                    "median entry time": times.median().strftime("%H:%M") if len(k) else None,
                    "fail %": (k[f"{key} · net %"] < 0).mean() * 100 if len(k) else None,
                    "mean net %": k[f"{key} · net %"].mean(), "median net %": k[f"{key} · net %"].median(),
                    "total Rs": k[f"{key} · net Rs"].sum(),
                    "same trades at 09:16: mean net %": k["09:16 net %"].mean(), "same trades at 09:16: total Rs": k["09:16 net Rs"].sum(),
                    "older half mean net %": tr[f"{key} · net %"].mean(), "older half at 09:16 %": tr["09:16 net %"].mean(),
                    "newer half mean net %": te[f"{key} · net %"].mean(), "newer half at 09:16 %": te["09:16 net %"].mean(),
                    "other days: mean net %": o[f"{key} · net %"].mean(), "other days at 09:16 %": o["09:16 net %"].mean()})
    s = pd.DataFrame(out)
    s["beats 09:16 in both halves"] = np.where((s["older half mean net %"] > s["older half at 09:16 %"])
                                              & (s["newer half mean net %"] > s["newer half at 09:16 %"]) & (s["trades taken"] >= 20)
                                              & (s["signs"] > 0), "yes", "no")
    s["helps only on pattern days"] = np.where((s["beats 09:16 in both halves"] == "yes")
                                              & (s["other days: mean net %"] <= s["other days at 09:16 %"]), "yes", "no")
    return pd.concat([s.iloc[:1], s.iloc[1:].sort_values("mean net %", ascending=False)])


def write(path, d: pd.DataFrame, s: pd.DataFrame) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    base = s.iloc[0]
    passed = s[s["beats 09:16 in both halves"] == "yes"]
    lines = [("S1 v12 fade · Nifty up yesterday + gap down days: enter when the option's indicators turn good (09:17 – 15:00)", FB),
             (f"{int(base['trades taken'])} pattern trades. 09:16 buy: fail {base['fail %']:.0f} %, mean {base['mean net %']:+.2f} %, median "
              f"{base['median net %']:+.2f} %, total ₹{base['total Rs']:,.0f}. Indicators on the option's own 1-minute candles: RSI 14, EMA 50/100/200, "
              "Supertrend 10 × 3. Buy at the next candle's open + 1 tick, v12 exit, real charges.", F),
             (f"{len(s) - 1} rules tested (each sign alone, every pair and every three). With this many rules on this few trades, the top of the "
              "list is partly luck: a rule counts only if it beats the 09:16 buy on the same trades in BOTH halves, with at least 20 trades.", F),
             ("", F), (f"Rules that pass: {len(passed)} of {len(s) - 1}", FB)]
    for _, r in passed.head(15).iterrows():
        lines.append((f"{r['entry rule']}: {int(r['trades taken'])} trades (no sign on {int(r['no sign by 15:00'])}), median entry {r['median entry time']}, "
                      f"fail {r['fail %']:.0f} %, mean {r['mean net %']:+.2f} % vs {r['same trades at 09:16: mean net %']:+.2f} % at 09:16 on the same trades; "
                      f"older half {r['older half mean net %']:+.2f} % vs {r['older half at 09:16 %']:+.2f} %, newer {r['newer half mean net %']:+.2f} % vs "
                      f"{r['newer half at 09:16 %']:+.2f} %; other days {r['other days: mean net %']:+.2f} % vs {r['other days at 09:16 %']:+.2f} % "
                      f"({'helps only on the pattern days' if r['helps only on pattern days'] == 'yes' else 'helps on other days too'})", F))
    lines += [("", F), ("Note: EMA 100 / 200 on 1-minute candles need 100 – 200 minutes of history, so before ~11:00 – 12:30 they lean on the "
                        "first prices of the day. Research only: nothing live changes.", F),
              ("Sheets: Rules (all, best mean first; 09:16 row on top) · Trades (each trade's 09:16 result and every rule's entry time and net).", F)]
    for i, (txt, font) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=txt)
        c.font = font
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 170
    sheet(wb, "Rules", s, "Pattern days only (other-days columns = the same rule on every other trade, as a control). Green = beats "
          "09:16 in both halves.", None)
    ws2 = wb["Rules"]
    from .fade_indicators_xlsx import GOOD
    col = list(s.columns).index("beats 09:16 in both halves")
    for i, v in enumerate(s["beats 09:16 in both halves"], 3):
        if v == "yes":
            for j in range(1, len(s.columns) + 1):
                ws2.cell(row=i, column=j).fill = GOOD
    _ = col
    pt = d[d["pattern"]].drop(columns=["pattern"])
    keep = ["day0", "symbol", "side", "half", "09:16 net %", "09:16 net Rs"] + [c for c in pt.columns if c.endswith(("· at", "· net %"))]
    sheet(wb, "Trades", pt[keep], "Each pattern trade: the 09:16 result and, for every rule, the entry time and net %.")
    wb.save(path)


def main() -> None:
    t = pd.read_feather(RES / "S1_fade_market_direction_trades.feather").sort_values("day0").reset_index(drop=True)
    f = market(t)
    f["pattern"] = (f["nifty prev day %"] > 0) & (f["nifty gap %"] < 0)
    d, rl = run(f, minute_book())
    s = summary(d, rl)
    write(RES / "S1_fade_pattern_entry.xlsx", d, s)
    pd.set_option("display.width", 300)
    cols = ["entry rule", "trades taken", "median entry time", "fail %", "mean net %", "median net %", "total Rs",
            "same trades at 09:16: mean net %", "older half mean net %", "older half at 09:16 %", "newer half mean net %",
            "newer half at 09:16 %", "other days: mean net %", "other days at 09:16 %", "beats 09:16 in both halves", "helps only on pattern days"]
    print(s[cols].head(30).round(2).to_string())
    print("passing:", (s["beats 09:16 in both halves"] == "yes").sum(), "of", len(s) - 1)


if __name__ == "__main__":
    main()
