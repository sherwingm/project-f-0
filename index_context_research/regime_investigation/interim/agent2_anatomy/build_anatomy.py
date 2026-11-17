"""Agent 2 (G1-F trade anatomy): build anatomy datasets from the ORIGINAL recorded trades. Read-only on all inputs.
Run:  python -W ignore build_anatomy.py     (writes only next to this script)
Nothing here changes a rule or generates an alternative entry. The engine is used only to (a) identify the same contract
and check the recorded net % is reproduced, and (b) read the option minute path of the recorded contract.
"""
import hashlib
import os
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
OUT = os.path.dirname(os.path.abspath(__file__))
REPO = "C:/Users/sherw/project-f-0"
sys.path.insert(0, os.path.join(REPO, "index_research", "scripts"))
sys.path.insert(0, REPO)
import lib  # noqa: E402
from index_data import load as L  # noqa: E402
from scanner.s3_engine import ENTRY_STALE, MARK_STALE, Leg, Spec, chain_between, run_day  # noqa: E402
from scanner.s3_buy_maxup import legs_of  # noqa: E402

REPLAY = f"{REPO}/g1_research/results/g1_live_replay_trades.csv"
CTX = f"{REPO}/index_context_research/results/context_dataset.csv"
G1C = f"{REPO}/g1_research/data/g1c_opt_trades.csv"
PRE_END = date(2024, 9, 30)           # class boundaries use history up to here (the store starts 2021-10-20, not 2018)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def tmin(ts):  # minutes since 09:15 within a session
    return ts.hour * 60 + ts.minute - (9 * 60 + 15)


def main():
    with open(os.path.join(OUT, "hashes.txt"), "w") as f:
        for p in (REPLAY, CTX, G1C, f"{REPO}/index_research/scripts/lib.py", f"{REPO}/scanner/s3_engine.py",
                  f"{REPO}/scanner/s3_buy_maxup.py"):
            f.write(f"{sha(p)}  {p.replace(REPO + '/', '')}\n")

    days = lib.minutes("NIFTY50")
    ses = sorted(days)
    pos = {d: i for i, d in enumerate(ses)}
    dc = pd.Series({d: float(days[d]["close"].iloc[-1]) for d in ses})
    dopen = {d: float(days[d]["open"].iloc[0]) for d in ses}
    vd = lib.vix_daily()
    vx = L.vix_1m(date(2024, 9, 1), date(2026, 10, 30)).sort_values("timestamp")
    vc = vd["close"]

    # history-based class boundaries (never from strategy returns)
    hist = dc[[d for d in ses if d <= PRE_END]]
    bounds = {}
    for k in (1, 5, 10, 20):
        r = (hist / hist.shift(k) - 1).dropna() * 100
        bounds[f"ret{k}"] = np.percentile(r, [20, 40, 60, 80])
    vh = vc[[d for d in vc.index if d <= PRE_END]]
    vix_p25, vix_p75 = np.percentile(vh, [25, 75])
    pd.Series({**{f"{k}_quintile_edges": list(np.round(v, 3)) for k, v in bounds.items()},
               "vix_p25": vix_p25, "vix_p75": vix_p75, "hist_days": len(hist)}).to_csv(os.path.join(OUT, "class_boundaries.csv"))

    ctx = pd.read_csv(CTX)
    ctx["day"] = pd.to_datetime(ctx["day"]).dt.date
    rp = pd.read_csv(REPLAY)
    rp["day"] = pd.to_datetime(rp["day"]).dt.date
    gc = pd.read_csv(G1C)
    gc["day"] = pd.to_datetime(gc["day"]).dt.date

    sets = {}
    for nm in ("G1F", "G1"):
        sets[nm] = ("PE", ctx[ctx.tset == nm].merge(rp[["day", "reason"]], on="day", how="left"))
    c = ctx[ctx.tset == "G1C"].merge(gc[["day", "B_1_reason"]].rename(columns={"B_1_reason": "reason"}), on="day", how="left")
    sets["G1C"] = ("CE", c)

    for name, (side, T) in sets.items():
        rows = []
        for r in T.itertuples():
            day = r.day
            i = pos[day]
            nxt = ses[i + 1]
            exp = date.fromisoformat(str(r.expiry)[:10])
            eh, em = (int(x) for x in r.entry.split(":"))
            ent_ts = pd.Timestamp(L.at(day, eh, em))
            sig_ts = ent_ts - timedelta(minutes=1)
            g = days[day]
            prev = ses[i - 1]
            o = {"tset": name, "day": day, "side": side, "weekday_name": day.strftime("%a"), "quarter": r.quarter, "half": r.half,
                 "entry_time": r.entry, "expiry": exp}
            # ---- PRE-ENTRY
            for k in (1, 5, 10, 20):
                o[f"ret{k}_pct"] = (dc[prev] / dc[ses[i - 1 - k]] - 1) * 100
            s20 = dc[ses[i - 20:i]].mean()
            s50 = dc[ses[i - 50:i]].mean()
            o["prev_vs_sma20_pct"] = (dc[prev] / s20 - 1) * 100
            o["prev_vs_sma50_pct"] = (dc[prev] / s50 - 1) * 100
            o["ma_structure"] = "bull" if dc[prev] > s20 > s50 else ("bear" if dc[prev] < s20 < s50 else "mixed")
            v = vx[vx["timestamp"] <= sig_ts]
            o["vix_signal"] = float(v["close"].iloc[-1]) if len(v) and v["timestamp"].iloc[-1].date() == day else np.nan
            o["vix_prev_close"] = float(vc[prev])
            o["vix_chg5_pct"] = (vc[prev] / vc[ses[i - 6]] - 1) * 100
            o["vix_chg1_pct"] = (vc[prev] / vc[ses[i - 2]] - 1) * 100
            o["vix_signal_vs_prev_pct"] = (o["vix_signal"] / vc[prev] - 1) * 100
            o["gap_pct_open"] = (dopen[day] / dc[prev] - 1) * 100
            sigbar = g[g["timestamp"] == sig_ts]
            sigc = float(sigbar["close"].iloc[0]) if len(sigbar) else np.nan
            hm = g["timestamp"].dt.hour * 60 + g["timestamp"].dt.minute
            rng = g[hm < 9 * 60 + 30]
            hi, lo = float(rng["high"].max()), float(rng["low"].min())
            o["signal_close"] = sigc
            o["intraday_ret_to_signal_pct"] = (sigc / dopen[day] - 1) * 100
            o["or_width_pct"] = (hi / lo - 1) * 100
            o["beyond_or_pct"] = ((lo - sigc) / lo * 100) if side == "PE" else ((sigc - hi) / hi * 100)
            o["breakout_min_after_0930"] = (sig_ts.hour * 60 + sig_ts.minute) - (9 * 60 + 30)
            o["dte_calendar"] = (exp - day).days
            o["dte_sessions"] = len([d for d in ses[i + 1:] if d <= exp])
            for col in ("breadth_prev", "atm_iv", "iv_skew", "pcr_oi", "gift_basis", "us_prev_ret", "fut_oi_chg", "fut_px_chg",
                        "fii_fut_longshare", "event_window", "expiry_day"):
                o[col] = getattr(r, col)
            # ---- OUTCOME (recorded)
            o["net_pct"] = r.net_pct
            o["net_rs"] = r.net_rs
            o["maxup_pct_next_close_file"] = r.maxup
            o["exit_reason_file"] = r.reason
            # ---- engine reproduction + option path
            spec = Spec("anat", [Leg("BUY", side, 0)], entry=(eh, em), exit=(15, 29), stop=0.5)
            res = run_day(spec, day, exp, exit_day=nxt)
            if res.get("skip"):
                o["repro_status"] = "skip: " + str(res["skip"])
            else:
                o["engine_net_pct"] = res["net_pct_premium"]
                o["engine_net_rs"] = res["net_rs"]
                o["engine_reason"] = res["reason"]
                o["repro_diff_pct"] = res["net_pct_premium"] - r.net_pct
                o["repro_status"] = "ok"
                legs = legs_of(res["legs"])
                _, k, opt, fi, fo = legs[0]
                o["strike"] = k
                o["paid_price"] = fi
                o["premium_rs"] = res["premium_rs"]
                o["fees_rs_engine"] = res["fees_rs"]
                exit_t = pd.Timestamp(f"{res['exit_day']} {res['exit_at']}").tz_localize(ent_ts.tz) if ent_ts.tzinfo else pd.Timestamp(f"{res['exit_day']} {res['exit_at']}")
                t_end = pd.Timestamp(L.at(nxt, 15, 29))
                ch = chain_between("NIFTY", exp, day, nxt)
                w = ch[(ch["timestamp"] > ent_ts) & (ch["timestamp"] <= t_end)]
                mins = pd.DatetimeIndex(sorted(w["timestamp"].unique()))
                gg = w[(w["strike"] == k) & (w["option_type"] == opt)].drop_duplicates("timestamp", keep="last")
                ser = pd.Series(gg["close"].to_numpy(float), index=pd.DatetimeIndex(gg["timestamp"]))
                seen = pd.Series(ser.index, index=ser.index)
                px0 = L.price_at(ch, k, opt, ent_ts, stale=ENTRY_STALE)
                val = ser.reindex(mins).ffill().fillna(px0 if px0 is not None else fi).to_numpy()
                sn = seen.reindex(mins).ffill().fillna(ent_ts)
                stale = (mins - pd.DatetimeIndex(sn)).total_seconds() > MARK_STALE * 60
                up = np.where(~stale, (val / fi - 1) * 100, np.nan)
                held = mins <= exit_t
                if np.isfinite(up).any():
                    ip = int(np.nanargmax(up))
                    o["mfe_any_pct"] = up[ip]
                    pk = mins[ip]
                    o["peak_at"] = pk.strftime("%Y-%m-%d %H:%M")
                    o["peak_on_entry_day"] = int(pk.date() == day)
                    o["peak_trading_min_after_entry"] = (tmin(pk) - tmin(ent_ts)) if pk.date() == day else (375 - tmin(ent_ts)) + tmin(pk)
                    if held.any() and np.isfinite(up[held]).any():
                        o["mfe_held_pct"] = np.nanmax(up[held])
                        o["mae_held_pct"] = np.nanmin(up[held])      # lowest option minute close vs price paid (negative = below)
                        o["mae_any_pct"] = np.nanmin(up)
                        o["mae_before_peak_pct"] = np.nanmin(up[: ip + 1])
                    o["exit_day"] = res["exit_day"]
                    o["exit_time"] = res["exit_at"]
                    o["exit_reason"] = res["reason"]
                    if res["exit_day"] == day:
                        o["duration_trading_min"] = tmin(exit_t) - tmin(ent_ts)
                    else:
                        o["duration_trading_min"] = (375 - tmin(ent_ts)) + tmin(exit_t)
                    o["duration_wall_min"] = (exit_t - ent_ts).total_seconds() / 60
                    if res["reason"] == "stop":
                        after = (mins > exit_t) & ~stale
                        o["stop_after_max_up_pct"] = np.nanmax(up[after]) if after.any() else np.nan
                        o["stop_nextclose_vs_paid_pct"] = up[-1] if np.isfinite(up[-1]) else np.nan
            # ---- POST-ENTRY (explanation only)
            o["post_next_open_gap_pct"] = (dopen[nxt] / dc[day] - 1) * 100
            o["post_next_close_vs_entrydayclose_pct"] = (dc[nxt] / dc[day] - 1) * 100
            o["post_entryday_close_vs_signalclose_pct"] = (dc[day] / sigc - 1) * 100
            o["post_spot_move_signal_to_nextclose_pct"] = (dc[nxt] / sigc - 1) * 100
            rows.append(o)
        D = pd.DataFrame(rows)
        for k in (1, 5, 10, 20):
            D[f"ret{k}_class"] = np.digitize(D[f"ret{k}_pct"], bounds[f"ret{k}"]) + 1
        D["vix_level_class"] = np.where(D.vix_signal < vix_p25, "low", np.where(D.vix_signal > vix_p75, "high", "normal"))
        D["vix_dir_class"] = np.where(D.vix_chg5_pct >= 5, "rising", np.where(D.vix_chg5_pct <= -5, "falling", "flat"))
        D["vix_chg1_sign"] = np.where(D.vix_chg1_pct > 0, "up", "down_or_flat")
        D["gap_class"] = np.where(D.gap_pct_open <= -0.3, "gap_down", np.where(D.gap_pct_open >= 0.3, "gap_up", "flat"))
        D["dte_class"] = np.where(D.dte_sessions >= 4, "4+", D.dte_sessions.astype(str))
        D["breakout_time_class"] = np.where(D.breakout_min_after_0930 < 30, "before_10:00",
                                            np.where(D.breakout_min_after_0930 < 90, "10:00-10:59", "11:00_or_later"))
        D["win"] = (D.net_pct > 0).astype(int)
        fn = "anatomy_dataset.csv" if name == "G1F" else f"anatomy_dataset_{name}.csv"
        D.to_csv(os.path.join(OUT, fn), index=False)
        ok = D[D.repro_status == "ok"]
        d = ok.repro_diff_pct.abs()
        print(f"{name}: n={len(D)} engine ok={len(ok)}; |diff|<=0.01: {(d <= 0.01).sum()}  <=0.1: {(d <= 0.1).sum()}  "
              f"<=0.5: {(d <= 0.5).sum()}  <=2: {(d <= 2).sum()}  reason same: {(ok.engine_reason == ok.exit_reason_file).sum()}  "
              f"max|diff|={d.max():.2f}")
    print("done")


if __name__ == "__main__":
    main()
