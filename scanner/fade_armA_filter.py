"""S1 fade · drop the trades where Arm A also fires: H (hindsight, day-0 close) and O (day-0 open) (numbers only).

    python -m scanner.fade_armA_filter

strategies/S1_v10_armA_overlap_filter.md fixes every choice. Reads the v10 backtest trades (entry = open, E1 exit,
2022-24 and 2025-26), the v11 exit on 1-minute candles (stop from 09:16, as live: S1_v10_bandv10_contracts.csv /
_minutes.csv via scanner.fade_s20_minutes.one; addendum 2026-10-20), eod2 opens / closes and the sector map.
Writes data/results/S1_v10_armA_overlap_filter.md and S1_v10_armA_overlap_filter_trades.csv.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .backtest_cheap_options import _read_index
from .backtest_s1_v2 import md
from .build import ROOT
from .equity import load_symbol
from .sectors import BENCHMARK, load_map
from .stats import clustered_t

RES, EOD2 = ROOT / "data" / "results", ROOT / "data" / "eod2"
BEAT, RAW_CAP, MIN_PEERS = 2.0, 10.0, 3
EXTRA = (1.0, 3.0)                                            # descriptive thresholds for O only


class Prices:
    """Opens and closes aligned to the NIFTY 50 calendar; leave-one-out sector gaps and returns."""

    def __init__(self, symbols: set[str]):
        self.cal = [t.strftime("%Y-%m-%d") for t in _read_index(EOD2).index]
        self.pos = {d: i for i, d in enumerate(self.cal)}
        self.sector_of = load_map()
        self.o, self.c = {}, {}
        for s in sorted(set(self.sector_of) | symbols):
            try:
                f = load_symbol(s, EOD2)
            except Exception:  # noqa: BLE001 - not every stock has eod2 history
                continue
            f.index = f.index.strftime("%Y-%m-%d")
            f = f[~f.index.duplicated(keep="last")].reindex(self.cal)
            self.o[s], self.c[s] = f["Open"].to_numpy(float), f["Close"].to_numpy(float)
        b = pd.read_csv(EOD2 / f"{BENCHMARK}.csv", usecols=["Date", "Open", "Close"], parse_dates=["Date"])
        b = b[b["Close"] > 0]
        b.index = b["Date"].dt.strftime("%Y-%m-%d")
        b = b[~b.index.duplicated(keep="last")].reindex(self.cal)
        self.bo, self.bc = b["Open"].to_numpy(float), b["Close"].to_numpy(float)
        self.members: dict[str, list[str]] = {}
        for s, k in self.sector_of.items():
            if s in self.c:
                self.members.setdefault(k, []).append(s)

    @staticmethod
    def _r(num: float, den: float) -> float:
        return num / den - 1 if num > 0 and den > 0 and not (math.isnan(num) or math.isnan(den)) else math.nan

    def ar(self, sym: str, day0: str) -> dict:
        i = self.pos.get(day0)
        out = {"raw_open": math.nan, "ar_open": math.nan, "raw_close": math.nan, "ar_close": math.nan, "bench": ""}
        if i is None or i < 1 or sym not in self.c:
            return out
        pc = self.c[sym][i - 1]
        raw_o, raw_c = self._r(self.o[sym][i], pc), self._r(self.c[sym][i], pc)
        peers = [p for p in self.members.get(self.sector_of.get(sym), []) if p != sym]
        go = [g for g in (self._r(self.o[p][i], self.c[p][i - 1]) for p in peers) if not math.isnan(g)]
        gc = [g for g in (self._r(self.c[p][i], self.c[p][i - 1]) for p in peers) if not math.isnan(g)]
        so = np.mean(go) if len(go) >= MIN_PEERS else self._r(self.bo[i], self.bc[i - 1])
        sc = np.mean(gc) if len(gc) >= MIN_PEERS else self._r(self.bc[i], self.bc[i - 1])
        out.update({"raw_open": raw_o * 100, "ar_open": (raw_o - so) * 100, "raw_close": raw_c * 100,
                    "ar_close": (raw_c - sc) * 100, "bench": "sector" if len(gc) >= MIN_PEERS else "nifty500"})
        return out


def flag(ar: float, raw: float, beat: float = BEAT) -> str:
    """'drop' when an Arm A beat (AR >= beat and raw < 10 %), 'keep' when not, 'unknown' when it cannot be computed."""
    if math.isnan(ar) or math.isnan(raw):
        return "unknown"
    return "drop" if ar >= beat and raw < RAW_CAP else "keep"


def stats(g: pd.DataFrame, net: str, prem: str) -> dict:
    if g.empty:
        return {"n": 0}
    pct = g[net] / g[prem] * 100
    return {"n": len(g), "win_pct": round((g[net] > 0).mean() * 100, 1), "mean_pct": round(pct.mean(), 2),
            "median_pct": round(pct.median(), 2), "total_rs": round(g[net].sum()),
            "t": clustered_t(pct, g["day0"]) if len(g) > 1 else None}


def groups(t: pd.DataFrame, net: str, prem: str, label: str) -> list[dict]:
    rows = []
    for side in ("all", "PE", "CE"):
        g = t if side == "all" else t[t["side"] == side]
        rows.append({"window": label, "side": side, "group": "all trades", **stats(g, net, prem)})
        for col, name in (("H", "H"), ("O", "O")):
            for f in ("keep", "drop"):
                rows.append({"window": label, "side": side, "group": f"{name} {f}", **stats(g[g[col] == f], net, prem)})
            u = g[g[col] == "unknown"]
            if len(u):
                rows.append({"window": label, "side": side, "group": f"{name} unknown (kept)", **stats(u, net, prem)})
    return rows


def v11_minutes() -> pd.DataFrame:
    """The minute trades with S1 v11's exit as live: the -20 % stop from 09:16 (v11_net), else the 15:20 result."""
    from .fade_s20_minutes import one
    c = pd.read_csv(RES / "S1_v10_bandv10_contracts.csv")
    mins = pd.read_csv(RES / "S1_v10_bandv10_minutes.csv")
    mins["t"] = mins["ts"].str[11:16]
    by = {k: g.sort_values("ts").reset_index(drop=True) for k, g in mins.groupby(["symbol", "day0", "side", "strike"])}
    rows = [x for r in c.itertuples() if (x := one(by.get((r.symbol, r.day0, r.side, float(r.strike))), r, "09:16"))]
    return pd.DataFrame(rows).rename(columns={"s20_net": "v11_net"})


def main() -> None:
    a = pd.read_csv(RES / "S1_v10_trades_2022_24.csv").assign(window="2022-24")
    b = pd.read_csv(RES / "S1_v10_trades.csv").assign(window="2025-26")
    t = pd.concat([a, b], ignore_index=True)
    t = t[(t["entry"] == "open") & (t["e1_excluded"].fillna("") == "")].reset_index(drop=True)
    m = v11_minutes()
    m["premium_rs"] = m["entry"] * m["lot"]
    px = Prices(set(t["symbol"]) | set(m["symbol"]))
    key = {k: px.ar(*k) for k in {(s, d) for s, d in zip(t["symbol"], t["day0"])} | {(s, d) for s, d in zip(m["symbol"], m["day0"])}}

    def tag(df: pd.DataFrame) -> pd.DataFrame:
        ar = pd.DataFrame([key[(s, d)] for s, d in zip(df["symbol"], df["day0"])], index=df.index)
        df = pd.concat([df, ar], axis=1)
        df["H"] = [flag(x, y) for x, y in zip(df["ar_close"], df["raw_close"])]
        df["O"] = [flag(x, y) for x, y in zip(df["ar_open"], df["raw_open"])]
        for e in EXTRA:
            df[f"O{e:g}"] = [flag(x, y, e) for x, y in zip(df["ar_open"], df["raw_open"])]
        return df

    t, m = tag(t), tag(m)
    t.to_csv(RES / "S1_v10_armA_overlap_filter_trades.csv", index=False)

    main_rows = groups(t[t["window"] == "2022-24"], "e1_net", "premium_rs", "2022-24")
    main_rows += groups(t[t["window"] == "2025-26"], "e1_net", "premium_rs", "2025-26")
    main_rows += groups(t, "e1_net", "premium_rs", "2022-26")
    mins = groups(m, "v11_net", "premium_rs", "v11 exit (minutes, stop from 09:16)") + \
        groups(m, "e1_net", "premium_rs", "v10 exit (minutes)")

    # the test (O, both sides)
    def od(w):
        g = t if w == "all" else t[t["window"] == w]
        g = g[g["O"] == "drop"]
        return g, (g["e1_net"] / g["premium_rs"] * 100)
    g1, p1 = od("2022-24")
    g2, p2 = od("2025-26")
    g3, p3 = od("all")
    mo = m[m["O"] == "drop"]
    p4 = mo["v11_net"] / mo["premium_rs"] * 100
    t3 = clustered_t(p3, g3["day0"]) if len(g3) > 1 else None
    test = pd.DataFrame([
        {"test": "1a O-dropped lose in 2022-24 (mean < 0)", "n": len(g1), "value": round(p1.mean(), 2) if len(g1) else None,
         "pass": bool(len(g1) and p1.mean() < 0)},
        {"test": "1b O-dropped lose in 2025-26 (mean < 0)", "n": len(g2), "value": round(p2.mean(), 2) if len(g2) else None,
         "pass": bool(len(g2) and p2.mean() < 0)},
        {"test": "2 pooled O-dropped t <= -2", "n": len(g3), "value": t3, "pass": bool(t3 is not None and t3 <= -2)},
        {"test": "3 O-dropped lose under v11 (minutes, stop from 09:16, mean < 0)", "n": len(mo), "value": round(p4.mean(), 2) if len(mo) else None,
         "pass": bool(len(mo) and p4.mean() < 0)},
    ])
    verdict = "PASS (candidate for the user's decision)" if test["pass"].all() else "FAIL (nothing changes)"

    # overlap: how much of H the open already shows; H vs real Arm A trades (2025-26)
    known = t[(t["H"] != "unknown") & (t["O"] != "unknown")]
    ov = pd.crosstab(known["H"].rename("H (close)"), known["O"].rename("O (open)"))
    arm = pd.read_csv(RES / "S1_v8_trades.csv")
    arm = arm[(arm["arm"] == "A") & (arm["excluded"].fillna("") == "")]
    real = set(zip(arm["symbol"], arm["signal_date"]))
    w = t[(t["window"] == "2025-26") & (t["day0"] >= "2025-04-01") & (t["day0"] <= "2026-09-25")]
    inA = pd.Series([(s, d) in real for s, d in zip(w["symbol"], w["day0"])], index=w.index)
    cross = pd.crosstab(w["H"].rename("H flag"), inA.rename("real Arm A trade"))

    extra = []
    for e in EXTRA:
        for f in ("keep", "drop"):
            for wl, g in (("2022-24", t[t["window"] == "2022-24"]), ("2025-26", t[t["window"] == "2025-26"])):
                extra.append({"threshold": f"AR open >= {e:g} %", "group": f, "window": wl,
                              **stats(g[g[f"O{e:g}"] == f], "e1_net", "premium_rs")})

    text = "\n".join([
        "# S1 fade · drop the trades where Arm A also fires (H = hindsight close, O = the 09:15 open)\n",
        "Numbers only. Pre-registered: strategies/S1_v10_armA_overlap_filter.md. v10 backtest trades, entry at the "
        "option's day-0 open, E1 same-day exit, net after charges. A trade is dropped when its stock is up >= 2 % "
        "more than its sector (and < 10 % raw): H at the day-0 close (Arm A's own signal, known only after the "
        "fade's sale), O at the day-0 open (known at 09:15). t is date-clustered. v11 = the -20 % stop "
        "from 09:16, as live (addendum 2026-10-20; the first run used the 09:15 column).\n",
        f"## Test (O, both sides): **{verdict}**\n\n" + md(test),
        "## All groups, v10 exit (E1)\n\n" + md(pd.DataFrame(main_rows)),
        "## Minute trades (Oct 2024 to Sep 2026): v11 exit and v10 exit\n\n" + md(pd.DataFrame(mins)),
        "## How many of Arm A's days the open already shows (2022-26, trades with both known)\n\n"
        + md(ov.reset_index()),
        "## H against the real Arm A trades (2025-04-01 to 2026-09-25)\n\n" + md(cross.reset_index()),
        "## Other thresholds for O (descriptive only, not the test)\n\n" + md(pd.DataFrame(extra)),
        "Trades: data/results/S1_v10_armA_overlap_filter_trades.csv.\n",
    ])
    (RES / "S1_v10_armA_overlap_filter.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
