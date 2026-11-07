"""Bias module, stage 1: DISCOVERY only (reports/lld/bias.md).

Reference tables, mining null (false-discovery yardstick), leakage AUC scan, regime checks inside discovery,
official-vs-minute gap labels (discovery minute era) and integrity checks. No validation label is read here.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from scipy import stats

import bias_common as bc
import stats_utils as su

OUT = bc.OUT
HYP = []          # hypothesis log rows
N_PERM = 200
RATE_TARGETS = bc.TARGETS + ["gap_flat"]
MEAN_TARGETS = ["y_range_pct", "y_oc", "y_gap_pct"]


def hyp(family, ul, split, test, n, effect, p, extra=""):
    HYP.append(dict(family=family, ul=ul, split=split, test=test, n=int(n) if n == n else n,
                    effect=effect, p=p, extra=extra))


# ------------------------------------------------------------------ reference tables
def group_specs(D):
    specs = [("all", pd.Series("all", index=D.index))]
    for col in ["ctx", "dk", "xkind", "wd_regime", "cal_next_dow", "gap_after", "o_gap_dir", "vix_terc"]:
        specs.append((col, D[col].fillna("unknown").astype(str)))
    specs.append(("xkind_ctx", D["xkind"] + "|" + D["ctx"]))
    specs.append(("regime_ctx", D["wd_regime"] + "|" + D["ctx"]))
    return specs


def ref_table(D, ul, split, log=True):
    rows = []
    base = {t: D[t].mean() for t in RATE_TARGETS}
    for tag, lab in group_specs(D):
        for lev in sorted(lab.unique()):
            m = lab == lev
            for t in RATE_TARGETS:
                x = D.loc[m, t].dropna()
                r = bc.rate_row(x.sum(), len(x), base[t])
                r.update(ul=ul, split=split, tag=tag, level=lev, target=t, stat="rate")
                if tag == "all":
                    r["p"] = np.nan
                rows.append(r)
                if log and tag != "all" and len(x) > 0:
                    hyp("ref", ul, split, f"{tag}={lev} {t} rate vs base", len(x), r["diff"], r["p"])
            for t in MEAN_TARGETS:
                x = D.loc[m, t].dropna().values
                c = D.loc[~m, t].dropna().values
                mu, lo, hi = su.mean_ci(x)
                p = stats.ttest_ind(x, c, equal_var=False).pvalue if (tag != "all" and len(x) > 1 and len(c) > 1) else np.nan
                rows.append(dict(ul=ul, split=split, tag=tag, level=lev, target=t, stat="mean", n=len(x), rate=mu,
                                 ci_lo=lo, ci_hi=hi, base=D[t].mean(), diff=mu - D[t].mean(), p=p, small_n=len(x) < 30))
                if log and tag != "all" and len(x) > 1:
                    hyp("ref", ul, split, f"{tag}={lev} mean {t} vs rest (Welch)", len(x), mu - D[t].mean(), p)
    return pd.DataFrame(rows)


def transition(D, ul, split, gcol_prev="o_gap_dir", gcol_next="y_gap_dir", label="minute"):
    ct = pd.crosstab(D[gcol_prev], D[gcol_next])
    chi = stats.chi2_contingency(ct.values)
    rows = []
    base = D[gcol_next].value_counts(normalize=True)
    for a in ct.index:
        n = ct.loc[a].sum()
        for b in ct.columns:
            k = ct.loc[a, b]
            r, lo, hi = su.wilson(k, n)
            rows.append(dict(ul=ul, split=split, labels=label, prev=a, nxt=b, n=n, k=k, rate=r, ci_lo=lo, ci_hi=hi,
                             base=base[b], diff=r - base[b], p=su.binom_p(k, n, base[b]),
                             chi2_p=chi.pvalue))
    return pd.DataFrame(rows), chi.pvalue


# ------------------------------------------------------------------ mining null
def build_rules(D, cutsrc):
    conds = []
    for f in bc.MINING_FEATURES:
        q20, q80 = cutsrc[f].quantile([0.2, 0.8]).values
        conds.append((f"{f}<={q20:.4g}", (D[f] <= q20).values))
        conds.append((f"{f}>={q80:.4g}", (D[f] >= q80).values))
    ctxs = [("t+1 D0", (D["ctx"] == "D0").values), ("t+1 D-1", (D["dk"] == "D-1").values),
            ("t+1 D+1", (D["ctx"] == "D+1").values), ("t+1 monthly cycle", (D["xkind"] == "monthly").values)]
    rules = list(conds)
    for cn, cm in conds:
        for xn, xm in ctxs:
            rules.append((f"{cn} & {xn}", cm & xm))
    names = [r[0] for r in rules]
    M = np.column_stack([r[1] for r in rules])
    return names, M


class Miner:
    def __init__(self, D, names, M, targets=bc.TARGETS, min_n=30):
        self.names, self.M = names, M
        self.Y = D[targets].values.astype(float)
        self.targets = targets
        self.base = self.Y.mean(0)
        self.nr = M.sum(0)
        self.tested = self.nr >= min_n
        R, J = M.shape[1], len(targets)
        maxn = int(self.nr.max())
        self.ptab = np.ones((R, J, maxn + 1))
        for r in range(R):
            if self.tested[r]:
                for j in range(J):
                    self.ptab[r, j, : self.nr[r] + 1] = bc.binom_two_sided_table(int(self.nr[r]), self.base[j])
        self.Mi = M.astype(np.int32)

    def evaluate(self, Y):
        K = self.Mi.T @ Y.astype(np.int32)                         # R x J
        R, J = K.shape
        p = self.ptab[np.arange(R)[:, None], np.arange(J)[None, :], K]
        rate = K / np.maximum(self.nr, 1)[:, None]
        edge = rate - self.base[None, :]
        p[~self.tested] = np.nan
        edge[~self.tested] = np.nan
        return K, rate, edge, p


NBINS = [(30, 59), (60, 119), (120, 249), (250, 100000)]


def run_metrics(miner, edge, p):
    q, _ = su.bh(p.ravel(), 0.10)
    q = q.reshape(p.shape)
    out = dict(n_tests=int(np.isfinite(p).sum()), n_p05=int(np.nansum(p < 0.05)), n_q10=int(np.nansum(q < 0.10)),
               min_p=float(np.nanmin(p)), best_edge=float(np.nanmax(np.abs(edge))))
    sig = np.where(p < 0.05, np.abs(edge), np.nan)
    out["best_edge_sig"] = float(np.nanmax(sig)) if np.isfinite(sig).any() else 0.0
    # direction targets (gap_up, gap_down, oc_pos, cc_pos = columns 0..3) vs volatility targets (4, 5)
    out["n_q10_dir_in_mixed"] = int(np.nansum(q[:, :4] < 0.10))
    qd, _ = su.bh(p[:, :4].ravel(), 0.10)
    out["n_q10_dir_only"] = int(np.nansum(qd < 0.10))
    out["n_p05_dir"] = int(np.nansum(p[:, :4] < 0.05))
    out["n_q10_vol"] = int(np.nansum(q[:, 4:] < 0.10))
    for j, t in enumerate(miner.targets):
        out[f"n_p05_{t}"] = int(np.nansum(p[:, j] < 0.05))
        out[f"best_edge_{t}"] = float(np.nanmax(np.abs(edge[:, j])))
    for lo, hi in NBINS:
        m = (miner.nr >= lo) & (miner.nr <= hi) & miner.tested
        out[f"best_edge_n{lo}"] = float(np.nanmax(np.abs(edge[m]))) if m.any() else np.nan
    return out, q


def mining(Ds):
    """Ds: {ul: usable discovery rows}. Real + 2 x 200 null runs; returns tables."""
    dates = {ul: Ds[ul]["date"].values for ul in Ds}
    assert np.array_equal(dates["NIFTY"], dates["BANKNIFTY"]), "panels must share the discovery row set"
    blocks = bc.week_blocks(dates["NIFTY"])
    miners, real_rows, real_p = {}, [], {}
    for ul, D in Ds.items():
        names, M = build_rules(D, D)
        mn = Miner(D, names, M)
        miners[ul] = mn
        K, rate, edge, p = mn.evaluate(mn.Y)
        met, q = run_metrics(mn, edge, p)
        real_p[ul] = (p, edge, met)
        for r in range(len(names)):
            for j, t in enumerate(mn.targets):
                real_rows.append(dict(ul=ul, rule=names[r], kind="single" if r < 40 else "two", target=t,
                                      n=int(mn.nr[r]), tested=bool(mn.tested[r]), k=int(K[r, j]), rate=rate[r, j],
                                      base=mn.base[j], edge=edge[r, j], p=p[r, j], q_ul=q[r, j]))
                if mn.tested[r]:
                    hyp("mining_real", ul, "discovery", f"rule [{names[r]}] {t} rate vs base", mn.nr[r], edge[r, j],
                        p[r, j])
    real = pd.DataFrame(real_rows)
    pb = np.concatenate([real_p[u][0].ravel() for u in bc.ULS])
    qb, _ = su.bh(pb, 0.10)
    real["q_both"] = np.nan
    for i, u in enumerate(bc.ULS):
        n = real_p[u][0].size
        real.loc[real.ul == u, "q_both"] = qb[i * n:(i + 1) * n]
    runs = []
    rows_real = []
    for ul in bc.ULS:
        m = dict(real_p[ul][2])
        m.update(ul=ul, variant="real", perm=-1)
        rows_real.append(m)
    nb_edges = {(v, ul): [] for v in ("week", "week_same_len", "dir_only") for ul in bc.ULS}
    # variants: week = all 6 labels permuted by whole weeks; week_same_len = weeks swapped only with weeks of the
    # same length; dir_only = only the 4 direction labels permuted (volatility labels stay real), to measure how
    # true volatility effects in the same BH family lower the bar for direction rules
    for variant, same, seed in (("week", False, 0), ("week_same_len", True, 1), ("dir_only", False, 2)):
        rng = np.random.default_rng(bc.SEED + seed)
        for i in range(N_PERM):
            idx = bc.perm_index(blocks, rng, same_length=same)
            ps = []
            for ul in bc.ULS:
                mn = miners[ul]
                Yp = mn.Y[idx]
                if variant == "dir_only":
                    Yp = np.column_stack([mn.Y[idx][:, :4], mn.Y[:, 4:]])
                K, rate, edge, p = mn.evaluate(Yp)
                met, _ = run_metrics(mn, edge, p)
                met.update(ul=ul, variant=variant, perm=i)
                runs.append(met)
                ps.append(p.ravel())
                nb_edges[(variant, ul)].append((np.abs(edge), mn.nr.copy(), mn.tested.copy()))
            qq, _ = su.bh(np.concatenate(ps), 0.10)
            runs.append(dict(ul="BOTH", variant=variant, perm=i, n_q10=int(np.nansum(qq < 0.10)),
                             n_p05=int(np.nansum(np.concatenate(ps) < 0.05))))
    runs = pd.DataFrame(runs + rows_real)
    rb = dict(ul="BOTH", variant="real", perm=-1, n_q10=int(np.nansum(qb < 0.10)), n_p05=int(np.nansum(pb < 0.05)))
    runs = pd.concat([runs, pd.DataFrame([rb])], ignore_index=True)
    # summary
    summ = []
    metrics = [c for c in runs.columns if c not in ("ul", "variant", "perm")]
    for variant in ("week", "week_same_len", "dir_only"):
        for ul in bc.ULS + ["BOTH"]:
            nul = runs[(runs.variant == variant) & (runs.ul == ul)]
            rl = runs[(runs.variant == "real") & (runs.ul == ul)].iloc[0]
            for c in metrics:
                v = nul[c].dropna()
                if v.empty or pd.isna(rl[c]):
                    continue
                if c == "min_p":
                    emp = (1 + (v <= rl[c]).sum()) / (1 + len(v))
                else:
                    emp = (1 + (v >= rl[c]).sum()) / (1 + len(v))
                summ.append(dict(variant=variant, ul=ul, metric=c, null_mean=v.mean(), null_p50=v.median(),
                                 null_p95=v.quantile(0.95), null_p99=v.quantile(0.99), real=rl[c], emp_p=emp,
                                 n_perm=len(v)))
    summ = pd.DataFrame(summ)
    # |edge| yardstick per target and n-bin (all null tests pooled)
    nbrows = []
    for (variant, ul), lst in nb_edges.items():
        if variant == "dir_only":
            continue
        E = np.stack([a for a, _, _ in lst])          # perm x R x J
        nr, tested = lst[0][1], lst[0][2]
        for lo, hi in NBINS:
            m = (nr >= lo) & (nr <= hi) & tested
            if not m.any():
                continue
            for j, t in enumerate(bc.TARGETS):
                e = E[:, m, j]
                nbrows.append(dict(variant=variant, ul=ul, target=t, n_bin=f"{lo}-{hi if hi < 100000 else 'max'}",
                                   n_rules=int(m.sum()), abs_edge_p95=np.quantile(e, 0.95),
                                   abs_edge_p99=np.quantile(e, 0.99), max_per_run_p95=np.quantile(e.max(1), 0.95)))
    return real, runs, summ, pd.DataFrame(nbrows), miners


# ------------------------------------------------------------------ leakage AUC
def auc_scan(D, ul, split="discovery"):
    feats = [c for c in D.columns if (c.startswith("f_") or c.startswith("f1515_"))
             and pd.api.types.is_numeric_dtype(D[c]) and not pd.api.types.is_bool_dtype(D[c])]
    feats += [c for c in D.columns if c.startswith("f_") and pd.api.types.is_bool_dtype(D[c])]
    gud = np.where(D["y_gap_dir"] == "up", 1.0, np.where(D["y_gap_dir"] == "down", 0.0, np.nan))
    tg = {"gap_up_vs_down": gud, "oc_pos": D["oc_pos"].values, "big_exc": D["big_exc"].values}
    rows = []
    for f in feats:
        x = bc._f(D[f]).values
        for tname, y in tg.items():
            a, n1, n0, p = bc.auc(x, y)
            rows.append(dict(ul=ul, split=split, feature=f, target=tname, auc=a, n1=n1, n0=n0, p=p,
                             dev=abs(a - 0.5) if a == a else np.nan, flag=(abs(a - 0.5) > 0.15) if a == a else False))
            if a == a and p == p:
                hyp("auc", ul, split, f"AUC {f} -> {tname}", n1 + n0, a - 0.5, p)
    return pd.DataFrame(rows)


def auc_controls(D, Pfull, ul):
    rows = []
    gud = np.where(D["y_gap_dir"] == "up", 1.0, np.where(D["y_gap_dir"] == "down", 0.0, np.nan))
    nxt_mom1 = Pfull["f_mom1"].shift(-1).reindex(D.index).values
    cases = [("positive: y_gap_pct", D["y_gap_pct"].values, gud, "gap_up_vs_down"),
             ("positive: y_oc", D["y_oc"].values, D["oc_pos"].values, "oc_pos"),
             ("planted leak: f_mom1 of t+1", nxt_mom1, D["oc_pos"].values, "oc_pos"),
             ("planted leak: f_mom1 of t+1", nxt_mom1, gud, "gap_up_vs_down")]
    for name, x, y, t in cases:
        a, n1, n0, p = bc.auc(x, y)
        rows.append(dict(ul=ul, control=name, target=t, auc=a, n1=n1, n0=n0, p=p))
    rng = np.random.default_rng(bc.SEED)
    for nsub, label in ((len(D), "full discovery"), (int(D["f1515_rv"].notna().sum()), "minute era (f1515 n)")):
        y = D["oc_pos"].values[:nsub]
        aucs = [bc.auc(rng.normal(size=nsub), y)[0] for _ in range(200)]
        aucs = np.abs(np.array(aucs) - 0.5)
        rows.append(dict(ul=ul, control=f"negative: noise feature, n={nsub} ({label})", target="oc_pos",
                         auc=np.nan, n1=np.nan, n0=np.nan, p=np.nan, null_absdev_p95=np.quantile(aucs, 0.95),
                         null_absdev_max=aucs.max()))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ regimes inside discovery
def regimes_disc(D, ul):
    rows = []
    tg = bc.TARGETS + ["gap_flat"]

    def comp(name, m, lev, split="discovery"):
        for t in tg:
            a = D.loc[m, t]
            b = D.loc[~m, t]
            p = su.two_prop(a.sum(), len(a), b.sum(), len(b))
            r, lo, hi = su.wilson(a.sum(), len(a))
            rows.append(dict(ul=ul, split=split, regime=name, level=lev, target=t, n=len(a), rate=r, ci_lo=lo,
                             ci_hi=hi, rest_rate=b.mean(), diff=r - b.mean(), p=p))
            hyp("regime", ul, split, f"{name}={lev} {t} vs rest", len(a), r - b.mean(), p)
        for t in ["y_range_pct"]:
            a, b = D.loc[m, t].dropna(), D.loc[~m, t].dropna()
            p = stats.ttest_ind(a, b, equal_var=False).pvalue
            rows.append(dict(ul=ul, split=split, regime=name, level=lev, target="mean " + t, n=len(a), rate=a.mean(),
                             ci_lo=np.nan, ci_hi=np.nan, rest_rate=b.mean(), diff=a.mean() - b.mean(), p=p))
            hyp("regime", ul, split, f"{name}={lev} mean {t} vs rest", len(a), a.mean() - b.mean(), p)

    for y in sorted(D["year"].unique()):
        comp("year", D["year"] == y, y)
    half = D["year"] + np.where(D["y_date"].str[5:7] <= "06", "H1", "H2")
    for h in sorted(half.unique()):
        comp("half", half == h, h)
    comp("covid", D["covid"], "2020-02-20..2020-06-30")
    for v in ["low", "mid", "high"]:
        comp("vix_terc", D["vix_terc"] == v, v)
    comp("label_source", D["src"] == "spot_1m", "minute close (t >= 2021-10-20)")
    # homogeneity across years (chi-square)
    for t in tg:
        ct = pd.crosstab(D["year"], D[t])
        ch = stats.chi2_contingency(ct.values)
        rows.append(dict(ul=ul, split="discovery", regime="year_chi2", level="2018-2022", target=t, n=len(D),
                         rate=np.nan, p=ch.pvalue))
        hyp("regime", ul, "discovery", f"year homogeneity chi2 {t}", len(D), np.nan, ch.pvalue)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ official vs minute close
def official_labels(P):
    P = P.copy()
    P["y_gap_off"] = (P["px_open"].shift(-1) / P["px_close_official"] - 1) * 100
    P["o_gap_off"] = (P["px_open"] / P["px_close_official"].shift(1) - 1) * 100
    for c, s in (("y_gap_dir_off", "y_gap_off"), ("o_gap_dir_off", "o_gap_off")):
        g = P[s]
        P[c] = np.where(g.isna(), None, np.where(g.abs() < 0.1, "flat", np.where(g > 0, "up", "down")))
    P["close_noise"] = (P["px_close"] / P["px_close_official"] - 1) * 100
    P["minute_era"] = (P["src"] == "spot_1m") & (P["y_src"] == "spot_1m")
    return P


def label_check(Pm, ul, split, miner_ctx=None):
    """Pm: usable rows of one split in the minute era with official labels."""
    rows = []
    agree = (Pm["y_gap_dir"] == Pm["y_gap_dir_off"]).mean()
    rows.append(dict(ul=ul, split=split, item="gap dir agreement minute vs official", value=agree, n=len(Pm)))
    ct = pd.crosstab(Pm["y_gap_dir"], Pm["y_gap_dir_off"])
    for a in ct.index:
        for b in ct.columns:
            rows.append(dict(ul=ul, split=split, item=f"confusion minute={a} official={b}", value=ct.loc[a, b], n=len(Pm)))
    for d in ["up", "flat", "down"]:
        km, ko = (Pm["y_gap_dir"] == d).sum(), (Pm["y_gap_dir_off"] == d).sum()
        p = su.two_prop(km, len(Pm), ko, len(Pm))
        rows.append(dict(ul=ul, split=split, item=f"rate {d} minute", value=km / len(Pm), n=len(Pm)))
        rows.append(dict(ul=ul, split=split, item=f"rate {d} official", value=ko / len(Pm), n=len(Pm), p=p))
        hyp("label", ul, split, f"gap {d} rate minute vs official close", len(Pm), (km - ko) / len(Pm), p,
            "two_prop on the same rows (not independent; indicative)")
    r = stats.pearsonr(Pm["close_noise"], Pm["y_gap_pct"])
    rows.append(dict(ul=ul, split=split, item="corr(minute-official close, y_gap minute)", value=r.statistic,
                     n=len(Pm), p=r.pvalue))
    hyp("label", ul, split, "corr(close noise, y_gap minute)", len(Pm), r.statistic, r.pvalue)
    slope = np.polyfit(Pm["close_noise"], Pm["y_gap_pct"], 1)[0]
    rows.append(dict(ul=ul, split=split, item="slope y_gap on close noise", value=slope, n=len(Pm)))
    for lab, ycol in (("minute", "y_gap_pct"), ("official", "y_gap_off")):
        r = stats.pearsonr(Pm["f_mom1"], Pm[ycol])
        rows.append(dict(ul=ul, split=split, item=f"corr(f_mom1, y_gap {lab})", value=r.statistic, n=len(Pm),
                         p=r.pvalue))
        hyp("label", ul, split, f"corr(f_mom1, y_gap {lab})", len(Pm), r.statistic, r.pvalue)
    near = ((Pm["y_gap_pct"].abs() - 0.1).abs() <= 0.05).mean()
    rows.append(dict(ul=ul, split=split, item="share |gap| within 0.05 pp of the 0.1 % band edge", value=near, n=len(Pm)))
    return pd.DataFrame(rows)


def flat_band(D, ul, split, col="y_gap_pct"):
    rows = []
    for b in (0.05, 0.10, 0.15, 0.20):
        g = D[col].dropna()
        rows.append(dict(ul=ul, split=split, label=col, band=b, n=len(g), up=(g >= b).mean(), flat=(g.abs() < b).mean(),
                         down=(g <= -b).mean()))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ integrity
def integrity(P, ul):
    rows = []
    c = P["px_close"]
    chk = {
        "f_mom1": (c / c.shift(1) - 1) * 100,
        "f_close_pos": (c - P["px_low"]) / (P["px_high"] - P["px_low"]),
        "f_dist_high20": (c / P["px_high"].shift(1).rolling(20).max() - 1) * 100,
        "f_hv10": np.log(c / c.shift(1)).rolling(10).std() * np.sqrt(252) * 100,
        "y_gap_pct": (P["px_open"].shift(-1) / c - 1) * 100,
        "y_oc": (P["px_close"].shift(-1) / P["px_open"].shift(-1) - 1) * 100,
        "y_cc": (c.shift(-1) / c - 1) * 100,
    }
    for k, v in chk.items():
        d = (v - P[k]).abs()
        ok = d.notna()
        rows.append(dict(ul=ul, check=f"recompute {k} from px columns", n=int(ok.sum()),
                         max_abs_diff=float(d[ok].max()), share_match_1e6=float((d[ok] < 1e-6).mean())))
    # shift tests: feature correlates with its own definition at lag 0, not with the future
    for k, v in (("f_mom1", chk["f_mom1"]),):
        for lag in (-1, 1):
            d = (v.shift(lag) - P[k]).abs()
            rows.append(dict(ul=ul, check=f"{k} vs recompute shifted {lag:+d} (must not match)", n=int(d.notna().sum()),
                             max_abs_diff=float(d.max()), share_match_1e6=float((d < 1e-6).mean())))
    # y_X == o_X of the next row
    for k in ["gap_pct", "oc", "cc", "range_pct", "max_exc"]:
        d = (P[f"o_{k}"].shift(-1) - P[f"y_{k}"]).abs()
        rows.append(dict(ul=ul, check=f"y_{k} == o_{k} of next row", n=int(d.notna().sum()),
                         max_abs_diff=float(d.max()), share_match_1e6=float((d.dropna() < 1e-9).mean())))
    # VIX vs raw vix_daily (raw filtered to <= 2024-06-30)
    import os
    store = os.environ.get("INDEX_STORE", "../fo-index-data/data/index")
    vp = Path(store) if Path(store).is_absolute() else (bc.ROOT.parent / store)
    vp = (vp / "vix_daily.parquet").resolve()
    if vp.exists():
        V = pd.read_parquet(vp)
        dcol = [c for c in V.columns if "date" in c.lower()][0]
        ccol = [c for c in V.columns if c.lower() == "close"][0]
        V["d"] = pd.to_datetime(V[dcol]).dt.strftime("%Y-%m-%d")
        V = V[V["d"] <= bc.OPEN_END].set_index("d")[ccol]
        sub = P[P["f_vix_src"] == "vix_daily"]
        for lag in (0, -1, 1):
            vv = V.reindex(pd.Series(sub["date"]).shift(-lag).values)
            d = np.abs(vv.values - sub["f_vix_close"].values)
            ok = ~np.isnan(d)
            rows.append(dict(ul=ul, check=f"f_vix_close vs raw vix_daily of row {lag:+d}", n=int(ok.sum()),
                             max_abs_diff=float(np.nanmax(d)), share_match_1e6=float((d[ok] < 1e-6).mean())))
    return pd.DataFrame(rows)


def redated(P, ul):
    S = pd.read_csv(bc.ROOT / "data" / f"sessions_{ul}.csv", dtype=str)
    S = S[S["date"] <= bc.OPEN_END].set_index("date")
    x = P[["date", "y_date", "f_opt_near_expiry", "cal_next_sessions_to_expiry"]].dropna(subset=["y_date"]).copy()
    x["cal_next_expiry_final"] = S["next_expiry"].reindex(x["y_date"]).values
    x["listed"] = x["f_opt_near_expiry"].astype(str).str[:10]
    d = x[x["listed"] != x["cal_next_expiry_final"]].copy()
    d["ul"] = ul
    R = pd.read_csv(bc.ROOT / "data" / "expiry_relabels.csv", dtype=str)
    R = R[(R["underlying"] == ul) & (R["old_last_traded"] <= bc.OPEN_END)]
    d["is_relabel_old"] = d["listed"].isin(R["old_expiry"])
    return d


# ------------------------------------------------------------------ main
def main():
    LOGF = bc.log_out("discovery")
    Ps, Ds, Dfull = {}, {}, {}
    ref, trans, aucs, ctrls, regs, labs, bands, integ, red = [], [], [], [], [], [], [], [], []
    for ul in bc.ULS:
        P, cuts = bc.load(ul)
        P = official_labels(P)
        Ps[ul] = P
        print(f"{ul}: open rows {len(P)}, VIX tercile cuts (discovery) {cuts.round(2).tolist()}")
        disc = P[P["split"] == "discovery"]
        print(f"  discovery rows {len(disc)}, split_edge {int(disc['split_edge'].sum())}, "
              f"unusable {int((~disc['usable']).sum())}")
        D = disc[disc["usable"]].copy()
        Ds[ul] = D
        ref.append(ref_table(D, ul, "discovery"))
        t, chip = transition(D, ul, "discovery")
        trans.append(t)
        hyp("ref", ul, "discovery", "gap dir transition chi2 (o_gap_dir x y_gap_dir)", len(D), np.nan, chip)
        aucs.append(auc_scan(D, ul))
        ctrls.append(auc_controls(D, P, ul))
        regs.append(regimes_disc(D, ul))
        Dm = D[D["minute_era"] & D["y_gap_dir_off"].notna() & D["o_gap_dir_off"].notna()]
        labs.append(label_check(Dm, ul, "discovery"))
        t2, _ = transition(Dm, ul, "discovery", "o_gap_dir", "y_gap_dir", "minute (minute era)")
        t3, _ = transition(Dm, ul, "discovery", "o_gap_dir_off", "y_gap_dir_off", "official (minute era)")
        trans += [t2, t3]
        bands += [flat_band(D, ul, "discovery"), flat_band(Dm, ul, "discovery", "y_gap_off")]
        integ.append(integrity(P, ul))
        red.append(redated(P, ul))
    pd.concat(ref).to_csv(OUT / "ref_discovery.csv", index=False)
    pd.concat(trans).to_csv(OUT / "gap_transition_discovery.csv", index=False)
    A = pd.concat(aucs)
    A.to_csv(OUT / "auc_leakage.csv", index=False)
    pd.concat(ctrls).to_csv(OUT / "auc_controls.csv", index=False)
    pd.concat(regs).to_csv(OUT / "regimes_discovery.csv", index=False)
    pd.concat(labs).to_csv(OUT / "label_official_vs_minute_discovery.csv", index=False)
    pd.concat(bands).to_csv(OUT / "flat_band_discovery.csv", index=False)
    pd.concat(integ).to_csv(OUT / "integrity.csv", index=False)
    pd.concat(red).to_csv(OUT / "redated_rows.csv", index=False)

    print("\nMining null: 200 rules x 6 targets per UL, 200 week-block permutations x 2 variants ...")
    real, runs, summ, nb, miners = mining(Ds)
    real.to_csv(OUT / "mining_real.csv", index=False)
    runs.to_csv(OUT / "mining_null_runs.csv", index=False)
    summ.to_csv(OUT / "mining_null_summary.csv", index=False)
    nb.to_csv(OUT / "mining_null_by_nbin.csv", index=False)
    show = summ[summ.metric.isin(["n_p05", "n_q10", "best_edge", "n_p05_dir", "n_q10_dir_in_mixed", "n_q10_dir_only",
                                  "n_q10_vol"])]
    print(show.round(4).to_string(index=False))

    # gap-label flips in the mining rules (discovery minute era): minute vs official labels
    flips = []
    for ul in bc.ULS:
        D = Ds[ul]
        m = (D["minute_era"] & D["y_gap_dir_off"].notna()).values
        Dm = D[m].copy()
        names, M = build_rules(Dm, D)       # cut points from all discovery rows
        Dm["gap_up_off"] = (Dm["y_gap_dir_off"] == "up").astype(float)
        Dm["gap_down_off"] = (Dm["y_gap_dir_off"] == "down").astype(float)
        mm = Miner(Dm, names, M, ["gap_up", "gap_down"])
        mo = Miner(Dm, names, M, ["gap_up_off", "gap_down_off"])
        _, _, em, pm = mm.evaluate(mm.Y)
        _, _, eo, po = mo.evaluate(mo.Y)
        ok = np.isfinite(pm)
        sm, so = (pm < 0.05) & ok, (po < 0.05) & ok
        for j, t in enumerate(["gap_up", "gap_down"]):
            flips.append(dict(ul=ul, target=t, n_rows=int(m.sum()), n_rules_tested=int(ok[:, j].sum()),
                              sig_minute=int(sm[:, j].sum()), sig_official=int(so[:, j].sum()),
                              sig_both=int((sm[:, j] & so[:, j]).sum()),
                              flips=int((sm[:, j] ^ so[:, j]).sum()),
                              sign_flips=int((np.sign(em[:, j]) != np.sign(eo[:, j]))[ok[:, j]].sum()),
                              corr_edge=float(np.corrcoef(em[ok[:, j], j], eo[ok[:, j], j])[0, 1]),
                              base_minute=mm.base[j], base_official=mo.base[j]))
        # AUC change per feature
        gm = np.where(Dm["y_gap_dir"] == "up", 1.0, np.where(Dm["y_gap_dir"] == "down", 0.0, np.nan))
        go = np.where(Dm["y_gap_dir_off"] == "up", 1.0, np.where(Dm["y_gap_dir_off"] == "down", 0.0, np.nan))
        for f in [c for c in Dm.columns if c.startswith(("f_", "f1515_")) and pd.api.types.is_float_dtype(Dm[c])]:
            a1, a2 = bc.auc(Dm[f].values, gm)[0], bc.auc(Dm[f].values, go)[0]
            flips.append(dict(ul=ul, target="AUC gap_up_vs_down", feature=f, auc_minute=a1, auc_official=a2,
                              d_auc=a2 - a1))
    pd.DataFrame(flips).to_csv(OUT / "label_rule_flips.csv", index=False)

    H = pd.DataFrame(HYP)
    H.insert(0, "id", [f"H{i:05d}" for i in range(1, len(H) + 1)])
    H.to_csv(OUT / "hypotheses_discovery.csv", index=False)
    print(f"\nhypotheses logged (discovery): {len(H)}  by family: {H.family.value_counts().to_dict()}")
    fl = A[A.flag]
    print(f"AUC flags |AUC-0.5|>0.15: {len(fl)}")
    print(fl[["ul", "feature", "target", "auc", "n1", "n0"]].to_string(index=False))
    LOGF.close()


if __name__ == "__main__":
    main()
