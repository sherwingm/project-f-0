"""Unified index trade dataset (index_context_research/PREREG_CONTEXT.md). One row per trade per trade set, with only information known before entry.
Output: results/context_dataset.csv. Read-only on every input; nothing existing is modified."""
import math
import os
import sys
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(REPO, "index_research", "scripts"))
sys.path.insert(0, REPO)
from lib import L, minutes  # noqa: E402  (cached 1-minute spot frames)
from scanner.s3_b2 import signal  # noqa: E402
from scanner.s3_buy4 import BUDGET, FOMC_US, RBI, expiry_after  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
GIFT = os.path.join(ROOT, "data", "gift")
R_RATE = 0.065


def bs_price(S, K, T, sig, cp):
    if T <= 0 or sig <= 0:
        return max(0.0, (S - K) if cp == "CE" else (K - S))
    d1 = (math.log(S / K) + (R_RATE + 0.5 * sig * sig) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    N = lambda x: 0.5 * math.erfc(-x / math.sqrt(2))  # noqa: E731
    if cp == "CE":
        return S * N(d1) - K * math.exp(-R_RATE * T) * N(d2)
    return K * math.exp(-R_RATE * T) * N(-d2) - S * N(-d1)


def iv(price, S, K, T, cp):
    intrinsic = max(0.0, (S - K) if cp == "CE" else (K - S)) * math.exp(-R_RATE * T)
    if not price or price != price or price <= intrinsic + 0.05 or T <= 0:
        return np.nan
    lo, hi = 0.01, 4.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if bs_price(S, K, T, mid, cp) > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def load_trades():
    g1 = pd.read_csv(os.path.join(REPO, "g1_research", "results", "g1_live_replay_trades.csv"), parse_dates=["day"])
    g1["day"] = g1["day"].dt.date
    a = g1.assign(tset="G1", side="PE", maxup=g1["max_up_pct_next_close"])[["tset", "day", "side", "dte", "net_pct", "net_rs", "net_pct_2x", "maxup", "g1f"]]
    f = a[a["g1f"] == 1].assign(tset="G1F")
    c = pd.read_csv(os.path.join(REPO, "g1_research", "data", "g1c_opt_trades.csv"), parse_dates=["day"])
    c["day"] = c["day"].dt.date
    cc = c[c["B_1_net"].notna()].assign(tset="G1C", side="CE", net_pct=c["B_1_net"], net_rs=c["B_1_rs"], net_pct_2x=c["B_2_net"], maxup=c["B_peak"], g1f=np.nan)[
        ["tset", "day", "side", "dte", "net_pct", "net_rs", "net_pct_2x", "maxup", "g1f"]]
    x = pd.read_csv(os.path.join(REPO, "g1_research", "data", "xp_history_minute.csv"), parse_dates=["day"])
    x["day"] = x["day"].dt.date
    xx = x[x["hold_pct"].notna()].assign(tset="XP", side="STRADDLE", dte=0, net_pct=x["hold_pct"], net_rs=x["hold_rs"], net_pct_2x=x["hold_2x_pct"], maxup=x["maxup"], g1f=np.nan)[
        ["tset", "day", "side", "dte", "net_pct", "net_rs", "net_pct_2x", "maxup", "g1f"]]
    return pd.concat([a, f, cc, xx], ignore_index=True)


def gift_frame():
    d = pd.read_csv(os.path.join(GIFT, "gift_dsp_futures.csv"), header=None, names=["date", "type", "sym", "expiry", "strike", "opt", "settle"], on_bad_lines="skip")
    d = d[d["date"] != "DATE"]
    d["date"] = pd.to_datetime(d["date"], format="%d-%b-%Y").dt.date
    d["expiry"] = pd.to_datetime(d["expiry"], format="%d-%b-%Y").dt.date
    d["settle"] = d["settle"].astype(float)
    n = d[(d["sym"] == "NIFTY") & (d["expiry"] >= d["date"])].sort_values(["date", "expiry"])
    near = n.groupby("date").first()
    return near, n


def fut_frame():
    b = pd.read_parquet(os.path.join(REPO, "index_research", "data", "bhav_NIFTY.parquet"))
    f = b[(b["FinInstrmTp"] == "IDF") & (b["XpryDt"] > b["TradDt"])]
    return f


def fii_frame():
    folder = os.path.join(REPO, "g1_research", "data", "external", "participant_oi")
    out = {}
    for fn in os.listdir(folder):
        try:
            t = pd.read_csv(os.path.join(folder, fn), skiprows=1)
            t.columns = [str(c).strip() for c in t.columns]
            r = t[t["Client Type"].astype(str).str.strip().str.upper() == "FII"].iloc[0]
            lg, sh = float(r["Future Index Long"]), float(r["Future Index Short"])
            out[date.fromisoformat(fn[:-4])] = lg / (lg + sh)
        except Exception:
            pass
    return pd.Series(out).sort_index()


def breadth_series():
    uni = open(os.path.join(REPO, "data", "fo_universe.txt")).read().split()
    ups = {}
    for s in uni:
        p = os.path.join(REPO, "data", "eod2", f"{s.lower()}.csv")
        if not os.path.exists(p):
            continue
        try:
            d = pd.read_csv(p, usecols=["Date", "Close"], parse_dates=["Date"])
        except Exception:
            continue
        d = d[d["Date"] >= "2023-01-01"].set_index("Date")["Close"]
        ups[s] = (d.diff() > 0).astype(float).where(d.diff().notna())
    U = pd.DataFrame(ups)
    return U.mean(axis=1) * 100, U.notna().sum(axis=1)


def main():
    T = load_trades()
    spot = minutes("NIFTY50")
    vixm = minutes("INDIAVIX")
    ses = sorted(spot)
    pos = {d: i for i, d in enumerate(ses)}
    dclose = pd.Series({d: float(spot[d]["close"].iloc[-1]) for d in ses})
    vclose = pd.Series({d: float(vixm[d]["close"].iloc[-1]) for d in vixm})
    sma20 = dclose.rolling(20).mean()
    near, gall = gift_frame()
    futs = fut_frame()
    fii = fii_frame()
    breadth, bcount = breadth_series()
    sp = pd.read_csv(os.path.join(REPO, "data", "parents", "yf_GSPC.csv"), parse_dates=["Date"]).set_index("Date")["Close"]
    sp_ret = sp.pct_change()
    expset = set(L.expiries("NIFTY"))
    events = set(RBI) | set(BUDGET) | set(FOMC_US)
    rows = []
    for _, t in T.iterrows():
        d = t["day"]
        if d not in pos or pos[d] < 6:
            continue
        i = pos[d]
        prev, prev2 = ses[i - 1], ses[i - 2]
        g = spot[d]
        r = {**t.to_dict()}
        # entry minute
        if t["tset"] == "XP":
            ent = pd.Timestamp(datetime.combine(d, datetime.min.time()), tz=g["timestamp"].iloc[0].tz) + pd.Timedelta(hours=9, minutes=16)
            exp = d
            sig_ts = ent - pd.Timedelta(minutes=1)
        else:
            sg = signal(g, 15, None)
            if sg is None or sg[0] != t["side"]:
                r["note"] = "signal mismatch"
                rows.append(r)
                continue
            sig_ts = sg[1]
            ent = sig_ts + pd.Timedelta(minutes=1)
            exp = expiry_after(d)
        r["entry"] = ent.strftime("%H:%M")
        r["expiry"] = exp
        r["gap_pct"] = (float(g["open"].iloc[0]) / dclose[prev] - 1) * 100
        v = vixm[d]
        vv = v[v["timestamp"] <= sig_ts]
        r["vix_signal"] = float(vv["close"].iloc[-1]) if len(vv) else np.nan
        r["vix_chg5"] = (vclose.get(prev, np.nan) / vclose.get(ses[i - 6], np.nan) - 1) * 100
        hist = [vclose.get(s_) for s_ in ses[max(0, i - 251):i - 1]]
        hist = [h for h in hist if h == h]
        r["vix_pct1y"] = (np.mean([h < vclose.get(prev) for h in hist]) * 100) if len(hist) > 100 and vclose.get(prev) == vclose.get(prev) else np.nan
        # GIFT (settlement of the previous Indian session; proxy only)
        if prev in near.index and prev2 in near.index:
            e1 = near.loc[prev, "expiry"]
            s1 = near.loc[prev, "settle"]
            s2 = gall[(gall["date"] == prev2) & (gall["expiry"] == e1)]["settle"]
            r["gift_basis"] = (s1 / dclose[prev] - 1) * 100
            r["gift_ret_prev"] = (s1 / float(s2.iloc[0]) - 1) * 100 if len(s2) else np.nan
        # S&P 500: last US session strictly before the trade date
        us = sp_ret[sp_ret.index < pd.Timestamp(d)].dropna()
        r["us_prev_ret"] = float(us.iloc[-1]) * 100 if len(us) and (pd.Timestamp(d) - us.index[-1]).days <= 5 and pd.Timestamp(d) <= sp.index[-1] + pd.Timedelta(days=4) else np.nan
        # index futures price / OI (previous session vs the one before, same expiry)
        f1 = futs[futs["TradDt"] == prev].sort_values("XpryDt")
        if len(f1):
            ex = f1.iloc[0]["XpryDt"]
            f0 = futs[(futs["TradDt"] == prev2) & (futs["XpryDt"] == ex)]
            if len(f0) and float(f0.iloc[0]["OpnIntrst"]) > 0:
                r["fut_oi_chg"] = (float(f1.iloc[0]["OpnIntrst"]) / float(f0.iloc[0]["OpnIntrst"]) - 1) * 100
                r["fut_px_chg"] = (float(f1.iloc[0]["ClsPric"]) / float(f0.iloc[0]["ClsPric"]) - 1) * 100
        if prev in fii.index and prev2 in fii.index:
            r["fii_fut_longshare"] = fii[prev] * 100
            r["fii_fut_chg"] = (fii[prev] - fii[prev2]) * 100
        # breadth proxy (survivorship biased)
        pt = pd.Timestamp(prev)
        if pt in breadth.index and bcount.get(pt, 0) > 100:
            r["breadth_prev"] = float(breadth[pt])
        r["event_window"] = int(d in events or ses[i + 1] in events if i + 1 < len(ses) else d in events)
        r["expiry_day"] = int(d in expset)
        r["weekday"] = d.weekday()
        r["trend_prev"] = int(dclose[prev] > sma20[prev])
        # option chain at the entry minute
        try:
            ch = L.options_day("NIFTY", exp, d)
            ch = ch[ch["timestamp"] <= ent]
            ch = ch[ch["timestamp"] >= ent - pd.Timedelta(minutes=10)]
            if len(ch):
                last = ch.sort_values("timestamp").groupby(["strike", "option_type"]).last().reset_index()
                S = float(g.loc[g["timestamp"] <= sig_ts, "close"].iloc[-1])
                atm = round(S / 50) * 50
                close_t = pd.Timestamp(datetime.combine(exp, datetime.min.time()), tz=ent.tz) + pd.Timedelta(hours=15, minutes=30)
                T = max((close_t - ent).total_seconds() / (365 * 24 * 3600), 1e-6)
                px = lambda k, c_: (lambda x: float(x["close"].iloc[0]) if len(x) else np.nan)(last[(last["strike"] == k) & (last["option_type"] == c_)])  # noqa: E731
                ivc, ivp = iv(px(atm, "CE"), S, atm, T, "CE"), iv(px(atm, "PE"), S, atm, T, "PE")
                r["atm_iv"] = np.nanmean([ivc, ivp]) * 100 if not (np.isnan(ivc) and np.isnan(ivp)) else np.nan
                r["iv_skew"] = (iv(px(atm - 100, "PE"), S, atm - 100, T, "PE") - iv(px(atm + 100, "CE"), S, atm + 100, T, "CE")) * 100
                w = last[(last["strike"] >= atm - 500) & (last["strike"] <= atm + 500) & last["oi"].notna()]
                co, po = w[w["option_type"] == "CE"]["oi"].sum(), w[w["option_type"] == "PE"]["oi"].sum()
                r["pcr_oi"] = po / co if co > 0 else np.nan
        except Exception as e:  # keep missing, never zero
            r["note"] = f"chain error {type(e).__name__}"
        rows.append(r)
    D = pd.DataFrame(rows)
    D["year"] = [d.year for d in D["day"]]
    D["quarter"] = [f"{d.year}Q{(d.month - 1) // 3 + 1}" for d in D["day"]]
    D["half"] = np.where(D["day"] <= date(2025, 9, 30), "D", "V")
    D.to_csv(os.path.join(ROOT, "results", "context_dataset.csv"), index=False)
    print(D.groupby("tset").size().to_dict())
    feats = ["gap_pct", "vix_signal", "vix_chg5", "vix_pct1y", "gift_basis", "gift_ret_prev", "us_prev_ret", "fut_oi_chg", "fut_px_chg", "fii_fut_longshare", "fii_fut_chg",
             "atm_iv", "pcr_oi", "iv_skew", "breadth_prev", "event_window", "expiry_day"]
    print("missing share by tset:")
    print(D.groupby("tset")[feats].agg(lambda s: round(s.isna().mean(), 2)).T.to_string())
    print("signal mismatches:", int(D["note"].eq("signal mismatch").sum()) if "note" in D else 0)


if __name__ == "__main__":
    main()
