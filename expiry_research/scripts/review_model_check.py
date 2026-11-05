"""Agent 5b review of module `model` (design: reports/lld/review_model.md). Independent rebuild from load_panel."""
import hashlib
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from panel_io import load_panel  # noqa: E402
from stats_utils import binom_p, wilson  # noqa: E402

ROOT = HERE.parent
M = ROOT / "results" / "model"
OUT = ROOT / "results" / "review_model"
OUT.mkdir(parents=True, exist_ok=True)
BIN = {"gap_up", "ret15_up", "ret30_up", "ret60_up", "oc_up", "gap_filled", "big_exc", "big_cc"}
O_EARLY = {"o_gap_pct", "d_absgap", "o_ret15", "o_ret30", "o_ret60"}
VIXC = {"TCLOSE": "f_vix_close", "D2": "l1_f_vix_close", "T1515": "f1515_vix_1514"}
ELECTION = ("2024-06-03", "2024-06-07")


def regime(ul, d):
    if ul == "NIFTY":
        return "2018 monthly-only" if d < "2019-02-14" else "Thu weekly"
    return "Thu" if d <= "2023-09-01" else ("Wed weekly + Thu monthly" if d <= "2024-02-29" else "Wed")


def panel(ul):
    P = load_panel(ul).sort_values("date").reset_index(drop=True)
    P["d_absgap"] = P["o_gap_pct"].abs()
    P["d_absmom1"] = P["f_mom1"].abs()
    tot = P["f_opt_near_ce_oi"] + P["f_opt_near_pe_oi"]
    P["d_opt_near_netoichg"] = (P["f_opt_near_pe_oi_chg"] - P["f_opt_near_ce_oi_chg"]) / tot.where(tot > 0)
    P["d_opt_near_straddle_daily"] = P["f_opt_near_straddle_pct"] / np.sqrt(np.maximum(P["f_opt_near_dte"], 1))
    P["d_opt_near_atmvol_ratio"] = P["f_opt_near_atm_pe_vol"] / P["f_opt_near_atm_ce_vol"].where(
        P["f_opt_near_atm_ce_vol"] > 0)
    for c in ["o_gap_filled", "f_opt_near_is_monthly"]:
        P[c] = P[c].map({True: 1.0, False: 0.0, 1: 1.0, 0: 0.0}).astype(float)
    # lag check: previous row's y_date must equal this row's date
    P["lag_ok"] = (P["y_date"].shift(1).astype("string").str[:10] == P["date"].astype("string").str[:10]).fillna(False)
    g = P["y_gap_pct"]
    T = pd.DataFrame(index=P.index)
    T["gap_up"] = (g > 0).astype(float).where(g.notna() & (g != 0))
    for k in ["15", "30", "60"]:
        T[f"ret{k}_up"] = (P[f"y_ret{k}"] > 0).astype(float).where(P[f"y_ret{k}"].notna())
    T["oc_up"] = (P["y_oc"] > 0).astype(float).where(P["y_oc"].notna())
    T["gap_filled"] = P["y_gap_filled"].map({True: 1.0, False: 0.0}).astype(float)
    T["big_exc"] = (P["y_max_exc"] >= 1).astype(float).where(P["y_max_exc"].notna())
    T["big_cc"] = (P["y_cc"].abs() >= 1).astype(float).where(P["y_cc"].notna())
    T["gap_abs"] = g.abs()
    T["high_pc"] = P["y_high_vs_prevclose"]
    T["low_pc"] = P["y_low_vs_prevclose"]
    T["abs_cc"] = P["y_cc"].abs()
    T["cc"] = P["y_cc"]
    T["max_exc"] = P["y_max_exc"]
    P = pd.concat([P, T.add_prefix("t_")], axis=1)
    P["sdate"] = P["y_date"].astype("string").str[:10]
    P["keep"] = (P["sdate"].notna() & (P["sdate"] < "2024-07-01")
                 & (P["cal_special_between"] != True)).fillna(False).astype(bool)  # noqa: E712
    sd = P["sdate"].fillna("9999")
    P["split"] = np.where(sd <= "2022-12-31", "discovery", np.where(sd <= "2024-06-30", "validation", "none"))
    P["year"] = P["sdate"].fillna("0000").str[:4]
    P["regime"] = [regime(ul, d) if isinstance(d, str) else "" for d in P["sdate"].fillna("")]
    return P


def col(P, name, cut):
    """Feature value aligned to the decision row of target s; checks availability at the cutoff."""
    if name.startswith("l1_"):
        return P[name[3:]].shift(1).where(P["lag_ok"]), "ok"
    if cut == "D2":
        return P[name], "LEAK: non-lagged feature at D2"
    if cut == "T1515" and not (name.startswith("f1515_") or name in O_EARLY):
        return P[name], "LEAK: TCLOSE feature at T1515"
    return P[name], "ok"


def apply(P, rule, cut):
    m = pd.Series(True, index=P.index)
    pres = pd.Series(True, index=P.index)
    flags = []
    for c in rule:
        x, f = col(P, c["f"], cut)
        flags.append(f)
        pres &= x.notna()
        ops = {"<=": x <= c["v"], ">=": x >= c["v"], "<": x < c["v"], ">": x > c["v"], "==": x == c["v"]}
        m &= ops[c["op"]]
    return (m & pres).fillna(False), pres, flags


def ctxmask(P, ctx):
    ie = P["cal_next_is_expiry"].fillna(False).astype(bool)
    if ctx == "all":
        return pd.Series(True, index=P.index)
    if ctx == "D0":
        return ie
    if ctx == "D0m":
        return ie & (P["cal_next_kind"] == "monthly")
    raise ValueError(ctx)


def frame_mask(P, cut):
    k = P["keep"].copy()
    if cut == "T1515":
        k &= P["f1515_ret_to_1514"].notna()
    return k


def stat(y, cond, base, binary, alt=None):
    yc, yb = y[cond].values, y[base].values
    n = len(yc)
    if n == 0 or len(yb) == 0:
        return dict(n=n, rate=np.nan, base=np.nan, eff=np.nan, p=np.nan)
    b = float(yb.mean())
    r = float(yc.mean())
    if binary:
        if not 0 < b < 1:
            p = np.nan
        elif alt is None:
            p = binom_p(int(yc.sum()), n, b)
        else:
            p = float(stats.binomtest(int(yc.sum()), n, b, alternative=alt).pvalue)
    else:
        p = float(stats.ttest_1samp(yc, b, alternative=alt or "two-sided").pvalue) if n >= 3 else np.nan
    return dict(n=n, rate=r, base=b, eff=r - b, p=p)


def shift_perm(y, cond, base, sign, minshift=20):
    """Circular-shift p: rule mask shifted against outcomes within the base rows (keeps autocorrelation)."""
    yb = y[base].values.astype(float)
    cb = cond[base].values.astype(bool)
    n = len(yb)
    if cb.sum() == 0 or n < 3 * minshift:
        return np.nan
    obs = yb[cb].mean() - yb.mean()
    sims = np.array([yb[np.roll(cb, k)].mean() - yb.mean() for k in range(minshift, n - minshift)])
    return float(((sims * sign) >= obs * sign - 1e-12).mean())


def main():
    C = pd.read_csv(M / "candidates_frozen.csv")
    V = pd.read_csv(M / "candidates_validation.csv")
    log = []
    sha = hashlib.sha256((M / "candidates_frozen.csv").read_bytes()).hexdigest()
    rec = (M / "candidates_frozen.sha256").read_text().strip()
    tf = (M / "candidates_frozen.csv").stat().st_mtime
    tv = (M / "candidates_validation.csv").stat().st_mtime
    log.append(dict(check="frozen sha256 matches record", value=sha == rec, detail=sha))
    log.append(dict(check="frozen mtime < validation mtime (s)", value=tf < tv, detail=round(tv - tf, 1)))
    log.append(dict(check="validation ids == frozen ids", value=set(C.cid) == set(V.cid), detail=len(C)))
    same_rules = (C.set_index("cid")["rule_json"] == V.set_index("cid")["rule_json"]).all()
    log.append(dict(check="validation rule_json == frozen rule_json", value=bool(same_rules), detail=""))
    sgn = np.sign(V.val_effect) == np.sign(V.disc_effect)
    half = V.val_effect.abs() >= 0.5 * V.disc_effect.abs()
    pr = (V.val_n >= 20) & sgn & (V.val_p_one_sided < 0.05) & half
    log.append(dict(check="pass rule reapplied == their val_pass", value=bool((pr == V.val_pass).all()),
                    detail=int(pr.sum())))
    H = pd.read_csv(M / "hypotheses.csv", usecols=["stage", "p"])
    log.append(dict(check="hypotheses.csv rows with p", value=int(H.p.notna().sum()),
                    detail=str(H.groupby("stage").p.count().to_dict())))

    PAN = {ul: panel(ul) for ul in ["NIFTY", "BANKNIFTY"]}
    for ul, P in PAN.items():
        k = P["keep"]
        log.append(dict(check=f"{ul} kept rows whose previous panel row is not the previous session",
                        value=int((~P.loc[k, "lag_ok"]).sum()), detail=""))
        ie = P["cal_next_is_expiry"].fillna(False).astype(bool) & k
        t_is_exp = P["cal_is_expiry"].fillna(False).astype(bool)
        lag_near = P["f_opt_near_expiry"].shift(1).astype("string").str[:10]
        chk = ie & ~t_is_exp
        miss = chk & (lag_near != P["sdate"])
        log.append(dict(check=f"{ul} D0 rows (t not expiry) where s was NOT the near expiry in bhavcopy of t-1",
                        value=int(miss.sum()), detail=f"of {int(chk.sum())}; {list(P.loc[miss, 'sdate'][:8])}"))

    keep_ids = V[V.label.isin(["Passed-validation", "Suggestive"])].cid.tolist()
    rows = []
    for cid in keep_ids:
        c = V[V.cid == cid].iloc[0]
        P = PAN[c["ul"]]
        cut = "TCLOSE" if c["cutoff"] == "CAL" else c["cutoff"]
        rule = json.loads(c["rule_json"])
        tg = c["target"]
        binary = tg in BIN
        y = P["t_" + tg]
        cond, pres, flags = apply(P, rule, cut)
        fm = (frame_mask(P, cut) & y.notna() & ctxmask(P, c["context"]) & pres).fillna(False)
        cond = cond & fm
        sign = 1 if c["direction"] == "higher" else -1
        alt = "greater" if sign > 0 else "less"
        r = dict(cid=cid, ul=c["ul"], cutoff=cut, target=tg, context=c["context"], rule=c["rule"],
                 label=c["label"], leak_flags=";".join(sorted(set(flags))) or "ok")
        for sp, pre in [("discovery", "d"), ("validation", "v")]:
            s = P["split"] == sp
            st = stat(y, cond & s, fm & s, binary, None if sp == "discovery" else alt)
            r.update({f"{pre}_{k}": v for k, v in st.items()})
        r["their_d_n"], r["their_d_eff"] = c["disc_n"], c["disc_effect"]
        r["their_v_n"], r["their_v_eff"], r["their_v_p"] = c["val_n"], c["val_effect"], c["val_p_one_sided"]
        r["match"] = bool((r["d_n"] == c["disc_n"]) and (r["v_n"] == c["val_n"])
                          and abs(r["d_eff"] - c["disc_effect"]) < 1e-6
                          and (r["v_n"] == 0 or abs(r["v_eff"] - c["val_effect"]) < 1e-6))
        vs = P["split"] == "validation"
        ds = P["split"] == "discovery"
        hits = P.loc[cond & vs, "sdate"]
        r["v_hit_months"] = hits.str[:7].nunique()
        r["v_hit_span"] = f"{hits.min()}..{hits.max()}" if len(hits) else ""
        r["v_hit_months_list"] = ",".join(sorted(hits.str[:7].unique()))
        r["v_shift_p"] = shift_perm(y[vs], cond[vs], fm[vs], sign) if r["v_n"] >= 5 else np.nan
        r["d_shift_p"] = shift_perm(y[ds], cond[ds], fm[ds], sign)
        ne = ~P["sdate"].fillna("").between(*ELECTION)
        st = stat(y, cond & vs & ne, fm & vs & ne, binary, alt)
        r["v_noelec_n"], r["v_noelec_eff"], r["v_noelec_p"] = st["n"], st["eff"], st["p"]
        src = {"big_exc": "t_max_exc", "big_cc": "t_abs_cc", "gap_up": "t_gap_abs"}.get(tg, "t_" + tg)
        A = ds | vs
        ca = cond & A
        r["dv_eff"] = stat(y, ca, fm & A, binary)["eff"]
        if tg != "gap_filled" and ca.sum() > 1:
            nd = max(1, math.ceil(0.01 * ca.sum()))
            idx = P.loc[ca, src].sort_values(ascending=(sign < 0)).index[:nd]
            c2 = ca.copy()
            c2.loc[idx] = False
            r["dv_drop1_eff"] = stat(y, c2, fm & A, binary)["eff"]
        if r["v_n"] >= 2 and tg != "gap_filled":
            cv = cond & vs
            i1 = P.loc[cv, src].sort_values(ascending=(sign < 0)).index[:1]
            cv2 = cv.copy()
            cv2.loc[i1] = False
            st = stat(y, cv2, fm & vs, binary, alt)
            r["v_drop_top1_eff"], r["v_drop_top1_p"] = st["eff"], st["p"]
        for yv in ["2023", "2024"]:
            s = vs & (P["year"] == yv)
            st = stat(y, cond & s, fm & s, binary)
            r[f"v{yv}_n"], r[f"v{yv}_eff"] = st["n"], st["eff"]
        regs = []
        for rg in sorted(P.loc[A & fm, "regime"].unique()):
            s = A & (P["regime"] == rg)
            st = stat(y, cond & s, fm & s, binary)
            regs.append(f"{rg}: n{st['n']} {st['eff']:+.3f}")
        r["dv_regimes"] = " | ".join(regs)
        vx, _ = col(P, VIXC[cut], cut)
        fd = fm & ds & vx.notna()
        fr = cond[fd].mean()
        best = None
        for side in ("hi", "lo"):
            q = vx[fd].quantile(1 - fr) if side == "hi" else vx[fd].quantile(fr)
            tw = ((vx >= q) if side == "hi" else (vx <= q)).fillna(False)
            e = stat(y, tw & fd, fd, binary)["eff"]
            if np.sign(e) == sign and (best is None or abs(e) > abs(best[2])):
                best = (side, q, e, tw)
        if best:
            side, q, e, tw = best
            fv = fm & vs & vx.notna()
            st = stat(y, tw & fv, fv, binary, alt)
            r["vix_twin"] = f"{VIXC[cut]} {'>=' if side == 'hi' else '<='} {q:.2f}"
            r["twin_d_eff"], r["twin_v_n"], r["twin_v_eff"], r["twin_v_p"] = e, st["n"], st["eff"], st["p"]
            inside = fm & A & tw & vx.notna()
            st2 = stat(y, cond & inside, inside, binary)
            r["rule_within_twin_n"], r["rule_within_twin_eff"], r["rule_within_twin_p"] = st2["n"], st2["eff"], st2["p"]
            outside = fm & A & ~tw & vx.notna()
            st3 = stat(y, cond & outside, outside, binary)
            r["rule_outside_twin_n"], r["rule_outside_twin_eff"], r["rule_outside_twin_p"] = (
                st3["n"], st3["eff"], st3["p"])
        if tg in ("low_pc", "high_pc"):
            for other in ["high_pc", "low_pc", "cc", "abs_cc", "max_exc"]:
                yo = P["t_" + other]
                for sp, pre in [(ds, "d"), (vs, "v")]:
                    st = stat(yo, cond & sp & yo.notna(), fm & sp & yo.notna(), False)
                    r[f"{pre}_{other}_eff"] = st["eff"]
                    r[f"{pre}_{other}_p"] = st["p"]
        rows.append(r)
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "recompute.csv", index=False)

    # components of M218 (NIFTY TCLOSE low_pc): calm only, PCR only, PCR within calm / non-calm
    P = PAN["NIFTY"]
    comp = []
    sdn = P["d_opt_near_straddle_daily"]
    pcr = P["f_opt_near_pcr_oi"]
    calm = sdn <= 0.6675
    hp = pcr > 1.006
    for sp in ["discovery", "validation"]:
        s0 = P["keep"] & (P["split"] == sp) & sdn.notna() & pcr.notna()
        parts = [("calm only", s0 & calm, s0), ("pcr only", s0 & hp, s0), ("M218 both", s0 & calm & hp, s0),
                 ("pcr within calm", s0 & calm & hp, s0 & calm), ("pcr within non-calm", s0 & ~calm & hp, s0 & ~calm)]
        for name, cnd, bse in parts:
            for other in ["low_pc", "high_pc", "cc", "max_exc"]:
                yo = P["t_" + other]
                st = stat(yo, cnd & yo.notna(), bse & yo.notna(), False)
                comp.append(dict(split=sp, component=name, target=other, n=st["n"], mean=st["rate"],
                                 base=st["base"], eff=st["eff"], p=st["p"]))
    pd.DataFrame(comp).to_csv(OUT / "m218_components.csv", index=False)

    # spot checks: CTX-D0 discovery and two Rejected direction rules
    sp_rows = []
    for ul, P in PAN.items():
        k = P["keep"] & (P["split"] == "discovery")
        ie = P["cal_next_is_expiry"]
        iex = ie.fillna(False).astype(bool)
        for tg in ["big_exc", "gap_up", "oc_up", "gap_abs"]:
            y = P["t_" + tg]
            b = k & y.notna() & ie.notna()
            st = stat(y, b & iex, b & ~iex, tg in BIN)
            if tg in BIN:
                st2 = stat(y, b & ~iex, b & ~iex, True)
                # two-sample comparison D0 vs non-expiry
                from stats_utils import two_prop
                tp = two_prop(int(y[b & iex].sum()), int((b & iex).sum()), int(y[b & ~iex].sum()),
                              int((b & ~iex).sum()))
            else:
                tp = stats.ttest_ind(y[b & iex], y[b & ~iex], equal_var=False).pvalue
            sp_rows.append(dict(check="CTX-D0 D0 vs non-expiry (discovery)", ul=ul, target=tg, n=st["n"],
                                value=st["rate"], base=st["base"], eff=st["eff"], p_two_sample=str(tp)))
    rej = V[(V.label == "Rejected") & V.target.isin(["gap_up", "oc_up"]) & (V.stage != "context")]
    rej = rej.sort_values("disc_p").head(2)
    for _, c in rej.iterrows():
        P = PAN[c["ul"]]
        cut = c["cutoff"]
        y = P["t_" + c["target"]]
        cond, pres, _ = apply(P, json.loads(c["rule_json"]), cut)
        fm = (frame_mask(P, cut) & y.notna() & ctxmask(P, c["context"]) & pres).fillna(False)
        alt = "greater" if c["direction"] == "higher" else "less"
        for sp in ["discovery", "validation"]:
            s = P["split"] == sp
            st = stat(y, cond & fm & s, fm & s, True, None if sp == "discovery" else alt)
            sp_rows.append(dict(check=f"Rejected {c['cid']} {c['rule']} [{c['context']},{cut}]", ul=c["ul"],
                                target=c["target"], split=sp, n=st["n"], value=st["rate"], base=st["base"],
                                eff=st["eff"], p_two_sample=str(st["p"]),
                                theirs=f"disc n{c['disc_n']} eff{c['disc_effect']:.3f}; "
                                       f"val n{c['val_n']} eff{c['val_effect']:.3f} p{c['val_p_one_sided']:.3f}"))
    pd.DataFrame(sp_rows).to_csv(OUT / "spot_checks.csv", index=False)

    # BH within the validation family only (testable candidates, n >= 20), vs the whole-log BH they report
    from stats_utils import bh
    T = V[V.val_n >= 20].copy()
    q, rej = bh(T.val_p_one_sided.fillna(1).values, 0.10)
    T["q_bh_validation_family"] = q
    T["bonferroni_sig"] = T.val_p_one_sided < 0.05 / len(T)
    T["election_week_hits"] = [int(R.loc[R.cid == c, "v_n"].iloc[0] - R.loc[R.cid == c, "v_noelec_n"].iloc[0])
                               if c in set(R.cid) else np.nan for c in T.cid]
    T[["cid", "ul", "target", "val_n", "val_effect", "disc_effect", "val_p_one_sided", "q_bh_validation_family",
       "bonferroni_sig", "election_week_hits", "label"]].sort_values("val_p_one_sided").to_csv(
        OUT / "validation_family_bh.csv", index=False)
    log.append(dict(check="validation family (n>=20) size / BH10 sig / Bonferroni sig / null-expected passes",
                    value=len(T), detail=f"{int(rej.sum())} / {int(T.bonferroni_sig.sum())} / {0.05 * len(T):.1f}"))
    pd.DataFrame(log).to_csv(OUT / "checks.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_colwidth", 120)
    print(pd.DataFrame(log).to_string())
    print(R["match"].value_counts().to_string())
    print(R["leak_flags"].value_counts().to_string())


if __name__ == "__main__":
    main()
