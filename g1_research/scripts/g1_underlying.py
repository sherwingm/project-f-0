"""G1 follow-through on NIFTY spot, five years (g1_research/UNDERLYING_PREREG.md). History only; record-only research."""
import os
import sys
import warnings
from datetime import time

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from index_data import load as L  # noqa: E402
from scanner import s3_regime as G  # noqa: E402
from scanner.s3_b2 import signal  # noqa: E402
import g1_formation as GF  # noqa: E402

D_END, V_END = pd.Timestamp("2023-09-30"), pd.Timestamp("2024-09-30")
BINARY = {"pd_inside", "pd_low_break"}


def main():
    s = L.spot_1m(pd.Timestamp("2021-10-01").date(), pd.Timestamp("2026-12-31").date(), "NIFTY50")
    s["d"] = s["timestamp"].dt.date
    s["t"] = s["timestamp"].dt.time
    s = s[(s["t"] >= time(9, 15)) & (s["t"] <= time(15, 29))]
    SPOT = {d: g.reset_index(drop=True) for d, g in s.groupby("d") if len(g) >= 300}
    days = sorted(SPOT)
    nxt = {days[i]: days[i + 1] for i in range(len(days) - 1)}
    daily = G.daily()
    vx = L.vix_1m(pd.Timestamp("2021-10-01").date(), pd.Timestamp("2026-12-31").date())
    vx["d"] = vx["timestamp"].dt.date
    vdaily = vx.groupby("d")["close"].last()
    rng5 = (daily["high"] - daily["low"])
    atr5 = rng5.rolling(5).mean().shift(1)
    atr20 = rng5.rolling(20).mean().shift(1)

    GF.L.spot_1m = lambda a, b, idx="NIFTY50": SPOT[a]            # day_features reads one day; serve it from memory
    # ---- baseline: same entry minute on every session
    base_rows = {}
    for d in days:
        if d not in nxt or d not in atr5.index or np.isnan(atr5[d]):
            continue
        g, g2 = SPOT[d], SPOT[nxt[d]]
        lowmin = np.minimum.accumulate(g["low"].values[::-1])[::-1]
        m2 = g2["low"].min()
        close2 = g2["close"].iloc[-1]
        for i, tt in enumerate(g["t"]):
            e = g["close"].iloc[i]
            base_rows.setdefault(tt, []).append(((e - min(lowmin[i], m2)) / atr5[d], (e - close2) / atr5[d]))
    base = {tt: np.mean(v, axis=0) for tt, v in base_rows.items()}

    rows = []
    for d in days:
        if d not in nxt or d not in atr5.index or np.isnan(atr5[d]) or d <= pd.Timestamp("2021-11-20").date():
            continue
        sg = signal(SPOT[d], 15, None)
        if sg is None or sg[0] != "PE":
            continue
        ent_t = (sg[1] + pd.Timedelta(minutes=1)).time()
        g = SPOT[d]
        er = g[g["t"] == ent_t]
        if er.empty:
            continue
        i = er.index[0]
        e = float(er["close"].iloc[0])
        g2 = SPOT[nxt[d]]
        low = min(g["low"].iloc[i:].min(), g2["low"].min())
        A5 = atr5[d]
        o = {"day": pd.Timestamp(d), "entry_t": ent_t, "F": (e - low) / A5, "N": (e - g2["close"].iloc[-1]) / A5,
             "F_base": base[ent_t][0], "N_base": base[ent_t][1]}
        try:
            f = GF.day_features(d, f"{sg[1].hour:02d}:{sg[1].minute:02d}", daily)
        except Exception:  # noqa: BLE001
            continue
        hi, lo = float(g[(g["t"] < time(9, 30))]["high"].max()), float(g[(g["t"] < time(9, 30))]["low"].min())
        dd = daily[daily.index < d]
        p = dd.iloc[-1]
        f["depth"] = (lo - float(sg_close(g, sg[1]))) / lo * 100
        f["time"] = (sg[1].hour - 9) * 60 + sg[1].minute - 30
        f["width"] = (hi - lo) / lo * 100
        f["gap"] = (float(g["open"].iloc[0]) / p["close"] - 1) * 100
        v = vx[(vx["d"] == d) & (vx["timestamp"].dt.time <= sg[1].time())]["close"]
        vo = vx[(vx["d"] == d)]["close"]
        f["vix"] = float(v.iloc[-1]) if len(v) else np.nan
        f["vixchg"] = float(v.iloc[-1] - vo.iloc[0]) if len(v) and len(vo) else np.nan
        f["prev1"] = (p["close"] / dd.iloc[-2]["close"] - 1) * 100
        f["prev5"] = (p["close"] / dd.iloc[-6]["close"] - 1) * 100
        f["ema20"] = (p["close"] / p["ema20"] - 1) * 100
        f["adx"] = p["adx14"]
        vh = vdaily[vdaily.index < d].tail(250)
        f["vix_pct"] = float((vh < f["vix"]).mean() * 100) if len(vh) >= 60 and not np.isnan(f["vix"]) else np.nan
        f["atr_x"] = atr5[d] / atr20[d] if atr20[d] else np.nan
        rows.append({**o, **f})
    T = pd.DataFrame(rows).sort_values("day").reset_index(drop=True)
    T["reach"] = (T["F"] >= 1.0).astype(int)
    T.to_csv(os.path.join(ROOT, "results", "g1_underlying_signals.csv"), index=False)
    pd.set_option("display.width", 250)
    print("signals", len(T), T["day"].min().date(), T["day"].max().date())
    print("\n=== Q0 follow-through vs the same-minute baseline (units: ATR5) ===")
    T["yr"] = T["day"].dt.year
    q0 = T.groupby("yr").agg(n=("F", "size"), F=("F", "mean"), F_base=("F_base", "mean"), N=("N", "mean"), N_base=("N_base", "mean"))
    q0.loc["all"] = [len(T), T["F"].mean(), T["F_base"].mean(), T["N"].mean(), T["N_base"].mean()]
    print(q0.round(3).to_string())
    t = stats.ttest_1samp(T["N"] - T["N_base"], 0)
    print(f"N minus baseline: mean {np.mean(T['N'] - T['N_base']):+.3f} ATR, t = {t.statistic:.2f}, p = {t.pvalue:.3f}")
    t2 = stats.ttest_1samp(T["F"] - T["F_base"], 0)
    print(f"F minus baseline: mean {np.mean(T['F'] - T['F_base']):+.3f} ATR, t = {t2.statistic:.2f}, p = {t2.pvalue:.3f}")
    print("share F>=0.5/1/2:", [round((T['F'] >= x).mean() * 100) for x in (0.5, 1, 2)], "| mean/median F", round(T['F'].mean(), 2), round(T['F'].median(), 2))

    feats = [c for c in T.columns if c not in ("day", "entry_t", "F", "N", "F_base", "N_base", "reach", "yr")]
    D, V, C = T[T["day"] <= D_END], T[(T["day"] > D_END) & (T["day"] <= V_END)], T[T["day"] > V_END]
    print(f"\nperiods: discovery {len(D)}, validation {len(V)}, confirmation {len(C)}  | reach(F>=1) {D.reach.mean()*100:.0f}% / {V.reach.mean()*100:.0f}% / {C.reach.mean()*100:.0f}%")
    out = []
    for f in feats:
        x = D[f].dropna()
        if len(x) < 60 or x.nunique() < 2:
            continue
        if f in BINARY:
            defs = [("=1", lambda s_: s_ == 1)]
        else:
            p33, p67 = np.percentile(x, [33.3, 66.7])
            defs = [(f"high >= {p67:.3g}", lambda s_, t_=p67: s_ >= t_), (f"low <= {p33:.3g}", lambda s_, t_=p33: s_ <= t_)]
        for name, cond in defs:
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
                row[f"{tag}_Fmed"] = gg.F.median() if len(gg) else np.nan
            out.append(row)
    R = pd.DataFrame(out)
    R["d_q"] = GF.bh(R["d_p"].values)
    R["d_eff"] = R["d_reach"] - R["d_out"]
    R["cand"] = (R["d_q"] <= 0.10) & (R["d_n"] >= 25)
    print("\nrules in family:", len(R), "| candidates:", int(R["cand"].sum()))
    print("strongest 12 in discovery:")
    print(R.sort_values("d_p").head(12)[["feature", "rule", "d_n", "d_reach", "d_out", "d_p", "d_q"]].round(3).to_string(index=False))
    Cn = R[R["cand"]].copy()
    R.drop(columns=["v_tab", "c_tab"]).to_csv(os.path.join(ROOT, "results", "g1_underlying_all_rules.csv"), index=False)
    if not len(Cn):
        print("\nno candidate at q <= 0.10")
        print("\nFOR INFORMATION ONLY (not a test): the 6 smallest discovery p, then validation and confirmation")
        print(R.sort_values("d_p").head(6)[["feature", "rule", "d_n", "d_reach", "d_out", "v_n", "v_reach", "v_out", "c_n", "c_reach", "c_out"]].round(1).to_string(index=False))
        return
    sg_ = np.sign(Cn["d_eff"])
    for tag in ("v", "c"):
        Cn[f"{tag}_eff"] = Cn[f"{tag}_reach"] - Cn[f"{tag}_out"]
        Cn[f"{tag}_p1"] = [stats.fisher_exact(tb, alternative="greater" if e > 0 else "less")[1] for tb, e in zip(Cn[f"{tag}_tab"], Cn["d_eff"])]
    Cn["pass_v"] = (Cn["v_n"] >= 20) & (np.sign(Cn["v_eff"]) == sg_) & (Cn["v_p1"] < 0.05) & (Cn["v_eff"].abs() >= 0.5 * Cn["d_eff"].abs())
    Cn["pass_c"] = Cn["pass_v"] & (Cn["c_n"] >= 20) & (np.sign(Cn["c_eff"]) == sg_) & (Cn["c_p1"] < 0.05)
    print("\ncandidates through validation and confirmation:")
    print(Cn[["feature", "rule", "d_n", "d_reach", "d_out", "d_q", "v_n", "v_reach", "v_out", "v_p1", "pass_v", "c_n", "c_reach", "c_out", "c_p1", "pass_c"]].round(3).to_string(index=False))
    Cn.drop(columns=["v_tab", "c_tab"]).to_csv(os.path.join(ROOT, "results", "g1_underlying_candidates.csv"), index=False)


def sg_close(g, ts):
    return g[g["timestamp"] == ts]["close"].iloc[0]


if __name__ == "__main__":
    main()
