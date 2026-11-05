"""Coordinator's single final out-of-sample test (design: reports/lld/final.md; plan: FINAL_TEST_PLAN.md).

The only script that opens data/sealed/ (panel_io.load_sealed_final(ul, coordinator=True)). Features are rebuilt
with each module's own code; a code-path proof on the validation split runs first and stops the script on any
mismatch, before a final-period statistic is computed.
Run (Git Bash, from the repo root):
  INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe expiry_research/scripts/final_test.py
"""
import hashlib
import inspect
import json
import math
import sys
import textwrap
import warnings
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
warnings.simplefilter("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402
from sklearn.linear_model import LinearRegression, LogisticRegression  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

import panel_io  # noqa: E402
import stats_utils as su  # noqa: E402
import pricepath_common as ppc  # noqa: E402
import pricepath_validate as ppv  # noqa: E402
import optionchain_common as occ  # noqa: E402
import optionchain_features as ocf  # noqa: E402
import optionchain_validation as ocv  # noqa: E402
import model_common as mc  # noqa: E402
import model_validate as mv  # noqa: E402
import bias_common as bc  # noqa: E402
import bias_discovery as bd  # noqa: E402

ROOT = HERE.parent
RES = ROOT / "results"
OUT = RES / "final"
OUT.mkdir(parents=True, exist_ok=True)
FINAL_START = panel_io.FINAL_START
BIG = pd.Timestamp("2099-12-31")
PP_IDS = ["PPC032", "PPC062", "PPC092", "PPC098", "PPC129"]
OC_IDS = ["OC08", "OC13", "OC17", "OC21", "OC118"]
M_IDS = ["M143", "M218", "M220"]
ORDER = PP_IDS + OC_IDS + M_IDS
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append(dict(check=name, ok=bool(ok), detail=str(detail)))
    print(f"  [{'ok' if ok else 'FAIL'}] {name} {detail}")


def patched(func, edits, glb):
    """Re-define func from its own source with literal edits and overridden globals (same code otherwise)."""
    src = textwrap.dedent(inspect.getsource(func))
    for a, b in edits:
        assert src.count(a) >= 1, f"edit target not found in {func.__name__}: {a}"
        src = src.replace(a, b)
    g = dict(func.__globals__)
    g.update(glb)
    exec(compile(src, f"<patched {func.__name__}>", "exec"), g)
    return g[func.__name__]


def same(a, b):
    """Exact equality of two series (NaN == NaN); returns (ok, n, n_diff, max_abs_diff)."""
    a = pd.Series(a).reset_index(drop=True)
    b = pd.Series(b).reset_index(drop=True)
    if len(a) != len(b):
        return False, len(a), -1, np.nan
    an, bn = a.isna(), b.isna()
    try:
        af, bf = a.astype(float), b.astype(float)
        eq = (af == bf) | (an & bn)
        md = float((af - bf).abs().max()) if (~(an | bn)).any() else 0.0
    except (TypeError, ValueError):
        eq = (a.astype(str) == b.astype(str)) | (an & bn)
        md = np.nan
    return bool(eq.all()), len(a), int((~eq).sum()), md


# ------------------------------------------------------------------ panels (the one opening of the seal)
def combined(ul):
    O = panel_io.load_panel(ul)
    S = panel_io.load_sealed_final(ul, coordinator=True)
    assert list(O.columns) == list(S.columns), "open and sealed columns differ"
    O = O[O["date"] < S["date"].min()]
    for c in S.columns:  # keep the open file's dtypes where they differ only by nullability
        if O[c].dtype != S[c].dtype:
            try:
                S[c] = S[c].astype(O[c].dtype)
            except (TypeError, ValueError):
                pass
    C = pd.concat([O, S], ignore_index=True).sort_values("date").reset_index(drop=True)
    assert C["date"].is_unique
    print(f"{ul}: open rows {len(O)}, sealed rows {len(S)} ({S['date'].min()} .. {S['date'].max()}), "
          f"sealed split values {S['split'].value_counts().to_dict()}")
    return C


# ------------------------------------------------------------------ module frames
def pp_frame(ul, P):
    return ppc.build_features(ul, P)


def oc_frame(ul, COMB):
    load_raw = patched(ocf.load_raw, [('f.stem <= "2024-06"', 'f.stem <= "2099-12"')], {"CUTOFF": BIG})
    build = patched(ocf.build, [], {"load_panel": lambda u: COMB[u].copy(), "load_raw": load_raw, "CUTOFF": BIG})
    F, _ = build(ul)
    F["date"] = pd.to_datetime(F["date"])
    return F.sort_values("date").reset_index(drop=True)


def oc_context(F, ul):
    cf = patched(occ.context_frame,
                 [('tsplit = np.where(F["target_date"] < pd.Timestamp("2023-01-01"), "discovery", "validation")',
                   'tsplit = np.where(F["target_date"] < pd.Timestamp("2023-01-01"), "discovery", '
                   'np.where(F["target_date"] < pd.Timestamp("2024-07-01"), "validation", "final"))')],
                 {"CUTOFF": BIG})
    return cf(F, ul, "ALL")


def m_frame(ul, COMB):
    bf = patched(mc.build_frame,
                 [('< "2024-07-01"', '< "2099-01-01"'),
                  ('    assert not (F["split"] == "final").any()\n', '')],
                 {"load_panel": lambda u: COMB[u].copy()})
    return bf(ul, "TCLOSE")


# ------------------------------------------------------------------ per-candidate row tables
def from_open(g, h, lo):
    o = 1 + g / 100
    hfo = ((1 + h / 100) / o - 1) * 100
    lfo = ((1 + lo / 100) / o - 1) * 100
    return hfo, lfo


def pp_rows(P, c, split_mask):
    """Base rows of a pricepath rule (module's own rate_test rows) with flag, target, VIX, from-open target."""
    r, rows, sig = ppv.eval_rule(P, c, split_mask)
    y = P.loc[rows, c["target"]]
    idx = y[y.notna()].index
    T = P.loc[idx, ["date", "y_date", "f_vix_close"]].copy()
    cond = json.loads(c["cond_json"])
    T["feature"] = P.loc[idx, cond[0][0]]
    T["flag"] = sig.loc[idx].astype(bool)
    T["y"] = P.loc[idx, c["target"]].astype(float)
    hfo, lfo = from_open(P.loc[idx, "y_gap_pct"], P.loc[idx, "y_high_vs_prevclose"], P.loc[idx, "y_low_vs_prevclose"])
    T["y_open"] = (np.maximum(hfo, -lfo) >= 1).astype(float).where(hfo.notna() & lfo.notna())
    return T.reset_index(drop=True), r


def oc_rows(C, c, thr, med):
    y, v = occ.binary_target(C, c["target"], med)
    base_rows = y.notna() & C[c["signal"]].notna()
    m = occ.bucket_mask(C, c["signal"], c["bucket"], thr) & base_rows
    T = pd.DataFrame({"date": C["date"].dt.strftime("%Y-%m-%d"), "y_date": C["target_date"].dt.strftime("%Y-%m-%d"),
                      "f_vix_close": C["f_vix_close"], "feature": C[c["signal"]], "flag": m, "y": y})[base_rows]
    if c["target"] == "big_move":
        hfo, lfo = from_open(C["gap"], C["y_high_vs_prevclose"], C["y_low_vs_prevclose"])
        T["y_open"] = (np.maximum(hfo, -lfo) >= 1).astype(float).where(hfo.notna() & lfo.notna())[base_rows]
    else:  # range_big: the range has no gap in it; identical from the open
        T["y_open"] = T["y"]
    return T.reset_index(drop=True)


def m_rows(F, c):
    cond, base = mv.rows_for(F, c)
    rule = json.loads(c["rule_json"])
    T = pd.DataFrame({"date": F["date_t"], "y_date": F["target_date"], "f_vix_close": F["f_vix_close"],
                      "feature": F[rule[-1]["f"]] if len(rule) == 1 else F[rule[-1]["f"]], "flag": cond,
                      "y": F["t_" + c["target"]]})
    if len(rule) == 2:
        T["feature2"] = F[rule[0]["f"]]
    hfo, lfo = from_open(F["src_y_gap_pct"], F["src_y_high_vs_prevclose"], F["src_y_low_vs_prevclose"])
    if c["target"] == "big_exc":
        T["y_open"] = (np.maximum(hfo, -lfo) >= 1).astype(float).where(hfo.notna() & lfo.notna())
    else:  # low_pc -> low vs the t+1 open
        T["y_open"] = lfo
    return T[base].reset_index(drop=True)


# ------------------------------------------------------------------ statistics
def gate_stats(T, binary, d):
    """flagged rate / mean vs base of all rows T (module conventions), one-sided p in direction d."""
    yb, yc = T["y"].values, T.loc[T["flag"], "y"].values
    n, base = len(yc), float(np.mean(yb)) if len(yb) else np.nan
    alt = "greater" if d > 0 else "less"
    if binary:
        k = int(yc.sum())
        rate, lo, hi = su.wilson(k, n)
        p = float(stats.binomtest(k, n, base, alternative=alt).pvalue) if n and 0 < base < 1 else np.nan
    else:
        k = np.nan
        rate, lo, hi = su.mean_ci(yc)
        p = float(stats.ttest_1samp(yc, base, alternative=alt).pvalue) if n >= 3 else np.nan
    return dict(n=n, k=k, n_base=len(yb), rate=rate, ci_lo=lo, ci_hi=hi, base=base, effect=rate - base, p=p)


def open_stats(T, binary, d):
    U = T[T["y_open"].notna()].copy()
    U["y"] = U["y_open"]
    return gate_stats(U, binary, d)


def vix_gain(TR, TE, binary, d):
    """VIX-only model on discovery+validation rows TR, scored on final rows TE (model_vixbase settings)."""
    tr = TR[TR["f_vix_close"].notna()]
    x = TE[["f_vix_close"]].fillna(tr["f_vix_close"].median())
    if binary:
        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=5000))
        m.fit(tr[["f_vix_close"]], tr["y"].astype(int))
        pred = m.predict_proba(x)[:, 1]
    else:
        m = LinearRegression().fit(tr[["f_vix_close"]], tr["y"])
        pred = m.predict(x)
    res = TE["y"].values - pred
    f = TE["flag"].values
    rf, ru = res[f], res[~f]
    alt = "greater" if d > 0 else "less"
    p = float(stats.ttest_ind(rf, ru, equal_var=False, alternative=alt).pvalue) if len(rf) > 1 and len(ru) > 1 \
        else np.nan
    return dict(vix_pred_flagged=float(pred[f].mean()) if f.any() else np.nan,
                vix_pred_unflagged=float(pred[~f].mean()) if (~f).any() else np.nan,
                resid_flagged=float(rf.mean()) if len(rf) else np.nan,
                resid_unflagged=float(ru.mean()) if len(ru) else np.nan,
                resid_diff=float(rf.mean() - ru.mean()) if len(rf) and len(ru) else np.nan, vix_p=p)


# ------------------------------------------------------------------ main
def main():
    print("== opening the sealed final period (once) ==")
    COMB = {ul: combined(ul) for ul in panel_io.ULS}

    # frozen inputs
    FPP = pd.read_csv(RES / "pricepath" / "candidates_frozen.csv").set_index("id")
    FOC = pd.read_csv(RES / "optionchain" / "candidates_frozen.csv").set_index("cand")
    TH = pd.read_csv(RES / "optionchain" / "thresholds.csv")
    mfz = RES / "model" / "candidates_frozen.csv"
    msha = hashlib.sha256(mfz.read_bytes()).hexdigest()
    FM = pd.read_csv(mfz).set_index("cid")
    VPP = pd.read_csv(RES / "pricepath" / "validation.csv").set_index("id")
    VOC = pd.read_csv(RES / "optionchain" / "validation.csv").set_index("cand")
    VM = pd.read_csv(RES / "model" / "candidates_validation.csv").set_index("cid")

    print("\n== frozen files ==")
    check("model frozen sha256 equals recorded", msha == (RES / "model" / "candidates_frozen.sha256").read_text().strip(),
          msha[:16])
    for i in ORDER:
        lab = (VPP.loc[i, "label"] if i in VPP.index else
               ("Passed-validation" if VOC.loc[i, "passed"] else "x") if i in VOC.index else VM.loc[i, "label"])
        check(f"{i} passed validation in its module", lab == "Passed-validation", lab)

    # -------- rebuild with each module's code
    print("\n== rebuilding features with each module's own code ==")
    PPF = {ul: pp_frame(ul, COMB[ul]) for ul in ppc.ULS}
    OCF = {ul: oc_frame(ul, COMB) for ul in occ.ULS}
    OCC = {ul: oc_context(OCF[ul], ul) for ul in occ.ULS}
    MF = {ul: m_frame(ul, COMB) for ul in mc.ULS}

    # -------- code-path proof 1: features on validation rows
    print("\n== proof 1: rebuilt features equal the module's own values on validation rows ==")
    for ul in ppc.ULS:
        A = pp_frame(ul, panel_io.load_panel(ul))
        B = PPF[ul]
        a = A[A["split"] == "validation"].set_index("date")
        b = B.set_index("date").loc[a.index]
        for col in ["f_mom5", "f_streak_close", "o_cc", "f_fut_vol_r20", "f_vix_close", "usable", "ctx_ALL"]:
            ok, n, nd, md = same(a[col], b[col])
            check(f"pricepath {ul} {col}", ok, f"n {n} diff {nd} max {md}")
        lab = a.index[a["y_date"].fillna("9999") < FINAL_START]  # the 2024-06-28 edge label is blank in the open file
        ok, n, nd, md = same(a.loc[lab, "t_big"], b.loc[lab, "t_big"])
        check(f"pricepath {ul} t_big (labelled validation rows)", ok, f"n {n} diff {nd}")
    for ul in occ.ULS:
        S = occ.load_features(ul)
        S = S[S["split"] == "validation"].set_index("date")
        b = OCF[ul].set_index("date").loc[S.index]
        for col in ["wall_width", "wall_near", "iv_chg", "iv_proxy", "n_sess", "f_vix_close"]:
            ok, n, nd, md = same(S[col], b[col])
            check(f"optionchain {ul} {col} vs features_{ul}.parquet", ok, f"n {n} diff {nd} max {md}")
        lab = S.index[S["y_date"].fillna("9999").astype(str) < FINAL_START]  # 2024-06-28 edge label blank in open file
        for col in ["y_range_pct", "y_big_move_exc"]:
            ok, n, nd, md = same(S.loc[lab, col], b.loc[lab, col])
            check(f"optionchain {ul} {col}", ok, f"n {n} diff {nd}")
    for ul in mc.ULS:
        A = mc.build_frame(ul, "TCLOSE")
        a = A[A["split"] == "validation"].set_index("target_date")
        b = MF[ul].set_index("target_date").loc[a.index]
        for col in ["date_t", "d_opt_near_straddle_daily", "f_opt_near_pcr_oi", "f_atr14_pct", "f_vix_close",
                    "t_big_exc", "t_low_pc", "split"]:
            ok, n, nd, md = same(a[col], b[col])
            check(f"model {ul} {col}", ok, f"n {n} diff {nd} max {md}")

    # -------- per-candidate row tables (validation and final) + proof 2
    print("\n== proof 2: the final-test evaluation code reproduces each module's validation numbers ==")
    TAB = {}
    META = {}
    for i in PP_IDS:
        c = FPP.loc[i].copy()
        c["id"] = i
        P = PPF[c["ul"]]
        d = float(np.sign(c["effect"]))
        rows = {}
        for sp in ["discovery", "validation", "final"]:
            rows[sp], r = pp_rows(P, c, P["split"] == sp)
        dv = pd.concat([rows["discovery"], rows["validation"]], ignore_index=True)
        TAB[i] = dict(val=rows["validation"], fin=rows["final"], dv=dv)
        META[i] = dict(module="pricepath", ul=c["ul"], rule=c["rule"], target=c["target"], binary=True, d=d,
                       disc_n=c["n"], disc_rate=c["rate"], disc_base=c["base"], disc_effect=c["effect"])
        v = gate_stats(rows["validation"], True, d)
        ref = VPP.loc[i]
        ok = v["n"] == ref["val_n"] and math.isclose(v["base"], ref["val_base"], abs_tol=1e-12) and \
            math.isclose(v["rate"], ref["val_rate"], abs_tol=1e-12) and \
            math.isclose(v["p"], ref["val_p_one_sided"], rel_tol=1e-9)
        check(f"{i} validation n/rate/base/p", ok, f"n {v['n']} vs {ref['val_n']}, rate {v['rate']:.4f} vs "
              f"{ref['val_rate']:.4f}, base {v['base']:.4f} vs {ref['val_base']:.4f}")
    for i in OC_IDS:
        c = FOC.loc[i].copy()
        c["cand"] = i
        ul = c["underlying"]
        C = OCC[ul]
        tm = TH[(TH.underlying == ul) & (TH.ctx == "ALL") & (TH.signal == "_target_median")].iloc[0]
        med = {"agap": tm["agap"], "range": tm["range"]}
        thr = TH[(TH.underlying == ul) & (TH.ctx == "ALL") & (TH.signal == c["signal"])].iloc[0].to_dict()
        rv = float(c["rule"].split(">=")[1])
        check(f"{i} frozen threshold q67 matches rule text", abs(thr["q67"] - rv) < 1e-4 * max(1, abs(rv)),
              f"{thr['q67']:.6g} vs {rv}")
        d = float(np.sign(c["effect"]))
        rows = {sp: oc_rows(C[C["split"] == sp], c, thr, med) for sp in ["discovery", "validation", "final"]}
        TAB[i] = dict(val=rows["validation"], fin=rows["final"],
                      dv=pd.concat([rows["discovery"], rows["validation"]], ignore_index=True))
        META[i] = dict(module="optionchain", ul=ul, rule=c["rule"], target=c["target"] + (
            f" (range > {med['range']:.4g} %)" if c["target"] == "range_big" else ""), binary=True, d=d,
            disc_n=c["n"], disc_rate=c["rate"], disc_base=c["base"], disc_effect=c["effect"])
        n, k, rate, base = ocv.bucket_eval(C[C["split"] == "validation"], c, thr, med)
        v = gate_stats(rows["validation"], True, d)
        ref = VOC.loc[i]
        ok = (n == v["n"] == ref["val_n"]) and k == v["k"] == ref["val_k"] and \
            math.isclose(v["base"], ref["val_base"], abs_tol=1e-12) and math.isclose(base, ref["val_base"],
                                                                                    abs_tol=1e-12)
        check(f"{i} validation n/k/base", ok, f"n {v['n']} vs {ref['val_n']}, k {v['k']} vs {ref['val_k']}, "
              f"base {v['base']:.4f} vs {ref['val_base']:.4f}")
        d_rows = rows["discovery"]
        dd = gate_stats(d_rows, True, d)
        check(f"{i} discovery n/rate reproduced", dd["n"] == c["n"] and math.isclose(dd["rate"], c["rate"],
                                                                                       abs_tol=1e-12),
              f"n {dd['n']} vs {c['n']}")
    for i in M_IDS:
        c = FM.loc[i].copy()
        c["cid"] = i
        F = MF[c["ul"]]
        binary = c["target"] in mc.BIN_TARGETS
        d = 1.0 if c["direction"] == "higher" else -1.0
        rows = {sp: m_rows(F[F["split"] == sp].reset_index(drop=True), c) for sp in
                ["discovery", "validation", "final"]}
        TAB[i] = dict(val=rows["validation"], fin=rows["final"],
                      dv=pd.concat([rows["discovery"], rows["validation"]], ignore_index=True))
        META[i] = dict(module="model", ul=c["ul"], rule=c["rule"], target=c["target"], binary=binary, d=d,
                       disc_n=c["disc_n"], disc_rate=c["disc_rate"], disc_base=c["disc_base"],
                       disc_effect=c["disc_effect"])
        v = gate_stats(rows["validation"], binary, d)
        ref = VM.loc[i]
        ok = v["n"] == ref["val_n"] and math.isclose(v["rate"], ref["val_rate"], abs_tol=1e-12) and \
            math.isclose(v["base"], ref["val_base"], abs_tol=1e-12) and \
            math.isclose(v["p"], ref["val_p_one_sided"], rel_tol=1e-9)
        check(f"{i} validation n/rate/base/p", ok, f"n {v['n']} vs {ref['val_n']}, rate {v['rate']:.4f} vs "
              f"{ref['val_rate']:.4f}, base {v['base']:.4f} vs {ref['val_base']:.4f}")

    CK = pd.DataFrame(CHECKS)
    CK.to_csv(OUT / "code_path_checks.csv", index=False)
    if not CK["ok"].all():
        print("\nCODE-PATH PROOF FAILED: no final statistic computed.")
        print(CK[~CK["ok"]].to_string(index=False))
        sys.exit(1)
    print(f"\nall {len(CK)} code-path checks pass")

    # -------- the final test (computed once)
    print("\n== FINAL PERIOD: one evaluation per candidate ==")
    R = []
    for i in ORDER:
        m, T = META[i], TAB[i]
        g = gate_stats(T["fin"], m["binary"], m["d"])
        o = open_stats(T["fin"], m["binary"], m["d"])
        vx = vix_gain(T["dv"], T["fin"], m["binary"], m["d"])
        same_sign = bool(np.sign(g["effect"]) == np.sign(m["disc_effect"])) if g["n"] else False
        half = bool(abs(g["effect"]) >= 0.5 * abs(m["disc_effect"])) if g["n"] else False
        gate1 = bool(same_sign and g["p"] < 0.05 and half)
        R.append(dict(id=i, module=m["module"], ul=m["ul"], rule=m["rule"], target=m["target"],
                      disc_n=m["disc_n"], disc_rate=m["disc_rate"], disc_base=m["disc_base"],
                      disc_effect=m["disc_effect"],
                      fin_rows=g["n_base"], fin_n=g["n"], fin_k=g["k"], fin_rate=g["rate"], fin_ci_lo=g["ci_lo"],
                      fin_ci_hi=g["ci_hi"], fin_base=g["base"], fin_effect=g["effect"], fin_p_one_sided=g["p"],
                      same_sign=same_sign, half_effect=half, gate1=gate1,
                      fin_first=T["fin"]["y_date"].min(), fin_last=T["fin"]["y_date"].max(),
                      open_n=o["n"], open_rate=o["rate"], open_base=o["base"], open_effect=o["effect"],
                      open_p_one_sided=o["p"], **vx))
    R = pd.DataFrame(R)
    q, rej = su.bh(R["fin_p_one_sided"].values, 0.10)
    R["bh_q"] = q
    R["gate2_bh"] = rej
    R["label"] = np.where(R["gate1"] & R["gate2_bh"], "Validated (size)", "Rejected")
    R["beyond_vix"] = np.where(np.sign(R["resid_diff"]) == np.sign(R["disc_effect"]),
                               np.where(R["vix_p"] < 0.05, "adds (p<0.05)", "same sign, not significant"),
                               "no (opposite sign)")
    R.to_csv(OUT / "final_results.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(R[["id", "ul", "fin_rows", "fin_n", "fin_rate", "fin_base", "fin_effect", "disc_effect",
             "fin_p_one_sided", "bh_q", "gate1", "gate2_bh", "label"]].round(4).to_string(index=False))
    print(R[["id", "open_n", "open_rate", "open_base", "open_effect", "open_p_one_sided", "vix_pred_flagged",
             "resid_flagged", "resid_unflagged", "resid_diff", "vix_p", "beyond_vix"]].round(4).to_string(index=False))

    # -------- per-session flags
    for ul in ["NIFTY", "BANKNIFTY"]:
        parts = []
        for i in ORDER:
            if META[i]["ul"] != ul:
                continue
            T = TAB[i]["fin"].copy()
            cols = {"feature": f"{i}_feature", "flag": f"{i}_flag", "y": f"{i}_target", "y_open": f"{i}_target_open"}
            if "feature2" in T.columns:
                cols["feature2"] = f"{i}_feature2"
            T = T.rename(columns=cols)[["date", "y_date"] + list(cols.values())]
            T[f"{i}_flag"] = T[f"{i}_flag"].astype(int)
            parts.append(T.set_index(["date", "y_date"]))
        Fl = pd.concat(parts, axis=1).reset_index().sort_values("date")
        vix = COMB[ul].set_index("date")["f_vix_close"]
        Fl.insert(2, "f_vix_close", Fl["date"].map(vix))
        Fl.to_csv(OUT / f"flags_{ul}.csv", index=False)
        print(f"flags_{ul}.csv rows {len(Fl)}")

    # -------- Observed cross-checks
    print("\n== Observed (a): expiry-day direction base rates ==")
    load = patched(bc.load, [('    assert (P["date"] < "2024-07-01").all()\n', '')],
                   {"load_panel": lambda u: COMB[u].copy()})
    OBS, TRS = [], []
    for ul in panel_io.ULS:
        P, _ = load(ul)
        U = P[P["usable"]]
        for sp in ["discovery", "validation", "final"]:
            S = U[U["split"] == sp]
            if not len(S):
                continue
            for grp, M in [("all sessions", S), ("t+1 expiry day (D0)", S[S["ctx"] == "D0"]),
                           ("t+1 not expiry", S[(S["ctx"] != "D0") & (S["ctx"] != "unknown")])]:
                for tg in ["gap_up", "oc_pos"]:
                    x = M[tg].dropna()
                    r, lo, hi = su.wilson(int(x.sum()), len(x))
                    OBS.append(dict(ul=ul, split=sp, group=grp, target=tg, n=len(x), k=int(x.sum()), rate=r,
                                    ci_lo=lo, ci_hi=hi))
        for sp in ["discovery", "final"]:
            Df = U[U["split"] == sp]
            if len(Df) < 30:
                continue
            t, chip = bd.transition(Df, ul, sp)
            TRS.append(t)
            print(f"  {ul} {sp} gap transition chi-square p {chip:.4f} (n {len(Df)})")
    OB = pd.DataFrame(OBS)
    # final vs discovery for D0 (two-proportion), and D0 vs non-expiry inside the final period
    OB["p_vs_discovery"] = np.nan
    OB["p_D0_vs_nonexp"] = np.nan
    for idx, r in OB.iterrows():
        if r["split"] in ("validation", "final"):
            d = OB[(OB.ul == r.ul) & (OB.split == "discovery") & (OB.group == r.group) & (OB.target == r.target)]
            if len(d):
                OB.loc[idx, "p_vs_discovery"] = su.two_prop(r.k, r.n, d.k.iloc[0], d.n.iloc[0])
        if r["group"] == "t+1 expiry day (D0)":
            ne = OB[(OB.ul == r.ul) & (OB.split == r.split) & (OB.group == "t+1 not expiry") &
                    (OB.target == r.target)]
            if len(ne) and r.n:
                OB.loc[idx, "p_D0_vs_nonexp"] = su.two_prop(r.k, r.n, ne.k.iloc[0], ne.n.iloc[0])
    OB.to_csv(OUT / "observed_expiry_direction.csv", index=False)
    print(OB.round(4).to_string(index=False))
    ref = pd.read_csv(RES / "bias" / "ref_discovery.csv")
    for ul in ["NIFTY", "BANKNIFTY"]:
        for tg in ["gap_up", "oc_pos"]:
            rr = ref[(ref.ul == ul) & (ref.tag == "ctx") & (ref.level == "D0") & (ref.target == tg)]
            mine = OB[(OB.ul == ul) & (OB.split == "discovery") & (OB.group == "t+1 expiry day (D0)") &
                      (OB.target == tg)]
            if len(rr) and len(mine):
                ok = int(rr.n.iloc[0]) == int(mine.n.iloc[0]) and math.isclose(rr.rate.iloc[0], mine.rate.iloc[0],
                                                                               abs_tol=1e-12)
                print(f"  discovery D0 {ul} {tg} equals bias ref_discovery: {ok} "
                      f"(n {int(mine.n.iloc[0])}, {mine.rate.iloc[0]:.4f} vs {rr.rate.iloc[0]:.4f})")
    TR = pd.concat(TRS, ignore_index=True)
    TR.to_csv(OUT / "observed_gap_transition_final.csv", index=False)
    print(TR.round(4).to_string(index=False))
    print("done")


if __name__ == "__main__":
    main()
