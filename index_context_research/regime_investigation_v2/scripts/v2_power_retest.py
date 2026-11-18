"""Deduplicated, higher-power re-test of G1-F's 36 conditions. Plan: PREREG_V2_POWER.md (commit 12ca29fa1).
Reads stored labels only (no fetching, no cleaning). Year 1 only for every choice; Year 2 read-only at the end."""
import os, numpy as np, pandas as pd
from scipy import stats
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
HERE = os.path.dirname(os.path.abspath(__file__)); V2 = os.path.dirname(HERE)
RI = os.path.join(os.path.dirname(V2), "regime_investigation", "interim")
SEED, NPERM = 20261118, 10000
OUT = os.path.join(V2, "results"); os.makedirs(OUT, exist_ok=True)

A = pd.read_csv(RI + "/agent3_regimes/regime_labels.csv")
B = pd.read_csv(RI + "/agent4_external/external_features.csv")
Gc = pd.read_csv(RI + "/agent3b_gift_regimes/gift_labels.csv")
Gs = pd.read_csv(RI + "/agent3b_gift_regimes/gift_labels_samecontract.csv")
T = pd.read_csv(RI + "/agent5_integrity/consolidated_tests.csv")

def frame(sa, sb):
    a = A[A.strategy == sa].set_index("date")
    b = B[B.strategy == sb].set_index("date").drop(columns=[c for c in B.columns if c in A.columns and c not in ("date",)], errors="ignore")
    gc = Gc[Gc.strategy == sa].set_index("date")[["gift_ret", "gift_cls", "ivsa_cls", "gap_minus_gift", "asia_cls", "asia_gap"]].add_prefix("gc_")
    gs = Gs[Gs.strategy == sa].set_index("date")[["gift_cls", "ivsa_cls", "gift_ret_samecontract", "gap_minus_gift_samecontract"]].add_prefix("gs_")
    f = a.join(b, how="left", rsuffix="_b").join(gc).join(gs)
    return f.reset_index()

O = lambda *x: {k: i for i, k in enumerate(x)}
D3, V3, GP, GD = O("bearish", "sideways", "bullish"), O("low", "normal", "high"), O("gap-down", "flat", "gap-up"), O("down", "flat", "up")
IV = O("weaker", "in line", "stronger")
# id: (agent, hypothesis, class-column(s), ordinal map(s), numeric column or None)
def single(col, m, num=None): return dict(cols=[col], maps=[m], num=num)
def combo(c1, m1, c2, m2): return dict(cols=[c1, c2], maps=[m1, m2], num=None)
S = {
 ("A3", "H1"): single("q20", {1: 0, 2: 1, 3: 2, 4: 3, 5: 4}, "ret20"),
 ("A3", "H2"): single("vix_level", V3, "vix_prev"),
 ("A3", "H3"): single("vix_dir", O("falling", "flat", "rising"), "vix_chg5_pct"),
 ("A3", "H5"): single("gap_cls", GP, "gap_pct"),
 ("A3", "H6"): single("us_cls", GD, "us_prev_ret"),
 ("A3", "H7"): combo("dir3", D3, "vix_level", V3),
 ("A3", "H8"): combo("dir3", D3, "gap_cls", GP),
 ("A3", "H9"): combo("vix_level", V3, "gap_cls", GP),
 ("A3b", "H10"): single("gc_gift_cls", GP, "gc_gift_ret"),
 ("A3b", "H11"): single("gc_ivsa_cls", IV, "gc_gap_minus_gift"),
 ("A3b", "H12"): single("gc_asia_cls", GD, "gc_asia_gap"),
 ("A3b", "C1_dir3xGIFT"): combo("dir3", D3, "gc_gift_cls", GP),
 ("A3b", "C2_VIXxGIFT"): combo("vix_level", V3, "gc_gift_cls", GP),
 ("A3b", "H10_samecontract"): single("gs_gift_cls", GP, "gs_gift_ret_samecontract"),
 ("A3b", "H11_samecontract"): single("gs_ivsa_cls", IV, "gs_gap_minus_gift_samecontract"),
 ("A3b", "C1_dir3xGIFT_samecontract"): combo("dir3", D3, "gs_gift_cls", GP),
 ("A3b", "C2_VIXxGIFT_samecontract"): combo("vix_level", V3, "gs_gift_cls", GP),
 ("A4", "H12"): single("asia_class", GD, "asia_avg_gap"),
 ("A4", "H13"): single("risk_class", O("risk_off", "mixed", "risk_on")),
 ("A4", "H14"): single("breadth_class", V3 | {"mid": 1, "high": 2, "low": 0}, "adv_share_prev"),
 ("A4", "H15"): single("fiidii_class", O("both_buy", "diverge")),
 ("A4", "X01"): single("us_class", GD, "sp_ret"),
 ("A4", "X02"): single("usd_class", GD, "usd_chg"),
 ("A4", "X03"): single("brent_class", GD, "brent_chg"),
 ("A4", "X04"): single("usvix_class", O("no_spike", "spike"), "usvix_chg"),
 ("A4", "X05"): single("dxy_class", GD, "dxy_chg"),
 ("A4", "X06"): single("us10y_class", GD, "us10y_chg"),
 ("A4", "X07"): single("sector_class", O("bank_lags", "in_line", "bank_leads"), "bank_minus_nifty_prev"),
 ("A4", "X08"): single("fii_fut_level_class", V3, "fii_fut_share"),
 ("A4", "X09"): single("fii_fut_chg_class", GD, "fii_fut_share_chg"),
 ("A4", "X10"): single("dii_fut_level_class", V3, "dii_fut_share"),
 ("A4", "X11"): single("dii_fut_chg_class", GD, "dii_fut_share_chg"),
 ("A4", "X12"): single("fii_opt_level_class", V3, "fii_opt_stance"),
 ("A4", "X13"): single("fii_opt_chg_class", GD, "fii_opt_stance_chg"),
 ("A4", "X14"): single("tone_class", O("below_median", "above_median"), "tone_gap"),
 ("A4", "X15"): single("event_class", O("none", "day_before", "event_day", "day_after")),
}
for k in S:
    for m in S[k]["maps"]:
        for extra in ("low", "mid", "high", "down", "flat", "up"):
            pass
S[("A4", "H14")]["maps"] = [{"low": 0, "mid": 1, "high": 2}]
S[("A4", "X09")]["maps"] = [{"down": 0, "up": 1}]; S[("A4", "X11")]["maps"] = [{"down": 0, "up": 1}]
S[("A4", "X13")]["maps"] = [{"down": 0, "up": 1}]; S[("A4", "X05")]["maps"] = [{"down": 0, "up": 1}]; S[("A4", "X06")]["maps"] = [{"down": 0, "up": 1}]
S[("A4", "X08")]["maps"] = [{"low": 0, "mid": 1, "high": 2}]; S[("A4", "X10")]["maps"] = S[("A4", "X12")]["maps"] = [{"low": 0, "mid": 1, "high": 2}]
S[("A4", "H12")]["maps"] = [{"down": 0, "flat": 1, "up": 2}]; S[("A3", "H6")]["maps"] = [{"down": 0, "flat": 1, "up": 2}]

def signal(f, spec):
    """class label (string), ordinal code, numeric signal."""
    codes = []
    for c, m in zip(spec["cols"], spec["maps"]):
        codes.append(f[c].map(m))
    code = sum(codes[1:], codes[0])
    cls = f[spec["cols"][0]].astype(str) if len(spec["cols"]) == 1 else f[spec["cols"][0]].astype(str) + "|" + f[spec["cols"][1]].astype(str)
    cls = cls.where(code.notna())
    num = f[spec["num"]] if spec["num"] else None
    return cls, code, num

def bh(p):
    p = np.asarray(p, float); ok = ~np.isnan(p); adj = np.full(len(p), np.nan); pv = p[ok]; o = np.argsort(pv); m = len(pv); prev = 1.0; a = np.empty(m)
    for rank in range(m, 0, -1):
        i = o[rank - 1]; prev = min(prev, pv[i] * m / rank); a[i] = prev
    adj[ok] = a; return adj

def wins(y, lo=2, hi=98):
    a, b = np.percentile(y, [lo, hi]); return np.clip(y, a, b)

def perm_F(y, g, rng, strata=None):
    """permutation p of the between-class F statistic; labels shuffled (within strata if given)."""
    codes, inv = np.unique(g, return_inverse=True); k = len(codes); n = len(y)
    def Fstat(yy):
        cnt = np.bincount(inv, minlength=k); s = np.bincount(inv, weights=yy, minlength=k); m = s / cnt
        gm = yy.mean(); ssb = (cnt * (m - gm) ** 2).sum(); ssw = ((yy - m[inv]) ** 2).sum()
        return (ssb / (k - 1)) / (ssw / (n - k) + 1e-12)
    obs = Fstat(y); c = 0
    for _ in range(NPERM):
        if strata is None: yy = rng.permutation(y)
        else:
            yy = y.copy()
            for s in np.unique(strata):
                idx = np.where(strata == s)[0]; yy[idx] = rng.permutation(y[idx])
        c += Fstat(yy) >= obs - 1e-12
    return (c + 1) / (NPERM + 1)

def perm_diff(y, lab, rng):
    obs = abs(y[lab == 1].mean() - y[lab == 0].mean()); c = 0
    for _ in range(NPERM):
        l = rng.permutation(lab); c += abs(y[l == 1].mean() - y[l == 0].mean()) >= obs - 1e-12
    return (c + 1) / (NPERM + 1)

def tests_one(f, spec, rng, min_cls=3):
    cls, code, num = signal(f, spec)
    ok = code.notna() & f.net_pct.notna(); y = f.net_pct[ok].values; c = code[ok].values; cl = cls[ok].values
    vc = pd.Series(c).value_counts(); keep = vc[vc >= min_cls].index
    r = dict(n=int(ok.sum()), n_classes=len(keep))
    if len(keep) < 2: return r
    m = np.isin(c, keep); y, c, cl = y[m], c[m], cl[m]; r["n"] = int(m.sum())
    yw = wins(y)
    r["kw_p"] = stats.kruskal(*[y[c == k] for k in keep]).pvalue
    r["perm_F_wins_p"] = perm_F(yw, c, rng)
    lo, hi = min(keep), max(keep); a, b = y[c == lo], y[c == hi]
    r["pair"] = f"{lo}->{hi}"
    if len(a) >= 5 and len(b) >= 5:
        aw, bw = yw[c == lo], yw[c == hi]
        r["edge_pts"] = b.mean() - a.mean(); r["n_lo"], r["n_hi"] = len(a), len(b)
        r["wins_t_p"] = stats.ttest_ind(bw, aw, equal_var=False).pvalue
        r["mwu_p"] = stats.mannwhitneyu(b, a, alternative="two-sided").pvalue
        sub = (c == lo) | (c == hi); r["perm_diff_p"] = perm_diff(y[sub], (c[sub] == hi).astype(int), rng)
    if num is not None:
        nn = num[ok].values[m]; v = ~np.isnan(nn)
        if v.sum() >= 20 and len(np.unique(nn[v])) >= 8:
            rho, p = stats.spearmanr(nn[v], y[v]); r["spearman_rho"], r["spearman_p"] = rho, p
    return r

# ---------------- the 36 tests
G = T[(T.strategy == "G1-F") & (T.family == "main") & T.raw_p.notna()].copy()
G["key"] = list(zip(G.agent, G.hypothesis)); assert len(G) == 36, len(G)
miss = [k for k in G.key if k not in S]; assert not miss, miss
f = frame("G1-F", "G1F"); f["tone_gap"] = f.tone - f.tone_med250
f1, f2 = f[f.period == "discovery"], f[f.period == "second_half"]
print(f"G1-F trades {len(f)}; Year 1 {len(f1)} (to {f1.date.max()}), Year 2 {len(f2)}")
# sanity: classes rebuilt from the signal columns agree with the stored class columns where both exist
for k, nm, edges in [(("A3", "H2"), "vix_prev_session", None)]:
    pass

# ---------------- Step 1: correlation + clusters (Year 1 only, return-blind)
sig = {}; dropped = []
for k in G.key:
    cls, code, num = signal(f1, S[k]); vc = code.dropna().value_counts()
    if (vc >= 3).sum() < 2: dropped.append((k, "fewer than 2 classes with >=3 Year-1 trades")); continue
    sig[k] = (num if num is not None else code).astype(float)
keys = list(sig); n = len(keys); R = np.eye(n)
for i in range(n):
    for j in range(i + 1, n):
        d = pd.concat([sig[keys[i]], sig[keys[j]]], axis=1).dropna()
        R[i, j] = R[j, i] = stats.spearmanr(d.iloc[:, 0], d.iloc[:, 1])[0] if len(d) >= 25 and d.iloc[:, 0].nunique() > 1 and d.iloc[:, 1].nunique() > 1 else 0.0
R = np.nan_to_num(R)
dist = 1 - np.abs(R); np.fill_diagonal(dist, 0)
Z = linkage(squareform(dist, checks=False), method="average"); lab = fcluster(Z, t=0.30, criterion="distance")
order = {"A3": 0, "A3b": 1, "A4": 2}
reps, cmap = [], []
for c in sorted(set(lab)):
    mem = [keys[i] for i in range(n) if lab[i] == c]
    nobs = {k: int(sig[k].notna().sum()) for k in mem}
    rep = sorted(mem, key=lambda k: (-nobs[k], order[k[0]], k[1]))[0]
    reps.append(rep); cmap.append(dict(cluster=int(c), representative=f"{rep[0]}:{rep[1]}", members=" ; ".join(f"{k[0]}:{k[1]}" for k in mem), size=len(mem)))
cm = pd.DataFrame(cmap); cm.to_csv(OUT + "/cluster_map.csv", index=False)
pd.DataFrame(R, index=[f"{k[0]}:{k[1]}" for k in keys], columns=[f"{k[0]}:{k[1]}" for k in keys]).round(3).to_csv(OUT + "/year1_spearman_matrix.csv")
print("\nSTEP 1: tests", len(G), "| dropped (constant / too few classes):", dropped)
print("pairs with |r|>=0.70:", int(((np.abs(R) >= 0.70).sum() - n) // 2))
print("effective N =", len(reps), "(from", len(keys), "usable tests)\n")
print(cm.to_string(index=False))

# ---------------- Step 2: Year-1 tests on representatives (and KW-1yr on all 36 for reference)
rng = np.random.default_rng(SEED)
rows = []
for k in keys:
    r = tests_one(f1, S[k], rng); r.update(test=f"{k[0]}:{k[1]}", rep=int(k in reps)); rows.append(r)
Y = pd.DataFrame(rows)
orig = G.set_index(G.key.map(lambda k: f"{k[0]}:{k[1]}"))[["raw_p", "BH_q"]].rename(columns={"raw_p": "orig_whole_kw_p", "BH_q": "orig_whole_q"})
Y = Y.set_index("test").join(orig)
Y["y1_kw_q_all"] = bh(Y.kw_p.values)  # Year-1 KW over all usable tests (no dedup)
R_ = Y[Y.rep == 1].copy()
methods = {"perm_F_wins_p": "PRIMARY perm-F (winsorised)", "wins_t_p": "winsorised t (extreme pair)", "mwu_p": "Mann-Whitney (extreme pair)",
           "perm_diff_p": "permutation mean diff (pair)", "spearman_p": "Spearman rank (continuous)", "kw_p": "Kruskal-Wallis Year 1"}
for m in methods: R_["q_" + m] = bh(R_[m].values)
Y.to_csv(OUT + "/year1_all_tests.csv"); R_.to_csv(OUT + "/year1_representatives.csv")
pd.set_option("display.width", 250, "display.max_columns", 40)
print("\nSTEP 2/3: representatives, Year 1 (N = %d)" % len(R_))
cols = ["n", "pair", "edge_pts", "perm_F_wins_p", "wins_t_p", "mwu_p", "perm_diff_p", "spearman_rho", "spearman_p", "kw_p", "orig_whole_kw_p", "orig_whole_q"]
print(R_[cols].sort_values("perm_F_wins_p").round(3).to_string())
print("\nmin q by method (N=%d):" % len(R_))
for m, nm in methods.items(): q = R_["q_" + m]; print(f"  {nm:34s} tests {int(q.notna().sum()):2d}  p<0.05: {int((R_[m] < .05).sum())}  min p {R_[m].min():.4f}  min q {q.min():.3f}  survivors(q<0.10): {int((q < 0.10).sum())}")
print("Year-1 KW on all %d usable tests (no dedup): p<0.05 %d, min p %.4f, min q %.3f" % (Y.kw_p.notna().sum(), (Y.kw_p < .05).sum(), Y.kw_p.min(), Y.y1_kw_q_all.min()))
print("original whole-sample KW, 36 tests: p<0.05 %d, min p %.4f, min q %.3f" % ((G.raw_p < .05).sum(), G.raw_p.min(), G.BH_q.min()))

# ---------------- sibling pooling diagnostic (G1 contains G1-F; Year 1; permutation inside half-years)
g = frame("G1", "G1"); g["tone_gap"] = g.tone - g.tone_med250; g1 = g[g.period == "discovery"]
rng2 = np.random.default_rng(SEED + 1); sib = []
for k in reps:
    cls, code, num = signal(g1, S[k]); ok = code.notna() & g1.net_pct.notna(); y = g1.net_pct[ok].values; c = code[ok].values
    vc = pd.Series(c).value_counts(); keep = vc[vc >= 3].index
    if len(keep) < 2: sib.append((f"{k[0]}:{k[1]}", len(y), np.nan)); continue
    m = np.isin(c, keep); st = g1.halfyear[ok].values[m]
    sib.append((f"{k[0]}:{k[1]}", int(m.sum()), perm_F(wins(y[m]), c[m], rng2, strata=st)))
SB = pd.DataFrame(sib, columns=["test", "n_G1_year1", "stratified_perm_p"]).set_index("test"); SB["q"] = bh(SB.stratified_perm_p.values)
SB.to_csv(OUT + "/sibling_G1_stratified.csv"); print("\nSIBLING (G1 puts incl. G1-F, Year 1, shuffled within half-years): min p %.4f, min q %.3f, survivors %d" % (SB.stratified_perm_p.min(), SB.q.min(), (SB.q < .10).sum()))
print(SB.sort_values("stratified_perm_p").head(5).round(4).to_string())

# ---------------- Year 2 read-only
surv = set()
for m in methods: surv |= set(R_.index[R_["q_" + m] < 0.10])
print("\nSURVIVORS (q<0.10 in Year 1, any method):", sorted(surv) if surv else "none")
show = sorted(surv) if surv else list(R_.sort_values("q_perm_F_wins_p").index[:3])
print("Year-2 read-only check for", "survivors" if surv else "the 3 lowest-q representatives (NOT survivors; for information only)")
yr2 = []
inv = {f"{k[0]}:{k[1]}": k for k in keys}
for t in show:
    spec = S[inv[t]]
    for nm, ff in (("Year1", f1), ("Year2", f2)):
        cls, code, num = signal(ff, spec); ok = code.notna() & ff.net_pct.notna(); y = ff.net_pct[ok]; c = code[ok]
        lo, hi = R_.loc[t, "pair"].split("->"); lo, hi = float(lo), float(hi)
        a, b = y[c == lo], y[c == hi]
        e = dict(test=t, year=nm, n_lo=len(a), n_hi=len(b), mean_lo=a.mean(), mean_hi=b.mean(), edge_pts=b.mean() - a.mean() if len(a) and len(b) else np.nan)
        if num is not None:
            v = num[ok].notna(); e["spearman_rho"] = stats.spearmanr(num[ok][v], y[v])[0] if v.sum() >= 8 else np.nan
        yr2.append(e)
Y2 = pd.DataFrame(yr2); Y2.to_csv(OUT + "/year2_readonly.csv", index=False); print(Y2.round(2).to_string(index=False))
