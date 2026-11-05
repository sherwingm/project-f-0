"""Tradeability helpers: option-minute loading (with the known dedupe), spot open, lot size, charges, one straddle.

Design: reports/lld/tradeability.md. Read-only on the data store. Charges re-implement the formula of
server/charges.py (rates effective 2026-04-01); that module is not imported.
"""
import functools
import os

import numpy as np
import pandas as pd

STORE = os.environ.get("INDEX_STORE", "../fo-index-data/data/index")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# charges.py rates (options)
OPT_BROKERAGE = 20.0
OPT_STT_SELL_PCT = 0.15
OPT_NSE_PER_LAKH = 35.53
SEBI_PER_CRORE = 10.0
OPT_STAMP_BUY_PCT = 0.003
GST_PCT = 18.0


def leg_charges(side, qty, px):
    """Charges on one option order (charges.py `leg` formula, each component rounded to the paisa)."""
    value = qty * px
    brokerage = OPT_BROKERAGE
    stt = OPT_STT_SELL_PCT / 100 * value if side == "SELL" else 0.0
    exchange = OPT_NSE_PER_LAKH * value / 1e5
    sebi = SEBI_PER_CRORE * value / 1e7
    stamp = OPT_STAMP_BUY_PCT / 100 * value if side == "BUY" else 0.0
    gst = GST_PCT / 100 * (brokerage + exchange + sebi)
    return round(sum(round(v, 2) for v in (brokerage, stt, exchange, sebi, stamp, gst)), 2)


def _check_charges():
    # hand example: buy 75 x 100 = Rs 7,500 premium: brokerage 20, exchange 2.66475, sebi 0.0075, stamp 0.225,
    # gst 18 % of (20 + 2.66475 + 0.0075); each rounded with Python round(), as charges.py does
    got = leg_charges("BUY", 75, 100.0)
    exp = round(20.0 + round(2.66475, 2) + round(0.0075, 2) + round(0.225, 2) + round(0.18 * 22.67225, 2), 2)
    assert abs(got - exp) < 1e-9, (got, exp)


_check_charges()


@functools.lru_cache(maxsize=4096)
def opt_day(expiry, day):
    """Option minutes of one (expiry, day); None if the file is absent. Keeps upstox over kotak on duplicates."""
    p = os.path.join(STORE, "options_1m", "NIFTY", expiry, f"{day}.parquet")
    if not os.path.exists(p):
        return None
    d = pd.read_parquet(p, columns=["timestamp", "token", "strike", "option_type", "close", "source"])
    n0 = len(d)
    if d.duplicated(["timestamp", "token"]).any():
        d["_pri"] = (d["source"] != "upstox").astype(int)
        d = d.sort_values(["timestamp", "token", "_pri"]).drop_duplicates(["timestamp", "token"], keep="first")
        d = d.drop(columns="_pri")
    assert not d.duplicated(["timestamp", "token"]).any()
    assert not d.duplicated(["timestamp", "strike", "option_type"]).any(), (expiry, day)
    d = d[d["close"] > 0]
    d["hm"] = d["timestamp"].dt.strftime("%H:%M")
    d.attrs["dups_dropped"] = n0 - len(d)
    return d


def leg_series(d, strike, typ):
    """Close by HH:MM for one leg (empty Series if none)."""
    x = d[(d["strike"] == strike) & (d["option_type"] == typ)]
    return x.set_index("hm")["close"]


@functools.lru_cache(maxsize=64)
def _spot_month(ym):
    p = os.path.join(STORE, "spot_1m", "NIFTY50", f"{ym}.parquet")
    if not os.path.exists(p):
        return None
    s = pd.read_parquet(p, columns=["timestamp", "open"])
    s["day"] = s["timestamp"].dt.strftime("%Y-%m-%d")
    s["hm"] = s["timestamp"].dt.strftime("%H:%M")
    return s


def spot_open_0915(day):
    s = _spot_month(day[:7])
    if s is None:
        return np.nan
    x = s[(s["day"] == day) & (s["hm"] == "09:15")]
    return float(x["open"].iloc[0]) if len(x) else np.nan


@functools.lru_cache(maxsize=64)
def _bhav_month(ym):
    p = os.path.join(STORE, "options_daily", "NIFTY", f"{ym}.parquet")
    b = pd.read_parquet(p, columns=["TradDt", "XpryDt", "FinInstrmTp", "NewBrdLotQty"])
    b = b[b["FinInstrmTp"] == "IDO"]
    b["TradDt"] = b["TradDt"].astype(str).str[:10]
    b["XpryDt"] = b["XpryDt"].astype(str).str[:10]
    return b.groupby(["TradDt", "XpryDt"])["NewBrdLotQty"].agg(lambda v: sorted(set(v.dropna().astype(int))))


def lot_size(day, expiry):
    try:
        g = _bhav_month(day[:7])
    except FileNotFoundError:
        return np.nan
    v = g.get((day, expiry))
    if v is None or len(v) != 1:
        return np.nan
    return int(v[0])


def slip_pct(hm, s):
    """Plan slippage per leg: s normally, 2s before 09:30 or from 15:00."""
    return 2 * s if (hm < "09:30" or hm >= "15:00") else s


def net_pct(ce_in, pe_in, ce_out, pe_out, hm_in, hm_out, s, lot):
    si, so = slip_pct(hm_in, s) / 100, slip_pct(hm_out, s) / 100
    b_ce, b_pe = ce_in * (1 + si), pe_in * (1 + si)
    s_ce, s_pe = ce_out * (1 - so), pe_out * (1 - so)
    cost = lot * (b_ce + b_pe)
    proceeds = lot * (s_ce + s_pe)
    ch = (leg_charges("BUY", lot, b_ce) + leg_charges("BUY", lot, b_pe)
          + leg_charges("SELL", lot, s_ce) + leg_charges("SELL", lot, s_pe))
    return (proceeds - cost - ch) / cost * 100, ch


def drawdown(x):
    """Largest peak-to-trough of the cumulative sum (starting at 0), as a positive number."""
    c = np.concatenate([[0.0], np.cumsum(np.asarray(x, float))])
    return float(np.max(np.maximum.accumulate(c) - c))
