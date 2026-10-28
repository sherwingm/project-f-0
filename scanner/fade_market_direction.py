"""S1 v12 fade · when a trade fails, is the market up or down on day 0? (numbers only)

    python -m scanner.fade_market_direction

Uses the 339 v12 backtest trades (data/results/S1_v12_exit_trades.csv) and Nifty 50's daily close
(data/eod2/nifty 50.csv). Market move = day-0 close vs the previous close (daily file: no intraday
index minutes there). Fail = v12 net < 0. Also writes the trade table and a speed test of CSV vs
Parquet vs Feather on the big minutes file. Writes data/results/S1_fade_market_direction.md,
_trades.parquet and _trades.feather.
"""
from __future__ import annotations

import time

import pandas as pd
from scipy.stats import fisher_exact

from .backtest_s1_v2 import md
from .build import ROOT
from .stats import clustered_t

RES = ROOT / "data" / "results"


def load() -> pd.DataFrame:
    t = pd.read_csv(RES / "S1_v12_exit_trades.csv")
    n = pd.read_csv(ROOT / "data" / "eod2" / "nifty 50.csv", parse_dates=["Date"]).set_index("Date")["Close"]
    ret = (n / n.shift(1) - 1) * 100
    t["nifty_pct"] = pd.to_datetime(t["day0"]).map(ret).round(3)
    t = t.dropna(subset=["nifty_pct"]).copy()
    t["market"] = t["nifty_pct"].map(lambda x: "up" if x > 0 else "down")
    t["fail"] = t["v12 net Rs"] < 0
    t["stopped"] = t["v12 why"] == "stop"
    t["with_trade"] = ((t["side"] == "CE") & (t["nifty_pct"] > 0)) | ((t["side"] == "PE") & (t["nifty_pct"] < 0))
    return t


def line(g: pd.DataFrame) -> dict:
    return {"trades": len(g), "fail %": round(g["fail"].mean() * 100, 1), "stopped %": round(g["stopped"].mean() * 100, 1),
            "mean net %": round(g["v12 net %"].mean(), 2), "total Rs": int(g["v12 net Rs"].sum())}


def table(t: pd.DataFrame, by) -> pd.DataFrame:
    rows = [{**{"group": k if isinstance(k, str) else " / ".join(map(str, k))}, **line(g)} for k, g in t.groupby(by, observed=True)]
    return pd.DataFrame(rows)


def speed() -> pd.DataFrame:
    src = RES / "S1_v10_bandv10_minutes.csv"
    df = pd.read_csv(src)
    out = []
    for name, path, wr, rd in (("CSV", src, None, pd.read_csv),
                               ("Parquet", RES / "_speed.parquet", lambda p: df.to_parquet(p), pd.read_parquet),
                               ("Feather", RES / "_speed.feather", lambda p: df.to_feather(p), pd.read_feather)):
        if wr:
            wr(path)
        t0 = time.perf_counter()
        for _ in range(3):
            rd(path)
        out.append({"format": name, "size MB": round(path.stat().st_size / 1e6, 1),
                    "read s (mean of 3)": round((time.perf_counter() - t0) / 3, 3)})
        if wr:
            path.unlink()
    r = pd.DataFrame(out)
    r["read x faster than CSV"] = (r.loc[0, "read s (mean of 3)"] / r["read s (mean of 3)"]).round(1)
    return r


def main() -> None:
    t = load()
    t.to_parquet(RES / "S1_fade_market_direction_trades.parquet", index=False)
    t.to_feather(RES / "S1_fade_market_direction_trades.feather")
    up, dn = t[t["market"] == "up"], t[t["market"] == "down"]
    a = [[int(up["fail"].sum()), int((~up["fail"]).sum())], [int(dn["fail"].sum()), int((~dn["fail"]).sum())]]
    p_all = fisher_exact(a)[1]
    wt, ag = t[t["with_trade"]], t[~t["with_trade"]]
    p_with = fisher_exact([[int(ag["fail"].sum()), int((~ag["fail"]).sum())], [int(wt["fail"].sum()), int((~wt["fail"]).sum())]])[1]
    big = t[t["nifty_pct"].abs() >= 0.5]
    t["move"] = pd.cut(t["nifty_pct"], [-99, -1, -0.5, 0, 0.5, 1, 99], labels=["< -1 %", "-1 to -0.5", "-0.5 to 0", "0 to +0.5", "+0.5 to +1", "> +1 %"])
    fails = t[t["fail"]]
    text = "\n".join([
        "# S1 v12 fade · is the market up or down when the fade fails?\n",
        f"{len(t)} backtest trades ({t['day0'].min()} to {t['day0'].max()}), v12 exit, real charges. Market = Nifty 50 close on day 0 vs the "
        "previous close (daily file; it includes the overnight gap). Fail = net < 0. Fisher exact p-values.\n",
        f"## The failures only ({len(fails)} trades)\n\nMarket up on **{(fails['market'] == 'up').mean() * 100:.0f} %** of failing days, down on "
        f"{(fails['market'] == 'down').mean() * 100:.0f} %. Across all trades the market was up on {(t['market'] == 'up').mean() * 100:.0f} % of days.\n",
        f"## Fail rate by market direction (p = {p_all:.3f})\n\n" + md(table(t, "market")),
        "## By side (puts are the weak-result trades, calls the strong ones)\n\n" + md(table(t, ["side", "market"])),
        f"## Market with the trade vs against it (p = {p_with:.3f})\n\nWith = market down for a put, up for a call.\n\n"
        + md(table(t.assign(g=t["with_trade"].map({True: "market with the trade", False: "market against the trade"})), "g")),
        "## By size of the Nifty move\n\n" + md(table(t, "move")),
        f"## Days with a big move (|Nifty| >= 0.5 %, {len(big)} trades)\n\n" + md(table(big, "market")),
        "## Speed: CSV vs Parquet vs Feather (data/results/S1_v10_bandv10_minutes.csv)\n\n" + md(speed()),
        "\nTrade table with the market column: data/results/S1_fade_market_direction_trades.parquet (and .feather).\n",
    ])
    (RES / "S1_fade_market_direction.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
