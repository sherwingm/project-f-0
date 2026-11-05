"""pricepath validation (one pass) and robustness for the frozen candidates (reports/lld/pricepath.md).

Reads results/pricepath/candidates_frozen.csv (written by pricepath_discovery.py before this script existed in a run)
and records its sha256. Pass rule, fixed in advance: same sign as discovery, one-sided p < 0.05 vs the validation
base of the same context (binomial for rules; Welch / shuffle share for event candidates), effect >= half the
discovery effect. Validation n < 10: not judged (Suggestive stays Suggestive, a primary stays Observed).
Labels: Suggestive + pass -> Passed-validation; Suggestive + fail -> Rejected; primary (not Suggestive) + pass ->
Observed; primary + fail -> Rejected.
Robustness uses discovery + validation rows only. Nothing here reads data after 2024-06-30.
Run: ../.venvs/fo/Scripts/python.exe expiry_research/scripts/pricepath_validate.py   (from the repo root)
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pricepath_common import (OUT, ULS, add_quantile_targets, build_features, cond_mask,  # noqa: E402
                              cond_text, disc_quantiles, rate_test)
from pricepath_discovery import QCOLS, event_study, positions  # noqa: E402

SEED_VAL = 20261106
CONT = {"t_down": "y_cc", "t_up": "y_cc", "t_sharp_fall": "y_cc", "t_sharp_rise": "y_cc", "t_gap_up": "y_gap_pct",
        "t_oc_up": "y_oc", "t_ret30_up": "y_ret30", "t_big": "y_max_exc", "t_wide": "y_range_pct",
        "t_quiet": "y_range_pct", "t_rev": "y_cc", "t_rev_oc": "y_oc"}
FIXED_NEIGH = {"up3": [3.0], "dn3": [3.0], "fbu3": [1.0, 3.0], "fbd3": [1.0, 3.0], "round_dist_pct": [0.25, 0.75],
               "f_dist_high20": [-0.25, -1.0], "f_dist_low20": [0.25, 1.0]}


def one_sided_binom(k, n, p0, direction):
    if n == 0 or np.isnan(p0):
        return np.nan
    return float(stats.binomtest(int(k), int(n), p0, alternative="greater" if direction > 0 else "less").pvalue)


def one_sided_welch(x, y, direction):
    x, y = np.asarray(x, float), np.asarray(y, float)
    x, y = x[~np.isnan(x)], y[~np.isnan(y)]
    if len(x) < 2 or len(y) < 2:
        return np.nan
    return float(stats.ttest_ind(x, y, equal_var=False, alternative="greater" if direction > 0 else "less").pvalue)


def ev_masks(P, c, split_mask):
    """x (position rows) and y (comparison rows) masks of an event candidate within split_mask."""
    k = int(c["pos"])
    if c["kind"] == "weekly":
        era = split_mask & ((P["date"] >= "2019-02-11") if c["ul"] == "NIFTY" else True)
        return era & P[f"wk_{k}"], era & ~P[f"wk_{k}"]
    return split_mask & P[f"mo_{k}"], split_mask & P[f"mt_{k}"]


def eval_rule(P, c, split_mask):
    cond = json.loads(c["cond_json"])
    rows = P.index[split_mask & P["usable"] & P[f"ctx_{c['context']}"]]
    sig = cond_mask(P, [x[:3] for x in cond])
    return rate_test(P, rows, sig, c["target"]), rows, sig


def drop_best(P, rows, sig, target, direction):
    y = P.loc[rows, target]
    rows = y[y.notna()].index
    s = sig.loc[rows]
    srows = rows[s.values]
    m = math.ceil(0.01 * len(srows))
    want = 1.0 if direction > 0 else 0.0
    cand = P.loc[srows]
    cand = cand[cand[target] == want]
    cont = cand[CONT[target]].abs().sort_values(ascending=False)
    drop = cont.index[:m]
    keep = rows.difference(drop)
    return rate_test(P, keep, sig, target)


def neighbours(cond, Q):
    out = []
    for i, (col, op, v, q) in enumerate(cond):
        alts = []
        if q is not None:
            for dq in (-0.1, -0.05, 0.05, 0.1):
                q2 = round(q + dq, 2)
                if q2 in Q.get(col, {}):
                    alts.append((Q[col][q2], f"q{q2:.2f}"))
        elif col in ("nr4", "nr7"):
            alts.append(None)
        elif col == "f_streak_close":
            alts += [(v - 1, str(v - 1)), (v + 1, str(v + 1))]
        elif col in FIXED_NEIGH:
            alts += [(a, str(a)) for a in FIXED_NEIGH[col]]
        for a in alts:
            c2 = [list(x) for x in cond]
            if a is None:
                c2[i] = ["nr7" if col == "nr4" else "nr4", "==", 1.0, None]
                tag = c2[i][0]
            else:
                c2[i][2] = a[0]
                tag = f"{col} {op} {a[1]}"
            out.append((tag, c2))
    return out


def main():
    F = pd.read_csv(OUT / "candidates_frozen.csv")
    sha = hashlib.sha256((OUT / "candidates_frozen.csv").read_bytes()).hexdigest()
    print("frozen file sha256", sha, "candidates", len(F))
    rng = np.random.default_rng(SEED_VAL)
    PP, QQ = {}, {}
    shuffle_val = {}
    for ul in ULS:
        P = build_features(ul)
        positions(P, ul)
        Q = disc_quantiles(P, QCOLS)
        add_quantile_targets(P, Q)
        PP[ul], QQ[ul] = P, Q
        if (F[(F["ul"] == ul)]["kind"] == "monthly_shuffle").any():
            _, sh = event_study(P, ul, rng, split="validation", start="2023-01-01", end="2024-06-30")
            for r in sh:
                shuffle_val[(ul, r["pos"], r["metric"])] = r
    V, R, PRED = [], [], []
    for _, c in F.iterrows():
        P, Q = PP[c["ul"]], QQ[c["ul"]]
        d = float(np.sign(c["effect"]))
        val = P["split"] == "validation"
        dv = P["split"].isin(["discovery", "validation"])
        if c["type"] == "event":
            if c["kind"] == "monthly_shuffle":
                r = shuffle_val[(c["ul"], int(c["pos"]), c["metric"])]
                dd = r["draws"]
                n_v, v_val, comp = r["n"], r["value"], r["comp_value"]
                p1 = float(((dd >= v_val).mean() if d > 0 else (dd <= v_val).mean()) + 1 / len(dd)) if len(dd) \
                    and not np.isnan(v_val) else np.nan
            else:
                xm, ym = ev_masks(P, c, val)
                x, y = P.loc[xm, c["metric"]].dropna(), P.loc[ym, c["metric"]].dropna()
                n_v, v_val, comp = len(x), x.mean(), y.mean()
                if c["stat"] == "rate":
                    k1, n1, k2, n2 = x.sum(), len(x), y.sum(), len(y)
                    pp = (k1 + k2) / (n1 + n2)
                    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2)) if n1 and n2 else np.nan
                    z = (k1 / n1 - k2 / n2) / se if se else np.nan
                    p1 = float(stats.norm.sf(z * d)) if not np.isnan(z) else np.nan
                else:
                    p1 = one_sided_welch(x, y, d)
            eff_v = v_val - comp
            base_v = comp
            rate_v = v_val
        else:
            r, rows, sig = eval_rule(P, c, val)
            n_v, rate_v, base_v, eff_v = r["n"], r["rate"], r["base"], r["effect"]
            p1 = one_sided_binom(r["k"], r["n"], r["base"], d)
        same = np.sign(eff_v) == d
        half = abs(eff_v) >= 0.5 * abs(c["effect"]) if not np.isnan(eff_v) else False
        passed = bool(same and (p1 < 0.05) and half) if n_v >= 10 else None
        sugg = str(c["why"]).startswith("Suggestive")
        if passed is None:
            label = "Suggestive" if sugg else "Observed"
        elif sugg:
            label = "Passed-validation" if passed else "Rejected"
        else:
            label = "Observed" if passed else "Rejected"
        V.append(dict(id=c["id"], ul=c["ul"], type=c["type"], hyp=c["hyp"], context=c["context"],
                      target=c["target"], rule=c["rule"], disc_n=c["n"], disc_rate=c["rate"], disc_base=c["base"],
                      disc_effect=c["effect"], disc_p=c["p"], disc_q=c["bh_q"], val_n=n_v, val_rate=rate_v,
                      val_base=base_v, val_effect=eff_v, val_p_one_sided=p1, same_sign=bool(same),
                      half_effect=bool(half), passed=passed, label=label, why=c["why"]))
        # ---------------- robustness (discovery + validation)
        rob = dict(id=c["id"])
        if c["type"] == "rule":
            cond = json.loads(c["cond_json"])
            r_all, rows, sig = eval_rule(P, c, dv)
            rob.update(dv_n=r_all["n"], dv_rate=r_all["rate"], dv_base=r_all["base"], dv_effect=r_all["effect"])
            rd = drop_best(P, rows, sig, c["target"], d)
            rob["drop1_effect"] = rd["effect"]
            for grp in ("year", "wd_regime", "vix_t"):
                if grp == "vix_t":
                    v = P.loc[dv, "f_vix_close"]
                    P["vix_t"] = pd.qcut(v, 3, labels=["low", "mid", "high"]).reindex(P.index)
                same_n = tot = 0
                for g, gi in P.loc[rows].groupby(grp, observed=True).groups.items():
                    rg = rate_test(P, gi, sig, c["target"])
                    R.append(dict(id=c["id"], check=grp, group=str(g), n=rg["n"], rate=rg["rate"],
                                  base=rg["base"], effect=rg["effect"]))
                    if rg["n"] >= 5:
                        tot += 1
                        same_n += int(np.sign(rg["effect"]) == d)
                rob[f"{grp}_same_sign"] = f"{same_n}/{tot}"
            nb = neighbours(cond, Q)
            effs = []
            for tag, c2 in nb:
                sig2 = cond_mask(P, [x[:3] for x in c2])
                rn = rate_test(P, rows, sig2, c["target"])
                effs.append(rn["effect"])
                R.append(dict(id=c["id"], check="neighbour", group=tag, n=rn["n"], rate=rn["rate"], base=rn["base"],
                              effect=rn["effect"]))
            rob["neigh_same_sign"] = f"{sum(int(np.sign(e) == d) for e in effs if not np.isnan(e))}/{len(effs)}"
            # per-row predictions (one row per context row, discovery + validation)
            yv = P.loc[rows, ["date", "y_date", "split", c["target"], CONT[c["target"]]]].copy()
            yv["signal"] = sig.loc[rows].astype(int).values
            yv.columns = ["date", "y_date", "split", "target", "outcome_cont", "signal"]
            yv.insert(0, "id", c["id"])
            PRED.append(yv)
        else:
            xm, ym = ev_masks(P, c, dv)
            if c["kind"] == "monthly_shuffle":
                ym = dv & P[f"mt_{int(c['pos'])}"]
            met = c["metric"]
            x, y = P.loc[xm, met], P.loc[ym, met]
            rob.update(dv_n=int(x.notna().sum()), dv_rate=x.mean(), dv_base=y.mean(), dv_effect=x.mean() - y.mean())
            xs = x.dropna().sort_values(ascending=d < 0)
            m = math.ceil(0.01 * len(xs))
            rob["drop1_effect"] = xs.iloc[m:].mean() - y.mean()
            v = P.loc[dv, "f_vix_close"]
            P["vix_t"] = pd.qcut(v, 3, labels=["low", "mid", "high"]).reindex(P.index)
            for grp in ("year", "wd_regime", "vix_t"):
                same_n = tot = 0
                for g in P.loc[dv, grp].dropna().unique():
                    gm = P[grp] == g
                    xg, yg = P.loc[xm & gm, met].dropna(), P.loc[ym & gm, met].dropna()
                    e = xg.mean() - yg.mean() if len(xg) and len(yg) else np.nan
                    R.append(dict(id=c["id"], check=grp, group=str(g), n=len(xg), rate=xg.mean() if len(xg) else
                                  np.nan, base=yg.mean() if len(yg) else np.nan, effect=e))
                    if len(xg) >= 5 and not np.isnan(e):
                        tot += 1
                        same_n += int(np.sign(e) == d)
                rob[f"{grp}_same_sign"] = f"{same_n}/{tot}"
            rob["neigh_same_sign"] = "n/a"
            ev = P.loc[xm | ym, ["date", "split", met]].copy()
            ev["signal"] = xm.loc[ev.index].astype(int).values
            ev.columns = ["date", "split", "outcome_cont", "signal"]
            ev.insert(0, "id", c["id"])
            PRED.append(ev)
        V[-1].update({k: v for k, v in rob.items() if k != "id"})
    Vd = pd.DataFrame(V)

    def frac_ok(s):
        a, b = s.split("/")
        return int(b) > 0 and int(a) / int(b) >= 2 / 3

    Vd["robust"] = [bool(np.sign(r["drop1_effect"]) == np.sign(r["disc_effect"]) and frac_ok(r["year_same_sign"])
                         and frac_ok(r["vix_t_same_sign"]) and (r["neigh_same_sign"] == "n/a"
                                                                 or frac_ok(r["neigh_same_sign"])))
                    for _, r in Vd.iterrows()]
    Vd.insert(1, "frozen_sha256", sha[:16])
    Vd.to_csv(OUT / "validation.csv", index=False)
    pd.DataFrame(R).to_csv(OUT / "robustness.csv", index=False)
    pd.concat(PRED, ignore_index=True).to_csv(OUT / "predictions_frozen.csv", index=False)
    print(Vd["label"].value_counts().to_string())
    print("passed and robust", int(((Vd["label"] == "Passed-validation") & Vd["robust"]).sum()))


if __name__ == "__main__":
    main()
