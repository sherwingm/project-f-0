"""Option-chain / OI feature table for module optionchain (design: reports/lld/optionchain.md).

Reads panels via panel_io.load_panel and raw bhavcopy files 2018-01..2024-06 (rows TradDt <= 2024-06-30).
Writes results/optionchain/features_<UL>.parquet and bhavcopy_quality.csv.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from panel_io import load_panel  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "results" / "optionchain"
OUT.mkdir(parents=True, exist_ok=True)
STORE = Path(os.environ.get("INDEX_STORE", ROOT.parent.parent / "fo-index-data" / "data" / "index"))
CUTOFF = pd.Timestamp("2024-06-30")
GRID = {"NIFTY": 50, "BANKNIFTY": 100}


def load_raw(ul):
    files = sorted((STORE / "options_daily" / ul).glob("*.parquet"))
    files = [f for f in files if f.stem <= "2024-06"]
    cols = ["TradDt", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp", "ClsPric", "SttlmPric", "UndrlygPric",
            "OpnIntrst", "ChngInOpnIntrst", "TtlTradgVol"]
    R = pd.concat([pd.read_parquet(f, columns=cols) for f in files], ignore_index=True)
    R["TradDt"] = pd.to_datetime(R["TradDt"])
    R["XpryDt"] = pd.to_datetime(R["XpryDt"])
    R = R[R["TradDt"] <= CUTOFF]
    assert R["TradDt"].max() <= CUTOFF
    return R[R["FinInstrmTp"] == "IDO"].copy()


def quality(ul, R, P):
    R = R.copy()
    R["year"] = R["TradDt"].dt.year
    q = R.groupby("year").agg(rows=("SttlmPric", "size"),
                              settle_le0=("SttlmPric", lambda s: (s <= 0).mean()),
                              untraded=("TtlTradgVol", lambda s: (s == 0).mean()),
                              undrlyg_empty=("UndrlygPric", lambda s: s.isna().mean()))
    # strike sparsity near expiry, +-5 % of close
    px = P.set_index("date")["px_close"]
    ne = P.set_index("date")["f_opt_near_expiry"]
    sub = R[R["TradDt"].isin(px.index)].copy()
    sub["near"] = sub["TradDt"].map(ne)
    sub = sub[sub["XpryDt"] == sub["near"]]
    sub["S"] = sub["TradDt"].map(px)
    sub = sub[(sub["StrkPric"] / sub["S"] - 1).abs() <= 0.05]
    g = sub.groupby(["TradDt", "StrkPric"])["OpnIntrst"].sum().reset_index()
    g = g[g["OpnIntrst"] > 0].groupby("TradDt").size()
    full = (2 * 0.05 * px / GRID[ul]).reindex(g.index)
    cov = (g / full).rename("cov").to_frame()
    cov["year"] = cov.index.year
    q["near_strikes_oi_pm5"] = g.groupby(g.index.year).median()
    q["grid_coverage_pm5"] = cov.groupby("year")["cov"].median()
    q.insert(0, "underlying", ul)
    return q.reset_index()


def raw_features(ul, R, P):
    """ATM-zone PCR / flow (near expiry, +-2 %) and D0 settlement of the ATM straddle for each row."""
    Pi = P.set_index("date")
    out = pd.DataFrame(index=Pi.index)
    px = Pi["px_close"]
    ne = Pi["f_opt_near_expiry"]
    sub = R[R["TradDt"].isin(Pi.index)].copy()
    sub["near"] = sub["TradDt"].map(ne)
    sub = sub[sub["XpryDt"] == sub["near"]]
    sub["S"] = sub["TradDt"].map(px)
    z = sub[(sub["StrkPric"] / sub["S"] - 1).abs() <= 0.02]
    piv = z.pivot_table(index="TradDt", columns="OptnTp", values=["OpnIntrst", "ChngInOpnIntrst"], aggfunc="sum")
    nside = z.assign(side=np.sign(z["StrkPric"] - z["S"])).groupby(["TradDt", "side"])["StrkPric"].nunique().unstack()
    ok = (nside.get(-1.0, 0) >= 3) & (nside.get(1.0, 0) >= 3)
    ce, pe = piv[("OpnIntrst", "CE")], piv[("OpnIntrst", "PE")]
    cec, pec = piv[("ChngInOpnIntrst", "CE")], piv[("ChngInOpnIntrst", "PE")]
    atmz_pcr = (pe / ce).where(ok.reindex(piv.index, fill_value=False))
    atmz_flow = ((pec - cec) / (ce + pe)).where(ok.reindex(piv.index, fill_value=False))
    out["atmz_pcr"] = atmz_pcr.reindex(out.index)
    out["atmz_flow"] = atmz_flow.reindex(out.index)
    # final settlement on expiry day E: in this bhavcopy the expiring options' SttlmPric on E is the final settlement
    # value of the index (same number on every strike); it is 0 on 2018-19 expiries -> fallback official close of E
    exp_rows = R[(R["TradDt"] == R["XpryDt"]) & (R["SttlmPric"] > 0)]
    sidx = exp_rows.groupby("XpryDt")["SttlmPric"].median()
    K = Pi["f_opt_near_atm_strike"]
    out["settle_index_near"] = ne.map(sidx).values
    out["atm_strike"] = K
    out["near_expiry"] = ne
    return out.reset_index()


def build(ul):
    P = load_panel(ul).copy()
    P["date"] = pd.to_datetime(P["date"])
    P["f_opt_near_expiry"] = pd.to_datetime(P["f_opt_near_expiry"])
    R = load_raw(ul)
    q = quality(ul, R, P)
    rf = raw_features(ul, R, P)
    F = P.merge(rf[["date", "atmz_pcr", "atmz_flow", "settle_index_near"]], on="date", how="left")
    F = F.sort_values("date").reset_index(drop=True)
    same = F["f_opt_near_expiry"].eq(F["f_opt_near_expiry"].shift(1))
    # sessions (weekdays) from t+1 to near expiry inclusive
    d1 = F["date"].values.astype("datetime64[D]") + np.timedelta64(1, "D")
    e1 = F["f_opt_near_expiry"].values.astype("datetime64[D]") + np.timedelta64(1, "D")
    okd = ~pd.isna(F["f_opt_near_expiry"])
    ns = np.full(len(F), np.nan)
    ns[okd.values] = np.busday_count(d1[okd.values], e1[okd.values])
    F["n_sess"] = ns
    S = F["px_close"]
    K = F["f_opt_near_atm_strike"]
    tv = F["f_opt_near_straddle_pct"] - (K / S - 1).abs() * 100
    F["iv_proxy"] = tv / 0.7979 / np.sqrt(F["n_sess"].clip(lower=1)) * np.sqrt(252)
    F["pcr_oi_chg"] = (F["f_opt_near_pcr_oi"] - F["f_opt_near_pcr_oi"].shift(1)).where(same)
    F["iv_chg"] = (F["iv_proxy"] - F["iv_proxy"].shift(1)).where(same)
    F["net_oi_flow"] = (F["f_opt_near_pe_oi_chg"] - F["f_opt_near_ce_oi_chg"]) / (
        F["f_opt_near_ce_oi"] + F["f_opt_near_pe_oi"])
    F["wall_skew"] = F["f_opt_near_callwall_dist_pct"] + F["f_opt_near_putwall_dist_pct"]
    F["wall_width"] = F["f_opt_near_callwall_dist_pct"] - F["f_opt_near_putwall_dist_pct"]
    F["wall_near"] = np.minimum(F["f_opt_near_callwall_dist_pct"], -F["f_opt_near_putwall_dist_pct"])
    F["basis_ann"] = F["f_fut_basis_pct"] * 365 / F["f_fut_dte"]
    F["iv_hv"] = F["iv_proxy"] - F["f_hv10"]
    F["fut_oi_abs"] = F["f_futall_oi_chg"].abs() / F["f_futall_oi"]
    F["mp_abs"] = F["f_opt_near_maxpain_dist_pct"].abs()
    vol = F["f_opt_near_ce_vol"] + F["f_opt_near_pe_vol"]
    F["opt_vol"] = vol
    med = vol.groupby(F["n_sess"]).transform(lambda s: s.shift(1).rolling(5, min_periods=3).median())
    F["vol_surge"] = vol / med
    up = np.sign(F["f_mom1"])
    oi = np.sign(F["f_futall_oi_chg"])
    fb = pd.Series(np.nan, index=F.index, dtype=object)
    fb[(up > 0) & (oi > 0)] = "LB"
    fb[(up < 0) & (oi > 0)] = "SB"
    fb[(up > 0) & (oi < 0)] = "SC"
    fb[(up < 0) & (oi < 0)] = "LU"
    F["fut_build"] = fb
    fl = np.sign(F["f_opt_near_pe_oi_chg"] - F["f_opt_near_ce_oi_chg"])
    ob = pd.Series(np.nan, index=F.index, dtype=object)
    ob[(up > 0) & (fl > 0)] = "UP_PW"
    ob[(up > 0) & (fl < 0)] = "UP_CW"
    ob[(up < 0) & (fl > 0)] = "DN_PW"
    ob[(up < 0) & (fl < 0)] = "DN_CW"
    F["opt_build"] = ob
    F["mon_pcr_oi"] = F["f_opt_mon_pcr_oi"]
    F["pcr_oi"] = F["f_opt_near_pcr_oi"]
    F["pcr_vol"] = F["f_opt_near_pcr_vol"]
    F["maxpain_dist"] = F["f_opt_near_maxpain_dist_pct"]
    F["iv"] = F["iv_proxy"]
    F["strad_chg"] = F["f_opt_near_straddle_chg1"]
    F["top3"] = F["f_opt_near_top3_oi_share"]
    # next-row (t+1) values, for D2 targets (labels of t+2) and settlement close of t+1
    nxt = F.shift(-1)
    for c in ["y_gap_pct", "y_oc", "y_ret30", "y_cc", "y_range_pct", "y_max_exc", "y_big_move_exc", "y_gap_filled",
              "y_date"]:
        F["n_" + c] = nxt[c]
    F["close_official"] = F["px_close_official"].fillna(F["px_close"])
    F["close_official_t1"] = F["close_official"].shift(-1)  # session t+1 close (label only)
    F["close_official_t2"] = F["close_official"].shift(-2)  # session t+2 close (label only)
    F["t1_date"] = F["date"].shift(-1)
    F["t2_date"] = F["date"].shift(-2)
    # labels for the last open rows must not come from beyond the open period (they are NaN in the panel anyway)
    for c in ["close_official_t1", "close_official_t2"]:
        F.loc[F["y_date"].isna() | (pd.to_datetime(F["y_date"]) > CUTOFF), c] = np.nan
    F.loc[F["t2_date"].isna() | (F["t2_date"] > CUTOFF), "close_official_t2"] = np.nan
    F["underlying"] = ul
    return F, q


def main():
    qs = []
    for ul in ["NIFTY", "BANKNIFTY"]:
        F, q = build(ul)
        F.to_parquet(OUT / f"features_{ul}.parquet", index=False)
        qs.append(q)
        print(ul, F.shape, "dates", F["date"].min().date(), F["date"].max().date())
        print("  near expiry == cal_next_date on eve rows:",
              (F.loc[F["cal_next_is_expiry"] == True, "f_opt_near_expiry"]  # noqa: E712
               == pd.to_datetime(F.loc[F["cal_next_is_expiry"] == True, "cal_next_date"])).mean().round(4))  # noqa
        for c in ["atmz_pcr", "atmz_flow", "iv_proxy", "vol_surge", "settle_index_near"]:
            print(f"  {c}: non-null {F[c].notna().sum()}  median {F[c].median():.4g}")
        eve = F[F["cal_next_is_expiry"] == True]  # noqa: E712
        print("  eve rows with bhavcopy settlement index:", eve["settle_index_near"].notna().sum(), "of", len(eve))
        d = (eve["settle_index_near"] / eve["close_official_t1"] - 1).abs() * 100
        print("  |settlement index / official close of t+1 - 1| %: median", round(d.median(), 4), "max", round(d.max(), 4))
    Q = pd.concat(qs)
    Q.to_csv(OUT / "bhavcopy_quality.csv", index=False)
    print(Q.to_string(index=False))


if __name__ == "__main__":
    main()
