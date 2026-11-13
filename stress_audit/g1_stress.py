"""G1 / G1-F stress test on NIFTY 1-minute option history (offline). Pre-registered: stress_audit/PREREG.md (+ AMENDMENTS.md).

    python -m stress_audit.g1_stress

Own single-leg simulator that mirrors scanner/s3_engine.simulate (same minute grid, stale rules, fills and charges) so the scenarios can change
one assumption at a time; it is validated against the engine and against g1_research/results/g1_live_replay_trades.csv before any scenario runs.
Nothing in scanner/, server/ or index_data/ is modified; charge overrides live only inside this process.
"""
from __future__ import annotations

import itertools
import os
from pathlib import Path

os.environ.setdefault("INDEX_STORE", str(Path(__file__).resolve().parents[2] / "fo-index-data" / "data" / "index"))   # before index_data is imported
from datetime import date, timedelta

import numpy as np
import pandas as pd

from index_data import load as L
from scanner import s3_engine as E
from scanner import s3_regime as G
from scanner.s3_b2 import signal
from scanner.s3_buy4 import expiry_after
from scanner.s3_put1_hold import WINDOW
from server import charges as ch

from . import common as C

STEP, TICK_SIZE = 50, None
BASE = dict(stop=0.50, exit="next_close", offset=0, delay=0, entry_mode="close", slip_mult=1.0, slip_add=0.0, extra_slip_volatile=0.0,
            charge_mult=1.0, exch=None, undated_stt=False, stop_mode="close", skip_wide=False)


def collect() -> pd.DataFrame:
    """One row per G1 signal day (first breakout below the range, 09:30-13:00): the data the simulator needs, loaded once."""
    sp = L.spot_1m(WINDOW[0], WINDOW[1] + timedelta(days=10), "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    days = {d: g for d, g in sp.groupby("d") if len(g) >= G.MIN_BARS}
    ses = sorted(days)
    rows = []
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
        ch_full = E.chain_between("NIFTY", e, day, nxt)
        atm = round(spot / STEP) * STEP
        keep = ch_full[(ch_full["option_type"] == "PE") & (ch_full["strike"].isin([atm - STEP, atm, atm + STEP]))].reset_index(drop=True)
        rows.append({"day": day, "day0": str(day), "nxt": nxt, "expiry": e, "ent_h": ent.hour, "ent_m": ent.minute, "spot": spot, "atm": atm,
                     "lot": L.lot_on(day, "NIFTY", e), "dte": sum(1 for d in ses if day < d <= e), "chain": keep,
                     "grid": np.sort(ch_full["timestamp"].unique()), "full": ch_full})
    return pd.DataFrame(rows)


def _slip(t, cfg, volatile) -> float:
    wide = t.time() < pd.Timestamp("2000-01-01 09:30").time() or t.time() >= pd.Timestamp("2000-01-01 15:00").time()
    s = (E.SLIP_WIDE if wide else E.SLIP) * cfg["slip_mult"] + cfg["slip_add"]
    return s + (cfg["extra_slip_volatile"] if volatile else 0.0)


def _fees(side, qty, px, on, cfg) -> float:
    kw = {} if cfg["undated_stt"] else {"on": on}
    return ch.leg("PE", side, qty, px, **kw)["total"] * cfg["charge_mult"]


def sim(t, cfg: dict, volatile=False):
    k = t.atm + cfg["offset"] * STEP
    df = t.chain[t.chain["strike"] == k]
    day, nxt = t.day, t.nxt
    t_in = L.at(day, t.ent_h, t.ent_m + cfg["delay"]) if t.ent_m + cfg["delay"] < 60 else L.at(day, t.ent_h + 1, t.ent_m + cfg["delay"] - 60)
    if cfg["exit"] == "next_close":
        t_out, exit_day = L.at(nxt, 15, 29), nxt
    elif cfg["exit"] == "next_0916":
        t_out, exit_day = L.at(nxt, 9, 16), nxt
    else:
        t_out, exit_day = L.at(day, 15, 15), day
    px0 = L.price_at(df, k, "PE", t_in, stale=E.ENTRY_STALE)
    if px0 is None or px0 <= 0:
        return {"skipped": "no entry price"}
    candle = df[df["timestamp"] == t_in]
    if cfg["skip_wide"] and len(candle) and (candle["high"].iloc[-1] - candle["low"].iloc[-1]) / candle["open"].iloc[-1] > 0.10:
        return {"skipped": "entry minute range > 10 %"}
    base_in = float(candle["high"].iloc[-1]) if cfg["entry_mode"] == "high" and len(candle) else px0
    fill_in = base_in * (1 + _slip(t_in, cfg, volatile))
    prem = fill_in
    grid = pd.DatetimeIndex(t.grid)
    grid = grid[(grid > t_in) & (grid <= t_out)]
    exit_t, reason, last = t_out, "time", None
    if len(grid):
        w = df[(df["timestamp"] > t_in) & (df["timestamp"] <= t_out)].drop_duplicates("timestamp", keep="last")
        ser = pd.Series(w["close"].to_numpy(float), index=pd.DatetimeIndex(w["timestamp"]))
        seen = pd.Series(ser.index, index=ser.index)
        p = ser.reindex(grid).ffill().fillna(px0).to_numpy()
        sn = seen.reindex(grid).ffill().fillna(t_in)
        valid = ~((grid - pd.DatetimeIndex(sn)).total_seconds() > E.MARK_STALE * 60)
        lvl = prem * (1 - cfg["stop"])
        if cfg["stop_mode"] == "low":
            lo = pd.Series(w["low"].to_numpy(float), index=ser.index).reindex(grid).to_numpy()
            op = pd.Series(w["open"].to_numpy(float), index=ser.index).reindex(grid).to_numpy()
            lo = np.where(np.isnan(lo), p, lo)
            op = np.where(np.isnan(op), p, op)
            hit = valid & (lo <= lvl + 1e-9)
        else:
            hit = valid & ((p - fill_in) <= -cfg["stop"] * prem)
        if hit.any():
            i = int(np.argmax(hit))
            exit_t, reason = grid[i], "stop"
            if cfg["stop_mode"] == "low":
                last = float(min(lvl, op[i]))                                      # ASSUMED fill; the minute's low is a bound
            elif cfg["stop_mode"] == "late":
                last = float(p[i + 1]) if i + 1 < len(p) else float(p[i])         # ASSUMED: sold one minute after the close crossed
                exit_t = grid[i + 1] if i + 1 < len(p) else grid[i]
            else:
                last = float(p[i])
        else:
            last = float(p[-1])
    if reason == "time":
        pm = L.price_at(df, k, "PE", t_out, stale=E.MARK_STALE)
        if pm is not None:
            last = pm
    if last is None:
        last = px0
    fill_out = last * (1 - _slip(exit_t, cfg, volatile))
    if cfg["exch"]:
        ch.configure({"OPT_NSE_PER_LAKH": cfg["exch"]})
    try:
        fees = _fees("BUY", t.lot, fill_in, day, cfg) + _fees("SELL", t.lot, fill_out, pd.Timestamp(exit_t).date(), cfg)
    finally:
        if cfg["exch"]:
            ch.configure({"OPT_NSE_PER_LAKH": 35.53})
    net = (fill_out - fill_in) * t.lot - fees
    held_h = (pd.Timestamp(exit_t) - t_in).total_seconds() / 3600
    return {"strike": k, "entry": round(fill_in, 4), "exit": round(fill_out, 4), "reason": reason, "exit_at": pd.Timestamp(exit_t).strftime("%Y-%m-%d %H:%M"),
            "net_rs": round(net, 2), "net_pct": round(net / (prem * t.lot) * 100, 4), "hours_held": round(held_h, 2), "charges_rs": round(fees, 2),
            "entry_minute": f"{t_in:%H:%M}"}


def run(trades: pd.DataFrame, sid: str, **over) -> pd.DataFrame:
    cfg = {**BASE, **over}
    out = []
    for t in trades.itertuples():
        r = sim(t, cfg, volatile=bool(getattr(t, "volatile_day", False)))
        if "skipped" in r:
            continue
        out.append({"scenario": sid, "tid": t.Index, "day0": t.day0, "g1f": bool(t.g1f), "half": t.half, "lot": t.lot, **r})
    return pd.DataFrame(out)


def validate(trades: pd.DataFrame) -> dict:
    """The simulator against the engine (same trade, same Spec) and against the stored replay file."""
    rp = pd.read_csv(C.ROOT / "g1_research" / "results" / "g1_live_replay_trades.csv")
    mine = run(trades, "B0")
    eng = []
    for t in trades.itertuples():
        sp = E.Spec("G1", [E.Leg("BUY", "PE", 0)], entry=(t.ent_h, t.ent_m), exit=(15, 29), stop=0.50)
        r = E.simulate(t.full, t.spot, t.day, sp, t.lot, "NIFTY", t.nxt)
        eng.append({"tid": t.Index, "eng_net": r.get("net_rs"), "eng_skip": r.get("skip")})
    eng = pd.DataFrame(eng)
    m = mine.merge(eng, on="tid", how="outer")
    diff = (m["net_rs"] - m["eng_net"]).abs()
    out = {"trades_collected": len(trades), "sim_trades": len(mine), "engine_trades": int(eng["eng_net"].notna().sum()),
           "max_abs_diff_vs_engine_rs": float(diff.max()), "n_diff_over_1rs": int((diff > 1).sum()),
           "engine_total_rs": round(float(eng["eng_net"].sum()), 0), "sim_total_rs": round(float(mine["net_rs"].sum()), 0),
           "replay_file_trades": len(rp), "replay_file_total_rs_undated_stt": round(float(rp["net_rs"].sum()), 0),
           "replay_file_g1f_trades": int((rp["g1f"] == 1).sum()), "replay_file_g1f_total_rs": round(float(rp.loc[rp["g1f"] == 1, "net_rs"].sum()), 0)}
    return out


SCENARIOS = [
    ("C1", "slippage +1 % of price per side added to the engine's", "assumed", dict(slip_add=0.01)),
    ("C2", "slippage doubled (2 x the engine's 0.5 % / 1 %)", "assumed", dict(slip_mult=2.0)),
    ("C3", "all charges x 2", "assumed", dict(charge_mult=2.0)),
    ("C4", "exchange charge Rs 35.03 per lakh (stress only; production keeps 35.53)", "assumed", dict(exch=35.03)),
    ("C5", "STT at the old undated 2026 table (how the stored replay was written)", "assumed", dict(undated_stt=True)),
    ("C6", "combined: slippage x 2 and charges x 2", "assumed", dict(slip_mult=2.0, charge_mult=2.0)),
    ("C7", "volatile-day adversity: +1 % slippage per side on the top decile of |NIFTY| days", "assumed", dict(extra_slip_volatile=0.01)),
    ("E1", "entry one minute later (same strike)", "assumed", dict(delay=1)),
    ("E2", "entry two minutes later (same strike)", "assumed", dict(delay=2)),
    ("E3", "entry at the entry minute's HIGH", "BOUND", dict(entry_mode="high")),
    ("E4", "skip trades whose entry-minute range exceeds 10 % of its open", "assumed rule", dict(skip_wide=True)),
    ("S5", "stop checked on every minute's LOW (as live checks every second), sold at min(stop level, that minute's open)", "BOUND", dict(stop_mode="low")),
    ("S6", "stop detected on the close, sold one minute later", "assumed", dict(stop_mode="late")),
    ("C8", "worst case: E1 + slippage x 2 + charges x 2 + stop sold one minute late", "assumed", dict(delay=1, slip_mult=2.0, charge_mult=2.0, stop_mode="late")),
]


def main() -> None:
    C.OUT.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("INDEX_STORE", str(C.IDX))
    trades = collect()
    rp = pd.read_csv(C.ROOT / "g1_research" / "results" / "g1_live_replay_trades.csv")
    rp["day0"] = rp["day"].astype(str)
    trades["day0"] = trades["day"].astype(str)
    g1f = dict(zip(rp["day0"], rp["g1f"] == 1))
    trades["g1f"] = trades["day0"].map(g1f).fillna(False)
    trades["half"] = ["Oct24-Sep25" if d <= "2025-09-30" else "Oct25-Oct26" for d in trades["day0"]]
    reg = C.add_regimes(trades.drop(columns=["chain", "grid", "full"]), "day0")
    for col in ("vix_regime", "vol_regime", "trend_prev", "half_year", "volatile_day"):
        trades[col] = reg[col].to_numpy()
    v = validate(trades)
    print("validation:", v)
    (C.OUT / "g1_validation.json").write_text(__import__("json").dumps(v, indent=2), encoding="utf-8")
    tolerance_ok = v["sim_trades"] == v["engine_trades"] and v["max_abs_diff_vs_engine_rs"] < 1.0
    if not tolerance_ok:
        print("STOP: simulator does not reproduce the engine within Rs 1 per trade; see g1_validation.json")
        return
    regf = pd.DataFrame({"tid": trades.index, "vix_regime": trades["vix_regime"], "vol_regime": trades["vol_regime"], "trend_prev": trades["trend_prev"], "half_year": trades["half_year"]})
    allt, meta = {}, {}
    allt["B0"] = run(trades, "B0")
    meta["B0"] = ("baseline: live rule, ATM put, 50 % stop on the minute close, sold next session 15:29, engine slippage, dated STT", "observed minute closes + assumed slippage")
    for sid, desc, ptype, over in SCENARIOS:
        allt[sid] = run(trades, sid, **over)
        meta[sid] = (desc, ptype)
    base = C.summarize(allt["B0"])
    base_f = C.summarize(allt["B0"][allt["B0"]["g1f"]])
    rows = []
    for track, sel in (("G1", lambda d: d), ("G1-F", lambda d: d[d["g1f"]])):
        b = base if track == "G1" else base_f
        for sid, d in allt.items():
            d = sel(d)
            d = d.merge(regf, on="tid", how="left")
            s = C.summarize(d, strategy=track, scenario=sid, description=meta[sid][0], price_type=meta[sid][1])
            s["mean_hours_held"] = round(d["hours_held"].mean(), 1) if len(d) else None
            s["sessions_with_trade"] = d["day0"].nunique()
            halves = {h: g["net_pct"].mean() for h, g in d.groupby("half")}
            for h, vv in halves.items():
                s[f"mean_pct_{h}"] = round(vv, 3)
            s["delta_vs_B0_rs"] = s.get("net_rs", 0) - b.get("net_rs", 0)
            s["delta_vs_B0_pct_points"] = round(s.get("exp_pct", 0) - b.get("exp_pct", 0), 3)
            s["verdict"] = C.verdict(s, halves)
            rows.append(s)
    res = pd.DataFrame(rows)
    rng = np.random.default_rng(C.SEED)
    extra = []
    for track, sel in (("G1", lambda d: d), ("G1-F", lambda d: d[d["g1f"]])):
        L0 = sel(allt["B0"])
        for frac in (0.10, 0.20, 0.30):
            ex, tot = [], []
            for _ in range(1000):
                keep = rng.random(len(L0)) >= frac
                ex.append(L0.loc[keep, "net_pct"].mean())
                tot.append(L0.loc[keep, "net_rs"].sum())
            extra.append({"strategy": track, "scenario": f"E5_{int(frac * 100)}", "description": f"random {int(frac * 100)} % of trades not taken, 1,000 draws (seed {C.SEED}); exp_pct = mean of the draws",
                          "price_type": "assumed", "n": round(len(L0) * (1 - frac)), "exp_pct": round(float(np.mean(ex)), 3), "net_rs": round(float(np.mean(tot)), 0),
                          "ci95_cluster_lo": round(float(np.percentile(ex, 5)), 2), "ci95_cluster_hi": round(float(np.percentile(ex, 95)), 2),
                          "verdict": "5th-95th percentile of the draws in the ci95 columns (not a confidence interval)"})
    res = pd.concat([res, pd.DataFrame(extra)], ignore_index=True)
    res.to_csv(C.OUT / "scenario_results_g1.csv", index=False)
    pd.concat(allt.values(), ignore_index=True).to_csv(C.OUT / "trades_g1_all_scenarios.csv", index=False)
    # ambiguous: S5 differs from baseline
    m = allt["B0"].merge(allt["S5"], on="tid", suffixes=("", "_s5"))
    amb = m.loc[(m["net_rs"] - m["net_rs_s5"]).abs() > 0.005, "tid"]
    amb.to_csv(C.OUT / "g1_ambiguous_trades.csv", index=False, header=["tid"])
    # sensitivity map (no ranking)
    sens = []
    for stp, ex, off in itertools.product((0.40, 0.50, 0.60), ("same_1515", "next_0916", "next_close"), (-1, 0, 1)):
        d = run(trades, "grid", stop=stp, exit=ex, offset=off)
        for track, sel in (("G1", d), ("G1-F", d[d["g1f"]])):
            s = C.summarize(sel, boot=False, strategy=track, stop=stp, exit=ex, strike_offset=("one strike OTM (lower)" if off == -1 else "ATM" if off == 0 else "one strike ITM (higher)"),
                            is_live_rule=(stp == 0.50 and ex == "next_close" and off == 0))
            sens.append(s)
    pd.DataFrame(sens).to_csv(C.OUT / "sensitivity_g1.csv", index=False)
    # regimes
    regs = []
    for sid in ("B0", "C6", "E1"):
        for track, sel in (("G1", allt[sid]), ("G1-F", allt[sid][allt[sid]["g1f"]])):
            d = sel.merge(regf, on="tid", how="left")
            for col in ("vix_regime", "vol_regime", "trend_prev", "half_year", "half"):
                for lv, g in d.groupby(col):
                    s = C.summarize(g, strategy=track, scenario=sid, regime=col, level=lv)
                    s["note"] = "too few" if len(g) < 30 else ""
                    regs.append(s)
    pd.DataFrame(regs).to_csv(C.OUT / "regimes_g1.csv", index=False)
    print(res[res.strategy.isin(["G1", "G1-F"])][["strategy", "scenario", "n", "exp_pct", "net_rs", "win_pct", "profit_factor", "max_dd_rs", "t_clustered", "delta_vs_B0_rs", "verdict"]].to_string())
    print("ambiguous (S5 differs):", len(amb), "| sensitivity cells G1 exp>0:", int(((pd.DataFrame(sens).strategy == "G1") & (pd.DataFrame(sens).exp_pct > 0)).sum()), "of 27")
    C.write_manifest({"g1_validation": v, "g1_scenarios": [s[0] for s in SCENARIOS]})


if __name__ == "__main__":
    main()
