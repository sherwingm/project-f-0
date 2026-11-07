"""Max-up capture by method / pattern (the user, 2026-11-06: "our main motive is to take away the max up after entry
... it is not about the exit"). Descriptive only: no exit rule, no booked P&L.

For every NIFTY session that the tradeability study priced (final period, option minutes from 2024-09-26), entry is
the 09:16 minute close of the ATM CE and PE (strike nearest the 09:15 open), for two expiries:
    a = nearest expiry on or after the day (0 days to expiry on expiry day), b = nearest expiry after the day.
Max up = the highest later minute close vs the entry, per leg (CE, PE), for the straddle (CE + PE in the same
minute) and for the better leg (max of CE and PE max ups, i.e. "one of the two doubled").
Horizons: (day) 09:17 -> 15:29 of the entry day; (exp) 09:17 of the entry day -> 15:29 of the expiry day (held,
no exit), for expiry b only.
Groups: every day; expiry context (D0 / D-1 / other); each research signal's flagged days; the opening gap of the
entry day (known at 09:15); the 09:15 candle; VIX tercile. Information is all known by 09:16.
Out: results/maxup/capture_rows.csv (one row per day x expiry), capture_summary.csv, capture_by_dte.csv.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tradeability_common as tc  # noqa: E402

ROOT = tc.ROOT
OUT = os.path.join(ROOT, "results", "maxup")
os.makedirs(OUT, exist_ok=True)
LEVELS = (25, 50, 100, 200)
SIGNALS = ["PPC032", "PPC062", "OC13", "OC17", "M143", "M218", "M220"]
NAMES = {"PPC032": "after a sharp 5-day fall", "PPC062": "after 3+ up closes", "OC13": "OI walls far (nearest)",
         "OC17": "OI walls wide apart", "M143": "straddle/sqrt(dte) high", "M218": "PCR>1 & calm (straddle)",
         "M220": "PCR>1 & calm (ATR)"}


def spot_day(day):
    s = tc._spot_month(day[:7])
    if s is None:
        return None
    return s[s["day"] == day]


def prev_close(day):
    for k in range(1, 8):
        d = (pd.Timestamp(day) - pd.Timedelta(days=k)).strftime("%Y-%m-%d")
        p = os.path.join(tc.STORE, "spot_1m", "NIFTY50", f"{d[:7]}.parquet")
        if not os.path.exists(p):
            continue
        x = pd.read_parquet(p, columns=["timestamp", "close"])
        x = x[x["timestamp"].dt.strftime("%Y-%m-%d") == d]
        x = x[x["timestamp"].dt.strftime("%H:%M") <= "15:29"]
        if len(x):
            return float(x["close"].iloc[-1])
    return np.nan


def mu(entry, later):
    later = later.dropna()
    return (later.max() / entry - 1) * 100 if len(later) and entry > 0 else np.nan


def one(day, expiry, strike):
    """Max ups for one (day, expiry, strike); None if the legs are not priced at 09:16."""
    d = tc.opt_day(expiry, day)
    if d is None:
        return None
    ce, pe = tc.leg_series(d, strike, "CE"), tc.leg_series(d, strike, "PE")
    if "09:16" not in ce.index or "09:16" not in pe.index:
        return None
    c0, p0 = float(ce["09:16"]), float(pe["09:16"])
    rest = lambda s: s[(s.index > "09:16") & (s.index <= "15:29")]  # noqa: E731
    st = (ce + pe).dropna()
    r = {"ce_in": c0, "pe_in": p0, "ce_day": mu(c0, rest(ce)), "pe_day": mu(p0, rest(pe)),
         "strad_day": mu(c0 + p0, rest(st))}
    # held to the expiry day, no exit (all later days of this expiry)
    cs, ps, ss = [rest(ce)], [rest(pe)], [rest(st)]
    for dd in pd.bdate_range(pd.Timestamp(day) + pd.Timedelta(days=1), pd.Timestamp(expiry)):
        x = tc.opt_day(expiry, dd.strftime("%Y-%m-%d"))
        if x is None:
            continue
        a, b = tc.leg_series(x, strike, "CE"), tc.leg_series(x, strike, "PE")
        a, b = a[a.index <= "15:29"], b[b.index <= "15:29"]
        cs.append(a), ps.append(b), ss.append((a + b).dropna())
    r["ce_exp"], r["pe_exp"] = mu(c0, pd.concat(cs)), mu(p0, pd.concat(ps))
    r["strad_exp"] = mu(c0 + p0, pd.concat(ss))
    return r


def main():
    t = pd.read_csv(os.path.join(ROOT, "results", "tradeability", "trades.csv"))
    t = t[t["exit"] == "i_1515"].drop_duplicates(["trade_date", "exp_choice"])
    rows = []
    pc_cache = {}
    for _, x in t.iterrows():
        day = x["trade_date"]
        r = one(day, x["expiry"], float(x["strike"]))
        if r is None:
            continue
        if day not in pc_cache:
            sd = spot_day(day)
            o915 = sd[sd["hm"] == "09:15"]
            pcl = prev_close(day)
            op = float(o915["open"].iloc[0]) if len(o915) else np.nan
            c915 = np.nan
            p = os.path.join(tc.STORE, "spot_1m", "NIFTY50", f"{day[:7]}.parquet")
            z = pd.read_parquet(p, columns=["timestamp", "close"])
            z = z[(z["timestamp"].dt.strftime("%Y-%m-%d") == day) & (z["timestamp"].dt.strftime("%H:%M") == "09:15")]
            if len(z):
                c915 = float(z["close"].iloc[0])
            pc_cache[day] = ((op / pcl - 1) * 100 if pcl == pcl and op == op else np.nan,
                             (c915 / op - 1) * 100 if op == op and c915 == c915 else np.nan)
        gap, bar = pc_cache[day]
        rows.append({"day": day, "exp_choice": x["exp_choice"], "expiry": x["expiry"], "exp_kind": x["exp_kind"],
                     "dte": int(x["dte"]), "ctx": x["ctx"], "vix_terc": x["vix_terc"], "strike": x["strike"],
                     "gap_pct": gap, "bar915_pct": bar, **{s: x[f"{s}_flag"] for s in SIGNALS}, **r})
    R = pd.DataFrame(rows)
    for h in ("day", "exp"):
        R[f"best_{h}"] = R[[f"ce_{h}", f"pe_{h}"]].max(axis=1)
    R.to_csv(os.path.join(OUT, "capture_rows.csv"), index=False)

    def groups(D):
        yield "Every day", D
        for c in ("D0", "D-1", "other"):
            yield f"Expiry context {c}", D[D["ctx"] == c]
        for s in SIGNALS:
            yield f"{s} · {NAMES[s]}", D[D[s] == 1]
        g = D["gap_pct"]
        yield "Gap up >= +0.3 %", D[g >= 0.3]
        yield "Gap down <= -0.3 %", D[g <= -0.3]
        yield "Gap flat (|gap| < 0.3 %)", D[g.abs() < 0.3]
        yield "Big gap |gap| >= 0.5 %", D[g.abs() >= 0.5]
        yield "09:15 candle up", D[D["bar915_pct"] > 0]
        yield "09:15 candle down", D[D["bar915_pct"] < 0]
        for v in ("low", "mid", "high"):
            yield f"VIX tercile {v}", D[D["vix_terc"] == v]
        yield "D0 + gap |>= 0.3 %|", D[(D["ctx"] == "D0") & (g.abs() >= 0.3)]
        yield "D0 + VIX high", D[(D["ctx"] == "D0") & (D["vix_terc"] == "high")]

    def stats(D, col):
        v = D[col].dropna().values
        o = {"n": len(v), "mean": np.mean(v) if len(v) else np.nan, "median": np.median(v) if len(v) else np.nan}
        for lv in LEVELS:
            o[f"ge{lv}"] = np.mean(v >= lv) if len(v) else np.nan
            o[f"n_ge{lv}"] = int((v >= lv).sum())
        return o

    out, byd = [], []
    for ch in ("a", "b"):
        D = R[R["exp_choice"] == ch]
        for name, G in groups(D):
            for leg in ("ce", "pe", "best", "strad"):
                for h in (("day", "exp") if ch == "b" else ("day",)):
                    out.append({"expiry": ch, "group": name, "leg": leg, "horizon": h, **stats(G, f"{leg}_{h}")})
            for dte, Gd in G.groupby(G["dte"].clip(upper=4)):
                for leg in ("best", "ce", "pe", "strad"):
                    byd.append({"expiry": ch, "group": name, "dte": f"{dte}{'+' if dte == 4 else ''}", "leg": leg,
                                **stats(Gd, f"{leg}_day")})
    S = pd.DataFrame(out)
    S.to_csv(os.path.join(OUT, "capture_summary.csv"), index=False)
    pd.DataFrame(byd).to_csv(os.path.join(OUT, "capture_by_dte.csv"), index=False)
    pd.set_option("display.width", 220)
    show = S[(S["leg"] == "best")].copy()
    for c in ("mean", "median"):
        show[c] = show[c].round(0)
    for lv in LEVELS:
        show[f"ge{lv}"] = (show[f"ge{lv}"] * 100).round(0)
    print(show[["expiry", "group", "horizon", "n", "mean", "median", "ge50", "ge100", "ge200", "n_ge100"]].to_string(index=False))
    print("rows", len(R))


if __name__ == "__main__":
    main()
