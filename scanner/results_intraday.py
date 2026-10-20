"""S1 · results filed during market hours: fade or keep going after the first 15 minutes (step 1, stock only).

    python -m scanner.results_intraday --nifty-dir <folder of spot_1m/NIFTY50/*.parquet>

strategies/S1_intraday_results_reaction.md fixes every choice. Reads data/results/S1_intraday_cases.csv, the stock
minutes S1_intraday_minutes.csv (GitHub fetch: index_data.fetch_results_minutes), NIFTY 50 minutes (branch
index-data), data/financials.json and the v10 backtest trades. Writes data/results/S1_intraday_results_reaction.md
and .xlsx (one row per case).
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

from .backtest_s1_v2 import md
from .build import ROOT
from .event_screens import strong, weak
from .stats import clustered_t

RES = ROOT / "data" / "results"
BUCKETS = [(-1e9, -3, "<= -3 %"), (-3, -1, "-3..-1 %"), (-1, 1, "-1..+1 %"), (1, 3, "+1..+3 %"), (3, 1e9, ">= +3 %")]
OUTER = ("<= -3 %", "-3..-1 %", "+1..+3 %", ">= +3 %")
EXIT = "15:20"


def hm(t: str, add: int) -> str:
    h, m = map(int, t.split(":"))
    x = h * 60 + m + add
    return f"{x // 60:02d}:{x % 60:02d}"


def at(s: pd.Series, t: str, tol: int = 5) -> float:
    """The close of the minute starting at t, else the last close up to `tol` minutes before; NaN if none."""
    for k in range(tol + 1):
        v = s.get(hm(t, -k))
        if v is not None and not math.isnan(v):
            return float(v)
    return math.nan


def mv(s: pd.Series, a: str, b: str) -> float:
    x, y = at(s, a), at(s, b)
    return (y / x - 1) * 100 if x > 0 and y > 0 else math.nan


def bucket(x: float) -> str | None:
    if math.isnan(x):
        return None
    return next(n for lo, hi, n in BUCKETS if lo <= x < hi)


def measures(stock: pd.Series, nifty: pd.Series | None, t0: str) -> dict:
    pre, t15 = hm(t0, -1), hm(t0, 15)
    raw = {"B15": mv(stock, hm(t0, -16), pre), "R15": mv(stock, pre, t15), "RA": mv(stock, t15, EXIT)}
    mk = {k: (mv(nifty, *w) if nifty is not None else math.nan)
          for k, w in (("B15", (hm(t0, -16), pre)), ("R15", (pre, t15)), ("RA", (t15, EXIT)))}
    return {**{f"{k}_raw": v for k, v in raw.items()}, **{f"{k}_mkt": v for k, v in mk.items()},
            **{k: raw[k] - mk[k] for k in raw}}


def stats(g: pd.DataFrame, col: str = "RA") -> dict:
    g = g.dropna(subset=[col])
    if g.empty:
        return {"n": 0}
    cont = (g[col] * g["R15"] > 0).mean() * 100
    return {"n": len(g), "mean_RA": round(g[col].mean(), 3), "median_RA": round(g[col].median(), 3),
            "continue_pct": round(cont, 1), "t": clustered_t(g[col], g["day"]) if len(g) > 1 else None}


def table(df: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = []
    for b in [n for _, _, n in BUCKETS]:
        g = df[df["bucket"] == b]
        for w in ("2022-24", "2025-26", "all"):
            gw = g if w == "all" else g[g["window"] == w]
            rows.append({by: b, "window": w, **stats(gw)})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nifty-dir", type=Path, required=True)
    a = ap.parse_args()
    cases = pd.read_csv(RES / "S1_intraday_cases.csv")
    mins = pd.read_csv(RES / "S1_intraday_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    stock = {k: g.set_index("t")["c"] for k, g in mins.groupby(["symbol", "day"])}
    nf = pd.concat([pd.read_parquet(p) for p in sorted(a.nifty_dir.glob("*.parquet"))])
    nf["day"], nf["t"] = nf["timestamp"].dt.strftime("%Y-%m-%d"), nf["timestamp"].dt.strftime("%H:%M")
    nifty = {d: g.drop_duplicates("t").set_index("t")["close"] for d, g in nf.groupby("day")}
    import json
    fin = json.loads((ROOT / "data" / "financials.json").read_text(encoding="utf-8"))
    from .peak_study import result_quality

    rows, miss = [], {}
    for r in cases.itertuples():
        s = stock.get((r.symbol, r.day))
        why = None
        if s is None:
            why = "no_minutes"
        else:
            m = measures(s, nifty.get(r.day), r.t0)
            if math.isnan(m["R15_raw"]) or math.isnan(m["RA_raw"]):
                why = "minutes_do_not_cover_t0_to_1520"
        if why:
            miss[(r.day[:4], why)] = miss.get((r.day[:4], why), 0) + 1
            continue
        q = result_quality(fin, r.symbol, r.day)
        cls = "strong" if strong(q, 10) else "weak" if weak(q) else "neither"
        rows.append({"symbol": r.symbol, "day": r.day, "t0": r.t0, **{k: round(v, 3) for k, v in m.items()},
                     "class": cls, "window": "2022-24" if r.day < "2025-01-01" else "2025-26"})
    df = pd.DataFrame(rows)
    df["bucket"] = df["R15"].map(bucket)
    df = df.dropna(subset=["bucket"])

    main_t = table(df, "R15 bucket (adjusted)")
    raw = df.assign(R15=df["R15_raw"], RA=df["RA_raw"])
    raw["bucket"] = raw["R15"].map(bucket)
    raw_t = table(raw, "R15 bucket (raw)")
    cls_rows = []
    for c in ("strong", "weak", "neither"):
        for b in [n for _, _, n in BUCKETS]:
            cls_rows.append({"class": c, "R15 bucket": b, **stats(df[(df["class"] == c) & (df["bucket"] == b)])})
    yr = pd.DataFrame([{"year": y, "R15 bucket": b, **stats(df[(df["day"].str[:4] == y) & (df["bucket"] == b)])}
                       for y in sorted(df["day"].str[:4].unique()) for b in OUTER])

    test = []
    for b in OUTER:
        g = df[df["bucket"] == b]
        s1, s2, sp = stats(g[g["window"] == "2022-24"]), stats(g[g["window"] == "2025-26"]), stats(g)
        m1, m2, t = s1.get("mean_RA"), s2.get("mean_RA"), sp.get("t")
        same = m1 is not None and m2 is not None and (m1 > 0) == (m2 > 0) and m1 != 0
        big = m1 is not None and m2 is not None and abs(m1) >= 0.5 and abs(m2) >= 0.5
        sig = t is not None and abs(t) >= 3
        kind = ("continuation" if (m1 > 0) == (b.startswith("+") or b.startswith(">=")) else "fade") if same else "-"
        test.append({"bucket": b, "n 22-24": s1.get("n"), "mean RA 22-24": m1, "n 25-26": s2.get("n"),
                     "mean RA 25-26": m2, "pooled t": t, "same sign": same, "|mean| >= 0.5 both": big, "|t| >= 3": sig,
                     "pattern": kind, "PASS": bool(same and big and sig)})
    test = pd.DataFrame(test)
    verdict = "PASS: step 2 may test " + ", ".join(f"{r.bucket} {r.pattern}" for r in test.itertuples() if r.PASS) \
        if test["PASS"].any() else "FAIL: no bucket passes; step 1 closes, no option test"

    timing = pd.DataFrame([{"window": w, "n": len(g), "mean |B15| (15 min before t0)": round(g["B15"].abs().mean(), 3),
                            "mean |R15| (first 15 min)": round(g["R15"].abs().mean(), 3),
                            "mean |RA| (after, to 15:20)": round(g["RA"].abs().mean(), 3)}
                           for w, g in (("all", df), ("2022-24", df[df["window"] == "2022-24"]),
                                        ("2025-26", df[df["window"] == "2025-26"]))])

    # the loss question: fade backtest trades whose filing was one of these cases (filed in market hours)
    ft = pd.concat([pd.read_csv(RES / "S1_v10_trades_2022_24.csv"), pd.read_csv(RES / "S1_v10_trades.csv")])
    ft = ft[(ft["entry"] == "open") & (ft["e1_excluded"].fillna("") == "")]
    j = ft.merge(df, left_on=["symbol", "filed"], right_on=["symbol", "day"], how="inner")
    loss = []
    for side, g in j.groupby("side"):
        bet = -1 if side == "PE" else 1                          # put: bets on a fall
        for lab, gg in (("filing day moved WITH the fade's bet (R15+RA)", g[(g["R15"] + g["RA"]) * bet > 0]),
                        ("filing day moved AGAINST it", g[(g["R15"] + g["RA"]) * bet <= 0])):
            loss.append({"fade side": side, "group": lab, "trades": len(gg),
                         "mean R15+RA on the filing day %": round((gg["R15"] + gg["RA"]).mean(), 2) if len(gg) else None,
                         "fade win %": round((gg["e1_net"] > 0).mean() * 100, 1) if len(gg) else None,
                         "fade total Rs (15:20)": round(gg["e1_net"].sum()) if len(gg) else None})
    loss = pd.DataFrame(loss)

    excl = pd.DataFrame([{"year": y, "why": w, "cases": n} for (y, w), n in sorted(miss.items())])
    text = "\n".join([
        "# S1 · results filed during market hours: fade or keep going? (step 1, stock only)\n",
        "Pre-registered: strategies/S1_intraday_results_reaction.md. 1-minute closes; R15 = the move from the last "
        "minute before the announcement to 15 minutes after it; RA = from there to the 15:20 close (the test). Moves "
        "are minus NIFTY 50's over the same minutes unless marked raw. t is date-clustered. continue_pct = the share "
        "of cases where RA went the same way as R15.\n",
        f"Cases: {len(cases)} filings; with usable minutes: {len(df)}.\n",
        f"## Test: **{verdict}**\n\n" + md(test),
        "## By first-15-minute move (adjusted)\n\n" + md(main_t),
        "## Same, raw moves\n\n" + md(raw_t),
        "## By the fade's numbers class (adjusted)\n\n" + md(pd.DataFrame(cls_rows)),
        "## By year (outer buckets, adjusted)\n\n" + md(yr),
        "## Timing check: is the stored time late?\n\n" + md(timing),
        "## The loss question: v10 backtest fade trades whose filing came in market hours the session before\n\n"
        + (md(loss) if len(loss) else "(none)\n")
        + f"\n{len(j)} fade trades matched. The fade buys at the next session's open; this shows whether the filing day "
          "had already moved its way.\n",
        "## Cases without usable minutes\n\n" + md(excl),
    ])
    (RES / "S1_intraday_results_reaction.md").write_text(text, encoding="utf-8")
    df.to_excel(RES / "S1_intraday_results_reaction.xlsx", index=False)
    print(text)


if __name__ == "__main__":
    main()
