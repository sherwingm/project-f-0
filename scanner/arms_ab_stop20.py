"""S1 arms A / B · the fade's -20 % stop on the live call arms: prev (S1 v7 exits) vs new (+ the -20 % stop) (numbers only).

    python -m scanner.arms_ab_stop20

strategies/S1_arms_ab_stop20_study.md fixes every choice. Reads data/results/S1_v8_trades.csv (the live rules' trades,
arms A and B, re-run 2026-10-20) and the 1-minute candles of their holding days, S1_v10_bandab_minutes.csv (fetched
on GitHub: `fetch_band_minutes ab`). Writes data/results/S1_arms_ab_stop20.md and S1_arms_ab_stop20_trades.csv.
"""
from __future__ import annotations

import pandas as pd

from . import backtest_s1_v4 as v4
from .backtest_s1_v2 import md
from .build import ROOT
from .stats import clustered_t

RES, CACHE = ROOT / "data" / "results", ROOT / "data" / "cache"
STOP, TICK_CHANGE = 0.80, "2025-11-03"
SESSIONS = sorted(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}" for p in CACHE.glob("fo_bhavcopy_*.csv"))


def tick(day: str) -> float:
    return 0.05 if day < TICK_CHANGE else 0.01


def one(r, m: pd.DataFrame | None) -> dict:
    """prev (the backtest's own exit) and new (the -20 % stop from d1 + 1, 09:16, on minutes; else prev)."""
    out = {"arm": r.arm, "symbol": r.symbol, "entry_date": r.entry_date, "exit_date": r.exit_date, "reason_prev": r.exit_reason,
           "lot": int(r.lot), "entry": float(r.entry_price), "premium": float(r.entry_price) * int(r.lot),
           "net_prev": float(r.net), "net_new": float(r.net), "fired": False, "excluded": ""}
    need = [d for d in SESSIONS if r.entry_date < d <= r.exit_date]
    if not need:
        return out                                               # sold on d1: the stop is not active that day
    if m is None or m.empty:
        out["excluded"] = "no_minute_candles"
        return out
    m = m[(m["date"] > r.entry_date) & (m["date"] <= r.exit_date) & (m["t"] >= "09:16") & (m["t"] <= "15:29")]
    have = set(m["date"])
    stop = STOP * out["entry"]
    hit = m[m["l"] <= stop + 1e-9]
    first_hit_day = hit["date"].iloc[0] if len(hit) else None
    gap = [d for d in need if d not in have and (first_hit_day is None or d < first_hit_day)]
    if gap:
        out["excluded"] = f"missing_minutes:{len(gap)}"           # a needed day without candles before any stop
        return out
    if hit.empty:
        return out
    i = hit.index[0]
    row = m.loc[i]
    tk = tick(row["date"])
    fill = round(max(tk, min(stop, float(row["o"])) - tk), 2)
    slip = v4.SLIPPAGE.get(r.category, v4.SLIPPAGE["unknown"])
    _, _, net = v4.net_of(out["entry"], fill, out["lot"], slip)
    later = m.loc[m.index > i]
    out.update({"fired": True, "net_new": net, "stop_date": row["date"], "stop_time": row["t"], "fill": fill,
                "stop_session": need.index(row["date"]) + 1,
                "peak_after_pct": round((float(later["h"].max()) / out["entry"] - 1) * 100, 1) if len(later) else None})
    return out


def stats(g: pd.DataFrame, col: str) -> dict:
    pct = g[col] / g["premium"] * 100
    return {"n": len(g), "win_pct": round((g[col] > 0).mean() * 100, 1), "mean_pct": round(pct.mean(), 2),
            "median_pct": round(pct.median(), 2), "total_rs": round(g[col].sum())}


def main() -> None:
    t = pd.read_csv(RES / "S1_v8_trades.csv")
    t = t[t["arm"].isin(["A", "B"]) & (t["excluded"].fillna("") == "")]
    mins = pd.read_csv(RES / "S1_v10_bandab_minutes.csv")
    mins["date"], mins["t"] = mins["ts"].str[:10], mins["ts"].str[11:16]
    by = {k: g.sort_values("ts").reset_index(drop=True) for k, g in mins.groupby(["symbol", "day0", "strike"])}
    rows = pd.DataFrame([one(r, by.get((r.symbol, r.entry_date, float(r.strike)))) for r in t.itertuples()])
    rows.to_csv(RES / "S1_arms_ab_stop20_trades.csv", index=False)
    ok = rows[rows["excluded"] == ""]
    comp, years, after = [], [], []
    for arm in ("A", "B"):
        g = ok[ok["arm"] == arm]
        d = (g["net_new"] - g["net_prev"]) / g["premium"] * 100
        comp.append({"arm": arm, "exit": "prev (S1 v7: 50 % stop at a close, 5-session decay, T-1)", **stats(g, "net_prev")})
        comp.append({"arm": arm, "exit": "new (+ -20 % stop from d1+1 09:16, minutes)", **stats(g, "net_new"),
                     "mean_diff_pct": round(d.mean(), 2), "t_diff": clustered_t(d, g["entry_date"]) if len(g) > 1 else None})
        for y, gy in g.groupby(g["entry_date"].str[:4]):
            years.append({"arm": arm, "year": y, "n": len(gy), "prev_rs": round(gy["net_prev"].sum()),
                          "new_rs": round(gy["net_new"].sum())})
        f = g[g["fired"]]
        pa = f["peak_after_pct"].dropna()
        after.append({"arm": arm, "stopped": f"{len(f)} / {len(g)}",
                      "stopped on d1+1": int((f["stop_session"] == 1).sum()),
                      "back above entry before prev's exit": f"{(pa >= 0).mean() * 100:.0f} %" if len(pa) else "-",
                      "reached +50 %": f"{(pa >= 50).mean() * 100:.0f} %" if len(pa) else "-",
                      "prev better on these": int((f["net_prev"] > f["net_new"]).sum()),
                      "prev on these Rs": round(f["net_prev"].sum()), "new on these Rs": round(f["net_new"].sum())})
    excl = rows[rows["excluded"] != ""]["excluded"].str.split(":").str[0].value_counts().to_dict()
    text = "\n".join([
        "# S1 arms A / B · prev (live exit) vs new (+ the fade's -20 % stop), 2025-04-01 to 2026-09-25\n",
        "Numbers only. Pre-registered: strategies/S1_arms_ab_stop20_study.md. Trades: the live rules (S1 v7 old_expiry) "
        "re-run 2026-10-20 (arm B 74 trades as recorded; arm A 175 vs 172 recorded on 2026-10-14, the data has grown). "
        "Same entry (d1's VWAP + 1 tick) for both; new adds a -20 % stop on 1-minute prices from the session after entry, "
        "filled at min(stop, minute open) - 1 tick; else prev's exit. Net after charges and % slippage. t of the "
        "per-trade difference (new - prev), date-clustered.\n",
        "## Prev vs new\n\n" + md(pd.DataFrame(comp)),
        "## By year (Rs)\n\n" + md(pd.DataFrame(years)),
        "## The stopped trades\n\n" + md(pd.DataFrame(after)),
        f"Excluded (both columns): {excl or 'none'}. Trades: data/results/S1_arms_ab_stop20_trades.csv.\n",
    ])
    (RES / "S1_arms_ab_stop20.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
