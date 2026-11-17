"""Agent 3b addendum: same-contract GIFT overnight = open(D, near-month contract c) / settlement(D_prev, same contract c) - 1.
Builds gift_labels_samecontract.csv, then runs the unchanged table code (gift_tables.py text with renamed outputs)."""
import os, re, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
O = pd.read_csv(os.path.join(HERE, "gift_labels.csv"), parse_dates=["date"])
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 4))
g = pd.read_csv(os.path.join(REPO, "index_context_research", "regime_investigation", "external_data", "gift_bhavcopy_futures.csv"))
n = g[g.contract.astype(str).str.match(r"^FUTIDXNIFTY\d{2}-[A-Z]{3}-\d{4}$")].copy()
n["d"] = pd.to_datetime(n.trade_date); n["exp"] = pd.to_datetime(n.contract.str[11:], format="%d-%b-%Y")
for c in ("open", "settlement"): n[c] = pd.to_numeric(n[c], errors="coerce")
n = n[n.exp >= n.d].sort_values(["d", "exp"])
days = np.array(sorted(n.d.unique()))
nm = n.groupby("d").first()
key = n.set_index(["d", "contract"]).settlement
prev = pd.Series(days, index=days).shift(1)
nm["prev_d"] = prev.reindex(nm.index)
nm["settle_same"] = [key.get((pd.Timestamp(p), c), np.nan) if p == p else np.nan for p, c in zip(nm.prev_d, nm.contract)]
nm["ret_same"] = (nm.open / nm.settle_same - 1) * 100
nm.loc[nm.open <= 0, "ret_same"] = np.nan
miss = int(nm.ret_same.isna().sum())
O["gift_ret_prevsettle_col"] = O.gift_ret; O["gift_cls_prevsettle_col"] = O.gift_cls
O["ivsa_cls_prevsettle_col"] = O.ivsa_cls
O["gift_ret_samecontract"] = O.date.map(nm.ret_same)
cl = lambda x, hi, lo, nmz: np.nan if x != x else (nmz[0] if x >= hi else (nmz[2] if x <= lo else nmz[1]))
O["gift_cls"] = O.gift_ret_samecontract.map(lambda x: cl(x, .3, -.3, ["gap-up", "flat", "gap-down"]))
O["gap_minus_gift_samecontract"] = O.gap_pct - O.gift_ret_samecontract
O["ivsa_cls"] = O.gap_minus_gift_samecontract.map(lambda x: cl(x, .2, -.2, ["stronger", "in line", "weaker"]))
O["gift_cls_rob"] = O.gift_cls_prevsettle_col; O["ivsa_cls_rob"] = O.ivsa_cls_prevsettle_col  # R1/R2 now = prev_settle column version
O.to_csv(os.path.join(HERE, "gift_labels_samecontract.csv"), index=False)
d = nm.copy(); d["d"] = d.index
nf = pd.read_csv(os.path.join(REPO, "data", "eod2", "nifty 50.csv"), parse_dates=["Date"]).set_index("Date")
d["actual"] = ((nf.Open / nf.Close.shift(1) - 1) * 100).reindex(d.index)
d["ps"] = (d.open / pd.to_numeric(d.prev_settle, errors="coerce") - 1) * 100
d["pr"] = (d.open / d.settlement.shift(1) - 1) * 100
out = [f"same-contract return missing on {miss} of {len(nm)} GIFT days; on trade rows missing: {int(O.groupby('strategy').gift_ret_samecontract.apply(lambda x: x.isna().sum()).sum())} ({O.groupby('strategy').gift_ret_samecontract.apply(lambda x: int(x.isna().sum())).to_dict()})"]
for lab, s in (("all days", d), ("trade window 2024-10-01..2026-10-23", d.loc["2024-10-01":"2026-10-23"])):
    s = s.dropna(subset=["ret_same", "ps", "pr", "actual"])
    out.append(f"{lab} n={len(s)}: corr with actual NIFTY gap: same-contract {s.ret_same.corr(s.actual):.3f}; prev_settle column {s.ps.corr(s.actual):.3f}; previous-row {s.pr.corr(s.actual):.3f}")
out.append(f"same-contract percentiles 1/5/50/95/99: {np.nanpercentile(nm.ret_same,[1,5,50,95,99]).round(3).tolist()}; days differing from previous-row by >0.05 pt: {int((abs(nm.ret_same-((nm.open/nm.settlement.shift(1)-1)*100))>0.05).sum())}")
for st, s in O.groupby("strategy"):
    s2 = s.dropna(subset=["gift_ret_samecontract"])
    out.append(f"{st}: n={len(s2)} corr(same-contract, actual gap) {s2.gift_ret_samecontract.corr(s2.gap_pct):.3f}; classes {s2.gift_cls.value_counts().to_dict()}; ivsa {s2.ivsa_cls.value_counts().to_dict()}")
    if st == "G1-F":
        for c in ("gap-down", "gap-up"):
            t = s2[s2.gift_cls == c]; out.append(f"  G1-F GIFT {c} (same-contract) n={len(t)}: actual gap classes {t.gap_cls.value_counts().to_dict()}")
open(os.path.join(HERE, "gift_samecontract_checks.txt"), "w").write("\n".join(out) + "\n"); print("\n".join(out))
src = open(os.path.join(HERE, "gift_tables.py"), encoding="utf-8").read()
for a, b in (("gift_labels.csv", "gift_labels_samecontract.csv"), ("gift_tables.csv", "gift_tables_samecontract.csv"), ("gift_tests.csv", "gift_tests_samecontract.csv"),
             ("gift_triple_status.csv", "gift_triple_status_samecontract.csv"), ("gift_consistency.csv", "gift_consistency_samecontract.csv"),
             ("gift_halfyear.csv", "gift_halfyear_samecontract.csv"), ("gift_vs_actual_descriptive.csv", "gift_vs_actual_descriptive_samecontract.csv"),
             ("R1_gift_prevrow", "R1_gift_prevsettlecol"), ("R2_ivsa_prevrow", "R2_ivsa_prevsettlecol"), ("gift_ret_rob", "gift_ret_prevsettle_col")):
    src = src.replace(a, b)
exec(compile(src, "gift_tables_samecontract_run", "exec"), {"__file__": os.path.join(HERE, "x.py")})
