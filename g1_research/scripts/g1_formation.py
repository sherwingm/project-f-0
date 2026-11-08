"""Formation patterns, one at a time (g1_research/FORMATION_PREREG.md). History only; record-only research."""
import os
import sys
import warnings
from datetime import date, time

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from index_data import load as L  # noqa: E402
from scanner import s3_regime as G  # noqa: E402

SPLIT = pd.Timestamp("2025-10-01")
BINARY = {"pd_inside", "pd_low_break"}


def day_features(day, sig_hhmm, daily):
    s = L.spot_1m(day, day, "NIFTY50")
    s = s[s["timestamp"].dt.date == day].copy()
    s["t"] = s["timestamp"].dt.time
    sh, sm = map(int, sig_hhmm.split(":"))
    ts = time(sh, sm)
    orb = s[(s["t"] >= time(9, 15)) & (s["t"] < time(9, 30))]
    hi, lo, rng = orb["high"].max(), orb["low"].min(), orb["high"].max() - orb["low"].min()
    sig = s[s["t"] == ts].iloc[0]
    pre = s[(s["t"] >= time(9, 30)) & (s["t"] < ts)]
    upto = s[(s["t"] >= time(9, 30)) & (s["t"] <= ts)]
    before = s[s["t"] < ts].tail(14)
    f = {}
    f["or_close_pos"] = (orb["close"].iloc[-1] - lo) / rng
    f["or_trend"] = (orb["close"].iloc[-1] / orb["open"].iloc[0] - 1) * 100
    f["or_lo_time"] = int(np.argmin(orb["low"].values))
    f["or_hi_time"] = int(np.argmax(orb["high"].values))
    f["or_front"] = (orb["high"].iloc[:5].max() - orb["low"].iloc[:5].min()) / rng
    f["or_last5"] = (orb["close"].iloc[-1] / orb["close"].iloc[min(9, len(orb) - 1)] - 1) * 100
    f["or_low_touches"] = int((orb["low"] <= lo * 1.0002).sum())
    f["open_pos"] = (orb["open"].iloc[0] - lo) / rng
    f["retest_hi"] = (upto["high"].max() - hi) / hi * 100
    mid = (hi + lo) / 2
    f["low_half"] = float((pre["close"] < mid).mean()) if len(pre) else np.nan
    f["n_inside"] = int(((pre["close"] <= hi) & (pre["close"] >= lo)).sum())
    f["squeeze"] = (sig["open"] - lo) / lo * 100
    hl = sig["high"] - sig["low"]
    f["bo_body"] = (sig["open"] - sig["close"]) / hl if hl > 0 else np.nan
    f["bo_close_pos"] = (sig["close"] - sig["low"]) / hl if hl > 0 else np.nan
    f["bo_range"] = hl / sig["close"] * 100
    br = (before["high"] - before["low"]).mean() if len(before) >= 5 else np.nan
    f["bo_range_x"] = hl / br if br and br > 0 else np.nan
    prev_bar = s[s["t"] < ts].tail(1)
    f["bo_gap_prev"] = (sig["open"] / prev_bar["close"].iloc[0] - 1) * 100 if len(prev_bar) else np.nan
    dl = daily[daily.index < day].tail(9)
    p, pp = dl.iloc[-1], dl.iloc[-2]
    pr = p["high"] - p["low"]
    f["pd_close_pos"] = (p["close"] - p["low"]) / pr
    f["pd_body"] = (p["close"] - p["open"]) / pr
    f["pd_range"] = pr / p["close"] * 100
    f["pd_nr7"] = pr / (dl["high"] - dl["low"]).iloc[-8:-1].mean()
    f["pd_inside"] = int(p["high"] < pp["high"] and p["low"] > pp["low"])
    f["pd_low_break"] = int(sig["close"] < p["low"])
    f["open_vs_pd"] = (orb["open"].iloc[0] - p["low"]) / pr
    f["or_vs_pd"] = rng / pr
    f["or_vs_atr"] = rng / (dl["high"] - dl["low"]).iloc[-5:].mean()
    c = dl["close"].values
    f["down_streak"] = int(sum(c[-i] < c[-i - 1] for i in (1, 2, 3)))
    f["lo_vs_pdl"] = (lo / p["low"] - 1) * 100
    return f


def bh(p):
    p = np.asarray(p, float)
    m = len(p)
    o = np.argsort(p)
    r = np.minimum.accumulate((p[o] * m / np.arange(1, m + 1))[::-1])[::-1]
    out = np.empty(m)
    out[o] = np.minimum(r, 1)
    return out


def main():
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    h = pd.read_csv(os.path.join(ROOT, "data", "g1_hold_days_trades.csv"))
    d["day"], h["day"] = pd.to_datetime(d["Day"]), pd.to_datetime(h["day"])
    T = d.merge(h[["day", "peak_k1", "k1_net", "k1_reason", "g1f"]], on="day").sort_values("day").reset_index(drop=True)
    daily = G.daily()
    rows, bad = [], 0
    for r in T.to_dict("records"):
        try:
            rows.append(day_features(r["day"].date(), str(r["Signal time"]), daily))
        except Exception as exc:  # noqa: BLE001
            bad += 1
            rows.append({})
            print("skip", r["day"].date(), exc)
    F = pd.DataFrame(rows)
    T = pd.concat([T, F], axis=1)
    T["reach"] = (T["peak_k1"] >= 100).astype(int)
    T.to_csv(os.path.join(ROOT, "results", "g1_formation_features.csv"), index=False)
    print("signals", len(T), "feature failures", bad)
    disc, val = T[T["day"] < SPLIT], T[T["day"] >= SPLIT]
    rules = []
    for f in F.columns:
        x = disc[f].dropna()
        if len(x) < 40 or x.nunique() < 2:
            continue
        if f in BINARY:
            rules.append((f, "=1", lambda s: s == 1))
        else:
            p33, p67 = np.percentile(x, [33.3, 66.7])
            rules.append((f, f"high >= {p67:.3g}", lambda s, t=p67: s >= t))
            rules.append((f, f"low <= {p33:.3g}", lambda s, t=p33: s <= t))
    out = []
    for f, name, cond in rules:
        def stat(df):
            df = df[df[f].notna()]
            g = df[cond(df[f])]
            o = df.drop(g.index)
            return g, o
        g, o = stat(disc)
        if len(g) < 5 or len(o) < 5:
            continue
        p = stats.fisher_exact([[g.reach.sum(), len(g) - g.reach.sum()], [o.reach.sum(), len(o) - o.reach.sum()]])[1]
        gv, ov = stat(val)
        out.append({"feature": f, "rule": name, "d_n": len(g), "d_reach": g.reach.mean() * 100, "d_out": o.reach.mean() * 100,
                    "d_med": g.peak_k1.median(), "d_p": p, "v_n": len(gv), "v_reach": gv.reach.mean() * 100 if len(gv) else np.nan,
                    "v_out": ov.reach.mean() * 100 if len(ov) else np.nan, "v_med": gv.peak_k1.median() if len(gv) else np.nan,
                    "v_tab": [[gv.reach.sum(), len(gv) - gv.reach.sum()], [ov.reach.sum(), len(ov) - ov.reach.sum()]]})
    R = pd.DataFrame(out)
    R["d_q"] = bh(R["d_p"].values)
    R["d_eff"] = R["d_reach"] - R["d_out"]
    R["cand"] = (R["d_q"] <= 0.10) & (R["d_n"] >= 25)
    pd.set_option("display.width", 250)
    print("rules in family:", len(R), "| candidates (q <= 0.10):", int(R["cand"].sum()))
    show = ["feature", "rule", "d_n", "d_reach", "d_out", "d_med", "d_p", "d_q"]
    print("\nstrongest 12 in discovery (reach = share with max up >= +100 % by the next close):")
    print(R.sort_values("d_p").head(12)[show].round(3).to_string(index=False))
    C = R[R["cand"]].copy()
    C.drop(columns=["v_tab"]).to_csv(os.path.join(ROOT, "results", "g1_formation_candidates_frozen.csv"), index=False)
    if len(C):
        C["v_eff"] = C["v_reach"] - C["v_out"]
        C["v_p1"] = [stats.fisher_exact(t, alternative="greater" if e > 0 else "less")[1] for t, e in zip(C["v_tab"], C["d_eff"])]
        sg = np.sign(C["d_eff"])
        C["passed"] = (C["v_n"] >= 20) & (np.sign(C["v_eff"]) == sg) & (C["v_p1"] < 0.05) & (C["v_eff"].abs() >= 0.5 * C["d_eff"].abs())
        print("\ncandidates on validation:")
        print(C[["feature", "rule", "d_n", "d_reach", "d_out", "d_p", "d_q", "v_n", "v_reach", "v_out", "v_eff", "v_p1", "v_med", "passed"]].round(3).to_string(index=False))
    else:
        print("\nno candidate: nothing reaches q <= 0.10 in discovery")
    # context: the lightest look at validation for the 6 smallest discovery p, labelled as NOT a test
    print("\nFOR INFORMATION ONLY (not a test): validation for the 6 smallest discovery p-values")
    top = R.sort_values("d_p").head(6)
    print(top[["feature", "rule", "d_n", "d_reach", "d_out", "v_n", "v_reach", "v_out", "v_med"]].round(1).to_string(index=False))
    R.drop(columns=["v_tab"]).to_csv(os.path.join(ROOT, "results", "g1_formation_all_rules.csv"), index=False)


if __name__ == "__main__":
    main()
