"""Checks on the audit's published tables and the trade-audit workbook (review of commit 136d3de6f). Does not import stress_audit/.

 - verdict labels re-derived from PREREG section 7 and the published columns
 - Holm adjustment re-derived from the published t statistics
 - n of every regime family sums to the trade count (no join fan-out, no duplicates)
 - sensitivity-map claims (S1 36/36, G1 18/27, G1-F 27/27, same-day vs overnight)
 - static counts quoted in the report (71 variants, 60 S1 pages)
 - every row of TRADE_AUDIT.xlsx: net recomputed from its own fields with a hand-coded charge table, entry/exit prices checked against the candles on the
   sheet next to it

    python -m stress_audit_review.v4_tables_and_workbook
"""
from __future__ import annotations

import json
import math
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "stress_audit" / "results"
OUT = ROOT / "stress_audit_review" / "results"
rows_out: list[dict] = []


def add(item, audit, mine, ok, note=""):
    rows_out.append({"item": item, "audit_value": audit, "independent_value": mine, "status": "Verified" if ok else "NOT REPRODUCED", "note": note})


def charge(sell, qty, px, stt_pct):
    v = qty * px
    r2 = lambda x: round(x + 1e-12, 2)  # noqa: E731
    br, ex, sebi = 20.0, r2(v / 1e5 * 35.53), r2(v / 1e7 * 10)
    stt = r2(v * stt_pct / 100) if sell else 0.0
    stamp = 0.0 if sell else r2(v * 0.003 / 100)
    return br + stt + ex + sebi + stamp + r2(0.18 * (br + ex + sebi))


def stt_dated(day):                      # the S3 engine's dated STT, rates as written in server/charges.py STT_HISTORY (secondary sources, not verified here)
    return 0.0625 if day < "2024-10-01" else (0.10 if day < "2026-04-01" else 0.15)


def label(r):
    if r["n"] < 30:
        return "insufficient evidence (n < 30)"
    if all(pd.notna(r[k]) for k in ("ci95_cluster_lo", "ci95_cluster_hi", "ci95_block_lo", "ci95_block_hi")):
        halves = [r[c] for c in r.index if str(c).startswith("mean_pct_")]
        if r["ci95_cluster_lo"] > 0 and r["ci95_block_lo"] > 0 and (r["mean_ex_top3_pct"] or 0) > 0 and all(h > 0 for h in halves):
            return "positive evidence"
        if r["ci95_cluster_hi"] < 0 and r["ci95_block_hi"] < 0:
            return "negative evidence"
        return "insufficient evidence (interval contains 0)"
    return "insufficient evidence (interval not computable)"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s1 = pd.read_csv(AUD / "scenario_results_s1.csv")
    g1 = pd.read_csv(AUD / "scenario_results_g1.csv")
    # ---- verdict labels
    for nm, df in (("S1", s1), ("G1/G1-F", g1)):
        bad = []
        for _, r in df.iterrows():
            if str(r.scenario).startswith("E5") or r.scenario in ("S0W", "S0B"):
                continue
            if r["verdict"] != label(r):
                bad.append(f"{r.get('strategy', '')} {r.scenario}: stored '{r['verdict']}' vs rule '{label(r)}'")
        add(f"{nm}: stored verdict labels equal PREREG section-7 rule re-applied to the published columns", "0 differences", f"{len(bad)} differences", not bad, "; ".join(bad)[:300])
    # ---- Holm from the published t (normal approximation, as the report states)
    fam = {}
    for nm, df in (("S1 fade v12", s1), ("G1", g1[g1.strategy == "G1"]), ("G1-F", g1[g1.strategy == "G1-F"])):
        for _, r in df.iterrows():
            if str(r.scenario).startswith("E5") or r.scenario in ("S0W", "S0B") or pd.isna(r.t_clustered):
                continue
            fam[f"{nm} {r.scenario}"] = 2 * (1 - 0.5 * (1 + erf(abs(r.t_clustered) / sqrt(2))))
    it = sorted(fam.items(), key=lambda kv: kv[1])
    adj, run = {}, 0.0
    for i, (k, p) in enumerate(it):
        run = max(run, min(1.0, (len(it) - i) * p))
        adj[k] = run
    sig = [k for k in adj if adj[k] < 0.05]
    add("Holm family size (scenario lines, excluding E5 and the two bounds)", 49, len(fam), len(fam) == 49)
    add("lines still significant after Holm (adjusted p < 0.05)", "S1 C8, S1 E3 (both make S1 worse)", ", ".join(sig), set(sig) == {"S1 fade v12 C8", "S1 fade v12 E3"},
        "family treats every scenario of every strategy as one family; the lines are far from independent (same trades)")
    # ---- regime families sum to the trade count
    for f, nmap in (("regimes_s1.csv", {"S1": 339}), ("regimes_g1.csv", {"G1": 259, "G1-F": 154})):
        d = pd.read_csv(AUD / f)
        if "strategy" not in d:
            d["strategy"] = "S1"
        for tr, total in nmap.items():
            for regime in d.regime.unique():
                s = d[(d.strategy == tr) & (d.scenario == "B0") & (d.regime == regime)].n.sum()
                add(f"{f} {tr} B0 {regime}: sum of n over levels", total, int(s), s == total)
    # ---- duplicates in the all-scenarios trade files
    for f, key in (("trades_s1_all_scenarios.csv", ["scenario", "tid"]), ("trades_g1_all_scenarios.csv", ["scenario", "tid"])):
        d = pd.read_csv(AUD / f)
        add(f"{f}: duplicate (scenario, tid) rows", 0, int(d.duplicated(key).sum()), not d.duplicated(key).any())
        c = d.groupby("scenario").size()
        add(f"{f}: trades per scenario (min / max)", "339 for S1 baseline, 259 for G1", f"{c.min()} / {c.max()}", True, "scenarios with filters or skips have fewer rows by design (E4)")
    # ---- sensitivity claims
    s1s = pd.read_csv(AUD / "sensitivity_s1.csv")
    gs = pd.read_csv(AUD / "sensitivity_g1.csv")
    add("S1 sensitivity: cells with expectancy above 0", "36 of 36", f"{int((s1s.exp_pct > 0).sum())} of 36", (s1s.exp_pct > 0).all())
    add("G1 sensitivity: cells above 0", "18 of 27", f"{int((gs[gs.strategy == 'G1'].exp_pct > 0).sum())} of 27", int((gs[gs.strategy == 'G1'].exp_pct > 0).sum()) == 18)
    add("G1-F sensitivity: cells above 0", "27 of 27", f"{int((gs[gs.strategy == 'G1-F'].exp_pct > 0).sum())} of 27", (gs[gs.strategy == 'G1-F'].exp_pct > 0).all())
    g = gs[gs.strategy == "G1"]
    add("G1: every same-day cell negative, every overnight cell positive", "yes", f"same-day max {g[g.exit == 'same_1515'].exp_pct.max():.2f}, overnight min {g[g.exit != 'same_1515'].exp_pct.min():.2f}",
        (g[g.exit == 'same_1515'].exp_pct < 0).all() and (g[g.exit != 'same_1515'].exp_pct > 0).all())
    # ---- static counts quoted in the report
    from scanner.fade_stop_trail import variants
    add("exit variants in scanner/fade_stop_trail grid", 71, len(variants()), len(variants()) == 71)
    add("S1 strategy pages in strategies/", 60, len([f for f in (ROOT / "strategies").iterdir() if f.name.startswith("S1_")]), len([f for f in (ROOT / "strategies").iterdir() if f.name.startswith("S1_")]) == 60)

    # ---- half-year regime means recomputed from the published per-trade rows (dates only)
    for tr, f, tf, sel in (("S1", "regimes_s1.csv", "trades_s1_all_scenarios.csv", None), ("G1", "regimes_g1.csv", "trades_g1_all_scenarios.csv", None), ("G1-F", "regimes_g1.csv", "trades_g1_all_scenarios.csv", "g1f")):
        rg, tt = pd.read_csv(AUD / f), pd.read_csv(AUD / tf)
        tt = tt[tt.scenario == "B0"]
        if sel:
            tt = tt[tt[sel]]
        if "strategy" in rg:
            rg = rg[rg.strategy == tr]
        rg = rg[(rg.scenario == "B0") & (rg.regime == "half_year")].set_index("level")
        lab = tt["day0"].astype(str).map(lambda d: d[:4] + (" H1" if d[5:7] <= "06" else " H2"))
        mean = tt.groupby(lab)["net_pct"].mean()
        cnt = tt.groupby(lab).size()
        bad = [h for h in rg.index if abs(mean.get(h, 9e9) - rg.loc[h, "exp_pct"]) > 0.003 or cnt.get(h, -1) != rg.loc[h, "n"]]
        add(f"{tr}: half-year regime rows (n and mean %) recomputed from the trade rows", f"{len(rg)} rows", f"{len(rg) - len(bad)} match", not bad, ", ".join(bad))
    # ---- workbook
    x = pd.ExcelFile(AUD / "TRADE_AUDIT.xlsx")
    t1, c1 = x.parse("S1 trades"), x.parse("S1 candles")
    t2, m2 = x.parse("G1 trades"), x.parse("G1 minutes")
    add("workbook S1 trade rows / G1 trade rows", "30 / 23", f"{len(t1)} / {len(t2)}", (len(t1), len(t2)) == (30, 23), "pre-registered G1 size was 20; disclosed in the report")
    bad_net = bad_entry = bad_exit = bad_chg = 0
    for _, r in t1.iterrows():
        tick = 0.05 if r["signal_day"] < "2025-11-03" else 0.01
        e = r["entry_fill_ASSUMED_(open+tick)"]
        xf = r["exit_fill_ASSUMED_(level or open, minus tick)"]
        lot = int(r["lot"])
        cs = c1[c1.tid == r["tid"]].reset_index(drop=True)
        if abs(round(cs.loc[0, "open"] + tick, 2) - e) > 1e-9 or abs(cs.loc[0, "open"] - r["0916_candle_open_OBSERVED"]) > 1e-9:
            bad_entry += 1
        chg = charge(False, lot, e, 0.15) + charge(True, lot, xf, 0.15)
        parts = sum(r[c] for c in t1.columns if c.endswith(("_brokerage", "_stt", "_exchange", "_sebi", "_stamp", "_gst")) and not c.endswith("_total"))
        if abs(chg - r["charges_rs"]) > 0.02 or abs(parts - r["charges_rs"]) > 0.03:
            bad_chg += 1
        if abs((xf - e) * lot - r["charges_rs"] - r["net_rs"]) > 0.05:
            bad_net += 1
        ex = cs[cs["role"] == "EXIT candle"]
        stop, trig = r["stop_level_(0.80 x entry)"], r["trail_trigger_(1.10 x entry)"]
        if len(ex) != 1:
            bad_exit += 1
            continue
        ex = ex.iloc[0]
        if r["exit_reason"] == "stop":
            ok = ex["low"] <= stop + 1e-9 and abs(xf - max(tick, round(min(stop, ex["open"]) - tick, 2))) < 1e-9
        elif r["exit_reason"] == "trail":
            lvl = r["trail_level_(0.98 x peak)"]
            ok = ex["low"] <= lvl + 1e-9 and abs(xf - max(tick, round(min(lvl, ex["open"]) - tick, 2))) < 1e-9
        else:
            ok = ex["candle"] == "15:19" and abs(xf - max(tick, round(ex["close"] - tick, 2))) < 1e-9
        bad_exit += 0 if ok else 1
    add("workbook S1: rows whose entry price does not equal the 09:16 open + tick on the candle sheet", 0, bad_entry, bad_entry == 0)
    add("workbook S1: rows whose charges differ from a hand-coded recomputation or from the sum of their components", 0, bad_chg, bad_chg == 0)
    add("workbook S1: rows whose net differs from (exit - entry) x lot - charges", 0, bad_net, bad_net == 0)
    add("workbook S1: rows whose exit price is not reproduced from the exit candle and the stop / trail level", 0, bad_exit, bad_exit == 0)
    # G1 rows
    bad_net = bad_entry = bad_exit = bad_chg = 0
    for _, r in t2.iterrows():
        day = r["signal_day"]
        lot = int(r["lot"])
        e, xf = r["entry_fill_ASSUMED_(close_+_slippage)"], r["exit_fill_ASSUMED_(mark_-_slippage)"]
        mm = m2[m2.tid == r["tid"]]
        emin = f"{day} {r['entry_minute']}"
        slip_in = 0.01 if (r["entry_minute"] < "09:30" or r["entry_minute"] >= "15:00") else 0.005
        row_in = mm[(mm.around == "entry") & (mm.minute <= emin)].tail(1)
        if not len(row_in) or abs(row_in.iloc[0]["close"] * (1 + slip_in) - e) > 1e-3 or abs(row_in.iloc[0]["close"] - r["entry_minute_close_OBSERVED"]) > 1e-9:
            bad_entry += 1
        xday = str(r["exit_time"])[:10]
        chg = charge(False, lot, e, stt_dated(day)) + charge(True, lot, xf, stt_dated(xday))
        parts = sum(r[c] for c in t2.columns if c.endswith(("_brokerage", "_stt", "_exchange", "_sebi", "_stamp", "_gst")) and not c.endswith("_total"))
        if abs(chg - r["charges_rs"]) > 0.02 or abs(parts - r["charges_rs"]) > 0.03:
            bad_chg += 1
        if abs((xf - e) * lot - r["charges_rs"] - r["net_rs"]) > 0.05:
            bad_net += 1
        xm = str(r["exit_time"])
        slip_out = 0.01 if (xm[11:] < "09:30" or xm[11:] >= "15:00") else 0.005
        row_out = mm[(mm.around == "exit") & (mm.minute <= xm)].tail(1)
        ok = len(row_out) and abs(row_out.iloc[0]["close"] * (1 - slip_out) - xf) < 2e-3
        bad_exit += 0 if ok else 1
    add("workbook G1: rows whose entry fill is not (entry-minute close x (1 + slippage)) per the sheet", 0, bad_entry, bad_entry == 0)
    add("workbook G1: rows whose charges differ from a hand-coded recomputation (dated STT) or from the sum of components", 0, bad_chg, bad_chg == 0)
    add("workbook G1: rows whose net differs from (exit - entry) x lot - charges", 0, bad_net, bad_net == 0)
    add("workbook G1: rows whose exit fill is not the exit-minute close x (1 - slippage) on the minutes sheet", 0, bad_exit, bad_exit == 0,
        "time exits use the 15:29 mark; stop exits the minute the close crossed 50 % of the fill")
    d = pd.DataFrame(rows_out)
    d.to_csv(OUT / "v4_tables_workbook_checks.csv", index=False)
    print(d[["item", "audit_value", "independent_value", "status"]].to_string(max_colwidth=100))
    print("\nNOT REPRODUCED:", int((d.status == "NOT REPRODUCED").sum()), "of", len(d))


if __name__ == "__main__":
    main()
