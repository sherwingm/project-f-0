"""IV-crush check (the user, 2026-11-07: "cuz of iv crush"). Descriptive, exploratory, history only; own folder.
Proxy for implied volatility = India VIX (no strike IV is stored). For each G1 trade: VIX at the entry minute, at the next
09:16 and at the next close; NIFTY at the same times; the put's price (from g1_followup_trades.csv) and what it did.
Question: when VIX FALLS after entry, does the put lose value / follow-up max up shrink even when NIFTY keeps falling?"""
import os
import sys
from datetime import date

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
from index_data import load as L  # noqa: E402
from scanner.s3_p1 import vix_at  # noqa: E402


def spot_at(day, hh, mm, cache):
    if day not in cache:
        s = L.spot_1m(day, day, "NIFTY50")
        cache[day] = s.set_index("timestamp")["close"] if len(s) else None
    s = cache[day]
    if s is None:
        return None
    s = s[s.index <= L.at(day, hh, mm)]
    return float(s.iloc[-1]) if len(s) else None


def main():
    d = pd.read_csv(os.path.join(REPO, "data", "results", "S3_G1_datasheet.csv"))
    fu = pd.read_csv(os.path.join(ROOT, "data", "g1_followup_trades.csv"))
    h = pd.read_csv(os.path.join(ROOT, "data", "g1_hold_days_trades.csv"))[["day", "g1f"]]
    d["day"], fu["day"], h["day"] = (pd.to_datetime(x["day"] if "day" in x else x["Day"]) for x in (d, fu, h))
    T = d.merge(fu, on="day").merge(h, on="day")
    vc, sc, rows = {}, {}, []
    for r in T.to_dict("records"):
        day = r["day"].date()
        expiry = date.fromisoformat(str(r["Expiry"])[:10])
        after = [x for x in L.trade_days("NIFTY", expiry) if x > day]
        if not after:
            continue
        hh, mm = (int(x) for x in str(r["Entry time"]).split(":"))
        nx = after[0]
        o = {"day": day, "g1f": r["g1f"], "paid": r["Premium paid (₹/unit)"], "px_d2": r["px_d2"], "px_d3": r["px_d3"],
             "fu_d2": r["fu_d2"], "fu_d3": r["fu_d3"],
             "vix_in": vix_at(day, hh, mm, vc), "vix_d2": vix_at(nx, 9, 16, vc), "vix_d3": vix_at(nx, 15, 29, vc),
             "nifty_in": spot_at(day, hh, mm, sc), "nifty_d2": spot_at(nx, 9, 16, sc), "nifty_d3": spot_at(nx, 15, 29, sc)}
        rows.append(o)
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(ROOT, "data", "g1_ivcrush_trades.csv"), index=False)
    T["put_d2"] = (T["px_d2"] / T["paid"] - 1) * 100
    T["put_d3"] = (T["px_d3"] / T["paid"] - 1) * 100
    T["dvix_d2"], T["dvix_d3"] = T["vix_d2"] - T["vix_in"], T["vix_d3"] - T["vix_in"]
    T["nifty_d2_pct"], T["nifty_d3_pct"] = (T["nifty_d2"] / T["nifty_in"] - 1) * 100, (T["nifty_d3"] / T["nifty_in"] - 1) * 100
    out = []
    for lab, sel in (("G1-F (main)", T[T["g1f"] == 1]), ("G1", T)):
        for tag, ncol, vcol, pcol, fcol in (("next 09:16", "nifty_d2_pct", "dvix_d2", "put_d2", "fu_d2"),
                                            ("next close", "nifty_d3_pct", "dvix_d3", "put_d3", "fu_d3")):
            x = sel.dropna(subset=[ncol, vcol, pcol])
            for nlab, nm in (("NIFTY lower than at entry", x[ncol] < 0), ("NIFTY higher than at entry", x[ncol] >= 0)):
                for vlab, vm in (("VIX fell", x[vcol] < 0), ("VIX rose", x[vcol] >= 0)):
                    g = x[nm & vm]
                    f = g[fcol].dropna()
                    out.append({"strategy": lab, "at": tag, "nifty": nlab, "vix": vlab, "n": len(g),
                                "put_mean_pct": g[pcol].mean(), "put_median_pct": g[pcol].median(),
                                "fu_n": len(f), "fu_mean": f.mean() if len(f) else np.nan, "fu_median": f.median() if len(f) else np.nan,
                                "fu_ge50": (f >= 50).mean() * 100 if len(f) else np.nan, "fu_ge100": (f >= 100).mean() * 100 if len(f) else np.nan})
        x = sel.dropna(subset=["dvix_d3", "put_d3", "nifty_d3_pct"])
        out.append({"strategy": lab, "at": "correlation", "nifty": "all", "vix": "VIX change vs put % (next close)", "n": len(x),
                    "put_mean_pct": x["dvix_d3"].corr(x["put_d3"])})
    S = pd.DataFrame(out)
    S.to_csv(os.path.join(ROOT, "results", "g1_ivcrush_summary.csv"), index=False)
    pd.set_option("display.width", 250)
    print(S.round(1).to_string(index=False))
    print("avg VIX entry -> next 09:16 -> next close:", round(T["vix_in"].mean(), 2), round(T["vix_d2"].mean(), 2), round(T["vix_d3"].mean(), 2))


if __name__ == "__main__":
    main()
