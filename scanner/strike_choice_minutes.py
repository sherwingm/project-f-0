"""S1 strike choice, a 09:16-knowable volume rule, and the next strike when the pick has no 09:16 trade (numbers only).

    python -m scanner.strike_choice_minutes build     # contract lists for the Upstox fetch (GitHub stock-options-probe)
    python -m scanner.strike_choice_minutes run       # the report, once the minute files are in data/results

Pre-registered in strategies/S1_strike_choice_minutes.md.
"""
from __future__ import annotations

import sqlite3
import sys

import pandas as pd

from .backtest_s1_v10 import Bhav, start_strike
from .build import ROOT

RES = ROOT / "data" / "results"
SPLIT = "2025-11-03"
PARTS = 2
WALK_EXTRA = 3          # strikes fetched past the pick


def fade_signals() -> pd.DataFrame:
    """The 468 realistic-entry fade signals with their pick, expiry, lot, start spot and walk length."""
    t = pd.read_csv(RES / "S1_fade_realistic_entry_trades.csv")
    con = pd.read_csv(RES / "S1_v10_bandv10_contracts.csv")[["symbol", "day0", "side", "expiry", "strike"]]
    v10 = pd.concat([pd.read_csv(RES / "S1_v10_trades.csv"), pd.read_csv(RES / "S1_v10_trades_2022_24.csv")])
    v10 = v10.drop_duplicates(["symbol", "day0", "side"])[["symbol", "day0", "side", "spot_prev_close", "strikes_walked"]]
    return t.merge(con, on=["symbol", "day0", "side"]).merge(v10, on=["symbol", "day0", "side"])


def chain(bh: Bhav, day: str, sym: str, exp: str, side: str) -> list[float]:
    d = bh.day(day)
    if d is None or sym not in d["chain"]:
        return []
    c = d["chain"][sym]
    return sorted(set(c[(c["XpryDt"] == exp) & (c["OptnTp"] == side)]["StrkPric"].astype(float)))


def ladder(ks: list[float], spot: float, side: str) -> tuple[list[float], list[float]]:
    """(the walk path from the at-the-money strike outward, the in-the-money strikes nearest first)."""
    k0 = start_strike(ks, spot, side)
    i = ks.index(k0)
    if side == "PE":
        return ks[: i + 1][::-1], ks[i + 1:]
    return ks[i:], ks[:i][::-1]


def ban_set() -> set[tuple[str, str]]:
    c = sqlite3.connect(ROOT / "data" / "events.sqlite")
    return set(c.execute("select symbol, event_date from events where type='ban' and subtype='in'").fetchall())


def armab_dropped() -> pd.DataFrame:
    """The arms A / B trades S1_armab_minutes dropped for 'no 09:16 candle' (same selection as that script)."""
    mins = pd.read_csv(RES / "S1_v10_bandarmab2_minutes.csv", usecols=["symbol", "day0", "strike", "ts"])
    mins["d"], mins["t"] = mins["ts"].str[:10], mins["ts"].str[11:16]
    have = {k: set(zip(g["d"], g["t"])) for k, g in mins.groupby(["symbol", "day0", "strike"])}
    tr = pd.read_csv(RES / "S1_armb_hold_and_nifty_trades.csv")
    tr = tr[(tr.variant == "LIVE") & tr.arm.isin(["A", "B"]) & tr.excluded.isna() & (tr.expiry >= "2024-10-01")]
    tr = tr.drop_duplicates(["arm", "symbol", "signal_date", "strike", "expiry"])
    out = []
    for r in tr.itertuples():
        h = have.get((r.symbol, r.signal_date, float(r.strike)))
        if h is None or any(d == r.entry_date for d, _ in h) is False:
            continue
        if (r.entry_date, "09:16") not in h:
            out.append(r._asdict())
    return pd.DataFrame(out)


def build() -> None:
    bh, rows, odd = Bhav(ROOT / "data" / "cache"), [], []
    for r in fade_signals().itertuples():
        ks = chain(bh, r.day0, r.symbol, r.expiry, r.side)
        if not ks:
            odd.append((r.symbol, r.day0, "no chain"))
            continue
        path, itm = ladder(ks, r.spot_prev_close, r.side)
        n = int(r.strikes_walked)
        if n >= len(path) or path[n] != r.strike:
            odd.append((r.symbol, r.day0, "walk does not land on the pick"))
        want = itm[:2] + path[: n + 1 + WALK_EXTRA]
        for k in want:
            if k != r.strike:
                rows.append(dict(symbol=r.symbol, day0=r.day0, side=r.side, expiry=r.expiry, strike=k))
    x = pd.DataFrame(rows).drop_duplicates()
    nbr = pd.read_csv(RES / "S1_v10_bandnbrfade_contracts.csv")       # fetched by the neighbour test: not again
    key = ["symbol", "day0", "side", "expiry", "strike"]
    x = x.merge(nbr[key].drop_duplicates(), on=key, how="left", indicator=True)
    print(f"candidates {len(x)}, already in the neighbour fetch {int((x['_merge'] == 'both').sum())}")
    x = x[x["_merge"] == "left_only"].drop(columns="_merge")
    groups = [g for _, g in x.groupby(["symbol", "expiry"], sort=True)]
    size, part, cur = len(x) / PARTS, 1, []
    n = 0
    for g in groups:                                       # keep one stock-expiry in one part (one contract-list call)
        cur.append(g)
        n += len(g)
        if n >= size * part and part < PARTS:
            pd.concat(cur).to_csv(RES / f"S1_v10_bandstrk{part}_contracts.csv", index=False)
            print(f"part {part}: {sum(len(c) for c in cur)} contracts")
            cur, part = [], part + 1
    pd.concat(cur).to_csv(RES / f"S1_v10_bandstrk{part}_contracts.csv", index=False)
    print(f"part {part}: {sum(len(c) for c in cur)} contracts; total {len(x)}; odd: {odd}")
    d = armab_dropped()
    nxt = []
    for r in d.itertuples():
        ks = chain(bh, r.entry_date, r.symbol, r.expiry, "CE")
        up = [k for k in ks if k > r.strike]
        if not up:
            print("arms: no strike above", r.symbol, r.entry_date, r.strike)
            continue
        nxt.append(dict(symbol=r.symbol, day0=r.signal_date, side="CE", expiry=r.expiry, strike=up[0],
                        **{"from": r.entry_date, "to": r.expiry}))
    pd.DataFrame(nxt).drop_duplicates().to_csv(RES / "S1_v10_bandabnext_contracts.csv", index=False)
    print(f"arms A / B dropped for no 09:16 candle: {len(d)}; next-strike contracts: {len(nxt)}")


if __name__ == "__main__":
    {"build": build}[sys.argv[1]]()
