"""Gaps module: Section 2 descriptive tables, behaviour by expiry type (discovery rows only).

Run after gaps_discovery.py (uses results/gaps/prepared_<UL>.parquet).
Writes results/gaps/{behaviour_by_context.csv, behaviour_by_regime.csv, extreme_time_hist.csv,
minute_coverage.csv, per_expiry_D0.csv}.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gaps_common import RES  # noqa: E402
from gaps_specs import BEH  # noqa: E402
from stats_utils import mean_ci, wilson  # noqa: E402

ULS = ["NIFTY", "BANKNIFTY"]


def ctx_label(r):
    if r["d0"]:
        return "D0 " + str(r["kind_ctx"])
    if r["k"] == 1:
        return "D-1"
    if r["dplus1"]:
        return "D+1"
    if r["k"] == 2:
        return "D-2"
    if r["k"] == 3:
        return "D-3"
    return "other (D-4.., not D+1)"


def summarise(s, ul, slice_, ctx):
    row = {"ul": ul, "slice": slice_, "ctx_t1": ctx, "n": len(s)}
    for col, kind, lab, minute in BEH:
        x = s[col].astype(float)
        if kind == "mean":
            m, lo, hi = mean_ci(x)
        else:
            m, lo, hi = wilson(x.sum(), x.notna().sum())
        row[col] = m
        row[col + "_lo"] = lo
        row[col + "_hi"] = hi
        if minute:
            row["n_minute"] = int(x.notna().sum())
    return row


def main():
    bc, br, eh, mc, pe = [], [], [], [], []
    for ul in ULS:
        P = pd.read_parquet(RES / f"prepared_{ul}.parquet")
        P["ctx"] = P.apply(ctx_label, axis=1)
        P["ctx2"] = np.where(P["d0"], "D0", P["ctx"])
        D = P[P["split"] == "discovery"]
        for c, s in D.groupby("ctx"):
            bc.append(summarise(s, ul, "discovery", c))
        for c, s in D.groupby("ctx2"):
            if c == "D0":
                bc.append(summarise(s, ul, "discovery", "D0 all"))
        o = D[~D["d0"] & (D["k"] != 1) & ~D["dplus1"]]
        bc.append(summarise(o, ul, "discovery", "ordinary (not D0/D-1/D+1)"))
        bc.append(summarise(D, ul, "discovery", "all sessions"))
        for (rg, c), s in D.groupby(["regime", "ctx2"]):
            br.append(summarise(s, ul, rg, c))
        for (dw, e), s in D.groupby(["cal_next_dow", "d0"]):
            br.append(summarise(s, ul, "by weekday of t+1", f"{dw} {'expiry' if e else 'non-expiry'}"))
        # extreme time histogram (minute days)
        M = D[D["y_high_min"].notna()]
        bins = [0, 30, 60, 120, 180, 240, 315, 376]
        lab = ["09:15-09:44", "09:45-10:14", "10:15-11:14", "11:15-12:14", "12:15-13:14", "13:15-14:29",
               "14:30-15:29"]
        for c, s in M.groupby("ctx2"):
            for what in ["y_high_min", "y_low_min"]:
                h = pd.cut(s[what], bins, right=False, labels=lab).value_counts(normalize=True).reindex(lab)
                eh.append({"ul": ul, "ctx_t1": c, "what": what, "n": len(s), **h.to_dict()})
        # minute coverage
        for sp in ["discovery", "validation"]:
            s = P[P["split"] == sp]
            mm = s["y_src"].eq("spot_1m")
            mc.append({"ul": ul, "split": sp, "rows": len(s), "minute_t1_rows": int(mm.sum()),
                       "first_minute_t1": s.loc[mm, "y_date"].min(), "D0_rows": int(s["d0"].sum()),
                       "D0_minute": int((s["d0"] & mm).sum()),
                       "D0_minute_gap>=0.3": int((s["d0"] & mm & (s["y_abs_gap"] >= 0.3)).sum()),
                       "D0_minute_gap>=0.5": int((s["d0"] & mm & (s["y_abs_gap"] >= 0.5)).sum()),
                       "D0_monthly_minute": int((s["d0"] & mm & (s["kind_ctx"] == "monthly")).sum())})
        # per-expiry rows (discovery and validation; validation columns are labels, no statistic here)
        E = P[P["d0"]][["ul", "split", "y_date", "kind_ctx", "regime", "cal_next_dow", "o_gap_dir", "y_gap_pct",
                        "y_bucket", "y_oc", "y_cc", "y_range_pct", "y_gap_filled", "y_gap_fill_min", "y_cont",
                        "y_soc", "se_ret15", "se_ret30", "se_ret60", "se_oc", "e_fill", "y_rv", "y_high_min",
                        "y_low_min", "f_vix_close", "vix_t"]]
        pe.append(E.rename(columns={"y_date": "expiry_date"}))
    pd.DataFrame(bc).to_csv(RES / "behaviour_by_context.csv", index=False)
    pd.DataFrame(br).to_csv(RES / "behaviour_by_regime.csv", index=False)
    pd.DataFrame(eh).to_csv(RES / "extreme_time_hist.csv", index=False)
    pd.DataFrame(mc).to_csv(RES / "minute_coverage.csv", index=False)
    pd.concat(pe).to_csv(RES / "per_expiry_D0.csv", index=False)
    pd.set_option("display.width", 250)
    B = pd.DataFrame(bc)
    print(B[["ul", "ctx_t1", "n", "y_range_pct", "y_abs_cc", "y_abs_oc", "y_abs_gap", "y_bigexc", "y_bigcc",
             "n_minute", "y_rv", "y_high_min", "y_low_min", "y_ext_last_hr"]].round(3).to_string(index=False))
    print(pd.DataFrame(mc).to_string(index=False))


if __name__ == "__main__":
    main()
