"""Tradeability of the final-test NIFTY size signals and of expiry itself: ATM straddle on real option minutes.

Design: reports/lld/tradeability.md (FINAL_TEST_PLAN.md "Tradeability"). One run. Outputs results/tradeability/.
Run from the repo root: ../.venvs/fo/Scripts/python.exe expiry_research/scripts/tradeability_run.py
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stats_utils as su  # noqa: E402
import tradeability_common as tc  # noqa: E402

OUT = os.path.join(tc.ROOT, "results", "tradeability")
os.makedirs(OUT, exist_ok=True)
SLIPS = (0.5, 1.0, 2.0)
TARGET = 1.20
RULES_DOWN = {"PPC062", "M218", "M220"}  # size view predicts a smaller move when flagged
UP5 = ["PPC032", "OC13", "OC17", "OC21", "M143"]

# ---------- inputs ----------
fr = pd.read_csv(os.path.join(tc.ROOT, "results", "final", "final_results.csv"))
# Validated = gate 1 and gate 2 (BH over the 13 one-sided p-values), as in final_test.py
q, rej = su.bh(fr["fin_p_one_sided"].values, 0.10)
fr["validated"] = fr["gate1"].astype(bool) & rej
VAL = fr[(fr["ul"] == "NIFTY") & fr["validated"]]["id"].tolist()
print("Validated NIFTY rules:", VAL)
assert set(VAL) == {"PPC032", "PPC062", "OC13", "OC17", "OC21", "M143", "M218", "M220"}, VAL

fl = pd.read_csv(os.path.join(tc.ROOT, "results", "final", "flags_NIFTY.csv"), dtype={"date": str, "y_date": str})
cal = pd.read_csv(os.path.join(tc.ROOT, "data", "expiry_calendar.csv"), dtype=str)
cal = cal[cal["underlying"] == "NIFTY"]
EXP = sorted(cal["expiry_date"].unique())
KIND = cal.groupby("expiry_date")["kind"].first().to_dict()
ses = pd.read_csv(os.path.join(tc.ROOT, "data", "sessions_NIFTY.csv"), dtype=str)
SES = ses["date"].tolist()
SIDX = {d: i for i, d in enumerate(SES)}
NEXT_EXP = dict(zip(ses["date"], ses["next_expiry"]))
EXPSET = set(EXP)

# VIX terciles of t over all final-period flag rows
vq = fl["f_vix_close"].quantile([1 / 3, 2 / 3]).values
fl["vix_terc"] = np.where(fl["f_vix_close"] <= vq[0], "low", np.where(fl["f_vix_close"] <= vq[1], "mid", "high"))
fl.loc[fl["f_vix_close"].isna(), "vix_terc"] = np.nan
print(f"VIX tercile cuts (VIX at t, final period, n {fl['f_vix_close'].notna().sum()}): {vq[0]:.2f} / {vq[1]:.2f}")


def dte(d, e):
    return SIDX[e] - SIDX[d] if e in SIDX else np.nan


def ctx(d):
    if d in EXPSET:
        return "D0"
    i = SIDX[d]
    if i + 1 < len(SES) and SES[i + 1] in EXPSET:
        return "D-1"
    return "other"


# ---------- trades ----------
rows, skipped = [], []
HM_PATH = None
for _, r in fl.iterrows():
    d = r["y_date"]
    assert d in SIDX, d
    ea = next(e for e in EXP if e >= d)
    eb = next(e for e in EXP if e > d)
    assert NEXT_EXP[d] == ea, (d, NEXT_EXP[d], ea)
    d2 = SES[SIDX[d] + 1] if SIDX[d] + 1 < len(SES) else None
    base = {"signal_date": r["date"], "trade_date": d, "ctx": ctx(d), "vix_t": r["f_vix_close"],
            "vix_terc": r["vix_terc"]}
    for k in [c for c in fl.columns if c.endswith("_flag")]:
        base[k] = r[k]
    so = tc.spot_open_0915(d)
    for ech, e in (("a", ea), ("b", eb)):
        info = dict(base, exp_choice=ech, expiry=e, exp_kind=KIND.get(e), dte=dte(d, e))

        def skip(reason, exit_="all"):
            skipped.append(dict(info, exit=exit_, reason=reason))

        if np.isnan(so):
            skip("no NIFTY spot 09:15 bar")
            continue
        K = float(np.floor(so / 50 + 0.5) * 50) if (so / 50) % 1 != 0.5 else float(np.floor(so / 50) * 50)
        info.update(spot_0915=so, strike=K)
        od = tc.opt_day(e, d)
        if od is None:
            skip("no option-minute file for (expiry, day)")
            continue
        ce, pe = tc.leg_series(od, K, "CE"), tc.leg_series(od, K, "PE")
        if "09:16" not in ce.index or "09:16" not in pe.index:
            skip(f"ATM {int(K)} CE/PE 09:16 bar missing (CE {'09:16' in ce.index}, PE {'09:16' in pe.index})")
            continue
        lot = tc.lot_size(d, e)
        if np.isnan(lot):
            skip("no lot size in bhavcopy")
            continue
        ce0, pe0 = float(ce["09:16"]), float(pe["09:16"])
        ent = ce0 + pe0
        assert ent > 0
        info.update(lot=lot, ce_in=ce0, pe_in=pe0, prem_in=ent, prem_in_rs=ent * lot)
        both = pd.concat([ce, pe], axis=1, keys=["ce", "pe"]).dropna()
        day_path = both[(both.index >= "09:17") & (both.index <= "15:15")]
        n_day_minutes = len(both[(both.index >= "09:17") & (both.index <= "15:15")])

        def finish(exit_, hm_out, ce1, pe1, path, d_out):
            st = path["ce"] + path["pe"]
            mx = float(st.max() / ent - 1) * 100 if len(st) else np.nan
            o = dict(info, exit=exit_, exit_date=d_out, exit_hm=hm_out, ce_out=ce1, pe_out=pe1,
                     prem_out=ce1 + pe1, gross_pct=((ce1 + pe1) / ent - 1) * 100, maxup_pct=mx,
                     path_minutes=len(st))
            for s in SLIPS:
                o[f"net_{s}"], o[f"charges_{s}"] = tc.net_pct(ce0, pe0, ce1, pe1, "09:16", hm_out, s, lot)
            if len(st):
                hm_best = st.idxmax()
                if isinstance(hm_best, tuple):
                    hm_best = hm_best[1]
                bce, bpe = path.loc[st.idxmax(), "ce"], path.loc[st.idxmax(), "pe"]
                o["maxup_net_0.5"] = tc.net_pct(ce0, pe0, float(bce), float(bpe), "09:16",
                                                hm_best, 0.5, lot)[0]
            rows.append(o)

        # exit (i): 15:15
        if "15:15" in ce.index and "15:15" in pe.index:
            finish("i_1515", "15:15", float(ce["15:15"]), float(pe["15:15"]), day_path, d)
        else:
            skip("15:15 bar missing", "i_1515")
        # exit (ii): +20 % target else 15:15
        st = day_path["ce"] + day_path["pe"]
        hit = st[st >= TARGET * ent - 1e-9]
        if len(hit):
            hm = hit.index[0]
            finish("ii_tgt20", hm, float(day_path.loc[hm, "ce"]), float(day_path.loc[hm, "pe"]),
                   day_path[day_path.index <= hm], d)
        elif "15:15" in ce.index and "15:15" in pe.index:
            finish("ii_tgt20", "15:15", float(ce["15:15"]), float(pe["15:15"]), day_path, d)
        else:
            skip("15:15 bar missing (target not hit)", "ii_tgt20")
        # exit (iii): next session 09:16
        if e == d:
            skip("not applicable: contract expires on the trade day", "iii_d2_0916")
        elif d2 is None:
            skip("no next session in store", "iii_d2_0916")
        else:
            od2 = tc.opt_day(e, d2)
            if od2 is None:
                skip("no option-minute file for next session", "iii_d2_0916")
            else:
                ce2, pe2 = tc.leg_series(od2, K, "CE"), tc.leg_series(od2, K, "PE")
                if "09:16" not in ce2.index or "09:16" not in pe2.index:
                    skip("next-session 09:16 bar missing", "iii_d2_0916")
                else:
                    b1 = both[both.index >= "09:17"].copy()
                    b2 = pd.concat([ce2, pe2], axis=1, keys=["ce", "pe"]).dropna()
                    b2 = b2[b2.index <= "09:16"]
                    path = pd.concat([b1.set_index("d1 " + b1.index), b2.set_index("d2 " + b2.index)])
                    finish("iii_d2_0916", "09:16", float(ce2["09:16"]), float(pe2["09:16"]), path, d2)

T = pd.DataFrame(rows)
S = pd.DataFrame(skipped)
T["dte_bucket"] = T["dte"].clip(upper=3).astype(int).astype(str).replace("3", "3+")
T.to_csv(os.path.join(OUT, "trades.csv"), index=False)
S.to_csv(os.path.join(OUT, "skipped.csv"), index=False)
dd = tc.opt_day("2026-10-19", "2026-10-15")
print(f"trades {len(T)}, skipped rows {len(S)}; 2026-10-19 dedupe example: dropped {dd.attrs['dups_dropped']} rows "
      "(incl. close <= 0) on 2026-10-15")
print(S.groupby(["exp_choice", "exit", "reason"]).size().to_string())


# ---------- summaries ----------
def summ(x, s=0.5):
    v = x[f"net_{s}"].values
    n = len(v)
    if n == 0:
        return {"n": 0}
    k = int((v > 0).sum())
    w = su.wilson(k, n)
    xs = x.sort_values(["trade_date"])
    mu = x["maxup_pct"].values
    return {"n": n, "win": w[0], "win_lo": w[1], "win_hi": w[2], "mean": float(np.mean(v)),
            "median": float(np.median(v)), "t": su.t_stat(v), "worst": float(np.min(v)), "best": float(np.max(v)),
            "dd": tc.drawdown(xs[f"net_{s}"].values), "maxup_mean": float(np.nanmean(mu)),
            "maxup_median": float(np.nanmedian(mu)), "maxup_ge100": float(np.mean(mu >= 100)),
            "n_ge100": int((mu >= 100).sum()), "gross_mean": float(x["gross_pct"].mean()),
            "first": xs["trade_date"].iloc[0], "last": xs["trade_date"].iloc[-1]}


def welch(a, b):
    if len(a) < 2 or len(b) < 2:
        return np.nan, np.nan
    tt = stats.ttest_ind(a, b, equal_var=False)
    p1 = tt.pvalue / 2 if tt.statistic > 0 else 1 - tt.pvalue / 2
    return float(np.mean(a) - np.mean(b)), float(p1)


sig, expf, spl = [], [], []
for (ech, ex), g in T.groupby(["exp_choice", "exit"]):
    for s in SLIPS:
        groups = {"EVERY_DAY": g}
        for rid in VAL:
            f = g[f"{rid}_flag"]
            groups[f"{rid}|flagged"] = g[f == 1]
            groups[f"{rid}|unflagged"] = g[f == 0]
        u = g[[f"{r}_flag" for r in UP5]]
        groups["UP5|flagged"] = g[(u == 1).any(axis=1)]
        groups["UP5|unflagged"] = g[(u == 0).all(axis=1)]
        for name, x in groups.items():
            o = {"exp_choice": ech, "exit": ex, "slip": s, "group": name, **summ(x, s)}
            if name.endswith("|flagged"):
                rid = name.split("|")[0]
                un = groups[f"{rid}|unflagged"]
                o["diff_vs_unflagged"], o["p_flag_gt_unflag"] = welch(x[f"net_{s}"].values, un[f"net_{s}"].values)
                o["maxup_diff_vs_unflagged"] = x["maxup_pct"].mean() - un["maxup_pct"].mean()
                o["size_view"] = "smaller" if rid in RULES_DOWN else "bigger"
                # plan rule, applied to every rule (review fix, LLD "Review fixes" 1)
                o["worth_trading"] = bool(o["diff_vs_unflagged"] > 0 and o["mean"] > 0)
                o["size_view_consistent"] = rid not in RULES_DOWN
            sig.append(o)
        # expiry family (no signal)
        for c, x in g.groupby("ctx"):
            other = g[g["ctx"] != c]
            o = {"exp_choice": ech, "exit": ex, "slip": s, "group": c, **summ(x, s)}
            o["diff_vs_rest"], o["p_gt_rest"] = welch(x[f"net_{s}"].values, other[f"net_{s}"].values)
            expf.append(o)
        for kd, x in g[g["ctx"] == "D0"].groupby("exp_kind"):
            expf.append({"exp_choice": ech, "exit": ex, "slip": s, "group": f"D0_{kd}", **summ(x, s)})
        # splits
        if s == 0.5:
            for name, x0 in [("EVERY_DAY", g), ("D0", g[g["ctx"] == "D0"]), ("D-1", g[g["ctx"] == "D-1"]),
                             ("UP5|flagged", groups["UP5|flagged"])] + \
                            [(f"{rid}|flagged", groups[f"{rid}|flagged"]) for rid in VAL]:
                for dim in ("dte_bucket", "vix_terc", "ctx"):
                    for lv, x in x0.groupby(dim):
                        spl.append({"exp_choice": ech, "exit": ex, "slip": s, "group": name, "split": dim,
                                    "level": lv, **summ(x, s)})

SG, EF, SP = pd.DataFrame(sig), pd.DataFrame(expf), pd.DataFrame(spl)
SG.to_csv(os.path.join(OUT, "summary_signals.csv"), index=False)
EF.to_csv(os.path.join(OUT, "summary_expiry.csv"), index=False)
SP.to_csv(os.path.join(OUT, "summary_splits.csv"), index=False)

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
cols = ["group", "n", "win", "mean", "median", "t", "worst", "dd", "maxup_mean", "maxup_median", "maxup_ge100"]
for ech in ("a", "b"):
    for ex in ("i_1515", "ii_tgt20", "iii_d2_0916"):
        print(f"\n=== signals: expiry {ech}, exit {ex}, slip 0.5 ===")
        x = SG[(SG.exp_choice == ech) & (SG.exit == ex) & (SG.slip == 0.5)]
        print(x[cols + ["diff_vs_unflagged", "p_flag_gt_unflag"]].round(3).to_string(index=False))
        print(f"=== expiry family: expiry {ech}, exit {ex}, slip 0.5 ===")
        x = EF[(EF.exp_choice == ech) & (EF.exit == ex) & (EF.slip == 0.5)]
        print(x[cols + ["diff_vs_rest", "p_gt_rest"]].round(3).to_string(index=False))
print("\n=== slippage sensitivity, EVERY_DAY / UP5 / D0 / D-1 mean net % ===")
a = pd.concat([SG[SG.group.isin(["EVERY_DAY", "UP5|flagged", "UP5|unflagged"])],
               EF[EF.group.isin(["D0", "D-1"])]])
print(a.pivot_table(index=["exp_choice", "exit", "group"], columns="slip", values="mean").round(2).to_string())
print("\n=== max up by dte bucket (exit i, slip 0.5) ===")
x = SP[(SP.split == "dte_bucket") & (SP.exit == "i_1515") & SP.group.isin(["EVERY_DAY", "D0", "D-1", "UP5|flagged"])]
print(x[["exp_choice", "group", "level", "n", "mean", "maxup_mean", "maxup_median", "maxup_ge100", "n_ge100"]]
      .round(3).to_string(index=False))
