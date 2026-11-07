"""Gaps module, step 1: discovery tables and the hypothesis log (design: reports/lld/gaps.md).

Run from C:/Users/sherw/project-f-0:
  INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe expiry_research/scripts/gaps_discovery.py
Writes results/gaps/{hypotheses.csv, transitions.csv, gap_buckets.csv, reversal_by_context.csv, streaks.csv,
close_pos.csv, fill_conditions.csv, prepared_<UL>.parquet}. Uses discovery rows only for every statistic.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gaps_common import RES, prepare  # noqa: E402
from gaps_eval import evaluate  # noqa: E402
from gaps_specs import add_derived, specs_for  # noqa: E402
from stats_utils import bh, wilson  # noqa: E402

ULS = ["NIFTY", "BANKNIFTY"]
DIRS = ["up", "flat", "down"]


def load(ul, rebuild=False):
    f = RES / f"prepared_{ul}.parquet"
    if f.exists() and not rebuild:
        return pd.read_parquet(f)
    P = add_derived(prepare(ul))
    P.to_parquet(f)
    return P


def ctx_slices(D):
    yield "all", D
    for k in range(5):
        yield f"t+1 = D-{k}" if k else "t+1 = D0", D[D["k"] == k]
    yield "t+1 = D+1", D[D["dplus1"]]
    yield "t+1 = D0 weekly", D[D["d0"] & (D["kind_ctx"] == "weekly")]
    yield "t+1 = D0 monthly", D[D["d0"] & (D["kind_ctx"] == "monthly")]
    yield "t+1 = D+1 after monthly", D[D["dplus1"] & (D["kind_ctx"] == "monthly")]
    yield "t+1 not D0/D-1/D+1", D[~D["d0"] & (D["k"] != 1) & ~D["dplus1"]]
    for r in sorted(D["regime"].unique()):
        yield f"regime {r}", D[D["regime"] == r]


def transitions(D, ul):
    rows = []
    for nm, S in ctx_slices(D):
        for fr in DIRS:
            s = S[S["o_gap_dir"] == fr]
            for to in DIRS:
                k = int((s["y_gap_dir"] == to).sum())
                r, lo, hi = wilson(k, len(s))
                rows.append({"ul": ul, "slice": nm, "from_gap_t": fr, "to_gap_t1": to, "n_from": len(s), "k": k,
                             "row_rate": r, "ci_lo": lo, "ci_hi": hi,
                             "uncond_rate_slice": (S["y_gap_dir"] == to).mean(), "thin": len(s) < 30})
    # by gap-size bucket of t
    for b in sorted(D["o_bucket"].dropna().unique()):
        s = D[D["o_bucket"] == b]
        for to in DIRS:
            k = int((s["y_gap_dir"] == to).sum())
            r, lo, hi = wilson(k, len(s))
            rows.append({"ul": ul, "slice": "by gap-size bucket of t", "from_gap_t": b, "to_gap_t1": to,
                         "n_from": len(s), "k": k, "row_rate": r, "ci_lo": lo, "ci_hi": hi,
                         "uncond_rate_slice": (D["y_gap_dir"] == to).mean(), "thin": len(s) < 30})
    return rows


def bucket_table(D, ul):
    rows = []
    for nm, S in ctx_slices(D):
        if not (nm == "all" or nm.startswith("t+1")):
            continue
        for b in sorted(S["y_bucket"].dropna().unique()):
            if b == "flat":
                continue
            s = S[S["y_bucket"] == b]
            m = s["se_oc"].notna()
            rows.append({"ul": ul, "slice": nm, "gap_bucket_t1": b, "n": len(s),
                         "cont_rate": s["y_cont"].mean(), "mean_signed_oc": s["y_soc"].mean(),
                         "fill_rate": s["y_fill"].mean(), "median_fill_min": s["y_gap_fill_min"].median(),
                         "n_minute": int(m.sum()), "mean_signed_ret15_e": s["se_ret15"].mean(),
                         "mean_signed_ret60_e": s["se_ret60"].mean(), "mean_signed_oc_e": s["se_oc"].mean(),
                         "fill_after_0916": s["e_fill"].mean(), "thin": len(s) < 30})
    return rows


def main():
    RES.mkdir(parents=True, exist_ok=True)
    rebuild = "--rebuild" in sys.argv
    hyp, tr, bt, rv, st, cp, fc = [], [], [], [], [], [], []
    for ul in ULS:
        P = load(ul, rebuild)
        D = P[P["split"] == "discovery"].copy()
        print(f"{ul}: discovery rows {len(D)} ({D['y_date'].min()} .. {D['y_date'].max()}), minute t+1 rows "
              f"{int(D['se_oc'].notna().sum())}, VIX cuts {P.attrs.get('vix_cuts', '')}")
        tr += transitions(D, ul)
        bt += bucket_table(D, ul)
        # reversal by k
        for k in range(6):
            s = D[D["k"] == k]
            r, lo, hi = wilson(s["rev"].sum(), s["rev"].notna().sum())
            rv.append({"ul": ul, "ctx_t1": f"k={k}" + (" (D0)" if k == 0 else ""), "n": int(s["rev"].notna().sum()),
                       "rev_rate": r, "ci_lo": lo, "ci_hi": hi, "base": D["rev"].mean()})
        s = D[D["dplus1"]]
        r, lo, hi = wilson(s["rev"].sum(), s["rev"].notna().sum())
        rv.append({"ul": ul, "ctx_t1": "D+1", "n": int(s["rev"].notna().sum()), "rev_rate": r, "ci_lo": lo,
                   "ci_hi": hi, "base": D["rev"].mean()})
        for thr in [0.5, 1.0]:
            for nm, s in [("all", D), ("t+1 = D0", D[D["d0"]]), ("t+1 = D-1", D[D["k"] == 1]),
                          ("t+1 = D+1", D[D["dplus1"]])]:
                s = s[s["o_gap_pct"].abs() >= thr]
                r, lo, hi = wilson(s["rev"].sum(), s["rev"].notna().sum())
                rv.append({"ul": ul, "ctx_t1": f"|gap t| >= {thr}, {nm}", "n": int(s["rev"].notna().sum()),
                           "rev_rate": r, "ci_lo": lo, "ci_hi": hi, "base": D["rev"].mean()})
        # streaks
        for sv in [-4, -3, -2, -1, 0, 1, 2, 3, 4]:
            s = D[np.clip(D["g_streak"], -4, 4) == sv]
            st.append({"ul": ul, "streak_t (capped +-4)": sv, "n": len(s), "next_gap_up": s["y_up"].mean(),
                       "next_gap_down": s["y_down"].mean(), "next_oc_pos": s["y_oc_pos"].mean(),
                       "next_cc_pos": s["y_cc_pos"].mean(), "mean_next_gap": s["y_gap_pct"].mean(),
                       "thin": len(s) < 30})
        # close position quintiles
        q = pd.cut(D["f_close_pos"], [-0.01, 0.2, 0.4, 0.6, 0.8, 1.01], labels=["0-0.2", "0.2-0.4", "0.4-0.6",
                                                                               "0.6-0.8", "0.8-1"])
        for b, s in D.groupby(q, observed=True):
            cp.append({"ul": ul, "close_pos_t": b, "n": len(s), "next_gap_up": s["y_up"].mean(),
                       "next_gap_down": s["y_down"].mean(), "mean_next_gap": s["y_gap_pct"].mean(),
                       "next_oc_pos": s["y_oc_pos"].mean()})
        # fill conditions table
        for nm, lo_, hi_ in [("0.1-0.3", 0.1, 0.3), ("0.3-0.5", 0.3, 0.5), ("0.5-1.0", 0.5, 1.0), (">=1.0", 1.0, 99)]:
            s = D[(D["y_abs_gap"] >= lo_) & (D["y_abs_gap"] < hi_)]
            row = {"ul": ul, "abs_gap": nm, "n": len(s), "fill_all": s["y_fill"].mean(),
                   "fill_up": s.loc[s["y_sgn"] > 0, "y_fill"].mean(), "fill_down": s.loc[s["y_sgn"] < 0, "y_fill"].mean()}
            for v in [1, 2, 3]:
                row[f"fill_vix_t{v}"] = s.loc[s["vix_t"] == v, "y_fill"].mean()
            row["fill_D0"] = s.loc[s["d0"], "y_fill"].mean()
            row["n_D0"] = int(s["d0"].sum())
            row["fill_Dm1"] = s.loc[s["k"] == 1, "y_fill"].mean()
            row["fill_Dp1"] = s.loc[s["dplus1"], "y_fill"].mean()
            row["fill_with_trend5"] = s.loc[s["y_sgn"] == s["mom5_sgn"], "y_fill"].mean()
            row["fill_against_trend5"] = s.loc[s["y_sgn"] == -s["mom5_sgn"], "y_fill"].mean()
            fc.append(row)
        # hypotheses
        for sp in specs_for(ul):
            r = evaluate(sp, D)
            hyp.append({"id": sp["id"], "ul": ul, "group": sp["group"], "rule": sp["rule"], "prm": sp["prm"],
                        "decision_time": sp["dt"], "target": sp["target"], "kind": sp["kind"],
                        "minute": sp["minute"], **{f"d_{k}": v for k, v in r.items()}})
    H = pd.DataFrame(hyp)
    H["d_thin"] = (H["d_n"] < 30) | ((H["kind"].isin(["rate_2g", "mean_2g"])) & (H["d_nB"] < 30))
    q, rej = bh(H["d_p"].values, 0.10)
    H["d_q"] = q
    H["d_bh_sig"] = rej
    H.to_csv(RES / "hypotheses.csv", index=False)
    pd.DataFrame(tr).to_csv(RES / "transitions.csv", index=False)
    pd.DataFrame(bt).to_csv(RES / "gap_buckets.csv", index=False)
    pd.DataFrame(rv).to_csv(RES / "reversal_by_context.csv", index=False)
    pd.DataFrame(st).to_csv(RES / "streaks.csv", index=False)
    pd.DataFrame(cp).to_csv(RES / "close_pos.csv", index=False)
    pd.DataFrame(fc).to_csv(RES / "fill_conditions.csv", index=False)
    print(f"family size {len(H)} tests ({H['d_p'].notna().sum()} with a p-value); BH-significant at 10 %: "
          f"{int(H['d_bh_sig'].sum())}; thin (n < 30): {int(H['d_thin'].sum())}")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 70)
    cols = ["id", "rule", "d_n", "d_nB", "d_rate", "d_base", "d_effect", "d_p", "d_q"]
    print(H.loc[H["d_bh_sig"], cols].to_string(index=False))


if __name__ == "__main__":
    main()
