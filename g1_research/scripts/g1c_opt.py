"""G1-C optimization study, as pre-registered in g1_research/G1C_OPT_PREREG.md (committed before any number).

Stages (run in this order; `validate` refuses to run before `discover` has written the frozen file):
  python g1_research/scripts/g1c_opt.py build      # simulate every variant on every call signal; prints counts only
  python g1_research/scripts/g1c_opt.py discover   # discovery half (signal day < 2025-10-01): table, BH 10 %, freeze candidates
  python g1_research/scripts/g1c_opt.py validate   # validation half (2025-10-01 ->), only for the frozen candidates
"""
import math
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from index_data import load as L  # noqa: E402
from scanner import s3_regime as G  # noqa: E402
from scanner.s3_b2 import signal  # noqa: E402
from scanner.s3_buy4 import expiry_after  # noqa: E402
from scanner.s3_buy_maxup import legs_of, max_up  # noqa: E402
from scanner.s3_engine import Leg, Spec, chain_between, run_day  # noqa: E402
from scanner.stats import clustered_t  # noqa: E402

WINDOW = (date(2024, 10, 1), date(2026, 10, 28))
SPLIT = date(2025, 10, 1)
TRADES = os.path.join(ROOT, "data", "g1c_opt_trades.csv")
FROZEN = os.path.join(ROOT, "results", "g1c_opt_candidates_frozen.csv")
Q = 0.10
MIN_N = 30
FEATURES = ["gap_pct", "or_width_pct", "vix_signal", "min_after_0930", "prev5_ret_pct", "prev_vs_ema20_pct", "depth_pct"]
EXITS = {"X1": (None, 15, 15, 0.5), "X2": ("a0", 9, 16, 0.5), "X3": ("a1", 15, 29, 0.5), "X4": ("a0", 15, 29, 0.35), "X5": ("a0", 15, 29, None)}


def run(side_off, ent, e, day, exit_day, hh, mm, stop, cm):
    spec = Spec("g1c-opt", [Leg("BUY", "CE", side_off)], entry=(ent.hour, ent.minute), exit=(hh, mm), stop=stop, cost_mult=cm)
    r = run_day(spec, day, e, exit_day=exit_day)
    return None if r.get("skip") else r


def build():
    sp = L.spot_1m(WINDOW[0] - timedelta(days=60), WINDOW[1] + timedelta(days=10), "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    days = {d: g for d, g in sp.groupby("d") if len(g) >= G.MIN_BARS}
    ses = sorted(days)
    dclose = pd.Series({d: float(days[d]["close"].iloc[-1]) for d in ses})
    ema20 = dclose.ewm(span=20, adjust=False).mean()
    vx = L.vix_1m(WINDOW[0], WINDOW[1] + timedelta(days=1))
    vx = vx.sort_values("timestamp")
    rows = []
    for i, day in enumerate(ses):
        if not WINDOW[0] <= day <= WINDOW[1] or i < 6:
            continue
        sg = signal(days[day], 15, None)
        if sg is None or sg[0] != "CE":
            continue
        e = expiry_after(day)
        if e is None:
            continue
        after = [x for x in ses[i + 1:] if x <= e]
        if not after:
            continue
        side, ts, hi, lo = sg
        ent = ts + timedelta(minutes=1)
        t_in = L.at(day, ent.hour, ent.minute)
        prev = ses[i - 1]
        v = vx[vx["timestamp"] <= ts]
        sig_close = float(days[day].loc[days[day]["timestamp"] == ts, "close"].iloc[0])
        o = {"day": day, "expiry": e, "dte": len(after),
             "gap_pct": (float(days[day]["open"].iloc[0]) / dclose[prev] - 1) * 100,
             "or_width_pct": (hi / lo - 1) * 100,
             "vix_signal": float(v["close"].iloc[-1]) if len(v) else np.nan,
             "min_after_0930": (ts.hour * 60 + ts.minute) - (9 * 60 + 30),
             "prev5_ret_pct": (dclose[prev] / dclose[ses[i - 6]] - 1) * 100,
             "prev_vs_ema20_pct": (dclose[prev] / ema20[prev] - 1) * 100,
             "depth_pct": (sig_close / hi - 1) * 100}
        pairs = [("B", 0, None, 15, 29, 0.5)] + [(k, 0, *v_) for k, v_ in EXITS.items()] + [("K1", -1, "a0", 15, 29, 0.5), ("K2", -2, "a0", 15, 29, 0.5)]
        chain = None
        for name, off, xd, hh, mm, stop in pairs:
            if name == "B":
                xd = "a0"
            exit_day = None if xd is None else (after[0] if xd == "a0" else after[min(1, len(after) - 1)])
            for cm in (1.0, 2.0):
                r = run(off, ent, e, day, exit_day, hh, mm, stop, cm)
                if r is None:
                    continue
                o[f"{name}_{int(cm)}_net"], o[f"{name}_{int(cm)}_rs"], o[f"{name}_{int(cm)}_reason"] = r["net_pct_premium"], r["net_rs"], r["reason"]
                if cm == 1.0 and name in ("B", "K1", "K2"):
                    if chain is None:
                        chain = chain_between("NIFTY", e, day, after[0])
                    lg = legs_of(r["legs"])
                    o[f"{name}_peak"] = max_up(chain, lg, t_in, L.at(after[0], 15, 29), L.at(after[0], 15, 29))["max_up_any_pct"]
        rows.append(o)
    T = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(TRADES), exist_ok=True)
    T.to_csv(TRADES, index=False)
    T["half"] = np.where(T["day"] < SPLIT, "discovery", "validation")
    print("signals simulated:", len(T), "| discovery:", (T.half == "discovery").sum(), "| validation:", (T.half == "validation").sum())


def pnorm_upper(t):
    return 0.5 * math.erfc(t / math.sqrt(2))


def load():
    T = pd.read_csv(TRADES, parse_dates=["day"])
    T["day"] = T["day"].dt.date
    # Amendment 1: previous close vs its 20-day SIMPLE average of daily closes (data up to the previous session only)
    sp = L.spot_1m(WINDOW[0] - timedelta(days=60), WINDOW[1] + timedelta(days=10), "NIFTY50")
    sp["d"] = sp["timestamp"].dt.date
    g = {d: x for d, x in sp.groupby("d") if len(x) >= G.MIN_BARS}
    ses = sorted(g)
    dc = pd.Series({d: float(g[d]["close"].iloc[-1]) for d in ses})
    sma = dc.rolling(20).mean()
    prev = {ses[i]: ses[i - 1] for i in range(1, len(ses))}
    T["prev_vs_sma20_pct"] = [(dc[prev[d]] / sma[prev[d]] - 1) * 100 if d in prev and not np.isnan(sma[prev[d]]) else np.nan for d in T["day"]]
    return T


def cells(T, med):
    """name -> (selection mask, net column prefix, peak column)"""
    out = {"B": (np.ones(len(T), bool), "B", "B_peak")}
    for k in EXITS:
        out[k] = (np.ones(len(T), bool), k, "B_peak")
    out["K1"] = (np.ones(len(T), bool), "K1", "K1_peak")
    out["K2"] = (np.ones(len(T), bool), "K2", "K2_peak")
    for f in FEATURES:
        out[f"{f}_keepLE"] = (T[f].to_numpy() <= med[f], "B", "B_peak")      # skip when the feature is above the discovery median
        out[f"{f}_keepGT"] = (T[f].to_numpy() > med[f], "B", "B_peak")       # skip when it is at or below it
    gap, ext = T["gap_pct"].to_numpy(), T["prev_vs_sma20_pct"].to_numpy()
    out["GAP075"] = (gap >= 0.75, "B", "B_peak")                                                  # Amendment 1
    out["SKIPEXT"] = (~((gap >= 0.2) & (gap <= 0.5) & (ext >= 2.5)), "B", "B_peak")              # Amendment 1
    return out


def summarise(T, sel, pre, peak):
    x = T[sel & T[f"{pre}_1_net"].notna().to_numpy()]
    n = len(x)
    if n == 0:
        return {"n": 0}
    net, rs = x[f"{pre}_1_net"], x[f"{pre}_1_rs"]
    pk = x[peak].dropna()
    top3 = net.sort_values(ascending=False).iloc[3:]
    t = clustered_t(net.to_numpy(float), [str(d) for d in x["day"]]) if n > 3 else np.nan
    n2 = x[f"{pre}_2_net"].dropna()
    return {"n": n, "maxup_ge50": (pk >= 50).mean() * 100, "maxup_ge100": (pk >= 100).mean() * 100, "maxup_ge200": (pk >= 200).mean() * 100,
            "maxup_mean": pk.mean(), "maxup_median": pk.median(), "win_pct": (net > 0).mean() * 100, "mean_pct": net.mean(),
            "median_pct": net.median(), "total_rs": rs.sum(), "t": t, "mean_2x": n2.mean(), "mean_ex_top3": top3.mean() if len(top3) else np.nan}


def table(T, med):
    rows = []
    for name, (sel, pre, pk) in cells(T, med).items():
        s = summarise(T, sel, pre, pk)
        rows.append({"cell": name, **s})
    return pd.DataFrame(rows)


def discover():
    T = load()
    D = T[T["day"] < SPLIT].reset_index(drop=True)
    med = {f: float(D[f].median()) for f in FEATURES}
    R = table(D, med)
    R["p_one_sided"] = [pnorm_upper(t) if (isinstance(t, float) and not math.isnan(t)) else np.nan for t in R["t"]]
    test = R[(R["cell"] != "B") & (R["n"] >= MIN_N) & R["p_one_sided"].notna()].sort_values("p_one_sided").reset_index(drop=True)
    m = len(test)
    test["bh_threshold"] = [(i + 1) / m * Q for i in range(m)]
    k = max([i for i in range(m) if test.loc[i, "p_one_sided"] <= test.loc[i, "bh_threshold"]], default=-1)
    test["survives"] = [i <= k for i in range(m)]
    R = R.merge(test[["cell", "bh_threshold", "survives"]], on="cell", how="left")
    R["tested"] = R["cell"].isin(test["cell"])
    R["too_few"] = (R["cell"] != "B") & (R["n"] < MIN_N)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    R.to_csv(os.path.join(ROOT, "results", "g1c_opt_discovery.csv"), index=False)
    cand = R[R["survives"] == True]  # noqa: E712
    cand = cand.assign(**{f"median_{f}": med[f] for f in FEATURES})[["cell"] + [f"median_{f}" for f in FEATURES]]
    cand.to_csv(FROZEN, index=False)
    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(f"DISCOVERY (signal day before {SPLIT}); tested {m} cells (n >= {MIN_N}); BH {Q:.0%}")
    cols = ["cell", "n", "maxup_ge50", "maxup_ge100", "maxup_ge200", "maxup_mean", "maxup_median", "win_pct", "mean_pct", "median_pct", "total_rs", "t", "mean_2x"]
    print(R[cols].round(2).to_string(index=False))
    print("too few:", list(R.loc[R["too_few"], "cell"]))
    print("survivors (frozen):", list(cand["cell"]) or "none")


def validate():
    if not os.path.exists(FROZEN):
        sys.exit("run `discover` first: the frozen candidate file does not exist")
    cand = pd.read_csv(FROZEN)
    print("frozen candidates:", list(cand["cell"]) or "none")
    if cand.empty:
        print("no candidate: nothing to validate; verdict = no candidate")
        return
    T = load()
    V = T[T["day"] >= SPLIT].reset_index(drop=True)
    med = {f: float(cand.iloc[0][f"median_{f}"]) for f in FEATURES}
    allc = cells(V, med)
    rows = []
    for name in cand["cell"]:
        sel, pre, pk = allc[name]
        s = summarise(V, sel, pre, pk)
        s["cell"] = name
        s["pass"] = bool(s["n"] >= MIN_N and s["mean_pct"] > 0 and s["t"] >= 1.5 and s["mean_2x"] > 0 and s["mean_ex_top3"] > 0)
        rows.append(s)
    R = pd.DataFrame(rows)
    R.to_csv(os.path.join(ROOT, "results", "g1c_opt_validation.csv"), index=False)
    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(R[["cell", "n", "maxup_ge100", "maxup_mean", "maxup_median", "win_pct", "mean_pct", "median_pct", "total_rs", "t", "mean_2x", "mean_ex_top3", "pass"]].round(2).to_string(index=False))


if __name__ == "__main__":
    {"build": build, "discover": discover, "validate": validate}[sys.argv[1]]()
