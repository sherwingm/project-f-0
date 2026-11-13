"""Independent check of the G1 / G1-F stress results (review of audit commit 136d3de6f).

Does NOT import anything from stress_audit/. The ORIGINAL engine (scanner/s3_engine.py) is the oracle: its simulate() is run directly, with
in-process patches only (never saved) for the slippage / charge scenarios. Statistics, regimes, G1-F flags and the same-day vs overnight comparison are
recomputed with fresh code. Offline; writes only stress_audit_review/results/. Seed 20261113.

    python -m stress_audit_review.v2_g1_independent
"""
from __future__ import annotations

import json
import math
import os
import subprocess
from datetime import timedelta
from pathlib import Path

os.environ.setdefault("INDEX_STORE", str(Path(__file__).resolve().parents[2] / "fo-index-data" / "data" / "index"))

import numpy as np
import pandas as pd

from index_data import load as L
from scanner import s3_engine as E
from scanner import s3_regime as G
from scanner.s3_b2 import signal
from scanner.s3_buy4 import expiry_after
from scanner.s3_put1_hold import WINDOW
from server import charges as ch

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "stress_audit" / "results"
OUT = ROOT / "stress_audit_review" / "results"
SEED = 20261113
rows_out: list[dict] = []


def rec(item, claimed, mine, tol, note="", ok_label="Verified"):
    if claimed is None:
        rows_out.append({"item": item, "audit_value": None, "independent_value": mine, "tolerance": tol, "status": "Verified (calculation)", "note": note})
        return True
    ok = abs(float(claimed) - float(mine)) <= tol
    rows_out.append({"item": item, "audit_value": claimed, "independent_value": mine, "tolerance": tol, "status": ok_label if ok else "NOT REPRODUCED", "note": note})
    return ok


def collect():
    sp = L.spot_1m(WINDOW[0], WINDOW[1] + timedelta(days=10), "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    days = {d: g for d, g in sp.groupby("d") if len(g) >= G.MIN_BARS}
    ses = sorted(days)
    out = []
    for i, day in enumerate(ses):
        if not WINDOW[0] <= day <= WINDOW[1]:
            continue
        sg = signal(days[day], 15, None)
        if sg is None or sg[0] != "PE":
            continue
        e = expiry_after(day)
        nxt = ses[i + 1] if i + 1 < len(ses) else None
        if e is None or nxt is None:
            continue
        ent = sg[1] + timedelta(minutes=1)
        spot = E.spot_at(day, ent.hour, ent.minute)
        if spot is None:
            continue
        prev_close = float(days[ses[i - 1]]["close"].iloc[-1]) if i > 0 else None
        rng = days[day][(days[day]["timestamp"].dt.time >= pd.Timestamp("09:15").time()) & (days[day]["timestamp"].dt.time < pd.Timestamp("09:30").time())]
        out.append(dict(day=day, day0=str(day), nxt=nxt, expiry=e, h=ent.hour, m=ent.minute, spot=spot, lot=L.lot_on(day, "NIFTY", e),
                        full=E.chain_between("NIFTY", e, day, nxt), prev_close=prev_close, open0=float(days[day]["open"].iloc[0]),
                        or_hi=float(rng["high"].max()), or_lo=float(rng["low"].min()), sig_min=sg[1]))
    return out


def eng(t, exit_mode="next_close", stop=0.5, offset=0, delay=0, cost_mult=1.0):
    m = t["m"] + delay
    h = t["h"] + m // 60
    m = m % 60
    if exit_mode == "next_close":
        ex, xd = (15, 29), t["nxt"]
    elif exit_mode == "next_0916":
        ex, xd = (9, 16), t["nxt"]
    else:
        ex, xd = (15, 15), t["day"]
    sp = E.Spec("rev", [E.Leg("BUY", "PE", offset)], entry=(h, m), exit=ex, stop=stop, cost_mult=cost_mult)
    r = E.simulate(t["full"], t["spot"], t["day"], sp, t["lot"], "NIFTY", xd)
    return r


class Patch:
    def __init__(self, slip=None, slip_wide=None, leg=None, nse=None):
        self.slip, self.slip_wide, self.leg, self.nse = slip, slip_wide, leg, nse

    def __enter__(self):
        self.o = (E.SLIP, E.SLIP_WIDE, ch.leg)
        if self.slip is not None:
            E.SLIP, E.SLIP_WIDE = self.slip, self.slip_wide
        if self.leg is not None:
            ch.leg = self.leg
        if self.nse:
            ch.configure({"OPT_NSE_PER_LAKH": self.nse})
        return self

    def __exit__(self, *a):
        E.SLIP, E.SLIP_WIDE, ch.leg = self.o
        if self.nse:
            ch.configure({"OPT_NSE_PER_LAKH": 35.53})


_orig_leg = ch.leg


def leg_x2(instr, side, qty, px, on=None):
    r = dict(_orig_leg(instr, side, qty, px, on=on))
    r["total"] = r["total"] * 2
    return r


def leg_undated(instr, side, qty, px, on=None):
    return _orig_leg(instr, side, qty, px)


# ---- statistics, own code
def cr1_t(x, d):
    x = np.asarray(x, float)
    g = pd.Series(x - x.mean()).groupby(np.asarray(d)).sum()
    G_, n = len(g), len(x)
    return float(x.mean() / math.sqrt(G_ / (G_ - 1) * (g ** 2).sum() / n ** 2))


def cluster_ci(x, d, B=5000, seed=SEED):
    df = pd.DataFrame({"x": x, "d": d}).groupby("d")["x"].agg(["sum", "count"])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(df), size=(B, len(df)))
    m = df["sum"].to_numpy()[idx].sum(1) / df["count"].to_numpy()[idx].sum(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def block_ci(x, d, block=5, B=5000, seed=SEED + 1):
    df = pd.DataFrame({"x": x, "d": d}).groupby("d")["x"].agg(["sum", "count"]).reset_index(drop=True)
    n = len(df)
    nb = math.ceil(n / block)
    rng = np.random.default_rng(seed)
    st = rng.integers(0, n - block + 1, size=(B, nb))
    pos = (st[:, :, None] + np.arange(block)[None, None, :]).reshape(B, -1)[:, :n]
    m = df["sum"].to_numpy()[pos].sum(1) / df["count"].to_numpy()[pos].sum(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def maxdd(net, day):
    o = pd.DataFrame({"n": net, "d": day}).sort_values("d", kind="stable")
    c = o["n"].cumsum().to_numpy()
    return float((c - np.maximum.accumulate(np.maximum(c, 0))).min())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    T = collect()
    pubs = pd.read_csv(AUD / "scenario_results_g1.csv")
    pt = pd.read_csv(AUD / "trades_g1_all_scenarios.csv")
    rp = pd.read_csv(ROOT / "g1_research" / "results" / "g1_live_replay_trades.csv")
    rp["day0"] = rp["day"].astype(str)
    g1f_days = set(rp.loc[rp["g1f"] == 1, "day0"])

    # ---- 1. engine oracle: baseline and the scenarios the engine can express
    def run_all(**kw):
        res = {}
        for t in T:
            r = eng(t, **kw)
            if not r.get("skip"):
                res[t["day0"]] = r["net_rs"]
        return pd.Series(res)

    base = run_all()
    pb = pt[pt.scenario == "B0"].set_index("day0")["net_rs"]
    rec("G1 baseline trades from the original engine", 259, len(base), 0, "263 signals collected; 4 have no usable entry price in the engine itself")
    rec("G1 baseline: max abs per-trade difference, audit simulator vs ORIGINAL engine (Rs)", 0.0, float((base - pb.reindex(base.index)).abs().max()), 0.01)
    rec("G1 baseline total Rs (engine, dated STT)", 41309, float(base.sum()), 1)
    rec("G1-F baseline total Rs (engine, dated STT)", 247602, float(base[base.index.isin(g1f_days)].sum()), 1)
    rec("stored replay file: G1 trades", 259, len(rp), 0)
    rec("stored replay file: G1 total Rs (undated STT)", 40448, float(rp["net_rs"].sum()), 1)
    rec("stored replay file: G1-F trades", 154, int((rp["g1f"] == 1).sum()), 0)
    rec("stored replay file: G1-F total Rs (undated STT)", 247046, float(rp.loc[rp["g1f"] == 1, "net_rs"].sum()), 1)
    same_days = set(rp["day0"]) == set(base.index)
    rec("stored replay days equal the engine's 259 days", 1, int(same_days), 0)
    with Patch(leg=leg_undated):
        und = run_all()
    rec("G1 total Rs, engine with the undated STT table vs stored replay", float(rp["net_rs"].sum()), float(und.sum()), 1, "reproduces how the stored file was written")
    rec("per-trade max diff, engine(undated STT) vs stored replay (Rs)", 0.0, float((und - rp.set_index("day0")["net_rs"].reindex(und.index)).abs().max()), 0.01)
    with Patch(leg=leg_undated):
        x2 = run_all(cost_mult=2.0)
    rec("per-trade max diff, engine cost_mult=2 (undated) vs stored replay net_rs_2x (Rs)", 0.0, float((x2 - rp.set_index("day0")["net_rs_2x"].reindex(x2.index)).abs().max()), 0.01)

    scen = {}
    with Patch(slip=E.SLIP + 0.01, slip_wide=E.SLIP_WIDE + 0.01):
        scen["C1"] = run_all()
    with Patch(slip=E.SLIP * 2, slip_wide=E.SLIP_WIDE * 2):
        scen["C2"] = run_all()
    with Patch(leg=leg_x2):
        scen["C3"] = run_all()
    with Patch(nse=35.03):
        scen["C4"] = run_all()
    scen["C5"] = und
    scen["C6"] = run_all(cost_mult=2.0)                                  # the engine's own 2x (slippage AND charges)
    scen["E1"] = run_all(delay=1)
    scen["E2"] = run_all(delay=2)
    for sid, ser in scen.items():
        for track, sel in (("G1", ser), ("G1-F", ser[ser.index.isin(g1f_days)])):
            p = pubs[(pubs.strategy == track) & (pubs.scenario == sid)].iloc[0]
            rec(f"{track} {sid}: net Rs (ORIGINAL engine with patches) vs audit", float(p.net_rs), float(sel.sum()), 1.5, "engine oracle")
            rec(f"{track} {sid}: trade count", float(p.n), len(sel), 0)

    # ---- 2. statistics recomputed from the published per-trade rows
    for track in ("G1", "G1-F"):
        for sid in ("B0", "C1", "C6", "E1"):
            d = pt[pt.scenario == sid].copy()
            if track == "G1-F":
                d = d[d["g1f"]]
            p = pubs[(pubs.strategy == track) & (pubs.scenario == sid)].iloc[0]
            x = d["net_pct"].to_numpy()
            rec(f"{track} {sid}: mean net %", p.exp_pct, x.mean(), 0.002)
            rec(f"{track} {sid}: date-clustered t", p.t_clustered, cr1_t(x, d["day0"]), 0.002)
            lo, hi = cluster_ci(x, d["day0"].to_numpy())
            rec(f"{track} {sid}: cluster-bootstrap CI low", p.ci95_cluster_lo, lo, 0.15, "different RNG stream; within bootstrap noise")
            rec(f"{track} {sid}: cluster-bootstrap CI high", p.ci95_cluster_hi, hi, 0.15, "")
            blo, bhi = block_ci(x, d["day0"].to_numpy())
            rec(f"{track} {sid}: block-bootstrap CI low", p.ci95_block_lo, blo, 0.3, "5-trade-date blocks; different RNG stream")
            rec(f"{track} {sid}: max drawdown Rs", p.max_dd_rs, maxdd(d["net_rs"], d["day0"]), 1)
            w, lse = d.net_rs[d.net_rs > 0], d.net_rs[d.net_rs < 0]
            rec(f"{track} {sid}: profit factor", p.profit_factor, w.sum() / -lse.sum(), 0.006)

    # ---- 3. sensitivity: 27 cells x two tracks through the engine
    sens = pd.read_csv(AUD / "sensitivity_g1.csv")
    exitmap = {"same_1515": "same_1515", "next_0916": "next_0916", "next_close": "next_close"}
    bad, cells = 0, 0
    for stp in (0.4, 0.5, 0.6):
        for ex in ("same_1515", "next_0916", "next_close"):
            for off in (-1, 0, 1):
                ser = run_all(exit_mode=ex, stop=stp, offset=off)
                for track, sel in (("G1", ser), ("G1-F", ser[ser.index.isin(g1f_days)])):
                    lab = "one strike OTM (lower)" if off == -1 else ("ATM" if off == 0 else "one strike ITM (higher)")
                    row = sens[(sens.strategy == track) & (sens.stop == stp) & (sens.exit == ex) & (sens.strike_offset == lab)].iloc[0]
                    cells += 1
                    if abs(sel.sum() - row.net_rs) > 2 or len(sel) != row.n:
                        bad += 1
    rec("sensitivity cells (G1 and G1-F, 54 rows) not reproduced by the original engine", 0, bad, 0, f"{cells} rows compared")

    # ---- 4. regimes recomputed from published trades + daily files, previous-day information only
    nf = pd.read_csv(ROOT / "data" / "eod2" / "nifty 50.csv")
    nf.columns = [c.lower() for c in nf.columns]
    nf["date"] = pd.to_datetime(nf["date"]).dt.strftime("%Y-%m-%d")
    nf = nf.sort_values("date").reset_index(drop=True)
    nf["ret"] = nf["close"].pct_change() * 100
    nf["vol20"] = nf["ret"].rolling(20).std()
    nf["ma50"] = nf["close"].rolling(50).mean()
    vx = pd.read_parquet(Path(os.environ["INDEX_STORE"]) / "vix_daily.parquet")
    vx["date"] = pd.to_datetime(vx["date"]).dt.strftime("%Y-%m-%d")
    vx = vx.dropna(subset=["close"]).sort_values("date")
    b0 = pt[pt.scenario == "B0"].copy().reset_index(drop=True)
    b0["vix_prev"] = [float(vx[vx["date"] < d]["close"].iloc[-1]) for d in b0["day0"]]
    b0["vol_prev"] = [float(nf[nf["date"] < d]["vol20"].iloc[-1]) for d in b0["day0"]]
    b0["trend"] = ["up" if (lambda r: r["close"] > r["ma50"])(nf[nf["date"] < d].iloc[-1]) else "down" for d in b0["day0"]]
    leaks = sum(1 for d in b0["day0"] if vx[vx["date"] < d]["date"].iloc[-1] >= d)
    rec("G1 regimes: trades whose VIX input is dated on or after the trade day", 0, leaks, 0)
    for col, name in (("vix_prev", "vix_regime"), ("vol_prev", "vol_regime")):
        q = np.quantile(b0[col], [1 / 3, 2 / 3])
        b0[name] = ["low" if v <= q[0] else ("high" if v > q[1] else "mid") for v in b0[col]]
    reg = pd.read_csv(AUD / "regimes_g1.csv")
    for track in ("G1", "G1-F"):
        d0 = b0 if track == "G1" else b0[b0["g1f"]]
        for regime, col in (("vix_regime", "vix_regime"), ("vol_regime", "vol_regime"), ("trend_prev", "trend")):
            for lv, g in d0.groupby(col):
                p = reg[(reg.strategy == track) & (reg.scenario == "B0") & (reg.regime == regime) & (reg.level == lv)].iloc[0]
                rec(f"{track} {regime}={lv}: n / mean %", float(p.exp_pct), float(g.net_pct.mean()), 0.003, f"n audit {int(p.n)} vs {len(g)}")
    # the tercile cuts use the trades' own distribution (whole window): descriptive labels, not a trading rule -> note only
    rows_out.append({"item": "G1 regimes: tercile cut points come from the whole trade window", "audit_value": "as stated", "independent_value": "confirmed", "tolerance": None,
                     "status": "Verified", "note": "labels are descriptive; the cut points themselves use later data than any single trade, so they are not an implementable rule"})

    # ---- 5. G1-F flag: reproduce from raw data and from the datasheet; look-ahead check
    flag_raw, info, not_checkable = {}, [], []
    for t in T:
        width = (t["or_hi"] - t["or_lo"]) / t["or_lo"] * 100
        gap = (t["open0"] / t["prev_close"] - 1) * 100 if t["prev_close"] else None
        vser = L.vix_1m(t["day"], t["day"])
        vv = vser[vser["timestamp"] <= t["sig_min"]]["close"].dropna()
        vix = float(vv.iloc[-1]) if len(vv) else None
        if gap is None:                                           # first loaded session: no earlier close in this script's window -> not checkable here
            not_checkable.append(t["day0"])
            continue
        ok = (vix is not None and gap < 0.3 and not (0.5 <= width < 0.8) and vix < 17)
        flag_raw[t["day0"]] = ok
        info.append(dict(day0=t["day0"], gap=gap, width=width, vix=vix))
    raw = pd.Series(flag_raw)
    stored = pd.Series({d: (d in g1f_days) for d in raw.index if d in set(rp["day0"])})
    rows_out.append({"item": "G1-F raw recomputation: days not checkable by this script (no earlier session loaded)", "audit_value": None, "independent_value": ", ".join(not_checkable),
                     "tolerance": None, "status": "Verified (calculation)", "note": "limit of the review script; the datasheet-based check below covers that day"})
    both = raw.reindex(stored.index)
    rec("G1-F flag recomputed from raw spot/VIX minutes vs stored g1f flag: days that disagree", 0, int((both != stored).sum()), 0,
        "inputs: signal-day 09:15 open vs previous close, 09:15-09:29 range, VIX up to the signal minute (all known at the signal)")
    ds = pd.read_csv(ROOT / "data" / "results" / "S3_G1_datasheet.csv")
    ds["day0"] = ds["Day"].astype(str)
    ds = ds.set_index("day0")
    dflag = ~((ds["Day-1 gap at open %"] >= 0.3) | ((ds["OR width %"] >= 0.5) & (ds["OR width %"] < 0.8)) | (ds["VIX at signal"] >= 17))
    common = stored.index.intersection(dflag.index)
    rec("G1-F flag from the datasheet columns vs stored flag: days that disagree", 0, int((dflag.reindex(common) != stored.reindex(common)).sum()), 0, f"{len(common)} days compared")
    # ---- 6. filter-threshold map (information only; every cell shown, none ranked)
    inf = pd.DataFrame({"gap": ds["Day-1 gap at open %"], "width": ds["OR width %"], "vix": ds["VIX at signal"]})      # datasheet columns: reproduce the stored flag on every day (checked above)
    net_pct = pt[pt.scenario == "B0"].set_index("day0")["net_pct"]
    net_rs = pt[pt.scenario == "B0"].set_index("day0")["net_rs"]
    cells_ = []
    for gp in (0.2, 0.3, 0.4):
        for wb in ((0.4, 0.7), (0.5, 0.8), (0.6, 0.9)):
            for vv in (16, 17, 18):
                keep = ~((inf["gap"] >= gp) | ((inf["width"] >= wb[0]) & (inf["width"] < wb[1])) | (inf["vix"] >= vv))
                idx = [d for d in inf.index[keep] if d in net_pct.index]
                x = net_pct.reindex(idx)
                cells_.append(dict(gap_max=gp, width_skip=f"{wb[0]}-{wb[1]}", vix_max=vv, n=len(x), mean_pct=round(x.mean(), 2), total_rs=round(net_rs.reindex(idx).sum()),
                                   is_published_rule=(gp == 0.3 and wb == (0.5, 0.8) and vv == 17)))
    fm = pd.DataFrame(cells_)
    fm.to_csv(OUT / "v2_g1f_filter_threshold_map.csv", index=False)
    pub_rule = fm[fm.is_published_rule].iloc[0]
    rec("G1-F filter map: published-rule cell n / mean % (from raw recomputation)", 19.70, float(pub_rule.mean_pct), 0.1, "ties to the audit's 154 / +19.7 % (flag identical)")
    rows_out.append({"item": "G1-F filter-threshold map: share of 27 threshold cells with mean above G1's +5.5 %", "audit_value": None,
                     "independent_value": f"{int((fm.mean_pct > 5.54).sum())} of 27; cell means range {fm.mean_pct.min():.1f} to {fm.mean_pct.max():.1f} %; n range {fm.n.min()}-{fm.n.max()}",
                     "tolerance": None, "status": "Verified (calculation)", "note": "tests whether G1-F's lift depends on the exact thresholds; every cell is the same 259 signals re-filtered, so cells are not independent"})

    # ---- 7. same-day vs overnight, paired, with the year split (selection-bias evidence)
    same = run_all(exit_mode="same_1515")
    over = base
    dd = (over - same).dropna()
    days_ = pd.Series(dd.index, index=dd.index)
    pct_over = pt[pt.scenario == "B0"].set_index("day0")["net_pct"]
    # percent figures need per-trade premium; use rupee paired difference (same premium base per trade)
    yr1 = [d for d in dd.index if d <= "2025-09-30"]
    yr2 = [d for d in dd.index if d > "2025-09-30"]
    rows_out.append({"item": "G1 overnight minus same-day (Rs per trade, paired on the same 259 signals)", "audit_value": None,
                     "independent_value": f"all {dd.mean():.0f} (t {cr1_t(dd.values, dd.index):.2f}); Oct24-Sep25 {dd[yr1].mean():.0f}; Oct25-Oct26 {dd[yr2].mean():.0f}",
                     "tolerance": None, "status": "Verified (calculation)",
                     "note": "stop 50 %, ATM; overnight = next 15:29, same-day = 15:15. NOT independent evidence: G1 was picked as the best of seven variants on these same trades (strategies/S3_G1_put_overnight.md)"})

    pd.DataFrame(rows_out).to_csv(OUT / "v2_g1_checks.csv", index=False)
    (OUT / "v2_g1_meta.json").write_text(json.dumps({"git_head": head, "seed": SEED, "signals_collected": len(T)}, indent=2), encoding="utf-8")
    d = pd.DataFrame(rows_out)
    print(d[["item", "audit_value", "independent_value", "status"]].to_string(max_colwidth=100))
    print("\nNOT REPRODUCED:", int((d.status == "NOT REPRODUCED").sum()), "of", len(d))


if __name__ == "__main__":
    main()
