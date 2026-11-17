"""Agent 3b: descriptive diagnostics of the GIFT overnight measures against the actual NIFTY opening gap (all NIFTY days Oct 2024 - Oct 2026). Read-only."""
import os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, *[".."] * 4))
EX = os.path.join(REPO, "index_context_research", "regime_investigation", "external_data")
g = pd.read_csv(os.path.join(EX, "gift_bhavcopy_futures.csv"))
n = g[g.contract.astype(str).str.match(r"^FUTIDXNIFTY\d{2}-[A-Z]{3}-\d{4}$")].copy()
n["d"] = pd.to_datetime(n.trade_date); n["exp"] = pd.to_datetime(n.contract.str[11:], format="%d-%b-%Y")
nm = n[n.exp >= n.d].sort_values(["d", "exp"]).groupby("d").first()
for c in ("prev_settle", "open", "settlement"): nm[c] = pd.to_numeric(nm[c], errors="coerce")
nm["prim"] = (nm.open / nm.prev_settle - 1) * 100
nm["rob"] = (nm.open / nm.settlement.shift(1) - 1) * 100
nm["roll"] = nm.contract != nm.contract.shift(1)
nf = pd.read_csv(os.path.join(REPO, "data", "eod2", "nifty 50.csv"), parse_dates=["Date"]).set_index("Date")
nm["actual"] = ((nf.Open / nf.Close.shift(1) - 1) * 100).reindex(nm.index)   # eod2 open/prev close (context gap_pct differs by up to 0.4 pt on some days)
out = []
for lab, s in (("2023-07..2026-11 all", nm), ("2024-10-01..2026-10-23 (trade window)", nm.loc["2024-10-01":"2026-10-23"])):
    s = s.dropna(subset=["prim", "rob", "actual"])
    out.append(f"{lab}: n={len(s)}; corr(primary, actual gap)={s.prim.corr(s.actual):.2f}; corr(prev-row variant, actual gap)={s.rob.corr(s.actual):.2f}; roll days {int(s.roll.sum())}")
    ns = s[~s.roll]
    out.append(f"   excluding roll days n={len(ns)}: primary {ns.prim.corr(ns.actual):.2f}; prev-row {ns.rob.corr(ns.actual):.2f}; mean(prev-row minus primary) roll days {(s[s.roll].rob - s[s.roll].prim).mean():.2f} pt, other days {(ns.rob - ns.prim).mean():.2f} pt, sd {(ns.rob-ns.prim).std():.2f}")
    out.append(f"   primary class counts: gap-down {(s.prim<=-0.3).sum()}, gap-up {(s.prim>=0.3).sum()}, flat {((s.prim>-0.3)&(s.prim<0.3)).sum()}")
open(os.path.join(HERE, "gift_diagnostics.txt"), "w").write("\n".join(out) + "\n"); print("\n".join(out))
