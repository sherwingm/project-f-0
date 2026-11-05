"""Hypothesis family of the gaps module (design: reports/lld/gaps.md). Frozen by sha256 in candidates_frozen.csv.

Each spec is a dict:
  id, ul, group, rule, dt (decision time), target, kind, uses (columns the condition may read),
  cond(F, prm) -> bool mask, comp(F, prm) -> bool mask (2-group kinds), outcome (column), comp_col (companion for
  'drop best 1 %'), prm (default threshold), nbrs (neighbour thresholds), minute (needs minute data).
The condition functions get only the columns in `uses` (plus outcome rows are selected outside), so a TCLOSE rule
cannot read a label by accident. y_ columns in `uses` are allowed only for OPEN(t+1) rules and only the gap.
"""
import numpy as np

OPEN_ALLOWED = {"y_gap_pct", "y_gap_dir", "y_sgn", "y_abs_gap"}
T1515_FORBIDDEN = {"f_close_pos", "o_cc", "o_oc", "o_range_pct", "o_max_exc", "o_last_hour", "o_rv", "o_high_min",
                   "o_low_min", "o_gap_filled", "f_mom1", "f_mom5", "f_vix_close", "vix_t", "mom5_sgn"}
CTX_COLS = ["k", "d0", "dplus1", "kind_ctx", "cal_next_dow", "regime"]

BEH = [  # (column, kind, label, minute)
    ("y_range_pct", "mean", "range % of prev close", False),
    ("y_abs_cc", "mean", "|close-to-close| %", False),
    ("y_abs_oc", "mean", "|open-to-close| %", False),
    ("y_abs_gap", "mean", "|gap| %", False),
    ("y_bigexc", "rate", "max excursion >= 1 %", False),
    ("y_bigcc", "rate", "|cc| >= 1 %", False),
    ("y_rv", "mean", "intraday realised vol %", True),
    ("y_high_min", "mean", "minute of session high", True),
    ("y_low_min", "mean", "minute of session low", True),
    ("y_ext_last_hr", "rate", "high or low made in last hour", True),
]


def S(**kw):
    kw.setdefault("comp", None)
    kw.setdefault("prm", None)
    kw.setdefault("nbrs", [])
    kw.setdefault("minute", False)
    kw.setdefault("comp_col", None)
    return kw


def ctx_mask(F, c):
    if c == "D0":
        return F["d0"]
    if c == "D+1":
        return F["dplus1"]
    if c.startswith("D-"):
        return F["k"] == int(c[2:])
    raise ValueError(c)


def specs_for(ul):
    u = ul[0]
    L = []
    gp = ["o_gap_pct", "o_gap_dir"]
    # ---- T: transitions (gap of t -> gap of t+1), T1515(t)
    L += [
        S(id=f"{u}_T1", group="T", rule="gap of t up (>= +0.1 %) -> gap of t+1 down", dt="T1515(t)", target="y_down",
          kind="rate_vs_base", uses=gp, cond=lambda F, p: F["o_gap_dir"] == "up", outcome="y_down", comp_col="-y_gap_pct"),
        S(id=f"{u}_T2", group="T", rule="gap of t down -> gap of t+1 up", dt="T1515(t)", target="y_up",
          kind="rate_vs_base", uses=gp, cond=lambda F, p: F["o_gap_dir"] == "down", outcome="y_up", comp_col="y_gap_pct"),
        S(id=f"{u}_T3", group="T", rule="gap of t up -> gap of t+1 up", dt="T1515(t)", target="y_up",
          kind="rate_vs_base", uses=gp, cond=lambda F, p: F["o_gap_dir"] == "up", outcome="y_up", comp_col="y_gap_pct"),
        S(id=f"{u}_T4", group="T", rule="gap of t down -> gap of t+1 down", dt="T1515(t)", target="y_down",
          kind="rate_vs_base", uses=gp, cond=lambda F, p: F["o_gap_dir"] == "down", outcome="y_down", comp_col="-y_gap_pct"),
        S(id=f"{u}_T5", group="T", rule="gap of t >= +prm % -> gap of t+1 down", dt="T1515(t)", target="y_down",
          kind="rate_vs_base", uses=gp, cond=lambda F, p: F["o_gap_pct"] >= p, prm=0.5, nbrs=[0.4, 0.6],
          outcome="y_down", comp_col="-y_gap_pct"),
        S(id=f"{u}_T6", group="T", rule="gap of t <= -prm % -> gap of t+1 up", dt="T1515(t)", target="y_up",
          kind="rate_vs_base", uses=gp, cond=lambda F, p: F["o_gap_pct"] <= -p, prm=0.5, nbrs=[0.4, 0.6],
          outcome="y_up", comp_col="y_gap_pct"),
        S(id=f"{u}_T7", group="T", rule="gap of t >= +prm % -> gap of t+1 down", dt="T1515(t)", target="y_down",
          kind="rate_vs_base", uses=gp, cond=lambda F, p: F["o_gap_pct"] >= p, prm=1.0, nbrs=[0.8, 1.2],
          outcome="y_down", comp_col="-y_gap_pct"),
        S(id=f"{u}_T8", group="T", rule="gap of t <= -prm % -> gap of t+1 up", dt="T1515(t)", target="y_up",
          kind="rate_vs_base", uses=gp, cond=lambda F, p: F["o_gap_pct"] <= -p, prm=1.0, nbrs=[0.8, 1.2],
          outcome="y_up", comp_col="y_gap_pct"),
        S(id=f"{u}_T9", group="T", rule="3x3 transition up/flat/down of t -> t+1 is not independent", dt="T1515(t)",
          target="y_gap_dir", kind="chi2", uses=gp, cond=lambda F, p: F["o_gap_dir"].notna(), outcome="y_gap_dir"),
    ]
    # ---- X: reversal of the previous gap by context of t+1
    for c in ["D0", "D-1", "D-2", "D-3", "D-4", "D+1"]:
        L.append(S(id=f"{u}_X{c.replace('-', 'm').replace('+', 'p')}", group="X",
                   rule=f"t+1 is {c}: next gap reverses the gap of t (both non-flat)", dt="T1515(t)", target="rev",
                   kind="rate_vs_base", uses=CTX_COLS, cond=(lambda c: lambda F, p: ctx_mask(F, c))(c),
                   outcome="rev", comp_col="rev_mag"))
    L.append(S(id=f"{u}_Xtrend", group="X", rule="reversal rate rises as t+1 approaches expiry (k = 4..0)",
               dt="T1515(t)", target="rev", kind="trend", uses=CTX_COLS, cond=lambda F, p: F["k"] <= 4, outcome="rev"))
    L.append(S(id=f"{u}_XL", group="X", rule="|gap of t| >= prm % reverses more when t+1 is D0/D-1 than when k >= 2",
               dt="T1515(t)", target="rev", kind="rate_2g", uses=CTX_COLS + gp, prm=0.5, nbrs=[0.4, 0.6],
               cond=lambda F, p: (F["o_gap_pct"].abs() >= p) & (F["k"] <= 1),
               comp=lambda F, p: (F["o_gap_pct"].abs() >= p) & (F["k"] >= 2), outcome="rev", comp_col="rev_mag"))
    # ---- S: streaks
    for nm, sgn, thr, out, dt, cc in [("S1", 1, 2, "y_up", "T1515(t)", "y_gap_pct"),
                                      ("S2", 1, 3, "y_up", "T1515(t)", "y_gap_pct"),
                                      ("S3", -1, 2, "y_down", "T1515(t)", "-y_gap_pct"),
                                      ("S4", -1, 3, "y_down", "T1515(t)", "-y_gap_pct"),
                                      ("S5", 1, 2, "y_oc_pos", "TCLOSE(t)", "y_oc"),
                                      ("S6", -1, 2, "y_oc_neg", "TCLOSE(t)", "-y_oc"),
                                      ("S7", 1, 3, "y_oc_pos", "TCLOSE(t)", "y_oc"),
                                      ("S8", -1, 3, "y_oc_neg", "TCLOSE(t)", "-y_oc")]:
        d = "up" if sgn > 0 else "down"
        L.append(S(id=f"{u}_{nm}", group="S", rule=f">= prm consecutive gaps {d} ending at t -> {out} on t+1",
                   dt=dt, target=out, kind="rate_vs_base", uses=["g_streak"], prm=thr,
                   nbrs=[thr - 1, thr + 1] if thr == 2 else [thr - 1, thr + 1],
                   cond=(lambda s: lambda F, p: F["g_streak"] * s >= p)(sgn), outcome=out, comp_col=cc))
    # ---- C: close position -> next gap
    L += [
        S(id=f"{u}_C1", group="C", rule="close in top of day's range (f_close_pos >= prm) -> gap of t+1 up",
          dt="TCLOSE(t)", target="y_up", kind="rate_vs_base", uses=["f_close_pos"], prm=0.8, nbrs=[0.75, 0.85],
          cond=lambda F, p: F["f_close_pos"] >= p, outcome="y_up", comp_col="y_gap_pct"),
        S(id=f"{u}_C2", group="C", rule="close in bottom of range (f_close_pos <= 1-prm) -> gap of t+1 down",
          dt="TCLOSE(t)", target="y_down", kind="rate_vs_base", uses=["f_close_pos"], prm=0.8, nbrs=[0.75, 0.85],
          cond=lambda F, p: F["f_close_pos"] <= 1 - p, outcome="y_down", comp_col="-y_gap_pct"),
        S(id=f"{u}_C3", group="C", rule="15:14 price in top of range (f1515_pos_in_range >= prm) -> gap of t+1 up",
          dt="T1515(t)", target="y_up", kind="rate_vs_base", uses=["f1515_pos_in_range"], prm=0.8,
          nbrs=[0.75, 0.85], minute=True,
          cond=lambda F, p: F["f1515_pos_in_range"] >= p, outcome="y_up", comp_col="y_gap_pct"),
        S(id=f"{u}_C4", group="C", rule="15:14 price in bottom of range (<= 1-prm) -> gap of t+1 down",
          dt="T1515(t)", target="y_down", kind="rate_vs_base", uses=["f1515_pos_in_range"], prm=0.8,
          nbrs=[0.75, 0.85], minute=True,
          cond=lambda F, p: F["f1515_pos_in_range"] <= 1 - p, outcome="y_down", comp_col="-y_gap_pct"),
        S(id=f"{u}_C5", group="C", rule="t+1 is D0 and f_close_pos >= prm -> gap of t+1 up", dt="TCLOSE(t)",
          target="y_up", kind="rate_vs_base", uses=["f_close_pos"] + CTX_COLS, prm=0.8, nbrs=[0.75, 0.85],
          cond=lambda F, p: (F["f_close_pos"] >= p) & F["d0"], outcome="y_up", comp_col="y_gap_pct"),
        S(id=f"{u}_C6", group="C", rule="t+1 is D0 and f_close_pos <= 1-prm -> gap of t+1 down", dt="TCLOSE(t)",
          target="y_down", kind="rate_vs_base", uses=["f_close_pos"] + CTX_COLS, prm=0.8, nbrs=[0.75, 0.85],
          cond=lambda F, p: (F["f_close_pos"] <= 1 - p) & F["d0"], outcome="y_down", comp_col="-y_gap_pct"),
        S(id=f"{u}_C7", group="C", rule="t is expiry day (t+1 D+1) and f_close_pos >= prm -> gap of t+1 up",
          dt="TCLOSE(t)", target="y_up", kind="rate_vs_base", uses=["f_close_pos"] + CTX_COLS, prm=0.8,
          nbrs=[0.75, 0.85], cond=lambda F, p: (F["f_close_pos"] >= p) & F["dplus1"], outcome="y_up",
          comp_col="y_gap_pct"),
        S(id=f"{u}_C8", group="C", rule="t is expiry day (t+1 D+1) and f_close_pos <= 1-prm -> gap of t+1 down",
          dt="TCLOSE(t)", target="y_down", kind="rate_vs_base", uses=["f_close_pos"] + CTX_COLS, prm=0.8,
          nbrs=[0.75, 0.85], cond=lambda F, p: (F["f_close_pos"] <= 1 - p) & F["dplus1"], outcome="y_down",
          comp_col="-y_gap_pct"),
    ]
    # ---- L: large opening gap of t+1 -> rest of the session (OPEN(t+1))
    og = ["y_gap_pct", "y_abs_gap", "y_sgn"]
    small = lambda F, p: (F["y_abs_gap"] >= 0.1) & (F["y_abs_gap"] < 0.5)  # noqa: E731
    L += [
        S(id=f"{u}_L1", group="L", rule="|gap of t+1| >= prm %: close-open moves with the gap (continuation)",
          dt="OPEN(t+1)", target="y_cont", kind="rate_vs_base", uses=og, prm=0.5, nbrs=[0.4, 0.6],
          cond=lambda F, p: F["y_abs_gap"] >= p, outcome="y_cont", comp_col="y_soc"),
        S(id=f"{u}_L2", group="L", rule="|gap of t+1| >= prm %: continuation", dt="OPEN(t+1)", target="y_cont",
          kind="rate_vs_base", uses=og, prm=1.0, nbrs=[0.8, 1.2],
          cond=lambda F, p: F["y_abs_gap"] >= p, outcome="y_cont", comp_col="y_soc"),
        S(id=f"{u}_L3", group="L", rule="signed oc (with-gap +) for |gap| >= prm vs 0.1-0.5 % gaps", dt="OPEN(t+1)",
          target="y_soc", kind="mean_2g", uses=og, prm=0.5, nbrs=[0.4, 0.6],
          cond=lambda F, p: F["y_abs_gap"] >= p, comp=small, outcome="y_soc"),
        S(id=f"{u}_L4", group="L", rule="signed oc for |gap| >= prm vs 0.1-0.5 % gaps", dt="OPEN(t+1)",
          target="y_soc", kind="mean_2g", uses=og, prm=1.0, nbrs=[0.8, 1.2],
          cond=lambda F, p: F["y_abs_gap"] >= p, comp=small, outcome="y_soc"),
        S(id=f"{u}_L5", group="L", rule="signed 09:16->close return for |gap| >= prm vs 0.1-0.5 % gaps (minute)",
          dt="OPEN(t+1)", target="se_oc", kind="mean_2g", uses=og, prm=0.5, nbrs=[0.4, 0.6], minute=True,
          cond=lambda F, p: F["y_abs_gap"] >= p, comp=small, outcome="se_oc"),
        S(id=f"{u}_L6", group="L", rule="gap up >= prm %: continuation", dt="OPEN(t+1)", target="y_cont",
          kind="rate_vs_base", uses=og, prm=0.5, nbrs=[0.4, 0.6],
          cond=lambda F, p: F["y_gap_pct"] >= p, outcome="y_cont", comp_col="y_soc"),
        S(id=f"{u}_L7", group="L", rule="gap down <= -prm %: continuation", dt="OPEN(t+1)", target="y_cont",
          kind="rate_vs_base", uses=og, prm=0.5, nbrs=[0.4, 0.6],
          cond=lambda F, p: F["y_gap_pct"] <= -p, outcome="y_cont", comp_col="y_soc"),
    ]
    # ---- E: strong gap on D0 / D-1 / D+1 vs same-size gaps elsewhere (OPEN(t+1))
    for c in ["D0", "D-1", "D+1"]:
        cn = c.replace("-", "m").replace("+", "p")
        for thr in [0.3, 0.5]:
            tn = str(thr).replace(".", "")
            mk = (lambda c: (lambda F, p: (F["y_abs_gap"] >= p) & ctx_mask(F, c),
                             lambda F, p: (F["y_abs_gap"] >= p) & ~ctx_mask(F, c)))(c)
            nb = [0.25, 0.4] if thr == 0.3 else [0.4, 0.6]
            for tgt, kind, cc in [("y_cont", "rate_2g", "y_soc"), ("y_fill", "rate_2g", "-y_soc"),
                                  ("y_soc", "mean_2g", None)]:
                L.append(S(id=f"{u}_E{cn}_{tn}_{tgt[2:]}", group="E",
                           rule=f"|gap| >= prm % on {c} vs same gaps on other days: {tgt}", dt="OPEN(t+1)",
                           target=tgt, kind=kind, uses=og + CTX_COLS, prm=thr, nbrs=nb, cond=mk[0], comp=mk[1],
                           outcome=tgt, comp_col=cc))
    mk = (lambda F, p: (F["y_abs_gap"] >= p) & F["d0"], lambda F, p: (F["y_abs_gap"] >= p) & ~F["d0"])
    for tgt, kind in [("se_ret15", "mean_2g"), ("se_ret30", "mean_2g"), ("se_ret60", "mean_2g"),
                      ("se_oc", "mean_2g"), ("e_fill", "rate_2g")]:
        L.append(S(id=f"{u}_ED0m_{tgt}", group="E",
                   rule=f"|gap| >= prm % on D0 vs other days, entry at 09:15 bar close: {tgt} (minute)",
                   dt="OPEN(t+1)", target=tgt, kind=kind, uses=og + CTX_COLS, prm=0.3, nbrs=[0.25, 0.4],
                   cond=mk[0], comp=mk[1], outcome=tgt, minute=True,
                   comp_col=("-se_oc" if tgt == "e_fill" else None)))
    # ---- F: gap-fill conditions within size buckets (OPEN(t+1))
    for bn, lo, hi in [("a", 0.1, 0.5), ("b", 0.5, 99)]:
        inb = (lambda lo, hi: lambda F: (F["y_abs_gap"] >= lo) & (F["y_abs_gap"] < hi))(lo, hi)
        fu = og + CTX_COLS + ["vix_t", "mom5_sgn"]
        for nm, rule, a, b in [
            ("dir", "gap up vs gap down", lambda F: F["y_sgn"] > 0, lambda F: F["y_sgn"] < 0),
            ("vix", "VIX tercile 3 vs 1 (discovery cut points)", lambda F: F["vix_t"] == 3, lambda F: F["vix_t"] == 1),
            ("near", "t+1 is D0 or D-1 vs k >= 2", lambda F: F["k"] <= 1, lambda F: F["k"] >= 2),
            ("dp1", "t+1 is D+1 vs other", lambda F: F["dplus1"], lambda F: ~F["dplus1"]),
            ("trend", "gap with the 5-session trend vs against it", lambda F: F["y_sgn"] == F["mom5_sgn"],
             lambda F: F["y_sgn"] == -F["mom5_sgn"]),
        ]:
            L.append(S(id=f"{u}_F{bn}_{nm}", group="F",
                       rule=f"gap fill, |gap| in [{lo},{hi}) %: {rule}", dt="OPEN(t+1)", target="y_fill",
                       kind="rate_2g", uses=fu,
                       cond=(lambda inb, a: lambda F, p: inb(F) & a(F))(inb, a),
                       comp=(lambda inb, b: lambda F, p: inb(F) & b(F))(inb, b),
                       outcome="y_fill", comp_col="-y_soc"))
    # ---- P: first session after expiry
    pu = CTX_COLS + ["o_cc"]
    L += [
        S(id=f"{u}_P1", group="P", rule="t is expiry day: gap of t+1 against the expiry-day close-close move (vs other t)",
          dt="TCLOSE(t)", target="gap_vs_cc_rev", kind="rate_2g", uses=pu,
          cond=lambda F, p: F["dplus1"], comp=lambda F, p: ~F["dplus1"], outcome="gap_vs_cc_rev",
          comp_col="gap_vs_cc_mag"),
        S(id=f"{u}_P2", group="P", rule="t is expiry day: oc of t+1 against the expiry-day cc move (vs other t)",
          dt="TCLOSE(t)", target="oc_vs_cc_rev", kind="rate_2g", uses=pu,
          cond=lambda F, p: F["dplus1"], comp=lambda F, p: ~F["dplus1"], outcome="oc_vs_cc_rev",
          comp_col="oc_vs_cc_mag"),
        S(id=f"{u}_P3", group="P", rule="t is expiry day: cc of t+1 against the expiry-day cc move (vs other t)",
          dt="TCLOSE(t)", target="cc_vs_cc_rev", kind="rate_2g", uses=pu,
          cond=lambda F, p: F["dplus1"], comp=lambda F, p: ~F["dplus1"], outcome="cc_vs_cc_rev",
          comp_col="cc_vs_cc_mag"),
        S(id=f"{u}_P4", group="P", rule="|cc of t| >= prm % on an expiry day: oc of t+1 reverses (vs same move other t)",
          dt="TCLOSE(t)", target="oc_vs_cc_rev", kind="rate_2g", uses=pu, prm=1.0, nbrs=[0.8, 1.2],
          cond=lambda F, p: F["dplus1"] & (F["o_cc"].abs() >= p),
          comp=lambda F, p: ~F["dplus1"] & (F["o_cc"].abs() >= p), outcome="oc_vs_cc_rev", comp_col="oc_vs_cc_mag"),
        S(id=f"{u}_P5", group="P", rule="t+1 is D+1: gap up rate vs base", dt="TCLOSE(t)", target="y_up",
          kind="rate_vs_base", uses=CTX_COLS, cond=lambda F, p: F["dplus1"], outcome="y_up", comp_col="y_gap_pct"),
    ]
    # ---- B: behaviour by expiry type (calendar, known in advance)
    ordinary = lambda F, p: ~F["d0"] & ~(F["k"] == 1) & ~F["dplus1"]  # noqa: E731
    for col, mk_, lab, minute in BEH:
        kind = "mean_2g" if mk_ == "mean" else "rate_2g"
        for c in ["D0", "D-1", "D+1"]:
            cn = c.replace("-", "m").replace("+", "p")
            L.append(S(id=f"{u}_B{cn}_{col[2:]}", group="B", rule=f"{lab}: {c} vs ordinary sessions",
                       dt="calendar", target=col, kind=kind, uses=CTX_COLS,
                       cond=(lambda c: lambda F, p: ctx_mask(F, c))(c), comp=ordinary, outcome=col, minute=minute))
        L.append(S(id=f"{u}_Bmw_{col[2:]}", group="B", rule=f"{lab}: monthly D0 vs weekly D0", dt="calendar",
                   target=col, kind=kind, uses=CTX_COLS, cond=lambda F, p: F["d0"] & (F["kind_ctx"] == "monthly"),
                   comp=lambda F, p: F["d0"] & (F["kind_ctx"] == "weekly"), outcome=col, minute=minute))
    if ul == "NIFTY":
        for col in ["y_range_pct", "y_abs_cc", "y_abs_oc"]:
            L.append(S(id=f"{u}_Bthu_{col[2:]}", group="B",
                       rule=f"{col}: non-expiry Thursday vs other ordinary days, NIFTY 2018 (monthly-only) control",
                       dt="calendar", target=col, kind="mean_2g", uses=CTX_COLS,
                       cond=lambda F, p: (F["regime"] == "N18_monthly_only") & (F["cal_next_dow"] == "Thursday")
                       & ~F["d0"],
                       comp=lambda F, p: (F["regime"] == "N18_monthly_only") & (F["cal_next_dow"] != "Thursday")
                       & ~F["d0"] & ~(F["k"] == 1) & ~F["dplus1"], outcome=col))
    for s in L:
        s["ul"] = ul
    return L


def all_specs():
    return specs_for("NIFTY") + specs_for("BANKNIFTY")


def add_derived(P):
    """Outcome helper columns used by specs (all describe t+1; labels only)."""
    sgn_cc = np.sign(P["o_cc"])
    nf = P["y_gap_dir"] != "flat"
    P["gap_vs_cc_rev"] = np.where(nf & (sgn_cc != 0), (P["y_sgn"] == -sgn_cc).astype(float), np.nan)
    P["gap_vs_cc_mag"] = -P["y_gap_pct"] * sgn_cc
    P["oc_vs_cc_rev"] = np.where((sgn_cc != 0) & (P["y_oc"] != 0), (np.sign(P["y_oc"]) == -sgn_cc).astype(float),
                                 np.nan)
    P["oc_vs_cc_mag"] = -P["y_oc"] * sgn_cc
    P["cc_vs_cc_rev"] = np.where((sgn_cc != 0) & (P["y_cc"] != 0), (np.sign(P["y_cc"]) == -sgn_cc).astype(float),
                                 np.nan)
    P["cc_vs_cc_mag"] = -P["y_cc"] * sgn_cc
    P["rev_mag"] = -P["y_gap_pct"] * np.sign(P["o_gap_pct"])
    P["y_ext_last_hr"] = np.where(P["y_high_min"].isna() | P["y_low_min"].isna(), np.nan,
                                  (np.maximum(P["y_high_min"], P["y_low_min"]) >= 315).astype(float))
    return P
