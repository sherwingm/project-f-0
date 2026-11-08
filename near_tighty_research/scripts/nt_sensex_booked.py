"""Near Tighty on SENSEX: the booked result (the user, 2026-11-08: "SENSEX ... put compute for this"; "this is near tighty").
History only, in-sample, descriptive. Near Tighty = the G1 downside opening-range put, only when the expiry is 1-3 sessions
away (strategies/NT_near_tighty.md). No G1-F filter is used anywhere here (G1-F belongs to the index chat's g1_research/).

    INDEX_STORE=<index-data checkout>/data/index python near_tighty_research/scripts/nt_sensex_booked.py

Entries: the G1 rule on SENSEX as the index chat built it (g1_research/data/sensex_maxup_free_trades.csv, Oct 2024 -> Oct 2026:
first close below the 09:15-09:29 range, ATM put, step 100, entry price = the minute's last close x 1.005, x 1.01 before
09:30). Only the entry list is read; the G1-F flag column is ignored. NT = 1-3 sessions from the entry day to expiry
(server.sessions.sessions_to_expiry, NSE holidays counted); 4-5 sessions are shown for contrast.
Booking = the same code as nt_targets.py: the put's minute closes after the entry minute, the 50 % stop (a close <= 50 % of the
price paid sells at that close), sold at the next session's 09:16 (what Near Tighty sells at) or, shown beside it, the next
session's 15:29; optional resting sell at 2x / 3x; 0.5 % slippage on the exit. SENSEX lot fixed at 20 (the repo's R2 convention;
no SENSEX lot table in the store). Charges from server/charges.py (NSE rates; BSE's exchange fee is a few percent lower).
NIFTY Near Tighty beside it comes from data/nt_target_trades.csv (same code).
Writes near_tighty_research/data/nt_sensex_booked_trades.csv, results/nt_sensex_booked_summary.csv.
"""
import os
import sys
from datetime import date

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "near_tighty_research", "scripts"))
import nt_targets as N  # noqa: E402
from index_data import load as L  # noqa: E402
from scanner.s3_engine import chain_between  # noqa: E402
from scanner.stats import clustered_t  # noqa: E402
from server import charges as C  # noqa: E402
from server import sessions  # noqa: E402

LOT = 20
WINDOWS = {"next_0916": (9, 16), "next_close": (15, 29)}
TARGETS = (None, 2.0, 3.0)
SPLIT = "2025-10-01"


def book() -> pd.DataFrame:
    d = pd.read_csv(os.path.join(REPO, "g1_research", "data", "sensex_maxup_free_trades.csv"))
    rows = []
    for r in d.to_dict("records"):
        day, expiry = date.fromisoformat(str(r["day"])[:10]), date.fromisoformat(str(r["expiry"])[:10])
        dte = sessions.sessions_to_expiry(day, expiry)
        k, paid = float(r["strike"]), float(r["paid"])
        hh, mm = (int(x) for x in str(r["entry"]).split(":"))
        t_in = L.at(day, hh, mm)
        later = [x for x in L.trade_days("SENSEX", expiry) if x > day]
        if not later:
            continue
        nxt = later[0]
        for wname, (eh, em) in WINDOWS.items():
            t_end = L.at(nxt, eh, em)
            ser = N.marks(chain_between("SENSEX", expiry, day, nxt), k, t_in, t_end)
            for tg in TARGETS:
                s = N.simulate(ser, paid, t_in, t_end, tg)
                if s is None:
                    continue
                px, why, ts = s
                sell = px * (1 - N.SLIP)
                ch = C.leg("PE", "BUY", LOT, paid)["total"] + C.leg("PE", "SELL", LOT, sell)["total"]
                net = (sell - paid) * LOT - ch
                rows.append({"day": r["day"], "dte": dte, "nt": int(1 <= dte <= 3), "window": wname,
                             "target": "none" if tg is None else f"{tg:g}x", "paid": paid, "sold": sell, "reason": why,
                             "sold_at": ts.strftime("%Y-%m-%d %H:%M"), "max_up_pct": (ser.max() / paid - 1) * 100,
                             "net_rs": net, "net_pct": net / (paid * LOT) * 100})
    return pd.DataFrame(rows)


def stats(g: pd.DataFrame) -> dict:
    x = g["net_pct"]
    h1, h2 = g[g["day"].astype(str) < SPLIT]["net_pct"], g[g["day"].astype(str) >= SPLIT]["net_pct"]
    top = g.nlargest(5, "net_rs")
    return {"n": len(g), "mean_pct": x.mean(), "median_pct": x.median(), "won": (x > 0).mean(),
            "t": clustered_t(x, g["day"].astype(str)), "total_rs": g["net_rs"].sum(), "half1_pct": h1.mean(),
            "half2_pct": h2.mean(), "n_half1": len(h1), "n_half2": len(h2), "stop_hit": (g["reason"] == "stop").mean(),
            "worst_rs": g["net_rs"].min(), "top5_rs": top["net_rs"].sum(),
            "mean_without_top5_pct": g.drop(top.index)["net_pct"].mean(),
            "max_up_ge100": (g["max_up_pct"] >= 100).mean()}


def nifty_nt() -> pd.DataFrame:
    t = pd.read_csv(os.path.join(REPO, "near_tighty_research", "data", "nt_target_trades.csv"))
    t = t[t["window"].isin(("nt_live", "g1_live"))].copy()
    t["day"] = t["day"].astype(str)
    t["window"] = t["window"].map({"nt_live": "next_0916", "g1_live": "next_close"})
    return t


def main():
    s = book()
    s.to_csv(os.path.join(ROOT, "data", "nt_sensex_booked_trades.csv"), index=False)
    out = []
    for idx, df in (("SENSEX", s), ("NIFTY", nifty_nt())):
        for (grp, win, tg), g in df.groupby([df["nt"].map({1: "NT 1-3 sessions", 0: "4-5 sessions"}), "window", "target"]):
            out.append({"index": idx, "group": grp, "window": win, "target": tg, **stats(g)})
    S = pd.DataFrame(out)
    S.to_csv(os.path.join(ROOT, "results", "nt_sensex_booked_summary.csv"), index=False)
    pd.set_option("display.width", 260)
    print(S[S["group"] == "NT 1-3 sessions"].round(2).to_string(index=False))
    print(s.groupby("dte").size().to_string())


if __name__ == "__main__":
    main()
