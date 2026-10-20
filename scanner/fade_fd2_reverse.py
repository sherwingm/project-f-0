"""S1 fade · the reverse trade on the fd2 days: a call instead of the losing put (backtest; numbers only).

    python -m scanner.fade_fd2_reverse

strategies/S1_fade_fd2_reverse.md fixes every choice. Takes the SKIP trades of S1_fade_filing_day_skip_trades.csv,
flips the side and re-runs the v10 entry (open + 1 tick, walk away from the money) and E1 exit (close - 1 tick) with
scanner.backtest_s1_v10's own functions. Writes data/results/S1_fade_fd2_reverse.md and _trades.csv.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from . import backtest_s1_v4 as v4
from . import backtest_s1_v10 as v10
from .backtest_cheap_options import sessions_to
from .backtest_s1_v2 import md
from .build import ROOT
from .fade_live import choose_expiry
from .option_engine import TICK
from .stats import clustered_t

RES, CACHE = ROOT / "data" / "results", ROOT / "data" / "cache"


def main() -> None:
    from .nse_fo import download_fo_prices
    t = pd.read_csv(RES / "S1_fade_filing_day_skip_trades.csv")
    t = t[t["group"].str.startswith("SKIP")].copy()
    sessions = sorted(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}" for p in CACHE.glob("fo_bhavcopy_*.csv"))
    cal = [date.fromisoformat(d) for d in sessions]
    bhav = v10.Bhav(CACHE)
    rows = []
    for r in t.itertuples():
        side = "CE" if r.side == "PE" else "PE"
        i = sessions.index(r.day0)
        prev = bhav.day(sessions[i - 1])
        chain, spot = prev["chain"].get(r.symbol), prev["spot"].get(r.symbol)
        base = {"symbol": r.symbol, "day0": r.day0, "orig_side": r.side, "side": side, "D": round(r.D, 2),
                "orig_net_pct": r.e1_net_pct, "window": r.window}
        exp = choose_expiry(chain["XpryDt"][chain["OptnTp"] == side], cal[i],
                            lambda a, e: sessions_to(cal, a, date.fromisoformat(e))) if chain is not None else None
        if exp is None or not spot:
            rows.append({**base, "excluded": "no_strike_or_expiry"})
            continue
        p = download_fo_prices(cal[i], CACHE)
        strikes = chain.loc[(chain["XpryDt"] == exp) & (chain["OptnTp"] == side), "StrkPric"]
        w = v10.walk(strikes, spot, side, v10.quotes_of(p, r.symbol, exp, side), "open")
        if isinstance(w, str):
            rows.append({**base, "excluded": w})
            continue
        q, fill, _, walked = w
        sell = max(0.0, round(q.close - TICK, 2))
        slip = v4.SLIPPAGE.get(r.category, v4.SLIPPAGE["unknown"])
        _, _, net = v10.net_of(side, fill, sell, q.lot, slip)
        rows.append({**base, "excluded": "", "expiry": exp, "strike": q.strike, "walked": walked, "lot": q.lot,
                     "entry": fill, "exit": sell, "high": q.high, "net": net, "net_pct": round(net / (fill * q.lot) * 100, 2)})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "S1_fade_fd2_reverse_trades.csv", index=False)
    ok = df[df["excluded"] == ""]

    def st(g):
        if g.empty:
            return {"n": 0}
        return {"n": len(g), "win %": round((g["net"] > 0).mean() * 100, 1), "mean net %": round(g["net_pct"].mean(), 2),
                "median net %": round(g["net_pct"].median(), 2), "total Rs": round(g["net"].sum()),
                "t": clustered_t(g["net_pct"], g["day0"]) if len(g) > 1 else None,
                "orig side mean %": round(g["orig_net_pct"].mean(), 2)}
    tab = pd.DataFrame([{"reverse": f"{o} -> {'CE' if o == 'PE' else 'PE'}", "window": w,
                         **st(ok[(ok["orig_side"] == o) & ((ok["window"] == w) | (w == "all"))])}
                        for o in ("PE", "CE") for w in ("2022-24", "2025-26", "all")])
    c = ok[ok["orig_side"] == "PE"]
    s, s1, s2 = st(c), st(c[c["window"] == "2022-24"]), st(c[c["window"] == "2025-26"])
    test = pd.DataFrame([
        {"test": "1 at least 20 reversed calls", "value": s["n"], "pass": s["n"] >= 20},
        {"test": "2 pooled mean > 0 with t >= 2", "value": f"{s.get('mean net %')} % / t {s.get('t')}",
         "pass": bool(s["n"] and s["mean net %"] > 0 and (s["t"] or 0) >= 2)},
        {"test": "3a mean > 0 in 2022-24", "value": s1.get("mean net %"), "pass": bool(s1["n"] and s1["mean net %"] > 0)},
        {"test": "3b mean > 0 in 2025-26", "value": s2.get("mean net %"), "pass": bool(s2["n"] and s2["mean net %"] > 0)},
    ])
    verdict = "PASS (a paper shadow track at most; the user's decision)" if test["pass"].all() else "FAIL (nothing changes)"
    excl = df["excluded"].replace("", "traded").value_counts().rename_axis("outcome").reset_index(name="trades")
    text = "\n".join([
        "# S1 fade · the reverse trade on the fd2 days (a call instead of the losing put)\n",
        "Pre-registered: strategies/S1_fade_fd2_reverse.md. Same days as the 37 skips; the side flipped; v10 entry "
        "(day-0 open + 1 tick, walk away from the money) and same-day exit (close - 1 tick), charges and % slippage. "
        "Daily data only (no v11 stop). t is date-clustered. These days were chosen because the puts lost: biased "
        "in favour of the idea.\n",
        f"## Test (puts reversed to calls): **{verdict}**\n\n" + md(test),
        "## Results\n\n" + md(tab),
        "## Trades\n\n" + md(df.drop(columns=["window"])),
        "## Outcomes\n\n" + md(excl),
    ])
    (RES / "S1_fade_fd2_reverse.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
