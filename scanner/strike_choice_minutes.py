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


# ---------------------------------------------------------------- the report
V12 = {"S": 20, "mode": "touch", "start": "09:17", "A": 10, "D": 2, "re": False}
FADE_MINUTES = ("v10", "nbrfade", "strk1", "strk2")
LABELS = ("ITM2", "ITM1", "ATM", "walk -1", "pick", "walk +1", "walk +2", "walk +3")
XS = (1, 2, 5, 10, 25)


def load_minutes(bands) -> dict:
    """{(symbol, day0, side, strike): DataFrame(d, t, o, h, l, c, volume) sorted}, from every band file present."""
    from .fastio import read_table
    out, missing = {}, []
    for b in bands:
        f = RES / f"S1_v10_band{b}_minutes.csv"
        if not f.exists():
            missing.append(f.name)
            continue
        m = read_table(f)
        m["d"], m["t"] = m["ts"].str[:10], m["ts"].str[11:16]
        for k, g in m.groupby(["symbol", "day0", "side", "strike"]):
            key = (k[0], k[1], k[2], float(k[3]))
            if key not in out:
                out[key] = g.sort_values("ts")[["d", "t", "o", "h", "l", "c", "volume"]].reset_index(drop=True)
    if missing:
        print("minute files missing:", missing)
    return out


def day_volumes() -> dict:
    """{(symbol, expiry, side, strike, day): contracts traded} from the cached bhavcopy (the backtest's day-0 check)."""
    import glob
    want = set(fade_signals()["day0"])
    out = {}
    for f in glob.glob(str(ROOT / "data" / "cache" / "fo_bhavcopy_2*.csv")):
        s = f[-12:-4]
        day = f"{s[:4]}-{s[4:6]}-{s[6:]}"
        if day not in want:
            continue
        b = pd.read_csv(f, usecols=["TckrSymb", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "TtlTradgVol"])
        b = b[b["FinInstrmTp"] == "STO"]
        for r in b.itertuples():
            out[(str(r.TckrSymb).strip(), str(r.XpryDt)[:10], r.OptnTp, float(r.StrkPric), day)] = float(r.TtlTradgVol)
    return out


def fade_trade(c: pd.DataFrame | None, day: str, lot: int, side: str) -> dict | None:
    """v12 on one strike's day-0 candles; None if it has no 09:16 candle."""
    from server import charges as ch
    from .fade_stop_trail import walk
    if c is None:
        return None
    c = c[(c["d"] == day) & (c["t"] >= "09:16") & (c["t"] <= "15:19")].reset_index(drop=True)
    if c.empty or c["t"].iloc[0] != "09:16":
        return None
    tick = 0.05 if day < SPLIT else 0.01
    e = round(float(c["o"].iloc[0]) + tick, 2)
    sell, _ = walk(c, e, tick, V12, 1)
    net = (sell - e) * lot - ch.leg(side, "BUY", lot, e)["total"] - ch.leg(side, "SELL", lot, sell)["total"]
    return {"entry": e, "exit": sell, "net": round(net, 2), "net_pct": round(net / (e * lot) * 100, 3), "cost": e * lot}


def vol_0915(c: pd.DataFrame | None, day: str, lot: int) -> float:
    if c is None:
        return 0.0
    v = c[(c["d"] == day) & (c["t"] == "09:15")]["volume"]
    return float(v.iloc[0]) / lot if len(v) else 0.0


def stats_of(g: pd.DataFrame, col: str = "net_pct") -> dict:
    from .stats import clustered_t
    if g.empty:
        return {"n": 0}
    x = g[col]
    top = g.sort_values("net", ascending=False)
    return {"n": len(g), "win %": round((x > 0).mean() * 100, 1), "mean %": round(x.mean(), 2),
            "median %": round(x.median(), 2), "total Rs": round(g["net"].sum()), "t": clustered_t(x, g["day0"]),
            "mean without top 3 %": round(top.iloc[3:][col].mean(), 2) if len(g) > 3 else None}


def run() -> None:
    from .backtest_s1_v2 import md
    from .stats import clustered_t
    sig = fade_signals()
    ban = ban_set()
    sig["in_ban"] = [(s, d) in ban for s, d in zip(sig["symbol"], sig["day0"])]
    mins = load_minutes(FADE_MINUTES)
    bh = Bhav(ROOT / "data" / "cache")
    dv = day_volumes()
    rows, walks, nxt = [], [], []
    for r in sig.itertuples():
        ks = chain(bh, r.day0, r.symbol, r.expiry, r.side)
        path, itm = ladder(ks, r.spot_prev_close, r.side)
        n, lot = int(r.strikes_walked), int(r.lot)
        lab = {"ITM2": itm[1] if len(itm) > 1 else None, "ITM1": itm[0] if itm else None, "ATM": path[0],
               "walk -1": path[n - 1] if n >= 1 else None, "pick": r.strike}
        for j in (1, 2, 3):
            lab[f"walk +{j}"] = path[n + j] if n + j < len(path) else None
        base = dict(symbol=r.symbol, day0=r.day0, side=r.side, lot=lot, in_ban=r.in_ban,
                    half="train" if r.day0 < SPLIT else "test")
        for name, k in lab.items():                                          # Test 1
            if k is None:
                continue
            t = fade_trade(mins.get((r.symbol, r.day0, r.side, float(k))), r.day0, lot, r.side)
            if t and t["entry"] >= 2:
                rows.append({**base, "rule": name, "strike": k, **t})
        for x in XS:                                                          # Test 2
            got, why = None, "no strike passed"
            for j, k in enumerate(path[: 15]):
                if j > n + WALK_EXTRA:
                    why = "beyond the fetch"
                    break
                c = mins.get((r.symbol, r.day0, r.side, float(k)))
                if vol_0915(c, r.day0, lot) < x:
                    continue
                t = fade_trade(c, r.day0, lot, r.side)
                if t is None:
                    continue
                if t["entry"] < 2:
                    why = "premium below 2"
                    break
                if t["cost"] < 600:
                    why = "walk below band"
                    break
                if t["cost"] > 8000:
                    continue
                got = {**base, "rule": f"09:15 volume >= {x} lots", "strike": k, "changed": k != r.strike, **t}
                break
            walks.append(got or {**base, "rule": f"09:15 volume >= {x} lots", "dropped": why})
        if pd.notna(r.B_excluded) and r.B_excluded:                          # Test 3, fade
            for j in range(n + 1, min(n + 1 + WALK_EXTRA, len(path))):
                k = path[j]
                if dv.get((r.symbol, r.expiry, r.side, float(k), r.day0), 0) < 50:
                    continue
                t = fade_trade(mins.get((r.symbol, r.day0, r.side, float(k))), r.day0, lot, r.side)
                if t is None:
                    continue
                if t["entry"] < 2 or t["cost"] < 600:
                    break
                if t["cost"] > 8000:
                    continue
                nxt.append({**base, "rule": "next strike", "strike": k, "steps": j - n, **t})
                break
    T = pd.DataFrame(rows)
    T = T[~T["in_ban"]]
    W = pd.DataFrame(walks)
    N = pd.DataFrame(nxt)
    out = ["# S1 strike choice, 09:16 volume rule, next strike (fade v12; arms A / B next strike)\n",
           "Numbers only. Pre-registered: strategies/S1_strike_choice_minutes.md. Entry 09:16 open + 1 tick, v12 exit, "
           f"1-minute Upstox candles; ban-day signals dropped ({int(sig['in_ban'].sum())}). Train before {SPLIT}, test from it.\n"]
    # Test 1
    pick = T[T["rule"] == "pick"].set_index(["symbol", "day0", "side"])
    t1 = []
    for name in LABELS:
        g = T[T["rule"] == name]
        row = {"strike rule": name, **stats_of(g), "lot over Rs 8,000 %": round((g["cost"] > 8000).mean() * 100, 1) if len(g) else None,
               "mean lot Rs": round(g["cost"].mean()) if len(g) else None}
        if name != "pick" and len(g):
            j = g.set_index(["symbol", "day0", "side"]).join(pick[["net_pct", "net"]], rsuffix="_pick", how="inner")
            d = j["net_pct"] - j["net_pct_pick"]
            dd = d.reset_index()
            row.update({"paired n": len(j), "diff vs pick (points)": round(d.mean(), 2),
                        "diff t": clustered_t(d.values, dd["day0"].values),
                        "diff train": round(d[j["half"] == "train"].mean(), 2), "diff test": round(d[j["half"] == "test"].mean(), 2),
                        "Rs vs pick": round((j["net"] - j["net_pick"]).sum())})
            ok = (row["diff vs pick (points)"] > 0 and (row["diff t"] or 0) >= 2 and row["diff train"] > 0
                  and row["diff test"] > 0 and row["Rs vs pick"] > 0)
            row["beats the pick"] = ("over budget" if ok and row["lot over Rs 8,000 %"] > 50 else "YES") if ok else "no"
        t1.append(row)
    out += ["## Test 1 · which strike (v12)\n", md(pd.DataFrame(t1)),
            "\nPass: paired diff > 0 with t >= 2, > 0 in both halves, and more Rs. No lot cap on the alternatives.\n"]
    # Test 2
    cur = T[T["rule"] == "pick"]
    t2 = [{"rule": "today: >= 50 contracts on the whole day (not known at 09:16)", "half": h, **stats_of(cur[cur["half"] == h])}
          for h in ("train", "test")]
    best, bm = None, None
    for x in XS:
        name = f"09:15 volume >= {x} lots"
        g = W[(W["rule"] == name)]
        g = g[g["dropped"].isna() & ~g["in_ban"]] if "dropped" in g else g[~g["in_ban"]]
        for h in ("train", "test"):
            s = stats_of(g[g["half"] == h])
            s["picks changed"] = int(g[g["half"] == h]["changed"].sum()) if len(g) else 0
            t2.append({"rule": name, "half": h, **s})
            if h == "train" and s.get("n") and (bm is None or s["mean %"] > bm):
                best, bm = x, s["mean %"]
    drops = W[W.get("dropped").notna()].groupby(["rule", "dropped"]).size().reset_index(name="signals") if "dropped" in W else pd.DataFrame()
    out += ["## Test 2 · a volume rule known at 09:16 (v12)\n", md(pd.DataFrame(t2)),
            f"\nTrain picks X = {best} (highest train mean). Judge its test row against today's test row.\n",
            "Signals without a trade per rule:\n", md(drops)]
    # Test 3 fade
    N = N[~N["in_ban"]] if len(N) else N
    out += ["## Test 3 · next strike when the pick has no 09:16 trade\n",
            f"Fade: {int(sig['B_excluded'].notna().sum())} signals had no 09:16 candle on the pick; next strike found for {len(N)}.\n",
            md(pd.DataFrame([{"set": "fade, the added next-strike trades", **stats_of(N)},
                             {"set": "fade, the 409 picks + the added", **stats_of(pd.concat([cur, N]))},
                             {"set": "fade, the picks alone", **stats_of(cur)}]))]
    out += arms_next(ban)
    pd.concat([T, W, N], ignore_index=True).to_csv(RES / "S1_strike_choice_minutes_trades.csv", index=False)
    text = "\n".join(out)
    (RES / "S1_strike_choice_minutes.md").write_text(text, encoding="utf-8")
    print(text)


def arms_next(ban: set) -> list[str]:
    """The arms A / B trades dropped for 'no 09:16 candle': the next call strike up, and (side line) the same strike entered
    at its first candle after 09:16 (up to 09:30)."""
    from . import backtest_s1_v4 as v4
    from .armab_minutes import VARIANTS, calendar, iso, run_one
    from .backtest_s1_v2 import md
    cal = [iso(x) for x in calendar()]
    d = armab_dropped()
    nxt = pd.read_csv(RES / "S1_v10_bandabnext_contracts.csv")
    up = {(r.symbol, r.day0, r.expiry): float(r.strike) for r in nxt.itertuples()}
    mn = load_minutes(("abnext", "armab2"))
    rows = []
    for r in d.itertuples():
        if (r.symbol, r.entry_date) in ban:
            continue
        for setname, k, shift in (("next strike up", up.get((r.symbol, r.signal_date, r.expiry)), False),
                                  ("same strike, first candle 09:16-09:30", float(r.strike), True)):
            c = mn.get((r.symbol, r.signal_date, "CE", k)) if k else None
            if c is None:
                continue
            days = {x: g.reset_index(drop=True) for x, g in c.groupby("d")}
            if shift and r.entry_date in days:
                g = days[r.entry_date]
                first = g[(g["t"] >= "09:16") & (g["t"] <= "09:30")]
                if first.empty:
                    continue
                g = g[g.index >= first.index[0]].copy()
                g.loc[first.index[0], "t"] = "09:16"
                days[r.entry_date] = g
            for var in VARIANTS:
                res, _ = run_one(days, cal, r.entry_date, r.expiry, var)
                if not isinstance(res, dict):
                    continue
                slip = v4.SLIPPAGE.get(r.category, v4.SLIPPAGE["unknown"])
                _, _, net = v4.net_of(res["entry"], res["exit_price"], r.lot, slip)
                rows.append(dict(set=setname, arm=r.arm, variant=var, symbol=r.symbol, day0=r.entry_date, net=net,
                                 net_pct=round(net / (res["entry"] * r.lot) * 100, 3)))
    A = pd.DataFrame(rows)
    old = pd.read_csv(RES / "S1_armab_minutes_trades.csv").rename(columns={"entry_date": "day0"})
    tab = []
    for setname in ("next strike up", "same strike, first candle 09:16-09:30"):
        for arm in ("A", "B"):
            for var in VARIANTS:
                g = A[(A["set"] == setname) & (A["arm"] == arm) & (A["variant"] == var)] if len(A) else A
                o = old[(old["arm"] == arm) & (old["variant"] == var)]
                tab.append({"set": setname, "arm": arm, "variant": var, **{f"added {k}": v for k, v in stats_of(g).items()},
                            "with the old trades: n": len(o) + len(g),
                            "with the old: mean %": round(pd.concat([o["net_pct"], g["net_pct"]]).mean(), 2) if len(g) else None,
                            "old alone: mean %": round(o["net_pct"].mean(), 2)})
    A.to_csv(RES / "S1_strike_choice_armab_trades.csv", index=False)
    return ["\n## Test 3 · arms A / B, the trades dropped for no 09:16 candle\n",
            f"{len(d)} dropped trades; next strike up fetched for {len(up)} stock-days.\n", md(pd.DataFrame(tab))]


if __name__ == "__main__":
    {"build": build, "run": run}[sys.argv[1]]()
