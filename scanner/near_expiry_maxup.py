"""Near-expiry option buying: max up by days to expiry, NIFTY and stock options (descriptive only, no rule chosen).

    INDEX_STORE=<index-data checkout>/data/index BHAV_DIR=<main checkout>/data/cache python -m scanner.near_expiry_maxup

The user, 2026-11-04: "let use built to trade on the near expiry ... the plan to capture the trade more than 100%".
Asked first: how often does a near-expiry option bought by a fixed rule reach +100 % or more, and what does holding it
do, split by sessions to expiry (k = 0 is the expiry day itself). Nothing here is a strategy; it shows where the
+100 % moves are and what they cost.

Part A · NIFTY, 1-minute options (Oct 2024 → latest), every weekly expiry E and every session D with k = 0..4 sessions to E:
  spot at D 09:20, ATM = spot rounded to 50; call and put 0..6 strikes out of the money (50-point steps).
  Buy at the 09:20 close + slippage (0.5 %, 1 % for 2+ strikes out, as scanner.s3_engine).
  max_up        highest minute high after 09:20 on D up to E 15:29, % over the fill (gross, the user's measure)
  max_up_day    the same, D only (an intraday trade)
  sold_day      D 15:15 close − slippage, % (an intraday exit, the plan the user showed on 2026-11-03)
  held          E 15:15 close − slippage, % (held to expiry day)
Part B · stock options, daily NSE bhavcopy closes (no highs are cached), every monthly expiry 2021-01 → 2026-08,
  every F&O stock, sessions k = 1..10 before E: ATM = strike nearest the day's underlying price, call and put 0..5
  strikes out. Entry = D close + 0.5 % (contracts that traded on D, close ≥ ₹0.05 only).
  max_close_up  highest close on a later session that traded (volume > 0) up to E, % over the entry; a LOWER bound
                of the true max up (intraday highs are not in the cache)
  held          intrinsic value at E's underlying close, % (what holding to expiry pays, before STT / delivery)
Old bhavcopies (before 2024-07-05) carry no UndrlygPric: the same-expiry stock future's close stands in.
Charges are not included (₹40-60 a lot round trip; large against a ₹2-10 option). Writes
data/results/near_expiry_maxup.md and near_expiry_{nifty,stocks}_trades.csv.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from index_data import load as L
from scanner.s3_engine import spot_at

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "data" / "results"
BHAV = Path(os.getenv("BHAV_DIR") or ROOT / "data" / "cache")
LEVELS = (50, 100, 200, 500)


# ---------------- Part A: NIFTY minutes ----------------
def nifty() -> pd.DataFrame:
    rows = []
    for ex in L.expiries("NIFTY"):
        if not (date(2024, 10, 1) <= ex <= date(2026, 10, 31)):
            continue
        days = [d for d in L.trade_days("NIFTY", ex) if d <= ex]
        frames = {d: L.options_day("NIFTY", ex, d) for d in days[-5:]}
        if ex not in frames or frames[ex].empty:
            continue
        last = frames[ex]
        for k, d in enumerate(reversed(days[-5:])):
            ch = frames[d]
            s = spot_at(d, 9, 20)
            if s is None or ch.empty:
                continue
            atm = round(s / 50) * 50
            later = pd.concat([frames[x] for x in days[-5:] if x >= d], ignore_index=True)
            t0 = L.at(d, 9, 20)
            for opt in ("CE", "PE"):
                for o in range(7):
                    kk = atm + 50 * o if opt == "CE" else atm - 50 * o
                    px = L.price_at(ch, kk, opt, t0, stale=3)
                    if px is None or px <= 0:
                        continue
                    slip = 0.005 if o < 2 else 0.01
                    fill = px * (1 + slip)
                    g = later[(later["strike"] == kk) & (later["option_type"] == opt) & (later["timestamp"] > t0)]
                    gd = g[g["timestamp"].dt.date == d]
                    if gd.empty:
                        continue
                    hi = g.loc[g["high"].idxmax()]
                    sd = L.price_at(ch, kk, opt, L.at(d, 15, 15), stale=30)
                    he = L.price_at(last, kk, opt, L.at(ex, 15, 15), stale=30)
                    rows.append({
                        "expiry": ex, "day": d, "k": k, "opt": opt, "otm": o, "strike": kk, "spot": s,
                        "entry": round(fill, 2), "max_up": (hi["high"] / fill - 1) * 100,
                        "max_up_day": (gd["high"].max() / fill - 1) * 100,
                        "peak_day": hi["timestamp"].date(), "peak_at": hi["timestamp"].strftime("%H:%M"),
                        "sold_day": None if sd is None else (sd * (1 - slip) / fill - 1) * 100,
                        "held": None if he is None else (he * (1 - slip) / fill - 1) * 100,
                    })
    return pd.DataFrame(rows)


# ---------------- Part B: stock options, daily closes ----------------
def _bhav(day: date) -> pd.DataFrame:
    p = BHAV / f"fo_bhavcopy_{day:%Y%m%d}.csv"
    d = pd.read_csv(p)
    return d[d["FinInstrmTp"].isin(["STO", "STF"])]


def stocks() -> pd.DataFrame:
    sess = sorted(date.fromisoformat(f"{p.stem[-8:-4]}-{p.stem[-4:-2]}-{p.stem[-2:]}")
                  for p in BHAV.glob("fo_bhavcopy_*.csv"))
    pos = {d: i for i, d in enumerate(sess)}
    cache: dict[date, pd.DataFrame] = {}

    def get(d):
        if d not in cache:
            cache[d] = _bhav(d)
        return cache[d]

    expiries = set()
    for d in sess[::5]:
        expiries |= set(get(d).query("FinInstrmTp == 'STO'")["XpryDt"].unique())
    rows = []
    for es in sorted(expiries):
        ex = date.fromisoformat(es)
        if ex not in pos or ex > date(2026, 8, 31) or ex < date(2021, 1, 1):
            continue
        i = pos[ex]
        window = sess[max(0, i - 10): i + 1]
        opts = {d: get(d)[(get(d)["FinInstrmTp"] == "STO") & (get(d)["XpryDt"] == es)] for d in window}
        futs = {d: get(d)[(get(d)["FinInstrmTp"] == "STF") & (get(d)["XpryDt"] == es)].set_index("TckrSymb")["ClsPric"]
                for d in window}

        def und(d, o):
            """Underlying per stock: UndrlygPric (UDiFF files), else the same-expiry future's close (old files)."""
            u = o.groupby("TckrSymb")["UndrlygPric"].median()
            return u.fillna(futs[d]).combine_first(futs[d])

        und_ex = und(ex, opts[ex])
        # later traded closes per contract, by session
        long = pd.concat([o.assign(day=d) for d, o in opts.items()], ignore_index=True)
        long = long[long["TtlTradgVol"] > 0]
        for d in window[:-1]:
            k = i - pos[d]
            o = opts[d]
            if o.empty:
                continue
            fut = long[long["day"] > d].groupby(["TckrSymb", "StrkPric", "OptnTp"])["ClsPric"].max()
            und_d = und(d, o)
            for sym, g in o.groupby("TckrSymb"):
                spot = und_d.get(sym)
                if spot is None or pd.isna(spot) or not spot or pd.isna(und_ex.get(sym)):
                    continue
                strikes = np.sort(g["StrkPric"].unique())
                atm_i = int(np.argmin(np.abs(strikes - spot)))
                for opt in ("CE", "PE"):
                    for off in range(6):
                        j = atm_i + off if opt == "CE" else atm_i - off
                        if not (0 <= j < len(strikes)):
                            continue
                        kk = strikes[j]
                        r = g[(g["StrkPric"] == kk) & (g["OptnTp"] == opt)]
                        if r.empty or r["TtlTradgVol"].iloc[0] <= 0 or r["ClsPric"].iloc[0] < 0.05:
                            continue
                        entry = float(r["ClsPric"].iloc[0]) * 1.005
                        mx = fut.get((sym, kk, opt))
                        ue = und_ex[sym]
                        intr = max(0.0, ue - kk) if opt == "CE" else max(0.0, kk - ue)
                        rows.append({
                            "expiry": ex, "day": d, "k": k, "symbol": sym, "opt": opt, "otm": off, "strike": kk,
                            "spot": spot, "entry": round(entry, 2), "lot": r["NewBrdLotQty"].iloc[0] if "NewBrdLotQty" in r else None,
                            "max_close_up": None if mx is None else (mx / entry - 1) * 100,
                            "held": (intr / entry - 1) * 100,
                        })
        for d in list(cache):
            if d < window[0]:
                del cache[d]
    return pd.DataFrame(rows)


def flag_changed(b: pd.DataFrame) -> pd.DataFrame:
    """Column `excluded`: "corp_action" (split, bonus, demerger, scheme or rights ex-date after the entry day, up to
    expiry, from data/cache/corp_actions.csv), "contract_changed" when the contract is not in the expiry-day bhavcopy (NSE adjusted the
    strikes for a split, bonus or demerger: TATASTEEL Jul 2022, HAL Sep 2023, RELIANCE Jul 2023 ...), or
    "price_jump" when the underlying moved more than 40 % between the entry day and expiry (an adjustment the strike
    check missed). Such rows stay in the CSV and are left out of every table."""
    b = b.copy()
    b["excluded"] = ""
    for ex, g in b.groupby("expiry"):
        e = _bhav(date.fromisoformat(str(ex)))
        e = e[(e["FinInstrmTp"] == "STO") & (e["XpryDt"] == str(ex))]
        have = set(zip(e["TckrSymb"], e["StrkPric"].astype(float), e["OptnTp"]))
        miss = np.array([(r.symbol, float(r.strike), r.opt) not in have for r in g.itertuples()])
        fut = e.groupby("TckrSymb")["UndrlygPric"].median()
        f = _bhav(date.fromisoformat(str(ex)))
        f = f[(f["FinInstrmTp"] == "STF") & (f["XpryDt"] == str(ex))].set_index("TckrSymb")["ClsPric"]
        und = fut.fillna(f).combine_first(f)
        ratio = g["symbol"].map(und) / g["spot"]
        jump = ((ratio > 1.4) | (ratio < 1 / 1.4)).to_numpy()
        b.loc[g.index[jump & ~miss], "excluded"] = "price_jump"
        b.loc[g.index[miss], "excluded"] = "contract_changed"
    ca = pd.read_csv(BHAV / "corp_actions.csv")
    ca = ca[ca["kind"].isin(["split", "bonus"]) | ca["subject"].str.contains("demerg|arrangement|amalgamation|rights|"
                                                                           "reduction", case=False, na=False)]
    for r in ca.itertuples():                                # ex-date after the entry day, up to expiry
        m = (b["symbol"] == r.symbol) & (b["day"].astype(str) < r.ex_date) & (b["expiry"].astype(str) >= r.ex_date) \
            & (b["excluded"] == "")
        b.loc[m, "excluded"] = "corp_action"
    return b


# ---------------- tables ----------------
def summary(df: pd.DataFrame, up: str, extra: list[str], by: list[str]) -> pd.DataFrame:
    out = []
    for key, g in df.groupby(by):
        u = g[up].dropna()
        row = dict(zip(by, key if isinstance(key, tuple) else (key,)))
        row.update({"trades": len(g), "paid_median": g["entry"].median(), f"{up}_mean": u.mean(),
                    f"{up}_median": u.median()})
        for lv in LEVELS:
            row[f"hit_{lv}"] = (u >= lv).mean() * 100
        for c in extra:
            v = g[c].dropna()
            row[f"{c}_mean"] = v.mean()
            row[f"{c}_median"] = v.median()
            row[f"{c}_won"] = (v > 0).mean() * 100
        out.append(row)
    return pd.DataFrame(out)


def md_table(t: pd.DataFrame) -> str:
    cols = list(t.columns)
    fmt = lambda v: f"{v:+.0f} %" if isinstance(v, float) and abs(v) < 1e6 else str(v)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in t.itertuples(index=False):
        lines.append("| " + " | ".join(fmt(v) if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(lines)


def main():
    RES.mkdir(parents=True, exist_ok=True)
    import sys
    if "--flag-only" in sys.argv:                       # re-flag the saved stock rows, no re-run
        a = pd.read_csv(RES / "near_expiry_nifty_trades.csv")
        b = flag_changed(pd.read_csv(RES / "near_expiry_stocks_trades.csv").drop(columns="excluded", errors="ignore"))
        b.to_csv(RES / "near_expiry_stocks_trades.csv", index=False)
        tb = summary(b[b["excluded"] == ""], "max_close_up", ["held"], ["opt", "k", "otm"])
        tb.to_csv(RES / "near_expiry_stocks_summary.csv", index=False)
        print(b["excluded"].value_counts())
        return
    if "--stocks-only" in sys.argv:
        a = pd.read_csv(RES / "near_expiry_nifty_trades.csv")
    else:
        a = nifty()
        a.to_csv(RES / "near_expiry_nifty_trades.csv", index=False)
    b = flag_changed(stocks())
    b.to_csv(RES / "near_expiry_stocks_trades.csv", index=False)
    ta = summary(a, "max_up", ["max_up_day", "sold_day", "held"], ["opt", "k", "otm"])
    tb = summary(b[b["excluded"] == ""], "max_close_up", ["held"], ["opt", "k", "otm"])
    ta.to_csv(RES / "near_expiry_nifty_summary.csv", index=False)
    tb.to_csv(RES / "near_expiry_stocks_summary.csv", index=False)
    print(len(a), len(b))


if __name__ == "__main__":
    main()
