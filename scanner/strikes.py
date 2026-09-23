"""Strike-level option data per stock, nearest expiry, from the same F&O bhavcopy.

Per stock:
    expiry                 nearest option expiry on/after the trade date
    strikes[]              ATM ± N strikes: strike, CE/PE open interest, change in OI, volume, close premium
    max_call_oi_strike     strike with the largest call OI  (commonly read as a resistance zone)
    max_put_oi_strike      strike with the largest put OI   (commonly read as a support zone)
    max_pain               strike where option buyers' total intrinsic value is smallest
    atm                    strike closest to the underlying close

These are descriptive levels computed from positioning data; nothing here says what to trade.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STRIKES_EACH_SIDE = 8


def option_chains(bhav: pd.DataFrame, closes: dict[str, float],
                  each_side: int = STRIKES_EACH_SIDE) -> tuple[dict[str, dict], dict[str, str]]:
    """Return (chains, problems). A stock whose chain cannot be built lands in `problems` with the
    reason; it never stops the other stocks. Strikes listed on one side only (a call with no put,
    or the reverse) are kept with 0 OI/volume and a null price on the missing side."""
    sto = bhav[bhav["FinInstrmTp"] == "STO"].copy()
    if sto.empty:
        return {}, {}
    sto["XpryDt"] = pd.to_datetime(sto["XpryDt"], errors="coerce")
    trade_date = pd.to_datetime(bhav["TradDt"].iloc[0])
    out: dict[str, dict] = {}
    problems: dict[str, str] = {}
    for sym, g in sto.groupby("TckrSymb"):
        try:
            built = _chain_for_symbol(sym, g, closes.get(sym), trade_date, each_side)
            if built is None:
                problems[sym] = "no options on or after the trade date" if closes.get(sym) is not None else "no equity close for this session"
            else:
                out[sym] = built
        except Exception as exc:  # noqa: BLE001 - one broken chain must not cost the whole day's build
            problems[sym] = f"{type(exc).__name__}: {exc}"
    return out, problems


def _chain_for_symbol(sym: str, g: pd.DataFrame, spot: float | None, trade_date, each_side: int) -> dict | None:
    if spot is None:
        return None
    future_exp = g.loc[g["XpryDt"] >= trade_date, "XpryDt"]
    if future_exp.empty:
        return None
    expiry = future_exp.min()
    e = g[g["XpryDt"] == expiry]
    if True:
        chain = e.pivot_table(index="StrkPric", columns="OptnTp",
                              values=["OpnIntrst", "ChngInOpnIntrst", "TtlTradgVol", "ClsPric"],
                              aggfunc="sum").sort_index()
        strikes = chain.index.to_numpy(dtype=float)
        if len(strikes) == 0:
            return None

        def col(metric, side, fill):
            # a strike listed on one side only shows up as NaN on the other: OI/volume/change are
            # 0 there, the price is unknown (kept NaN, rendered as null)
            if (metric, side) not in chain:
                return np.full(len(strikes), fill, dtype=float)
            arr = chain[(metric, side)].to_numpy(dtype=float)
            return arr if fill is None else np.nan_to_num(arr, nan=fill)

        ce_oi, pe_oi = col("OpnIntrst", "CE", 0.0), col("OpnIntrst", "PE", 0.0)
        ce_chg, pe_chg = col("ChngInOpnIntrst", "CE", 0.0), col("ChngInOpnIntrst", "PE", 0.0)
        ce_vol, pe_vol = col("TtlTradgVol", "CE", 0.0), col("TtlTradgVol", "PE", 0.0)
        ce_px, pe_px = col("ClsPric", "CE", None), col("ClsPric", "PE", None)

        # max pain over the whole chain: total intrinsic value owed to option holders if the
        # underlying settled at each strike S = Σ CE_OI(K)·max(S−K,0) + Σ PE_OI(K)·max(K−S,0)
        S = strikes[:, None]; K = strikes[None, :]
        pain = (ce_oi[None, :] * np.clip(S - K, 0, None)).sum(axis=1) + (pe_oi[None, :] * np.clip(K - S, 0, None)).sum(axis=1)
        max_pain = float(strikes[int(pain.argmin())])
        atm_i = int(np.abs(strikes - spot).argmin())
        lo, hi = max(0, atm_i - each_side), min(len(strikes), atm_i + each_side + 1)

        rows = []
        for i in range(lo, hi):
            rows.append({"strike": float(strikes[i]),
                         "ce_oi": int(ce_oi[i]), "ce_oi_chg": int(ce_chg[i]), "ce_vol": int(ce_vol[i]), "ce_close": _px(ce_px[i]),
                         "pe_oi": int(pe_oi[i]), "pe_oi_chg": int(pe_chg[i]), "pe_vol": int(pe_vol[i]), "pe_close": _px(pe_px[i])})
        one_sided = int(np.sum(np.isnan(ce_px) | np.isnan(pe_px)))
        return {
            "expiry": expiry.strftime("%Y-%m-%d"),
            "atm": float(strikes[atm_i]),
            "max_call_oi_strike": float(strikes[int(ce_oi.argmax())]) if ce_oi.max() > 0 else None,
            "max_put_oi_strike": float(strikes[int(pe_oi.argmax())]) if pe_oi.max() > 0 else None,
            "max_pain": max_pain,
            "total_ce_oi": int(ce_oi.sum()), "total_pe_oi": int(pe_oi.sum()),
            "one_sided_strikes": one_sided,
            "strikes": rows,
        }


def _px(v: float):
    return None if v is None or np.isnan(v) else round(float(v), 2)
