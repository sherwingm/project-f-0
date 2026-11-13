"""S1 fade v12 stress test on 1-minute candles (offline). Pre-registered: stress_audit/PREREG.md (+ AMENDMENTS.md).

    python -m stress_audit.s1_stress

Observed prices = traded prices in the Upstox candle files. Everything else (the tick, slippage, a later entry, a candle high or low used as a fill, a
delayed stop) is an ASSUMED execution price or a stress BOUND and is labelled as such in scenario_results.csv.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from scanner.fade_realistic_studies import HALF, SETS, TICK_CHANGE
from scanner.fastio import read_table
from scanner.build import ROOT as REPO
from server import charges as ch

from . import common as C

RES = REPO / "data" / "results"
BASE = dict(entry_shift=0, entry_mode="open", stop=0.20, start=0.10, gap=0.02, order="L", stop_fill="std", trail_fill="std",
            slip=0.0, extra_slip_volatile=0.0, slip_by_cap=False, charge_mult=1.0, exch=None, dated_stt=False, skip_wide=False)


def load_trades() -> pd.DataFrame:
    """The 339 baseline trades (lot_ok and entry >= Rs 2) with their day-0 candles 09:16-15:19, exactly as scanner/fade_minutes_retest builds them."""
    cat = pd.read_csv(RES / "S1_v10_trades.csv")[["symbol", "day0", "side", "category"]].drop_duplicates(["symbol", "day0", "side"])
    catmap = {(r.symbol, r.day0, r.side): r.category for r in cat.itertuples()}
    rows, seen = [], set()
    for s in SETS:
        c = pd.read_csv(RES / f"S1_v10_{s}_contracts.csv")
        mins = read_table(RES / f"S1_v10_{s}_minutes.csv")
        mins["t"] = mins["ts"].str[11:16]
        by = {k: g.sort_values("ts") for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
        for r in c.itertuples():
            key = (r.symbol, r.day0, r.side, float(r.strike))
            if key in seen or key not in by:
                continue
            seen.add(key)
            m = by[key]
            m = m[(m["t"] >= "09:16") & (m["t"] <= "15:19")].reset_index(drop=True)
            c16 = m[m["t"] == "09:16"]
            if m.empty or c16.empty:
                continue
            tick = 0.05 if r.day0 < TICK_CHANGE else 0.01
            eb = round(float(c16["o"].iloc[0]) + tick, 2)
            lot = int(r.lot)
            if not (600 <= eb * lot <= 8000 and eb >= 2):
                continue
            rows.append({"set": s, "symbol": r.symbol, "day0": r.day0, "side": r.side, "strike": float(r.strike), "lot": lot, "tick": tick,
                         "entry_B": eb, "half": HALF(r.day0), "category": catmap.get((r.symbol, r.day0, r.side), "unknown"),
                         "candles": m[["t", "o", "h", "l", "c", "volume"]].reset_index(drop=True)})
    return pd.DataFrame(rows).sort_values(["day0", "symbol"]).reset_index(drop=True)


def _chg(side, lot, price, leg, cfg, day) -> float:
    kw = {"on": pd.Timestamp(day).date()} if cfg["dated_stt"] else {}
    return ch.leg(side, leg, lot, price, **kw)["total"] * cfg["charge_mult"]


def _walk(c: pd.DataFrame, k: int, entry: float, tick: float, cfg: dict, order: str):
    """(price before slippage, index of the selling candle or None, reason). `entry` = the price paid. Stop and trail levels reference it."""
    o, h, l, cl = (c[x].to_numpy(float) for x in ("o", "h", "l", "c"))
    n = len(c)
    stop, trig = entry * (1 - cfg["stop"]), entry * (1 + cfg["start"]) if cfg["start"] is not None else None
    active, peak = False, None

    def fill(level, i, mode):
        if mode == "std":
            return min(level, o[i])
        if mode == "low":
            return l[i]
        return o[i + 1] if i + 1 < n else cl[-1]                       # next_open; the last candle falls back to its close

    for i in range(k + 1, n):
        if order == "L":
            if l[i] <= stop + 1e-9:
                return fill(stop, i, cfg["stop_fill"]), i, "stop"
            if trig is not None:
                if active and peak is not None:
                    lvl = peak * (1 - cfg["gap"])
                    if l[i] <= lvl + 1e-9:
                        return fill(lvl, i, cfg["trail_fill"]), i, "trail"
                if not active and h[i] >= trig - 1e-9:
                    active = True
                if active:
                    peak = h[i] if peak is None else max(peak, h[i])
        else:                                                              # order H: this candle's high comes before its low
            if trig is not None:
                if not active and h[i] >= trig - 1e-9:
                    active = True
                if active:
                    peak = h[i] if peak is None else max(peak, h[i])
                    lvl = peak * (1 - cfg["gap"])
                    if l[i] <= lvl + 1e-9:
                        return fill(lvl, i, cfg["trail_fill"]), i, "trail"
            if l[i] <= stop + 1e-9:
                return fill(stop, i, cfg["stop_fill"]), i, "stop"
    return cl[-1], None, "time"


def sim(t, cfg: dict, slip_override: float | None = None, order: str | None = None):
    c = t.candles
    k = cfg["entry_shift"]
    if k >= len(c) - 1:
        return None
    row = c.iloc[k]
    if cfg["skip_wide"] and (row["h"] - row["l"]) / row["o"] > 0.10:
        return {"skipped": "entry candle range > 10 %"}
    tick = t.tick
    base_px = round(float(row["o"]) + tick, 2) if cfg["entry_mode"] == "open" else float(row["h"])
    slip = cfg["slip"]
    if cfg["slip_by_cap"]:
        slip = {"large": 0.01, "mid": 0.02, "small": 0.03}.get(t.category, 0.03)
    if slip_override is not None:
        slip = slip_override
    if cfg["extra_slip_volatile"] and getattr(t, "volatile_day", False):
        slip += cfg["extra_slip_volatile"]
    buy = base_px * (1 + slip)
    px, idx, why = _walk(c, k, buy, tick, cfg, order or cfg["order"])
    sell = max(tick, round(px - tick, 2))
    sell = sell * (1 - slip)
    if cfg["exch"]:
        ch.configure({"OPT_NSE_PER_LAKH": cfg["exch"]})
    try:
        cb = _chg(t.side, t.lot, buy, "BUY", cfg, t.day0)
        cs = _chg(t.side, t.lot, sell, "SELL", cfg, t.day0)
    finally:
        if cfg["exch"]:
            ch.configure({"OPT_NSE_PER_LAKH": 35.53})
    net = (sell - buy) * t.lot - cb - cs
    last = len(c) - 1 if idx is None else idx
    return {"entry": round(buy, 4), "exit": round(sell, 4), "reason": why, "exit_idx": last, "net_rs": round(net, 2),
            "net_pct": round(net / (buy * t.lot) * 100, 4), "minutes_held": last - k + 1, "entry_candle": str(row["t"]),
            "exit_candle": str(c.iloc[last]["t"]), "charges_rs": round(cb + cs, 2)}


def run_scenario(trades: pd.DataFrame, sid: str, **over) -> pd.DataFrame:
    cfg = {**BASE, **over}
    out = []
    for t in trades.itertuples():
        r = sim(t, cfg)
        if r is None or "skipped" in (r or {}):
            continue
        out.append({"scenario": sid, "symbol": t.symbol, "day0": t.day0, "side": t.side, "half": t.half, "lot": t.lot, **r})
    return pd.DataFrame(out)


def bracket(trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, set]:
    """Order L (baseline), order H, and the per-trade worst / best of the two; plus the set of ambiguous trades (different result)."""
    L = run_scenario(trades, "B0")
    H = run_scenario(trades, "S0H", order="H")
    m = L.merge(H, on=["symbol", "day0", "side"], suffixes=("_L", "_H"))
    amb = set(map(tuple, m.loc[(m["net_rs_L"] - m["net_rs_H"]).abs() > 0.005, ["symbol", "day0", "side"]].to_numpy()))
    worst = m.apply(lambda r: r if r.net_rs_L <= r.net_rs_H else r, axis=1)
    pick = lambda better: pd.DataFrame([  # noqa: E731
        {**{k: r[k + ("_L" if (r.net_rs_L <= r.net_rs_H) == (not better) else "_H")] for k in ("entry", "exit", "reason", "exit_idx", "net_rs", "net_pct", "minutes_held", "entry_candle", "exit_candle", "charges_rs")},
         "symbol": r.symbol, "day0": r.day0, "side": r.side, "half_L": r.half_L, "lot": r.lot_L} for _, r in m.iterrows()])
    W, B = pick(False), pick(True)
    for d, sid in ((W, "S0W"), (B, "S0B")):
        d["scenario"] = sid
        d.rename(columns={"half_L": "half"}, inplace=True)
    return L, H, W, B, amb


SCENARIOS = [  # id, description, price type, overrides
    ("C1", "slippage 1 % of price per side", "assumed", dict(slip=0.01)),
    ("C2a", "slippage 2 % per side (2 x the mid-cap level)", "assumed", dict(slip=0.02)),
    ("C2b", "S1 daily-test slippage by cap (1 / 2 / 3 % per side)", "assumed", dict(slip_by_cap=True)),
    ("C3", "all charges x 2", "assumed", dict(charge_mult=2.0)),
    ("C4", "exchange charge Rs 35.03 per lakh (stress only; production keeps 35.53)", "assumed", dict(exch=35.03)),
    ("C5s", "STT by trade date (informational; baseline charges the 2026 STT on every date)", "assumed", dict(dated_stt=True)),
    ("C6", "combined: slippage 2 % per side and charges x 2", "assumed", dict(slip=0.02, charge_mult=2.0)),
    ("C7", "volatile-day adversity: +2 % slippage per side on the top decile of |NIFTY| days", "assumed", dict(extra_slip_volatile=0.02)),
    ("E1", "entry one candle later (09:17 open + tick)", "assumed", dict(entry_shift=1)),
    ("E2", "entry two candles later (09:18 open + tick)", "assumed", dict(entry_shift=2)),
    ("E3", "entry at the 09:16 candle HIGH", "BOUND", dict(entry_mode="high")),
    ("E4", "skip trades whose 09:16 candle range exceeds 10 % of its open", "assumed rule", dict(skip_wide=True)),
    ("S2", "stop sells at the stop candle's LOW", "BOUND", dict(stop_fill="low")),
    ("S3", "stop detected on its candle, sold at the NEXT candle's open - tick", "assumed", dict(stop_fill="next_open")),
    ("S3t", "trail sold at the NEXT candle's open - tick", "assumed", dict(trail_fill="next_open")),
    ("S4", "trail sells at the trail candle's LOW", "BOUND", dict(trail_fill="low")),
    ("C8", "worst case: E1 + slippage 2 % + charges x 2 + stop at next open", "assumed", dict(entry_shift=1, slip=0.02, charge_mult=2.0, stop_fill="next_open", trail_fill="next_open")),
]


def main() -> None:
    C.OUT.mkdir(parents=True, exist_ok=True)
    trades = load_trades()
    vol = C.add_regimes(trades.drop(columns=["candles"]), "day0")
    trades["volatile_day"] = vol["volatile_day"].to_numpy()
    for col in ("vix_regime", "vol_regime", "trend_prev", "half_year", "vix_prev"):
        trades[col] = vol[col].to_numpy()
    print(f"baseline set: {len(trades)} trades")
    L, H, W, B, amb = bracket(trades)
    base_row = C.summarize(L.assign(), pct="net_pct", rs="net_rs", day="day0")
    print("B0:", {k: base_row[k] for k in ("n", "exp_pct", "net_rs", "t_clustered")})
    allt = {"B0": L, "S0H": H, "S0W": W, "S0B": B}
    meta = {"B0": ("baseline: existing v12 rule, order L (stop first), tick penalty + charges, no slippage", "observed candle + assumed tick"),
            "S0H": ("order H: high before low inside a candle (as pre-registered)", "assumed ordering"),
            "S0W": ("BRACKET low end: per trade the worse of order L and order H (by outcome, a bound)", "BOUND"),
            "S0B": ("BRACKET high end: per trade the better of order L and order H (by outcome, a bound)", "BOUND")}
    for sid, desc, ptype, over in SCENARIOS:
        allt[sid] = run_scenario(trades, sid, **over)
        meta[sid] = (desc, ptype)
    vmap = trades.set_index(["symbol", "day0", "side"])
    rows = []
    for sid, d in allt.items():
        d = d.merge(trades[["symbol", "day0", "side", "vix_regime", "vol_regime", "trend_prev", "half_year"]], on=["symbol", "day0", "side"], how="left")
        allt[sid] = d
        s = C.summarize(d, scenario=sid, description=meta[sid][0], price_type=meta[sid][1])
        s["mean_minutes_held"] = round(d["minutes_held"].mean(), 1)
        s["sessions_with_trade"] = d["day0"].nunique()
        halves = {h: g["net_pct"].mean() for h, g in d.groupby("half")}
        s["mean_pct_Oct24_Oct25"] = round(halves.get("Oct24-Oct25", np.nan), 3)
        s["mean_pct_Nov25_Sep26"] = round(halves.get("Nov25-Sep26", np.nan), 3)
        s["delta_vs_B0_rs"] = s["net_rs"] - base_row["net_rs"]
        s["delta_vs_B0_pct_points"] = round(s["exp_pct"] - base_row["exp_pct"], 3)
        s["verdict"] = C.verdict(s, halves)
        rows.append(s)
    res = pd.DataFrame(rows)
    # E5 missed entries
    rng = np.random.default_rng(C.SEED)
    for frac in (0.10, 0.20, 0.30):
        ex, tot = [], []
        for _ in range(1000):
            keep = rng.random(len(L)) >= frac
            ex.append(L.loc[keep, "net_pct"].mean())
            tot.append(L.loc[keep, "net_rs"].sum())
        res = pd.concat([res, pd.DataFrame([{
            "scenario": f"E5_{int(frac * 100)}", "description": f"random {int(frac * 100)} % of trades not taken, 1,000 draws (seed {C.SEED}); exp_pct = mean of the draws",
            "price_type": "assumed", "n": round(len(L) * (1 - frac)), "exp_pct": round(float(np.mean(ex)), 3), "net_rs": round(float(np.mean(tot)), 0),
            "ci95_cluster_lo": round(float(np.percentile(ex, 5)), 2), "ci95_cluster_hi": round(float(np.percentile(ex, 95)), 2),
            "verdict": "5th-95th percentile of the draws in the ci95 columns (not a confidence interval)"}])], ignore_index=True)
    res.insert(0, "strategy", "S1 fade v12")
    res.to_csv(C.OUT / "scenario_results_s1.csv", index=False)
    pd.concat(allt.values(), ignore_index=True).to_csv(C.OUT / "trades_s1_all_scenarios.csv", index=False)
    pd.Series(sorted(amb)).to_csv(C.OUT / "s1_ambiguous_trades.csv", index=False, header=["symbol_day0_side"])
    # sensitivity map (no ranking)
    sens = []
    for stp, st, gp in itertools.product((0.15, 0.20, 0.25), (0.05, 0.10, 0.15), (0.01, 0.02, 0.03, 0.04)):
        d = run_scenario(trades, "grid", stop=stp, start=st, gap=gp)
        s = C.summarize(d, boot=False, stop=stp, trail_start=st, trail_gap=gp, is_v12=(stp == 0.20 and st == 0.10 and gp == 0.02))
        sens.append(s)
    sens = pd.DataFrame(sens)
    sens.to_csv(C.OUT / "sensitivity_s1.csv", index=False)
    # regimes (baseline and combined adverse)
    reg = []
    for sid in ("B0", "C6", "E1"):
        d = allt[sid]
        for col in ("vix_regime", "vol_regime", "trend_prev", "half_year", "half"):
            for lv, g in d.groupby(col):
                s = C.summarize(g, scenario=sid, regime=col, level=lv)
                s["note"] = "too few" if len(g) < 30 else ""
                reg.append(s)
    pd.DataFrame(reg).to_csv(C.OUT / "regimes_s1.csv", index=False)
    # distribution of ambiguity
    print("ambiguous trades (order L vs H differ):", len(amb))
    print(res[["scenario", "n", "exp_pct", "net_rs", "win_pct", "profit_factor", "max_dd_rs", "t_clustered", "delta_vs_B0_rs", "verdict"]].to_string())
    print("sensitivity cells with exp_pct > 0:", int((sens["exp_pct"] > 0).sum()), "of", len(sens))
    C.write_manifest({"s1_inputs": [C.manifest_entry(RES / f"S1_v10_{s}_{k}.csv") for s in SETS for k in ("contracts", "minutes")]
                      + [C.manifest_entry(RES / "S1_v10_trades.csv"), C.manifest_entry(C.ROOT / "data" / "eod2" / "nifty 50.csv"), C.manifest_entry(C.IDX / "vix_daily.parquet")],
                      "s1_baseline_trades": len(trades), "s1_scenarios": [s[0] for s in SCENARIOS]})


if __name__ == "__main__":
    main()
