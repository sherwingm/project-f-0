"""G1 follow-through vs FII/DII positions, news tone and heavyweights (g1_research/EXTERNAL_PREREG.md). History only."""
import glob
import io
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import g1_formation as GF  # noqa: E402

EXT = os.path.join(ROOT, "data", "external")
D_END, V_END = pd.Timestamp("2023-09-30"), pd.Timestamp("2024-09-30")
W = {"hdfcbank": 13, "icicibank": 8, "reliance": 9, "infy": 5, "tcs": 4, "itc": 4, "lt": 4, "bhartiartl": 4, "axisbank": 3, "sbin": 3, "kotakbank": 3}
BANKS = {"hdfcbank", "icicibank", "axisbank", "sbin", "kotakbank"}


def participant_frame():
    rows = {}
    for f in sorted(glob.glob(os.path.join(EXT, "participant_oi", "*.csv"))):
        d = os.path.basename(f)[:-4]
        try:
            df = pd.read_csv(f, skiprows=1)
            df.columns = [c.strip() for c in df.columns]
            df["Client Type"] = df["Client Type"].str.strip()
            r = {}
            for who in ("FII", "DII", "Client", "Pro"):
                x = df[df["Client Type"] == who].iloc[0]
                r[who] = {"fl": x["Future Index Long"], "fs": x["Future Index Short"], "cl": x["Option Index Call Long"],
                          "pl": x["Option Index Put Long"], "cs": x["Option Index Call Short"], "ps": x["Option Index Put Short"]}
            rows[pd.Timestamp(d)] = r
        except Exception:  # noqa: BLE001
            continue
    idx = sorted(rows)
    out = pd.DataFrame(index=idx)
    out["fii_fut_net"] = [rows[d]["FII"]["fl"] - rows[d]["FII"]["fs"] for d in idx]
    out["fii_fut_ratio"] = [rows[d]["FII"]["fl"] / (rows[d]["FII"]["fl"] + rows[d]["FII"]["fs"]) for d in idx]
    out["fii_put_net"] = [rows[d]["FII"]["pl"] - rows[d]["FII"]["ps"] for d in idx]
    out["fii_call_net"] = [rows[d]["FII"]["cl"] - rows[d]["FII"]["cs"] for d in idx]
    out["fii_opt_bear"] = out["fii_put_net"] - out["fii_call_net"]
    out["dii_fut_net"] = [rows[d]["DII"]["fl"] - rows[d]["DII"]["fs"] for d in idx]
    out["client_fut_net"] = [rows[d]["Client"]["fl"] - rows[d]["Client"]["fs"] for d in idx]
    out["pro_fut_net"] = [rows[d]["Pro"]["fl"] - rows[d]["Pro"]["fs"] for d in idx]
    cr = [rows[d]["Client"]["fl"] / (rows[d]["Client"]["fl"] + rows[d]["Client"]["fs"]) for d in idx]
    out["fii_vs_client"] = out["fii_fut_ratio"].values - np.array(cr)
    out["fii_fut_chg1"] = out["fii_fut_net"].diff(1)
    out["fii_fut_chg5"] = out["fii_fut_net"].diff(5)
    out["fii_opt_bear_chg1"] = out["fii_opt_bear"].diff(1)
    out["dii_fut_chg1"] = out["dii_fut_net"].diff(1)
    return out


def gdelt_series(mode):
    s = {}
    for f in sorted(glob.glob(os.path.join(EXT, "gdelt", f"{mode}_*.json"))):
        try:
            j = json.load(open(f, encoding="utf-8"))
            for ser in j.get("timeline", []):
                for p in ser["data"]:
                    s[pd.Timestamp(p["date"][:8])] = s.get(pd.Timestamp(p["date"][:8]), []) + [p["value"]]
        except Exception:  # noqa: BLE001
            continue
    return pd.Series({k: float(np.mean(v)) for k, v in s.items()}).sort_index()


def heavy():
    px = {}
    for n in W:
        d = pd.read_csv(os.path.join(REPO, "data", "eod2", f"{n}.csv"), parse_dates=["Date"]).set_index("Date")
        px[n] = d[["Open", "Close"]]
    return px


def main():
    T = pd.read_csv(os.path.join(ROOT, "results", "g1_underlying_signals.csv"), parse_dates=["day"])
    P = participant_frame()
    print("participant sessions:", len(P), P.index.min().date() if len(P) else None, P.index.max().date() if len(P) else None)
    tone, cov = gdelt_series("timelinetone"), gdelt_series("timelinevolraw")
    print("gdelt days: tone", len(tone), "coverage", len(cov))
    px = heavy()
    rows = []
    for d in T["day"]:
        r = {}
        prior = P.index[P.index < d]
        if len(prior):
            r.update(P.loc[prior[-1]].to_dict())
        if len(tone):
            pt = tone[tone.index < d]
            if len(pt) >= 25:
                r["tone_prev"], r["tone_5d"] = pt.iloc[-1], pt.iloc[-5:].mean()
                r["tone_chg"] = pt.iloc[-1] - pt.iloc[-21:-1].mean()
        if len(cov):
            pc = cov[cov.index < d]
            if len(pc) >= 25:
                r["cov_prev"], r["cov_x"] = pc.iloc[-1], pc.iloc[-1] / pc.iloc[-21:-1].mean()
        g, p1, p5, dn, od, bk, rest, wb, wr = 0.0, 0.0, 0.0, 0, 0, 0.0, 0.0, 0, 0
        ok = True
        for n, w in W.items():
            h = px[n]
            before = h[h.index < d]
            if d not in h.index or len(before) < 6:
                ok = False
                break
            gp = (h.loc[d, "Open"] / before["Close"].iloc[-1] - 1) * 100
            r1 = (before["Close"].iloc[-1] / before["Close"].iloc[-2] - 1) * 100
            r5 = (before["Close"].iloc[-1] / before["Close"].iloc[-6] - 1) * 100
            if abs(gp) > 15 or abs(r1) > 15:
                ok = False
                break
            g += w * gp
            p1 += w * r1
            p5 += w * r5
            dn += r1 < 0
            od += gp < 0
            if n in BANKS:
                bk += w * r1
                wb += w
            else:
                rest += w * r1
                wr += w
            if n == "hdfcbank":
                r["hdfc_gap"] = gp
            if n == "reliance":
                r["reliance_gap"] = gp
        if ok:
            sw = sum(W.values())
            r.update(hw_gap=g / sw, hw_prev1=p1 / sw, hw_prev5=p5 / sw, hw_breadth=dn, hw_gap_breadth=od,
                     bank_vs_rest_prev1=bk / wb - rest / wr)
        rows.append(r)
    F = pd.DataFrame(rows)
    T = pd.concat([T[["day", "F", "N", "reach", "gap"]], F], axis=1)
    T["hw_gap_vs_nifty"] = T["hw_gap"] - T["gap"]
    T = T.drop(columns=["gap"])
    feats = [c for c in T.columns if c not in ("day", "F", "N", "reach")]
    T.to_csv(os.path.join(ROOT, "results", "g1_external_features.csv"), index=False)
    print("feature coverage (non-missing of", len(T), "):")
    print(T[feats].notna().sum().to_string())
    D, V, C = T[T["day"] <= D_END], T[(T["day"] > D_END) & (T["day"] <= V_END)], T[T["day"] > V_END]
    out = []
    for f in feats:
        x = D[f].dropna()
        if len(x) < 60 or x.nunique() < 4:
            continue
        p33, p67 = np.percentile(x, [33.3, 66.7])
        for name, cond in ((f"high >= {p67:.4g}", lambda s_, t_=p67: s_ >= t_), (f"low <= {p33:.4g}", lambda s_, t_=p33: s_ <= t_)):
            def grp(df):
                df = df[df[f].notna()]
                g_ = df[cond(df[f])]
                return g_, df.drop(g_.index)
            g, o = grp(D)
            if len(g) < 5 or len(o) < 5:
                continue
            p = stats.fisher_exact([[g.reach.sum(), len(g) - g.reach.sum()], [o.reach.sum(), len(o) - o.reach.sum()]])[1]
            row = {"feature": f, "rule": name, "d_n": len(g), "d_reach": g.reach.mean() * 100, "d_out": o.reach.mean() * 100, "d_p": p}
            for tag, df in (("v", V), ("c", C)):
                gg, oo = grp(df)
                row[f"{tag}_n"] = len(gg)
                row[f"{tag}_reach"] = gg.reach.mean() * 100 if len(gg) else np.nan
                row[f"{tag}_out"] = oo.reach.mean() * 100 if len(oo) else np.nan
                row[f"{tag}_tab"] = [[gg.reach.sum(), len(gg) - gg.reach.sum()], [oo.reach.sum(), len(oo) - oo.reach.sum()]]
            out.append(row)
    R = pd.DataFrame(out)
    R["d_q"] = GF.bh(R["d_p"].values)
    R["d_eff"] = R["d_reach"] - R["d_out"]
    R["cand"] = (R["d_q"] <= 0.10) & (R["d_n"] >= 25)
    pd.set_option("display.width", 250)
    print("\nperiods: discovery", len(D), "validation", len(V), "confirmation", len(C))
    print("rules in family:", len(R), "| candidates:", int(R["cand"].sum()))
    print(R.sort_values("d_p").head(12)[["feature", "rule", "d_n", "d_reach", "d_out", "d_p", "d_q"]].round(3).to_string(index=False))
    R.drop(columns=["v_tab", "c_tab"]).to_csv(os.path.join(ROOT, "results", "g1_external_all_rules.csv"), index=False)
    Cn = R[R["cand"]].copy()
    if not len(Cn):
        print("\nno candidate at q <= 0.10")
        print("\nFOR INFORMATION ONLY (not a test): the 8 smallest discovery p, then validation and confirmation")
        print(R.sort_values("d_p").head(8)[["feature", "rule", "d_n", "d_reach", "d_out", "v_n", "v_reach", "v_out", "c_n", "c_reach", "c_out"]].round(1).to_string(index=False))
        return
    sg = np.sign(Cn["d_eff"])
    for tag in ("v", "c"):
        Cn[f"{tag}_eff"] = Cn[f"{tag}_reach"] - Cn[f"{tag}_out"]
        Cn[f"{tag}_p1"] = [stats.fisher_exact(tb, alternative="greater" if e > 0 else "less")[1] for tb, e in zip(Cn[f"{tag}_tab"], Cn["d_eff"])]
    Cn["pass_v"] = (Cn["v_n"] >= 20) & (np.sign(Cn["v_eff"]) == sg) & (Cn["v_p1"] < 0.05) & (Cn["v_eff"].abs() >= 0.5 * Cn["d_eff"].abs())
    Cn["pass_c"] = Cn["pass_v"] & (Cn["c_n"] >= 20) & (np.sign(Cn["c_eff"]) == sg) & (Cn["c_p1"] < 0.05)
    print(Cn[["feature", "rule", "d_n", "d_reach", "d_out", "d_q", "v_n", "v_reach", "v_out", "v_p1", "pass_v", "c_n", "c_reach", "c_out", "c_p1", "pass_c"]].round(3).to_string(index=False))
    Cn.drop(columns=["v_tab", "c_tab"]).to_csv(os.path.join(ROOT, "results", "g1_external_candidates.csv"), index=False)


if __name__ == "__main__":
    main()
