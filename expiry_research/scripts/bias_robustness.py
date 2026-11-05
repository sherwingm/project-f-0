"""Bias module, stage 4: robustness of the frozen candidates on discovery + validation, per-row candidate file,
and the final hypothesis log with BH over the whole family (reports/lld/bias.md)."""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

import bias_common as bc
import stats_utils as su

OUT = bc.OUT
LOGF = bc.log_out("robustness")
F = pd.read_csv(OUT / "candidates_frozen.csv")
CV = pd.read_csv(OUT / "candidates_validation.csv").set_index("id")
CONT = {"big_cc": "abs_y_cc", "big_exc": "y_max_exc", "y_range_pct": "y_range_pct", "gap_up": "abs_y_gap",
        "gap_down": "abs_y_gap", "oc_pos": "abs_y_oc", "cc_pos": "abs_y_cc"}


def mask(A, tag, lev):
    lab = A[tag].astype(str) if tag != "xkind_ctx" else (A["xkind"] + "|" + A["ctx"])
    return lab == lev


def neighbours(tag, lev):
    """Neighbouring contexts: D-k +- 1 (D-6+ -> D-5)."""
    kind, c = (lev.split("|") if "|" in lev else (None, lev))
    if not c.startswith("D-"):
        return []
    if c == "D-6+":
        nb = ["D-5"]
    else:
        k = int(c[2:])
        nb = [f"D-{j}" for j in (k - 1, k + 1) if 1 <= j <= 5]
    return [(f"{kind}|{n}" if kind else n) for n in nb]


def eff(A, m, target, stat):
    x = A.loc[m, target].dropna()
    if stat == "rate":
        return len(x), x.mean() if len(x) else np.nan, A[target].mean()
    return len(x), x.mean() if len(x) else np.nan, A[target].mean()


rows, prow = [], []
for ul in bc.ULS:
    P, _ = bc.load(ul)
    A = P[P["usable"]].copy()
    A["abs_y_cc"] = A["y_cc"].abs()
    A["abs_y_gap"] = A["y_gap_pct"].abs()
    A["abs_y_oc"] = A["y_oc"].abs()
    for _, c in F[F.underlying == ul].iterrows():
        sign = 1 if c.direction == "higher" else -1
        m = mask(A, c.tag, c.level)

        def add(check, sub, Am, mm, target=c.target):
            n, r, b = eff(Am, mm, target, c.stat)
            e = r - b if n else np.nan
            rows.append(dict(id=c.id, underlying=ul, check=check, subset=sub, n=n, value=r, base=b, effect=e,
                             same_sign=bool(n and np.sign(e) == sign), small_n=n < 30))

        add("all", "discovery+validation", A, m)
        # drop the 1 % most extreme outcomes (whole sample)
        cc = A[CONT[c.target]]
        keep = cc <= cc.quantile(0.99)
        add("drop top 1 % outcomes", f"{CONT[c.target]} <= p99", A[keep], m[keep])
        for y in sorted(A["year"].unique()):
            s = A["year"] == y
            add("per year", y, A[s], m[s])
        for reg in sorted(A["wd_regime"].unique()):
            s = A["wd_regime"] == reg
            add("per weekday regime", reg, A[s], m[s])
        for v in ["low", "mid", "high"]:
            s = A["vix_terc"] == v
            add("per VIX tercile", v, A[s], m[s])
        for g in ["1d", "2-3d", "4d+"]:
            s = A["gap_after"] == g
            add("per days to t+1 (weekend)", g, A[s], m[s])
        for nb in neighbours(c.tag, c.level):
            if nb.endswith("D-5") and c.level.endswith("D-6+"):
                add("neighbour context", nb, A, mask(A, c.tag if c.tag != "ctx" else "dk", nb))
            else:
                add("neighbour context", nb, A, mask(A, c.tag, nb))
        if c.target in ("big_cc", "big_exc"):
            base_col = A["y_cc"].abs() if c.target == "big_cc" else A["y_max_exc"]
            for th in (0.8, 1.2):
                A["_t"] = (base_col >= th).astype(float)
                add("neighbour threshold", f"{c.target} at {th} %", A, m, "_t")
        sub = A.loc[m, ["date", "y_date", "split", "ctx", "dk", "xkind", "wd_regime", "vix_terc", c.target]]
        sub = sub.rename(columns={c.target: "outcome"})
        sub.insert(0, "id", c.id)
        prow.append(sub)

R = pd.DataFrame(rows)
R.to_csv(OUT / "robustness.csv", index=False)
pd.concat(prow).to_csv(OUT / "candidate_rows.csv", index=False)
S = (R[R.check != "all"].groupby("id")
     .apply(lambda g: pd.Series(dict(n_subsets=len(g[g.n >= 30]), same_sign=int(g[g.n >= 30].same_sign.sum()),
                                     min_effect=g[g.n >= 30].effect.min(), max_effect=g[g.n >= 30].effect.max())),
            include_groups=False))
S = S.join(CV[["verdict"]])
S.to_csv(OUT / "robustness_summary.csv")
pd.set_option("display.width", 250)
print(S.to_string())
print(R[R.check.isin(["per year", "per days to t+1 (weekend)", "neighbour context"])]
      .round(3).to_string(index=False))

# final hypothesis log: whole family
H1 = pd.read_csv(OUT / "hypotheses_discovery.csv")
H2 = pd.read_csv(OUT / "hypotheses_validation.csv")
H2.insert(0, "id", [f"V{i:05d}" for i in range(1, len(H2) + 1)])
H = pd.concat([H1, H2], ignore_index=True)
H["q_all"], H["reject_all"] = su.bh(H["p"].values, 0.10)
H["small_n"] = H["n"] < 30
H.to_csv(OUT / "hypotheses.csv", index=False)
print(f"\nwhole family: {len(H)} tests (discovery {len(H1)}, validation {len(H2)}); BH q<0.10: {int(H.reject_all.sum())}")
print(H.groupby(["family", "split"]).agg(n=("p", "size"), q10=("reject_all", "sum")).to_string())
LOGF.close()
