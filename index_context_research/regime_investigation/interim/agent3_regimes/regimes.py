"""Agent 3: regime boundaries (NIFTY/VIX history 2018-01-01..2024-09-30 only) and regime labels per trade.
Read-only on inputs. Outputs: boundaries.json, regime_labels.csv, hashes.txt"""
import hashlib, json, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 4))
STORE = os.path.join(os.path.dirname(REPO), "fo-index-data", "data", "index")
H0, H1 = pd.Timestamp("2018-01-01"), pd.Timestamp("2024-09-30")
NIFTY = os.path.join(REPO, "data", "eod2", "nifty 50.csv")
VIXF = os.path.join(STORE, "vix_daily.parquet")
CTX = os.path.join(REPO, "index_context_research", "results", "context_dataset.csv")

nf = pd.read_csv(NIFTY, parse_dates=["Date"]).set_index("Date")["Close"].sort_index()
vx = pd.read_parquet(VIXF); vx = vx.set_index(pd.to_datetime(vx["date"]))["close"].sort_index().dropna()

feat = pd.DataFrame({"close": nf})
for k in (5, 10, 20):
    feat[f"ret{k}"] = nf / nf.shift(k) - 1
feat["sma20"] = nf.rolling(20).mean(); feat["sma50"] = nf.rolling(50).mean()
feat["ma"] = np.where((nf > feat.sma20) & (feat.sma20 > feat.sma50), "bull",
             np.where((nf < feat.sma20) & (feat.sma20 < feat.sma50), "bear", "mixed"))
hist = feat.loc[H0:H1]
b = {"history": [str(H0.date()), str(H1.date())], "n_sessions_nifty": int(len(hist))}
for k in (5, 10, 20):
    b[f"ret{k}_quintile_edges"] = [float(x) for x in hist[f"ret{k}"].quantile([.2, .4, .6, .8])]
vh = vx.loc[H0:H1]
b["vix_p25"], b["vix_p75"] = float(vh.quantile(.25)), float(vh.quantile(.75))
b["n_sessions_vix"] = int(len(vh))
b["vix_direction_threshold_pct"] = 5.0; b["vix_expansion_ratio"] = 1.10
b["gap_threshold_pct"] = 0.3; b["us_threshold_pct"] = 0.3
b["notes"] = "edges are NIFTY/VIX history only; ret = close(prev)/close(prev-k sessions)-1 as fractions"
json.dump(b, open(os.path.join(HERE, "boundaries.json"), "w"), indent=1)

def q5(x, edges):
    return 1 + int(np.searchsorted(edges, x, side="right")) if x == x else np.nan

d = pd.read_csv(CTX); d["day"] = pd.to_datetime(d["day"])
rows = []
nidx, vidx = feat.index, vx.index
for _, r in d.iterrows():
    day = r["day"]
    ip = nidx.searchsorted(day, side="left") - 1          # last NIFTY session strictly before the trade date
    pv = nidx[ip]; f = feat.iloc[ip]
    iv = vidx.searchsorted(day, side="left") - 1
    v_prev = float(vx.iloc[iv]); v_5 = float(vx.iloc[iv - 5])
    o = {"strategy": r["tset"], "date": day.date(), "side": r["side"], "dte": r["dte"], "entry": r["entry"],
         "prev_session": pv.date(), "vix_prev_session": vx.index[iv].date(),
         "ret5": f.ret5, "ret10": f.ret10, "ret20": f.ret20, "ma_struct": f.ma,
         "vix_prev": v_prev, "vix_chg5_pct": (v_prev / v_5 - 1) * 100, "vix_signal": r["vix_signal"],
         "vix_signal_over_prev": r["vix_signal"] / v_prev, "gap_pct": r["gap_pct"], "us_prev_ret": r["us_prev_ret"],
         "net_pct": r["net_pct"], "net_rs": r["net_rs"], "maxup": r["maxup"], "g1f": r["g1f"], "half": r["half"]}
    for k in (5, 10, 20):
        o[f"q{k}"] = q5(f[f"ret{k}"], b[f"ret{k}_quintile_edges"])
    o["dir5"] = o["q20"]
    o["dir3"] = {1: "bearish", 2: "bearish", 3: "sideways", 4: "bullish", 5: "bullish"}.get(o["q20"])
    o["vix_level"] = "low" if v_prev < b["vix_p25"] else ("high" if v_prev > b["vix_p75"] else "normal")
    c = o["vix_chg5_pct"]; o["vix_dir"] = "rising" if c >= 5 else ("falling" if c <= -5 else "flat")
    o["vix_expansion"] = "yes" if o["vix_signal_over_prev"] >= 1.10 else "no"
    g = r["gap_pct"]; o["gap_cls"] = "gap-down" if g <= -0.3 else ("gap-up" if g >= 0.3 else "flat")
    u = r["us_prev_ret"]
    o["us_cls"] = np.nan if u != u else ("down" if u <= -0.3 else ("up" if u >= 0.3 else "flat"))
    o["period"] = "discovery" if day <= pd.Timestamp("2025-09-30") else "second_half"
    o["halfyear"] = f"{day.year}H{1 if day.month <= 6 else 2}"
    rows.append(o)
L = pd.DataFrame(rows)
L["strategy"] = L["strategy"].replace({"G1F": "G1-F", "G1C": "G1-C"})
L.to_csv(os.path.join(HERE, "regime_labels.csv"), index=False)
with open(os.path.join(HERE, "hashes.txt"), "w") as h:
    for p in (NIFTY, VIXF, CTX):
        h.write(f"{hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]}  {os.path.relpath(p, REPO) if p.startswith(REPO) else p}\n")
print(json.dumps(b, indent=1)); print(L.groupby("strategy").size())
