import json, sys
import pandas as pd
from scanner.fade_s20_minutes import one, RES

S = sys.argv[1]  # folder holding trades.json (/api/paper/trades)
c = pd.read_csv(RES / "S1_v10_bandv10_contracts.csv")
mins = pd.read_csv(RES / "S1_v10_bandv10_minutes.csv")
mins["t"] = mins["ts"].str[11:16]
by = {k: g.sort_values("ts").reset_index(drop=True) for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
rows = []
for r in c.itertuples():
    m = by.get((r.symbol, r.day0, r.side, float(r.strike)))
    if m is None or m.empty:
        continue
    d = m[(m["t"] >= "09:15") & (m["t"] <= "15:19")]
    if d.empty:
        continue
    v = one(m, r, "09:16")
    e = float(r.entry_price)
    hi, lo = d.loc[d["h"].idxmax()], d.loc[d["l"].idxmin()]
    prem = e * int(r.lot)
    rows.append({"Stock": r.symbol, "Results day": r.day0, "Type": "Put" if r.side == "PE" else "Call", "Strike": r.strike,
                 "Expiry": r.expiry, "Lot": int(r.lot), "Entry Rs": e, "Premium Rs": round(prem),
                 "Max peak Rs": float(hi["h"]), "Max peak %": round((hi["h"] / e - 1) * 100, 1), "Peak time": hi["t"],
                 "Max dip Rs": float(lo["l"]), "Max dip %": round((lo["l"] / e - 1) * 100, 1), "Dip time": lo["t"],
                 "Came first": "peak" if hi["t"] < lo["t"] else "dip" if lo["t"] < hi["t"] else "same minute",
                 "15:19 close %": round((float(d["c"].iloc[-1]) / e - 1) * 100, 1),
                 "v10 net Rs (15:20)": round(float(r.e1_net)), "v10 net %": round(float(r.e1_net) / prem * 100, 1),
                 "v11 net Rs (-20% from 09:16)": round(v["s20_net"]), "v11 net %": round(v["s20_net"] / prem * 100, 1),
                 "v11 stopped": "yes" if v["fired"] else "no", "Stop time": v.get("stop_time") or ""})
bt = pd.DataFrame(rows)

lt = json.load(open(f"{S}/trades.json", encoding="utf-8"))
lt = lt if isinstance(lt, list) else next(v for v in lt.values() if isinstance(v, list))
live = []
for x in lt:
    if (x.get("rule") or {}).get("strategy") != "fade":
        continue
    e = x["entry"]["price"]; pk = x.get("held_peak") or {}; tr = x.get("held_trough") or {}
    live.append({"Stock": x["symbol"], "Opened": x["opened_at"][:16].replace("T", " "), "Closed": x["closed_at"][:16].replace("T", " "),
                 "Type": "Put" if x["instrument"] == "PE" else "Call", "Strike": x["strike"], "Lot": x["lot_size"], "Entry Rs": e,
                 "Max peak Rs": pk.get("price"), "Max peak %": round((pk["price"] / e - 1) * 100, 1) if pk.get("price") else None,
                 "Peak at": (pk.get("at") or "")[:16].replace("T", " "),
                 "Max dip Rs": tr.get("price"), "Max dip %": round((tr["price"] / e - 1) * 100, 1) if tr.get("price") else None,
                 "Dip at": (tr.get("at") or "")[:16].replace("T", " "),
                 "Exit Rs": x["exit"]["price"], "Exit %": round((x["exit"]["price"] / e - 1) * 100, 1),
                 "Net Rs": round(x["net_pnl"]), "Why sold": x["reason"], "Rule": (x.get("rule") or {}).get("version") or "v10"})
lv = pd.DataFrame(live)

def summ(g, name):
    return {"Group": name, "Trades": len(g), "Median peak %": g["Max peak %"].median(), "Median dip %": g["Max dip %"].median(),
            "Peak >= +20 %": f"{(g['Max peak %'] >= 20).mean()*100:.0f} %", "Peak >= +50 %": f"{(g['Max peak %'] >= 50).mean()*100:.0f} %",
            "Peak >= +100 %": f"{(g['Max peak %'] >= 100).mean()*100:.0f} %", "Dip <= -20 %": f"{(g['Max dip %'] <= -20).mean()*100:.0f} %",
            "Dip <= -50 %": f"{(g['Max dip %'] <= -50).mean()*100:.0f} %", "Peak came first": f"{(g['Came first'] == 'peak').mean()*100:.0f} %",
            "v10 total Rs": g["v10 net Rs (15:20)"].sum(), "v11 total Rs": g["v11 net Rs (-20% from 09:16)"].sum()}
sm = pd.DataFrame([summ(bt, "All"), summ(bt[bt.Type == "Put"], "Puts"), summ(bt[bt.Type == "Call"], "Calls")])

out = RES / "S1_fade_peak_dip.xlsx"
with pd.ExcelWriter(out, engine="xlsxwriter") as w:
    readme = pd.DataFrame({"Fade trades: max peak and max dip": [
        "Backtest sheet: 468 fade trades (v10 entry, Rs 2+), results days Oct 2024 - Sep 2026, from 1-minute prices.",
        "Entry = the option's day-0 open + 1 tick (the backtest's buy).",
        "Max peak = the highest price in any minute 09:15-15:19 that day; max dip = the lowest. Both as % of the entry.",
        "Came first = whether the peak or the dip happened earlier in the day.",
        "v10 net = sold at 15:20. v11 net = -20 % stop from 09:16 (the live rule from 21 Oct), else 15:20. Net of charges.",
        "Live sheet: the 10 real paper fade trades (15-19 Oct, v10), peak and dip from the server's polls while held.",
        "Peak and dip are the best and worst prices seen, not prices the trade could surely have sold at."]})
    readme.to_excel(w, "Read me", index=False)
    sm.to_excel(w, "Summary", index=False)
    bt.sort_values(["Results day", "Stock"]).to_excel(w, "Backtest trades", index=False)
    lv.to_excel(w, "Live trades", index=False)
    wb = w.book
    red, green = wb.add_format({"font_color": "#C00000"}), wb.add_format({"font_color": "#007A33"})
    for name, df in (("Summary", sm), ("Backtest trades", bt), ("Live trades", lv)):
        ws = w.sheets[name]
        ws.freeze_panes(1, 1); ws.autofilter(0, 0, len(df), len(df.columns) - 1)
        for i, col in enumerate(df.columns):
            ws.set_column(i, i, max(10, min(30, len(str(col)) + 2)))
            if "%" in col or "Rs" in col and "net" in col.lower() or col.startswith("Net"):
                ws.conditional_format(1, i, len(df), i, {"type": "cell", "criteria": "<", "value": 0, "format": red})
                ws.conditional_format(1, i, len(df), i, {"type": "cell", "criteria": ">", "value": 0, "format": green})
    w.sheets["Read me"].set_column(0, 0, 110)
print(out); print(sm.to_string(index=False)); print(lv[["Stock","Max peak %","Max dip %","Exit %","Net Rs"]].to_string(index=False))
