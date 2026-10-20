"""S1 fade · skip a fade trade when its market-hours filing day already moved >= 2 % the fade's way (both sides).

    python -m scanner.fade_filing_day_skip --nifty-dir <folder of spot_1m/NIFTY50/*.parquet>

strategies/S1_fade_filing_day_skip.md fixes every choice. Step 0 is a count gate: if the skip group is too small the
script stops after the counts. Writes data/results/S1_fade_filing_day_skip.md and _trades.csv.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

from .backtest_s1_v2 import md
from .build import ROOT
from .results_intraday import at, hm
from .stats import clustered_t

RES = ROOT / "data" / "results"
CUT, GATE_ALL, GATE_WIN = 2.0, 30, 10


def pct(a: float, b: float) -> float:
    return (b / a - 1) * 100 if a > 0 and b > 0 and not (math.isnan(a) or math.isnan(b)) else math.nan


def filing_day_moves(nifty_dir: Path) -> pd.DataFrame:
    cases = pd.read_csv(RES / "S1_intraday_cases.csv")
    mins = pd.read_csv(RES / "S1_intraday_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    stock = {k: g.drop_duplicates("t").set_index("t")["c"] for k, g in mins.groupby(["symbol", "day"])}
    nf = pd.concat([pd.read_parquet(p) for p in sorted(nifty_dir.glob("*.parquet"))])
    nf["day"], nf["t"] = nf["timestamp"].dt.strftime("%Y-%m-%d"), nf["timestamp"].dt.strftime("%H:%M")
    nifty = {d: g.drop_duplicates("t").set_index("t")["close"] for d, g in nf.groupby("day")}
    rows = []
    for r in cases.itertuples():
        s, n = stock.get((r.symbol, r.day)), nifty.get(r.day)
        pre = hm(r.t0, -1)
        d_raw = pct(at(s, pre), at(s, "15:29")) if s is not None else math.nan
        d_mkt = pct(at(n, pre), at(n, "15:29")) if n is not None else math.nan
        rows.append({"symbol": r.symbol, "day": r.day, "t0": r.t0, "D_raw": d_raw, "D": d_raw - d_mkt})
    return pd.DataFrame(rows)


def stats(g: pd.DataFrame, net: str = "e1_net", p: str = "e1_net_pct") -> dict:
    g = g.dropna(subset=[p])
    if g.empty:
        return {"n": 0}
    return {"n": len(g), "win %": round((g[net] > 0).mean() * 100, 1), "mean net %": round(g[p].mean(), 2),
            "median net %": round(g[p].median(), 2), "total Rs": round(g[net].sum()),
            "t": clustered_t(g[p], g["day0"]) if len(g) > 1 else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nifty-dir", type=Path, required=True)
    a = ap.parse_args()
    ft = pd.concat([pd.read_csv(RES / "S1_v10_trades_2022_24.csv"), pd.read_csv(RES / "S1_v10_trades.csv")])
    ft = ft[(ft["entry"] == "open") & (ft["e1_excluded"].fillna("") == "")].copy()
    ft["window"] = ["2022-24" if d < "2025-01-01" else "2025-26" for d in ft["day0"]]
    mv = filing_day_moves(a.nifty_dir)
    ft = ft.merge(mv, left_on=["symbol", "filed"], right_on=["symbol", "day"], how="left")
    ft["market_hours"] = ft["D"].notna()
    ft["D_bet"] = [(-d if s == "PE" else d) if not math.isnan(d) else math.nan for d, s in zip(ft["D"], ft["side"])]
    ft["group"] = ["not a market-hours filing" if math.isnan(x) else "SKIP (day already moved >= 2 % the fade's way)"
                   if x >= CUT else "mirror (day moved >= 2 % against the fade)" if x <= -CUT else "market hours, kept"
                   for x in ft["D_bet"]]
    skip = ft[ft["group"].str.startswith("SKIP")]

    counts = pd.DataFrame([{"group": g, **{w: int(((ft["group"] == g) & (ft["window"] == w)).sum()) for w in ("2022-24", "2025-26")},
                            "all": int((ft["group"] == g).sum())} for g in ft["group"].unique()])
    gate = len(skip) >= GATE_ALL and all((skip["window"] == w).sum() >= GATE_WIN for w in ("2022-24", "2025-26"))
    head = ["# S1 fade · skip trades whose market-hours filing day already moved the fade's way\n",
            "Pre-registered: strategies/S1_fade_filing_day_skip.md. D = the stock's move from the minute before the "
            "announcement to the filing day's 15:29 close, minus NIFTY 50's; D_bet = D in the fade's direction (-D for "
            "puts). Skip when D_bet >= +2 %. Fade trades: v10 backtest, entry at the open, E1 (15:20), net of charges.\n",
            f"Fade trades 2022-26: {len(ft)}; from market-hours filings: {int(ft['market_hours'].sum())}.\n",
            "## Step 0 · counts\n\n" + md(counts),
            f"Gate: the skip group needs >= {GATE_ALL} pooled and >= {GATE_WIN} in each window. "
            f"**{'PASSED: results below' if gate else 'FAILED: the study stops here (too few trades)'}**.\n"]
    if not gate:
        (RES / "S1_fade_filing_day_skip.md").write_text("\n".join(head), encoding="utf-8")
        print("\n".join(head))
        return

    v11 = None
    try:
        from .fade_armA_filter import v11_minutes
        v11 = v11_minutes()[["symbol", "day0", "side", "v11_net", "entry", "lot"]]
        v11 = v11.rename(columns={"entry": "m_entry", "lot": "m_lot"})
        ft = ft.merge(v11, on=["symbol", "day0", "side"], how="left")
        ft["v11_pct"] = ft["v11_net"] / (ft["m_entry"] * ft["m_lot"]) * 100
    except Exception as exc:  # noqa: BLE001
        print("v11 not available:", exc)
        ft["v11_net"] = ft["v11_pct"] = math.nan
    skip = ft[ft["group"].str.startswith("SKIP")]
    ft.to_csv(RES / "S1_fade_filing_day_skip_trades.csv", index=False)

    rows = []
    for g in ["SKIP (day already moved >= 2 % the fade's way)", "mirror (day moved >= 2 % against the fade)",
              "market hours, kept", "not a market-hours filing"]:
        for side in ("both", "PE", "CE"):
            for w in ("2022-24", "2025-26", "all"):
                x = ft[(ft["group"] == g) & ((ft["side"] == side) | (side == "both")) & ((ft["window"] == w) | (w == "all"))]
                rows.append({"group": g, "side": side, "window": w, **stats(x)})
    s1, s2 = skip[skip["window"] == "2022-24"], skip[skip["window"] == "2025-26"]
    sp = stats(skip)
    sv = skip.dropna(subset=["v11_pct"])
    test = pd.DataFrame([
        {"test": "1a skipped total Rs < 0 in 2022-24", "value": round(s1["e1_net"].sum()), "pass": s1["e1_net"].sum() < 0},
        {"test": "1b skipped total Rs < 0 in 2025-26", "value": round(s2["e1_net"].sum()), "pass": s2["e1_net"].sum() < 0},
        {"test": "2 pooled skipped mean < 0 with t <= -2", "value": f"{sp['mean net %']} % / t {sp['t']}",
         "pass": bool(sp["mean net %"] < 0 and (sp["t"] or 0) <= -2)},
        {"test": f"3 skipped mean < 0 under v11 (n {len(sv)}; required if >= 10)",
         "value": round(sv["v11_pct"].mean(), 2) if len(sv) else None,
         "pass": bool(len(sv) < 10 or sv["v11_pct"].mean() < 0)},
    ])
    verdict = "PASS (a candidate filter for the user's decision)" if test["pass"].all() else "FAIL (nothing changes)"
    whole = []
    for w in ("2022-24", "2025-26", "all"):
        x = ft if w == "all" else ft[ft["window"] == w]
        k = x[~x["group"].str.startswith("SKIP")]
        whole.append({"window": w, "all fade trades Rs": round(x["e1_net"].sum()), "n": len(x),
                      "with the skip Rs": round(k["e1_net"].sum()), "n kept": len(k),
                      "saved Rs": round(k["e1_net"].sum() - x["e1_net"].sum())})
    vrows = [{"group": g, **stats(ft[ft["group"] == g].dropna(subset=["v11_pct"]), "v11_net", "v11_pct")}
             for g in ft["group"].unique()]
    text = "\n".join(head + [
        f"## Test: **{verdict}**\n\n" + md(test),
        "## The whole fade, with and without the skip (v10, 15:20)\n\n" + md(pd.DataFrame(whole)),
        "## By group, side and window (v10, 15:20)\n\n" + md(pd.DataFrame(rows)),
        "## The same groups with v11's exit (minutes, Oct 2024 on)\n\n" + md(pd.DataFrame(vrows)),
        "Trades: data/results/S1_fade_filing_day_skip_trades.csv.\n",
    ])
    (RES / "S1_fade_filing_day_skip.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
