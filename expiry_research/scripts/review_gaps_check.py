"""Agent 5b: independent skeptical review of module "gaps". Own code from load_panel only (no gaps_* imports).
Writes results/review_gaps/{recompute.csv, robustness.csv, spotcheck.csv, bh_check.txt}.
Run from C:/Users/sherw/project-f-0:
  INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe expiry_research/scripts/review_gaps_check.py
"""
import glob
import hashlib
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel_io import load_panel  # noqa: E402
from stats_utils import bh, binom_p, mean_ci, two_prop, wilson  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "results" / "review_gaps"
OUT.mkdir(parents=True, exist_ok=True)
STORE = Path(os.environ["INDEX_STORE"])


def rows(ul):
    P = load_panel(ul).sort_values("date").reset_index(drop=True)
    P = P[~P.split_edge.astype(bool) & ~P.cal_special_between.astype(bool) & P.y_gap_pct.notna()].copy()
    P["d0"] = P.cal_next_is_expiry == True  # noqa: E712
    P["dm1"] = P.cal_next_sessions_to_expiry == 1
    P["dp1"] = (P.cal_next_sessions_since_expiry == 1) & ~P.d0
    P["ordi"] = ~P.d0 & ~P.dm1 & ~P.dp1
    P["yr"] = P.y_date.str[:4]
    P["dow"] = pd.to_datetime(P.y_date).dt.day_name().str[:3]
    v = P.loc[P.split == "discovery", "f_vix_close"]
    c1, c2 = v.quantile([1 / 3, 2 / 3])
    P["vixt"] = np.where(P.f_vix_close <= c1, 1, np.where(P.f_vix_close <= c2, 2, 3))
    P["minute"] = P.src.eq("spot_1m") & P.y_src.eq("spot_1m")
    return P


def r2(a, b, nm, **kw):
    k1, n1, k2, n2 = a.sum(), len(a), b.sum(), len(b)
    if min(n1, n2) == 0:
        return dict(test=nm, n=n1, nB=n2, **kw)
    r, lo, hi = wilson(k1, n1)
    return dict(test=nm, n=n1, nB=n2, rate=r, base=k2 / n2, effect=r - k2 / n2, ci_lo=lo, ci_hi=hi,
                p=two_prop(k1, n1, k2, n2), thin=min(n1, n2) < 30, **kw)


def m2(a, b, nm, **kw):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if min(len(a), len(b)) < 2:
        return dict(test=nm, n=len(a), nB=len(b), **kw)
    m, lo, hi = mean_ci(a)
    return dict(test=nm, n=len(a), nB=len(b), rate=m, base=b.mean(), effect=m - b.mean(), ci_lo=lo, ci_hi=hi,
                p=float(stats.ttest_ind(a, b, equal_var=False).pvalue), thin=min(len(a), len(b)) < 30, **kw)


def fa(S, lo=0.1, hi=0.5):
    g = S[(S.y_gap_pct.abs() >= lo) & (S.y_gap_pct.abs() < hi) & S.y_gap_filled.notna()]
    return g[g.y_gap_pct > 0].y_gap_filled.astype(float), g[g.y_gap_pct < 0].y_gap_filled.astype(float)


def minutes15(code):
    fs = [f for f in sorted(glob.glob(str(STORE / f"spot_1m/{code}/*.parquet"))) if Path(f).stem <= "2024-06"]
    m = pd.concat([pd.read_parquet(f, columns=["timestamp", "close"]) for f in fs])
    m["ts"] = m.timestamp.dt.tz_convert("Asia/Kolkata")
    m["d"] = m.ts.dt.strftime("%Y-%m-%d")
    m["hm"] = m.ts.dt.strftime("%H:%M")
    m = m[(m.d <= "2024-06-30") & (m.hm >= "09:15") & (m.hm <= "15:29")].drop_duplicates("ts")
    p = m.pivot_table(index="d", columns="hm", values="close", aggfunc="last")
    return (p["09:29"] / p["09:15"] - 1) * 100


def main():
    rec, rob, spot = [], [], []
    N, B = rows("NIFTY"), rows("BANKNIFTY")
    # 1. N_Fa_dir
    for sp in ["discovery", "validation"]:
        a, b = fa(N[N.split == sp])
        rec.append(r2(a, b, "N_Fa_dir", split=sp))
    sl = [("all disc+val", N)] + [(f"year {y}", N[N.yr == y]) for y in sorted(N.yr.unique())]
    sl += [(f"vix t{t}", N[N.vixt == t]) for t in (1, 2, 3)]
    sl += [("y_src spot_1m (15:29 close era)", N[N.y_src == "spot_1m"]),
           ("y_src official-close era", N[N.y_src != "spot_1m"])]
    sl += [(f"t+1 {d}", N[N.dow == d]) for d in ["Mon", "Tue", "Wed", "Thu", "Fri"]]
    for nm, S in sl:
        a, b = fa(S)
        rob.append(r2(a, b, "N_Fa_dir", slice=nm))
    for lo, hi in [(0.1, 0.3), (0.1, 0.4), (0.1, 0.6), (0.2, 0.5), (0.3, 0.5), (0.5, 1.0)]:
        for sp in ["discovery", "validation"]:
            a, b = fa(N[N.split == sp], lo, hi)
            rob.append(r2(a, b, "N_Fa_dir", slice=f"band {lo}-{hi} {sp}"))
    for sp in ["discovery", "validation"]:
        a, b = fa(B[B.split == sp])
        rob.append(r2(a, b, "N_Fa_dir", slice=f"BANKNIFTY twin {sp}"))
    g = N[(N.split == "discovery") & (N.y_gap_pct.abs() >= 0.1) & (N.y_gap_pct.abs() < 0.5)]
    rob.append(dict(test="N_Fa_dir", slice="mean |gap| up vs down (disc)",
                    rate=g[g.y_gap_pct > 0].y_gap_pct.abs().mean(), base=g[g.y_gap_pct < 0].y_gap_pct.abs().mean()))
    # 2/3. low_min D0 / D+1 vs ordinary (NIFTY)
    for ctx in ["d0", "dp1"]:
        nm = f"N_B{ctx}_low_min"
        for sp in ["discovery", "validation"]:
            S = N[(N.split == sp) & N.minute & N.y_low_min.notna()]
            rec.append(m2(S[S[ctx]].y_low_min, S[S.ordi].y_low_min, nm, split=sp))
        S = N[N.minute & N.y_low_min.notna()]
        for y in sorted(S.yr.unique()):
            s = S[S.yr == y]
            rob.append(m2(s[s[ctx]].y_low_min, s[s.ordi].y_low_min, nm, slice=f"year {y}"))
        a, b = S[S[ctx]].y_low_min, S[S.ordi].y_low_min
        rob.append(dict(test=nm, slice="median disc+val (Mann-Whitney p)", n=len(a), nB=len(b), rate=a.median(),
                        base=b.median(), p=float(stats.mannwhitneyu(a, b).pvalue)))
        Sd = S[S.split == "discovery"]
        o = Sd[Sd.ordi]
        rob.append(m2(o[o.dow == "Tue"].y_low_min, o[o.dow == "Mon"].y_low_min, nm,
                      slice="control disc: ordinary Tue vs Mon"))
        rob.append(m2(Sd[Sd.dm1].y_low_min, o.y_low_min, nm, slice="control disc: D-1 (Wed) vs ordinary"))
        for sp in ["discovery", "validation"]:
            S2 = B[(B.split == sp) & B.minute & B.y_low_min.notna()]
            rob.append(m2(S2[S2[ctx]].y_low_min, S2[S2.ordi].y_low_min, nm, slice=f"BANKNIFTY twin {sp}"))
    # 4. B_BDm1_abs_gap
    nm = "B_BDm1_abs_gap"
    for sp in ["discovery", "validation"]:
        S = B[B.split == sp]
        rec.append(m2(S[S.dm1].y_gap_pct.abs(), S[S.ordi].y_gap_pct.abs(), nm, split=sp))
        rob.append(m2(S[S.dm1].y_gap_pct.abs(), S[S.ordi & (S.dow != "Mon")].y_gap_pct.abs(), nm,
                      slice=f"vs ordinary excl. Monday {sp}"))
        rob.append(m2(S[S.ordi & (S.dow == "Mon")].y_gap_pct.abs(), S[S.ordi & (S.dow != "Mon")].y_gap_pct.abs(),
                      nm, slice=f"control: ordinary Monday vs ordinary non-Monday {sp}"))
        cd = (pd.to_datetime(S.y_date) - pd.to_datetime(S.date)).dt.days
        rob.append(m2(S[S.dm1 & (cd == 1)].y_gap_pct.abs(), S[S.ordi & (cd == 1)].y_gap_pct.abs(), nm,
                      slice=f"only 1-calendar-day gaps {sp}"))
    for y in sorted(B.yr.unique()):
        s = B[B.yr == y]
        rob.append(m2(s[s.dm1].y_gap_pct.abs(), s[s.ordi].y_gap_pct.abs(), nm, slice=f"year {y}"))
    S = B[B.split == "discovery"]
    a, b = S[S.dm1].y_gap_pct.abs(), S[S.ordi].y_gap_pct.abs()
    rob.append(m2(a, b.sort_values().iloc[: int(len(b) * 0.99)], nm, slice="disc, drop largest 1 % ordinary gaps"))
    rob.append(dict(test=nm, slice="median disc (Mann-Whitney p)", n=len(a), nB=len(b), rate=a.median(),
                    base=b.median(), p=float(stats.mannwhitneyu(a, b).pvalue)))
    # spot-check A: expiry-day 15-min fade after a >= 0.3 % gap (own minute loader)
    for ul, P, code in [("NIFTY", N, "NIFTY50"), ("BANKNIFTY", B, "NIFTYBANK")]:
        r15 = minutes15(code)
        Q = P[P.minute].copy()
        Q["r15"] = Q.y_date.map(r15)
        Q = Q[Q.r15.notna() & (Q.y_gap_pct.abs() >= 0.3)]
        Q["s15"] = Q.r15 * np.sign(Q.y_gap_pct)
        t = f"{ul[0]}_ED0m_se_ret15"
        for sp in ["discovery", "validation"]:
            s = Q[Q.split == sp]
            spot.append(m2(s[s.d0].s15, s[~s.d0].s15, t, split=sp))
        s = Q[Q.split == "discovery"]
        spot.append(m2(s[s.d0].s15, s[~s.d0 & s.dow.isin(["Wed", "Fri"])].s15, t, split="disc, D0 vs Wed/Fri non-D0"))
        s = Q[Q.split == "discovery"].copy()
        spot.append(m2(s[s.d0].s15.clip(upper=s[s.d0].s15.quantile(0.99)), s[~s.d0].s15, t,
                       split="disc, D0 top 1 % winsorised"))
    # spot-check B: D-1 gaps >= 0.5 % fill / signed oc
    for ul, P in [("NIFTY", N), ("BANKNIFTY", B)]:
        for sp in ["discovery", "validation"]:
            S = P[(P.split == sp) & (P.y_gap_pct.abs() >= 0.5) & P.y_gap_filled.notna()]
            spot.append(r2(S[S.dm1].y_gap_filled.astype(float), S[~S.dm1].y_gap_filled.astype(float),
                           f"{ul[0]}_EDm1_05_fill", split=sp))
            soc = S.y_oc * np.sign(S.y_gap_pct)
            spot.append(m2(soc[S.dm1], soc[~S.dm1], f"{ul[0]}_EDm1_05_soc", split=sp))
    # spot-check C: transition gap up -> gap down
    for ul, P in [("NIFTY", N), ("BANKNIFTY", B)]:
        D = P[P.split == "discovery"]
        a = D[D.o_gap_dir == "up"]
        k, n, base = int((a.y_gap_dir == "down").sum()), len(a), (D.y_gap_dir == "down").mean()
        r, lo, hi = wilson(k, n)
        spot.append(dict(test=f"{ul[0]}_T1 up->down", split="discovery", n=n, rate=r, base=base, effect=r - base,
                         ci_lo=lo, ci_hi=hi, p=binom_p(k, n, base)))
    pd.DataFrame(rec).to_csv(OUT / "recompute.csv", index=False)
    pd.DataFrame(rob).to_csv(OUT / "robustness.csv", index=False)
    pd.DataFrame(spot).to_csv(OUT / "spotcheck.csv", index=False)
    # BH and freeze-hash checks
    H = pd.read_csv(ROOT / "results/gaps/hypotheses.csv")
    q, rej = bh(H.d_p.values, 0.10)
    h = hashlib.sha256()
    for f in ["gaps_specs.py", "gaps_common.py", "gaps_eval.py"]:
        h.update((HERE / f).read_bytes())
    F = pd.read_csv(ROOT / "results/gaps/candidates_frozen.csv")
    mt = pd.Timestamp(os.path.getmtime(ROOT / "results/gaps/validation.csv"), unit="s", tz="UTC").tz_convert("Asia/Kolkata")
    txt = (f"family {len(H)}, p non-null {H.d_p.notna().sum()}, BH-sig (own bh call) {int(np.sum(rej))}, "
           f"max |q diff| {np.nanmax(np.abs(np.asarray(q) - H.d_q.values)):.2e}\n"
           f"frozen ids {list(F.id)}; BH-sig non-thin ids {list(H.loc[np.asarray(rej) & ~H.d_thin, 'id'])}\n"
           f"hash now {h.hexdigest()} vs frozen {F.code_sha256.iloc[0]} equal={h.hexdigest() == F.code_sha256.iloc[0]}\n"
           f"frozen_at {F.frozen_at.iloc[0]}; validation.csv mtime {mt}\n")
    (OUT / "bh_check.txt").write_text(txt, encoding="utf-8")
    print(txt)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)
    for f in ["recompute", "robustness", "spotcheck"]:
        print("=====", f)
        print(pd.read_csv(OUT / f"{f}.csv").round(4).to_string(index=False))


if __name__ == "__main__":
    main()
