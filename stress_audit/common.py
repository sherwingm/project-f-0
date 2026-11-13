"""Shared helpers for the stress audit (offline, read-only on every production file).

Pre-registered in stress_audit/PREREG.md (+ AMENDMENTS.md). Nothing here writes outside stress_audit/results/.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from scanner.stats import clustered_t

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "stress_audit" / "results"
SEED = 20261113
IDX = Path(os.environ.get("INDEX_STORE") or ROOT.parent / "fo-index-data" / "data" / "index")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def manifest_entry(path: Path) -> dict:
    return {"file": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}


# ---------------------------------------------------------------- regimes (daily files already on this PC)
def nifty_daily() -> pd.DataFrame:
    d = pd.read_csv(ROOT / "data" / "eod2" / "nifty 50.csv")
    d.columns = [c.lower() for c in d.columns]
    d["date"] = pd.to_datetime(d["date"]).dt.strftime("%Y-%m-%d")
    d = d.sort_values("date").reset_index(drop=True)
    d["ret"] = d["close"].pct_change() * 100
    d["vol20"] = d["ret"].rolling(20).std()
    d["ma50"] = d["close"].rolling(50).mean()
    d["above50"] = d["close"] > d["ma50"]
    return d


def vix_daily() -> pd.Series:
    v = pd.read_parquet(IDX / "vix_daily.parquet")
    v["date"] = pd.to_datetime(v["date"]).dt.strftime("%Y-%m-%d")
    return v.dropna(subset=["close"]).set_index("date")["close"]


def prev_value(series: pd.Series, day: str):
    """The last value strictly before `day` (what was known the evening before)."""
    s = series[series.index < day]
    return float(s.iloc[-1]) if len(s) else np.nan


def tercile_label(values: pd.Series, cuts) -> pd.Series:
    lo, hi = cuts
    return values.map(lambda x: "n/a" if pd.isna(x) else ("low" if x <= lo else ("high" if x > hi else "mid")))


def add_regimes(t: pd.DataFrame, day_col: str) -> pd.DataFrame:
    """VIX tercile, NIFTY 20-day volatility tercile and 50-day trend, all measured the evening before; tercile cuts from the window itself."""
    n = nifty_daily().set_index("date")
    vix = vix_daily()
    t = t.copy()
    t["vix_prev"] = [prev_value(vix, d) for d in t[day_col]]
    t["vol20_prev"] = [prev_value(n["vol20"].dropna(), d) for d in t[day_col]]
    t["trend_prev"] = [("up" if bool(n["above50"][n.index < d].iloc[-1]) else "down") if (n.index < d).any() else "n/a" for d in t[day_col]]
    for col, name in (("vix_prev", "vix_regime"), ("vol20_prev", "vol_regime")):
        q = t[col].quantile([1 / 3, 2 / 3]).to_numpy()
        t[name] = tercile_label(t[col], q)
    ret = n["ret"].abs()
    t["abs_ret_day"] = [float(ret.get(d, np.nan)) for d in t[day_col]]
    cut = np.nanquantile(t["abs_ret_day"], 0.9)
    t["volatile_day"] = t["abs_ret_day"] >= cut
    t["half_year"] = [d[:4] + (" H1" if d[5:7] <= "06" else " H2") for d in t[day_col]]
    return t


# ---------------------------------------------------------------- metrics
def drawdown(rs: pd.Series, days: pd.Series) -> dict:
    """Max drawdown (Rs) on the cumulative sum in date order; longest time under water (calendar days); days from worst trough to a new high."""
    if rs.empty:
        return {"max_dd_rs": 0.0, "longest_underwater_days": 0, "trough_to_recovery_days": None}
    order = np.argsort(pd.to_datetime(days).to_numpy(), kind="stable")
    cum = np.cumsum(rs.to_numpy()[order])
    d = pd.to_datetime(days).to_numpy()[order]
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    dd = cum - peak
    i_tr = int(np.argmin(dd))
    longest, start = 0, None
    for i in range(len(cum)):
        if dd[i] < 0:
            start = d[i] if start is None else start
            longest = max(longest, int((d[i] - start) / np.timedelta64(1, "D")))
        else:
            start = None
    rec = None
    after = np.where(cum[i_tr:] >= peak[i_tr])[0]
    if dd[i_tr] < 0 and len(after):
        rec = int((d[i_tr + after[0]] - d[i_tr]) / np.timedelta64(1, "D"))
    return {"max_dd_rs": round(float(dd.min()), 2), "longest_underwater_days": longest, "trough_to_recovery_days": rec}


def cluster_boot_ci(pct: np.ndarray, dates: np.ndarray, n=5000, seed=SEED) -> tuple[float, float]:
    """95 % interval of the mean by resampling DATES with replacement (same-day trades stay together)."""
    rng = np.random.default_rng(seed)
    u, inv = np.unique(dates, return_inverse=True)
    sums = np.bincount(inv, weights=pct, minlength=len(u))
    cnt = np.bincount(inv, minlength=len(u)).astype(float)
    if len(u) < 2:
        return (np.nan, np.nan)
    idx = rng.integers(0, len(u), size=(n, len(u)))
    m = sums[idx].sum(axis=1) / cnt[idx].sum(axis=1)
    return (float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)))


def block_boot_ci(pct: np.ndarray, dates: np.ndarray, block=5, n=5000, seed=SEED) -> tuple[float, float]:
    """95 % interval of the mean by a moving-block bootstrap over date-ordered trade DAYS (blocks of `block` consecutive trade dates)."""
    rng = np.random.default_rng(seed + 1)
    u, inv = np.unique(dates, return_inverse=True)
    if len(u) < block + 1:
        return (np.nan, np.nan)
    sums = np.bincount(inv, weights=pct, minlength=len(u))
    cnt = np.bincount(inv, minlength=len(u)).astype(float)
    nb = int(np.ceil(len(u) / block))
    starts = rng.integers(0, len(u) - block + 1, size=(n, nb))
    pos = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, : len(u)]
    m = sums[pos].sum(axis=1) / cnt[pos].sum(axis=1)
    return (float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)))


def summarize(t: pd.DataFrame, pct="net_pct", rs="net_rs", day="day0", boot=True, **lab) -> dict:
    """The pre-registered metric set for a set of trades (1 lot each)."""
    n = len(t)
    out = {**lab, "n": n}
    if n == 0:
        return out
    x, r = t[pct].to_numpy(float), t[rs].to_numpy(float)
    win, loss = r[r > 0], r[r < 0]
    out.update({
        "net_rs": round(r.sum(), 0), "exp_pct": round(x.mean(), 3), "exp_rs": round(r.mean(), 1), "median_pct": round(float(np.median(x)), 2),
        "win_pct": round((r > 0).mean() * 100, 1), "avg_win_rs": round(win.mean(), 0) if len(win) else 0.0,
        "avg_loss_rs": round(loss.mean(), 0) if len(loss) else 0.0,
        "profit_factor": round(win.sum() / -loss.sum(), 2) if len(loss) else float("inf"),
        "t_clustered": clustered_t(x, t[day].to_numpy()),
    })
    out.update(drawdown(t[rs], t[day]))
    srt = np.sort(x)[::-1]
    out["mean_ex_top3_pct"] = round(srt[3:].mean(), 3) if n > 3 else None
    k = max(1, int(np.ceil(0.05 * n)))
    top = np.sort(r)[::-1][:k].sum()
    out["top5pct_share_of_profit"] = round(top / r[r > 0].sum() * 100, 1) if (r > 0).any() else None
    if boot and n >= 5:
        d = t[day].to_numpy().astype(str)
        lo, hi = cluster_boot_ci(x, d)
        blo, bhi = block_boot_ci(x, d)
        out.update({"ci95_cluster_lo": round(lo, 2), "ci95_cluster_hi": round(hi, 2), "ci95_block_lo": round(blo, 2), "ci95_block_hi": round(bhi, 2)})
    return out


def verdict(row: dict, halves: dict | None = None) -> str:
    """Section 7 of the pre-registration."""
    if row.get("n", 0) < 30:
        return "insufficient evidence (n < 30)"
    c_lo, c_hi, b_lo, b_hi = (row.get(k) for k in ("ci95_cluster_lo", "ci95_cluster_hi", "ci95_block_lo", "ci95_block_hi"))
    if any(v is None or (isinstance(v, float) and np.isnan(v)) for v in (c_lo, c_hi, b_lo, b_hi)):
        return "insufficient evidence (interval not computable)"
    if c_lo > 0 and b_lo > 0 and (row.get("mean_ex_top3_pct") or 0) > 0 and (halves is None or all(v > 0 for v in halves.values())):
        return "positive evidence"
    if c_hi < 0 and b_hi < 0:
        return "negative evidence"
    return "insufficient evidence (interval contains 0)"


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def write_manifest(extra: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    prev = {}
    if (OUT / "RUN_MANIFEST.json").exists():
        prev = json.loads((OUT / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--", "stress_audit/*.py", "scanner", "server", "index_data"], cwd=ROOT, text=True).strip()
    m = {**prev, "scripts_clean_at_run": not dirty, "uncommitted_script_files": dirty.splitlines(), "run_time_ist": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30"), "git_head": git_head(), "seed": SEED,
         "prereg": "stress_audit/PREREG.md", **extra}
    (OUT / "RUN_MANIFEST.json").write_text(json.dumps(m, indent=2, default=str), encoding="utf-8")
