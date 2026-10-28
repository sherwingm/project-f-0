"""S1 v12 fade · does what Nifty does by 09:15 (known live) tell us which fades fail? (numbers only)

    python -m scanner.fade_market_gap

"Market down" by the close is only known at 15:30, after the 09:16 buy, so it cannot be a live filter. The gap (Nifty open vs the
previous close) is known at 09:15. Same 339 trades as fade_market_direction; Nifty daily OHLC from yfinance (^NSEI), cached as Feather.
Writes data/results/S1_fade_market_gap.md.
"""
from __future__ import annotations

import pandas as pd
from scipy.stats import fisher_exact

from .backtest_s1_v2 import md
from .build import ROOT

RES = ROOT / "data" / "results"


def nifty() -> pd.DataFrame:
    f = RES / "nifty_daily_ohlc.feather"
    if not f.exists():
        import yfinance as yf
        d = yf.download("^NSEI", start="2024-10-01", auto_adjust=False, progress=False)
        d.columns = [c[0] for c in d.columns]
        d.reset_index().to_feather(f)
    d = pd.read_feather(f).set_index("Date")
    d["gap"] = (d["Open"] / d["Close"].shift(1) - 1) * 100
    d["close_move"] = (d["Close"] / d["Close"].shift(1) - 1) * 100
    return d


def line(g: pd.DataFrame) -> dict:
    return {"trades": len(g), "fail %": round(g["fail"].mean() * 100, 1), "mean net %": round(g["v12 net %"].mean(), 2),
            "total Rs": int(g["v12 net Rs"].sum())}


def main() -> None:
    t = pd.read_feather(RES / "S1_fade_market_direction_trades.feather")
    n = nifty()
    t["gap"] = pd.to_datetime(t["day0"]).map(n["gap"]).round(3)
    t = t.dropna(subset=["gap"]).copy()
    t["gap_dir"] = t["gap"].map(lambda x: "gap up" if x > 0 else "gap down")
    t["gap_with_trade"] = ((t["side"] == "CE") & (t["gap"] > 0)) | ((t["side"] == "PE") & (t["gap"] < 0))
    t["same_as_close"] = (t["gap"] > 0) == (t["nifty_pct"] > 0)
    rows = lambda by: pd.DataFrame([{"group": k if isinstance(k, str) else " / ".join(map(str, k)), **line(g)}   # noqa: E731
                                    for k, g in t.groupby(by, observed=True)])
    a = t[t["gap_dir"] == "gap up"]; b = t[t["gap_dir"] == "gap down"]
    p = fisher_exact([[int(a["fail"].sum()), int((~a["fail"]).sum())], [int(b["fail"].sum()), int((~b["fail"]).sum())]])[1]
    w = t[t["gap_with_trade"]]; ag = t[~t["gap_with_trade"]]
    p2 = fisher_exact([[int(w["fail"].sum()), int((~w["fail"]).sum())], [int(ag["fail"].sum()), int((~ag["fail"]).sum())]])[1]
    t["gap_size"] = pd.cut(t["gap"], [-99, -0.5, -0.2, 0, 0.2, 0.5, 99], labels=["< -0.5", "-0.5..-0.2", "-0.2..0", "0..+0.2", "+0.2..+0.5", "> +0.5"])
    text = "\n".join([
        "# S1 v12 fade · what Nifty does by 09:15 (the gap) vs the fade's failures\n",
        f"{len(t)} backtest trades. Gap = Nifty open vs the previous close, known at 09:15, before the 09:16 buy. The day's close is not. "
        f"The gap and the close move point the same way on {t['same_as_close'].mean() * 100:.0f} % of these days.\n",
        f"## Fail rate by gap direction (p = {p:.3f})\n\n" + md(rows("gap_dir")),
        "## By side\n\n" + md(rows(["side", "gap_dir"])),
        f"## Gap with the trade (down for a put, up for a call) vs against it (p = {p2:.3f})\n\n"
        + md(rows(t["gap_with_trade"].map({True: "gap with the trade", False: "gap against the trade"}))),
        "## By gap size\n\n" + md(rows("gap_size")),
    ])
    (RES / "S1_fade_market_gap.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
