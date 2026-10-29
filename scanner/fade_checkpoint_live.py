"""S1 fade · live research checkpoint: audit + performance + peak capture + entry quality + early moves + shadows.

    python -m scanner.fade_checkpoint_live <paper_ledger.json> <observations_dir> [out_stem]

Read-only. Inputs are a copy of the server's ledger and its bid/ask record (data/observations/<day>.jsonl). Every
number comes from the stored records; nothing is reconstructed or filled in. Held-period statistics use only rows
with phase "held" at or before the sale; rows with phase "after_exit" are reported separately and never enter
realised P&L. Writes data/results/<out_stem>_tables.md and _trades.csv (default stem S1_fade_checkpoint_live).
Protocol and definitions: data/results/S1_fade_checkpoint_2026-10-29_report.md.
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from server import charges as ch
from server.peak import POST_EXIT_MINUTES

from .build import ROOT
from .fade_entry_quality import md_table

RES = ROOT / "data" / "results"
NEAR_EXIT_S = 5          # a held peak within this many seconds of the sale counts as "at the exit"
STALE_ROW_S = 60         # an observation whose last trade is older than this is "stale" for that row


def ts(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


def ltt_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace(" ", "T") + "+05:30")


def load_obs(d: Path, day: str, cache: dict) -> list[dict]:
    if day not in cache:
        f = d / f"{day}.jsonl"
        cache[day] = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()] if f.exists() else None
    return cache[day]


def fnum(x, nd=2):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(x, nd)


# ---------------------------------------------------------------------------------------------------- 1. audit
def audit(c: dict, rows: list[dict] | None) -> dict:
    """Per-trade record checks. Returns flags and the coverage numbers."""
    o, cl = ts(c["opened_at"]), ts(c["closed_at"])
    eo, xo, eq, pc, hb = (c.get(k) or {} for k in ("entry_order", "exit_order", "entry_quote", "peak_capture", "held_bid"))
    a = {"id": c["id"], "tz_ok": all(str(c.get(k, "")).endswith("+05:30") for k in ("opened_at", "closed_at"))}
    a["order_ok"] = bool(o < cl and ts(eo.get("placed_at")) <= ts(eo.get("filled_at")) <= cl
                         and ts(xo.get("placed_at")) <= ts(xo.get("filled_at")) and ts(xo["filled_at"]) >= o)
    # ledger arithmetic
    qty, e, x = c["qty"], c["entry"]["price"], c["exit"]["price"]
    gross = round((x - e) * qty, 2)
    chg = round(c["entry_charges"] + c["exit_charges"]["total"], 2)
    a["gross_ok"] = abs(gross - c["gross_pnl"]) < 0.02
    a["net_ok"] = abs(gross - chg - c["net_pnl"]) < 0.02 and abs(chg - c["charges_total"]) < 0.02
    a["capital_ok"] = abs(e * qty - c["capital_committed"]) < 0.02
    a["ret_ok"] = abs(c["net_pnl"] / c["capital_committed"] * 100 - c["return_pct"]) < 0.01
    a["fills_match_orders"] = (sum(l["qty"] for l in eo.get("levels", [])) == qty == sum(l["qty"] for l in xo.get("levels", []))
                               and abs(eo["levels"][0]["price"] - e) < 1e-9 and abs(xo["levels"][0]["price"] - x) < 1e-9)
    if rows is None:
        a["obs_file"] = False
        return a
    a["obs_file"] = True
    mine = sorted((r for r in rows if r["id"] == c["id"]), key=lambda r: r["t"])
    held = [r for r in mine if r["phase"] == "held"]
    post = [r for r in mine if r["phase"] == "after_exit"]
    a["held_rows"], a["post_rows"] = len(held), len(post)
    a["held_after_sale"] = sum(ts(r["t"]) > cl for r in held)              # must be 0
    a["post_before_sale"] = sum(ts(r["t"]) < cl for r in post)             # must be 0
    a["post_past_cutoff"] = sum(ts(r["t"]) > cl + timedelta(minutes=POST_EXIT_MINUTES) + timedelta(seconds=5) for r in post)
    tl = [o] + [ts(r["t"]) for r in held] + [cl]
    a["held_max_gap_s"] = round(max((b - a_).total_seconds() for a_, b in zip(tl, tl[1:])), 1)
    a["held_window_s"] = round((cl - o).total_seconds(), 1)
    pt = [ts(r["t"]) for r in post]
    a["post_span_min"] = round((pt[-1] - cl).total_seconds() / 60, 1) if pt else 0
    a["post_max_gap_s"] = round(max(((b - a_).total_seconds() for a_, b in zip([cl] + pt, pt)), default=0), 1)
    bad = lambda r: not r.get("bid") or r["bid"] <= 0                       # noqa: E731
    a["held_no_bid"] = sum(bad(r) for r in held)
    a["held_no_ask"] = sum(not r.get("ask") for r in held)
    a["held_crossed"] = sum(1 for r in held if r.get("bid") and r.get("ask") and r["bid"] > r["ask"])
    a["post_no_bid"] = sum(bad(r) for r in post)
    a["held_stale_ltt_rows"] = sum(1 for r in held if r.get("ltt") and (ts(r["t"]) - ltt_dt(r["ltt"])).total_seconds() > STALE_ROW_S)
    a["held_ltt_missing"] = sum(1 for r in held if not r.get("ltt"))
    # server/peak.py's held window starts at the first quote AFTER the entry, so the entry-quote row is left out here
    hb_bids = [r["bid"] for r in held if r.get("bid") and r.get("via") != "entry quote"]
    # rows are written only when the book changes, so a first poll that repeats the entry quote's book exists only as
    # the entry-quote row: the ledger peak / low must equal some held row's bid and bound every later held row
    all_b = {r["bid"] for r in held if r.get("bid")}
    pk, lo = pc.get("peak_bid", -1), pc.get("low_bid", -1)
    a["peak_matches_rows"] = bool(hb_bids) and pk in all_b and max(hb_bids) <= pk + 1e-9
    a["low_matches_rows"] = bool(hb_bids) and lo in all_b and min(hb_bids) >= lo - 1e-9
    a["rows_vs_quotes"] = f"{len(hb_bids)} / {hb.get('n')}"   # rows are written only when the book changes
    a["exit_is_last_bid"] = bool(hb_bids) and abs(hb_bids[-1] - x) < 1e-9 if xo.get("price_is_bid") else None
    a["sources"] = ", ".join(sorted(Counter(r.get("via") for r in held)))
    return a


# ------------------------------------------------------------------------------------------- per-trade metrics
def metrics(c: dict, rows: list[dict] | None) -> dict:
    r, eq, pc = c["rule"], c.get("entry_quote") or {}, c.get("peak_capture") or {}
    o, cl = ts(c["opened_at"]), ts(c["closed_at"])
    e, x, qty = c["entry"]["price"], c["exit"]["price"], c["qty"]
    spot = eq.get("spot") or r.get("spot_at_entry")
    k = c["strike"]
    otm = ((k - spot) / spot * 100 if c["instrument"] == "CE" else (spot - k) / spot * 100) if spot else None
    m = {"day": c["opened_at"][:10], "symbol": c["symbol"], "type": c["instrument"], "strike": k, "expiry": c["expiry"],
         "qty": qty, "entry": e, "exit": x, "reason": c["reason"], "opened": c["opened_at"][11:19],
         "closed": c["closed_at"][11:19], "held_s": round((cl - o).total_seconds()),
         "buy_value": c["capital_committed"], "charges": c["charges_total"], "net": c["net_pnl"], "net_pct": c["return_pct"],
         # entry-time features (known at or before the buy)
         "entry_delay_s": round((o - o.replace(hour=9, minute=15, second=0)).total_seconds()),
         "ltt_age_s": eq.get("ltt_age_s"), "stale_ltt": eq.get("stale_ltt"), "quote_src": eq.get("source"),
         "entry_bid": eq.get("bid"), "entry_ask": eq.get("ask"),
         "spread_rs": fnum(eq["ask"] - eq["bid"]) if eq.get("ask") and eq.get("bid") else None,
         "spread_pct_mid": fnum((eq["ask"] - eq["bid"]) / ((eq["ask"] + eq["bid"]) / 2) * 100) if eq.get("ask") and eq.get("bid") else None,
         "bid_over_entry": fnum(eq["bid"] / e, 3) if eq.get("bid") else None,
         "bid_at_or_below_stop": (eq["bid"] <= 0.80 * e) if eq.get("bid") else None,
         "ask_qty_fits": (eq.get("ask_qty") or 0) >= qty if eq.get("ask_qty") is not None else None,
         "otm_pct": fnum(otm), "days_to_expiry": (datetime.fromisoformat(c["expiry"]).date() - o.date()).days,
         "volume_at_entry": eq.get("volume"), "oi_at_entry": eq.get("oi"),
         "filing_move_vs_mkt": (r.get("shadow_fd2") or {}).get("D"), "np_yoy": r.get("np_yoy"), "rev_yoy": r.get("rev_yoy"),
         # peak capture (held bids only)
         "peak_bid": pc.get("peak_bid"), "peak_at": (pc.get("peak_at") or "")[11:19],
         "peak_ret_pct": pc.get("peak_return_pct"), "peak_gross": pc.get("peak_gross"), "peak_net": pc.get("peak_net"),
         "giveback": pc.get("giveback_rs"), "capture_pct": pc.get("capture_pct"), "capture_note": pc.get("capture_note"),
         "peak_qty": pc.get("peak_bid_qty"), "lot_fits_peak": pc.get("lot_fits_at_peak"), "mae_pct": pc.get("mae_pct"),
         "held_max_gap_s": pc.get("max_gap_s"), "quotes": pc.get("quotes")}
    # re-derive net at peak with the same charge schedule (the full lot at the peak bid; an estimate)
    if pc.get("peak_bid") is not None:
        rt = ch.round_trip(c["instrument"], "BUY", qty, e, pc["peak_bid"])
        m["peak_net_rederived"] = round((pc["peak_bid"] - e) * qty - rt["total"], 2)
    pa = ts(pc.get("peak_at"))
    first = (c.get("held_bid") or {}).get("first") or {}
    m["peak_where"] = (None if pa is None else "first quote" if first.get("at") == pc.get("peak_at")
                       else "at exit (≤5 s)" if (cl - pa).total_seconds() <= NEAR_EXIT_S else "before exit")
    m["left_at_exit_rs"] = fnum((pc["peak_bid"] - x) * qty) if pc.get("peak_bid") is not None else None
    # shadows (no orders; same entry, same qty)
    def sh(name):
        s = r.get(name) or {}
        return c["net_pnl"] if s.get("status") == "same" else s.get("net") if s.get("status") == "done" else None
    m["v11_net"], m["v10_net"], m["trail5_net"] = sh("shadow_v11"), sh("shadow_v10"), sh("shadow_trail")
    m["v10_fill_1520"] = (r.get("shadow_v10") or {}).get("fill")
    for kk in ("v11", "v10", "trail5"):
        m[f"{kk}_pct"] = fnum(m[f"{kk}_net"] / c["capital_committed"] * 100) if m[f"{kk}_net"] is not None else None
    # after-exit extremes kept by the server beyond the 60-minute rows (may run into later days)
    af = c.get("after") or {}
    m["after_peak_bid"] = (af.get("peak_bid") or {}).get("price")
    m["after_peak_bid_at"] = (af.get("peak_bid") or {}).get("at")
    m["after_low_bid"] = (af.get("low_bid") or {}).get("price")
    m["after_last_at"] = (af.get("last") or {}).get("at")
    # early path on observed bids: held rows and post-exit rows kept apart
    if rows is not None:
        mine = sorted((rr for rr in rows if rr["id"] == c["id"] and rr.get("bid")), key=lambda rr: rr["t"])
        for w in (1, 3, 5):
            win = [rr for rr in mine if 0 < (ts(rr["t"]) - o).total_seconds() <= w * 60]
            hw = [rr for rr in win if rr["phase"] == "held"]
            m[f"dip{w}_held_pct"] = fnum((min(rr["bid"] for rr in hw) / e - 1) * 100, 1) if hw else None
            m[f"dip{w}_path_pct"] = fnum((min(rr["bid"] for rr in win) / e - 1) * 100, 1) if win else None
            m[f"cov{w}_s"] = round((ts(win[-1]["t"]) - o).total_seconds()) if win else 0
        rec = next((rr for rr in mine if ts(rr["t"]) > o and rr["bid"] >= e and rr["phase"] == "held"), None)
        m["back_to_entry_held_min"] = fnum((ts(rec["t"]) - o).total_seconds() / 60, 1) if rec else None
        post = [rr for rr in mine if rr["phase"] == "after_exit"]
        rp = next((rr for rr in post if rr["bid"] >= e), None)
        m["back_to_entry_post60_min"] = fnum((ts(rp["t"]) - cl).total_seconds() / 60, 1) if rp else None
        # the stop: when the held bid first stood at or below 0.80 x entry, and was the stop checking yet (from 09:16)?
        lvl = 0.80 * e
        br = next((rr for rr in mine if rr["phase"] == "held" and rr["bid"] <= lvl), None)
        m["first_bid_below_stop_at"] = br["t"][11:19] if br else None
        m["breached_before_0916"] = (br["t"][11:19] < "09:16:00") if br else None
        m["exit_vs_stop_level_pct"] = fnum((x / lvl - 1) * 100, 1) if c["reason"] == "fade_stop" else None
        m["post60_max_bid"] = max((rr["bid"] for rr in post), default=None)
        m["post60_min_bid"] = min((rr["bid"] for rr in post), default=None)
        m["post60_last_bid"] = post[-1]["bid"] if post else None
        m["post60_span_min"] = fnum((ts(post[-1]["t"]) - cl).total_seconds() / 60, 1) if post else 0
    return m


# --------------------------------------------------------------------------------------------- summaries
def perf(d: pd.DataFrame) -> dict:
    n = len(d)
    w, l = d[d.net > 0], d[d.net < 0]
    cum = d.sort_values(["day", "closed"]).net.cumsum()
    dd = (cum - cum.cummax().clip(lower=0)).min()
    return {"trades": n, "wins": len(w), "losses": len(l), "breakeven": int((d.net == 0).sum()),
            "win %": round(len(w) / n * 100, 1) if n else None,
            "mean net % (on buy value)": round(d.net_pct.mean(), 2), "median net %": round(d.net_pct.median(), 2),
            "total net Rs": round(d.net.sum()), "total charges Rs": round(d.charges.sum()),
            "avg win Rs": round(w.net.mean()) if len(w) else None, "avg loss Rs": round(l.net.mean()) if len(l) else None,
            "profit factor": round(w.net.sum() / -l.net.sum(), 2) if len(l) and len(w) else None,
            "max drawdown Rs (realised, chronological)": round(dd), "total buy value Rs": round(d.buy_value.sum())}


def grp(d: pd.DataFrame, col: str, order=None) -> pd.DataFrame:
    out = []
    for g, x in d.groupby(col, dropna=False):
        out.append({col: g, "n": len(x), "wins": int((x.net > 0).sum()), "stops": int((x.reason == "fade_stop").sum()),
                    "mean net %": round(x.net_pct.mean(), 1), "median net %": round(x.net_pct.median(), 1),
                    "total net Rs": round(x.net.sum())})
    o = pd.DataFrame(out)
    if order:
        o[col] = pd.Categorical(o[col], order, ordered=True)
        o = o.sort_values(col)
    return o


def feature_rows(d: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    out = []
    for f in feats:
        v = d[[f, "net_pct", "net", "reason", "day"]].dropna(subset=[f])
        miss = len(d) - len(v)
        if v[f].dtype == bool or v[f].nunique() <= 2:
            parts = [(str(g), x) for g, x in v.groupby(f)]
            rho = None
        else:
            med = v[f].median()
            parts = [(f"≤ {med:g}", v[v[f] <= med]), (f"> {med:g}", v[v[f] > med])]
            rho = round(v[f].rank().corr(v.net_pct.rank()), 2) if len(v) > 2 else None
        desc = " | ".join(f"{lab}: n {len(x)}, win {int((x.net > 0).sum())}, stop {int((x.reason == 'fade_stop').sum())}, "
                          f"mean {x.net_pct.mean():+.1f} %" for lab, x in parts)
        out.append({"feature": f, "n": len(v), "missing": miss, "Spearman rho vs net %": rho, "split (median or level)": desc,
                    "days covered": ", ".join(sorted(v.day.unique()))[5:].replace("2026-", "")})
    return pd.DataFrame(out)


def main() -> None:
    ledger_p, obs_d = Path(sys.argv[1]), Path(sys.argv[2])
    stem = sys.argv[3] if len(sys.argv) > 3 else "S1_fade_checkpoint_live"
    L = json.loads(ledger_p.read_text(encoding="utf-8"))
    cache: dict = {}
    closed, opened = L.get("closed", []), L.get("positions", [])
    fade_all = [c for c in closed if "F" in ((c.get("rule") or {}).get("arms") or [])]
    open_fade = [c for c in opened if "F" in ((c.get("rule") or {}).get("arms") or [])]
    v12 = [c for c in fade_all if c["rule"].get("version") == "v12"]
    meas = [c for c in v12 if c.get("peak_capture") and c.get("entry_quote")]
    ids = [c["id"] for c in closed + opened]
    keys = [(c["tradingsymbol"], c["opened_at"]) for c in closed + opened]

    A = pd.DataFrame([audit(c, load_obs(obs_d, c["opened_at"][:10], cache)) for c in meas])
    M = pd.DataFrame([metrics(c, load_obs(obs_d, c["opened_at"][:10], cache)) for c in meas])
    M19 = pd.DataFrame([metrics(c, None) for c in v12])

    out = [f"# S1 fade · live checkpoint tables (generated by scanner/fade_checkpoint_live.py)\n",
           f"Ledger: `{ledger_p.name}` saved_at {L.get('saved_at')}; observation days: "
           f"{', '.join(sorted(k for k, v in cache.items() if v is not None))}.\n",
           "## Dataset\n",
           md_table(pd.DataFrame([{
               "closed positions (all arms)": len(closed), "open positions (all arms)": len(opened),
               "unique ids": len(set(ids)), "duplicate ids": len(ids) - len(set(ids)),
               "duplicate (contract, open time)": len(keys) - len(set(keys)),
               "fade closed (all versions)": len(fade_all), "fade open": len(open_fade),
               "fade v10 / v11 / v12": f"{sum(1 for c in fade_all if not c['rule'].get('version'))} / "
                                       f"{sum(1 for c in fade_all if c['rule'].get('version') == 'v11')} / {len(v12)}",
               "v12 measured (peak_capture + entry_quote)": len(meas),
               "all closed with peak_capture (any arm)": sum(1 for c in closed if c.get("peak_capture"))}])),
           "\n## Record audit (measured v12 trades)\n", md_table(A),
           "\n## Performance: 18 measured v12 trades\n", md_table(pd.DataFrame([perf(M)])),
           "\n## Performance: all 19 v12 trades (adds ADANIENSOL 23 Oct, unmeasured)\n", md_table(pd.DataFrame([perf(M19)])),
           "\n## By exit reason\n", md_table(grp(M, "reason")),
           "\n## By option type\n", md_table(grp(M, "type")),
           "\n## By day\n", md_table(grp(M, "day"))]
    M["premium band"] = pd.cut(M.entry, [0, 5, 15, 1e9], labels=["< Rs 5", "Rs 5-15", ">= Rs 15"], right=False).astype(str)
    out += ["\n## By entry premium\n", md_table(grp(M, "premium band", ["< Rs 5", "Rs 5-15", ">= Rs 15"]))]
    cols = ["day", "symbol", "type", "strike", "qty", "entry", "exit", "reason", "opened", "closed", "held_s", "buy_value",
            "charges", "net", "net_pct"]
    out += ["\n## Trades\n", md_table(M[cols])]
    pk = ["symbol", "entry", "peak_bid", "peak_at", "peak_where", "exit", "closed", "peak_gross", "peak_net",
          "peak_net_rederived", "net", "giveback", "left_at_exit_rs", "capture_pct", "peak_qty", "qty", "lot_fits_peak",
          "held_max_gap_s", "quotes"]
    out += ["\n## Peak capture (held bids only)\n", md_table(M[pk]),
            "\n" + md_table(pd.DataFrame([{
                "trades": len(M), "peak net > 0 (a paying peak)": int((M.peak_net > 0).sum()),
                "capture defined": int(M.capture_pct.notna().sum()),
                "peak at first quote": int((M.peak_where == "first quote").sum()),
                "peak before exit": int((M.peak_where == "before exit").sum()),
                "peak at exit (≤5 s)": int((M.peak_where == "at exit (≤5 s)").sum()),
                "sum of positive peak net Rs (est.)": round(M.peak_net.clip(lower=0).sum()),
                "sum giveback Rs": round(M.giveback.sum()), "realised Rs": round(M.net.sum()),
                "max held gap s (worst trade)": M.held_max_gap_s.max(), "lot fitted at peak": int(M.lot_fits_peak.sum())}]))]
    feats = ["entry_delay_s", "ltt_age_s", "stale_ltt", "spread_rs", "spread_pct_mid", "bid_over_entry",
             "bid_at_or_below_stop", "entry", "otm_pct", "days_to_expiry", "type", "volume_at_entry", "oi_at_entry",
             "filing_move_vs_mkt", "np_yoy", "ask_qty_fits"]
    fe = ["symbol", "day", "type", "entry_delay_s", "ltt_age_s", "stale_ltt", "quote_src", "entry_bid", "entry_ask",
          "spread_rs", "spread_pct_mid", "bid_over_entry", "bid_at_or_below_stop", "otm_pct", "days_to_expiry",
          "volume_at_entry", "filing_move_vs_mkt", "np_yoy", "reason", "net_pct"]
    out += ["\n## Entry features (all known at the buy)\n", md_table(M[fe]),
            "\n## Entry features vs outcome (descriptive; n = 18, 3 days)\n", md_table(feature_rows(M, feats))]
    M["after_peak_same_day"] = [bool(a_) and a_[:10] == dd for a_, dd in zip(M.after_peak_bid_at.fillna(""), M.day)]
    ea = ["symbol", "reason", "entry", "held_s", "dip1_held_pct", "dip1_path_pct", "dip3_held_pct", "dip3_path_pct",
          "dip5_held_pct", "dip5_path_pct", "cov5_s", "back_to_entry_held_min", "exit", "back_to_entry_post60_min",
          "post60_min_bid", "post60_max_bid", "post60_last_bid", "post60_span_min", "v10_fill_1520",
          "after_peak_bid", "after_peak_bid_at", "after_peak_same_day"]
    out += ["\n## Early path and recovery (observed bids; held vs after-exit kept apart)\n", md_table(M[ea])]
    sp = M[M.reason == "fade_stop"]
    out += ["\n## The stop (14 stopped trades)\n",
            md_table(sp[["symbol", "opened", "entry", "first_bid_below_stop_at", "breached_before_0916", "closed", "exit",
                         "exit_vs_stop_level_pct", "net_pct"]]),
            "\n" + md_table(pd.DataFrame([{
                "stopped": len(sp), "bid at/below stop before 09:16 (stop not yet checking)": int(sp.breached_before_0916.sum()),
                "exits at the first stop check (closed ≤ 09:16:30)": int((sp.closed <= "09:16:30").sum()),
                "median exit vs stop level %": sp.exit_vs_stop_level_pct.median(),
                "worst exit vs stop level %": sp.exit_vs_stop_level_pct.min(),
                "mean net % of stopped": round(sp.net_pct.mean(), 1),
                "back to entry within 60 min after the stop": int(sp.back_to_entry_post60_min.notna().sum()),
                "post-exit max bid ≥ entry, exit day (60-min rows or the server's after-peak, same day)": int(
                    ((sp.post60_max_bid >= sp.entry) | ((sp.after_peak_bid >= sp.entry) & sp.after_peak_same_day)).sum()),
                "15:20 bid above the stop sale": int((sp.v10_fill_1520 > sp.exit).sum()),
                "15:20 bid above entry": int((sp.v10_fill_1520 > sp.entry).sum()),
                "post-60-min low below the sale": int((sp.post60_min_bid < sp.exit).sum())}]))]
    sh = ["symbol", "reason", "net", "v11_net", "v10_net", "trail5_net", "net_pct", "v11_pct", "v10_pct", "trail5_pct"]

    def shsum(D, label):
        rows = []
        for k_, col, pc_ in (("v12 (real)", "net", "net_pct"), ("v11 shadow", "v11_net", "v11_pct"),
                             ("v10 shadow", "v10_net", "v10_pct"), ("5 % trail shadow", "trail5_net", "trail5_pct")):
            v = D[col].dropna()
            diff = (D["net_pct"] - D[pc_]).dropna()
            sd = st.stdev(diff) if len(diff) > 1 else 0
            rows.append({"set": label, "rule": k_, "n": len(v), "wins": int((v > 0).sum()), "total net Rs": round(v.sum()),
                         "mean net %": round(D[pc_].mean(), 2), "worst Rs": round(v.min()),
                         "v12 minus this, mean pts": round(diff.mean(), 2) if k_ != "v12 (real)" else None,
                         "t of difference": (round(diff.mean() / (sd / math.sqrt(len(diff))), 2) if sd else None) if k_ != "v12 (real)" else None,
                         "trades that differ": int((D["net"] != D[col]).sum())})
        return rows
    out += ["\n## Shadows per trade\n", md_table(M19[sh]),
            "\n## Shadows: summary\n", md_table(pd.DataFrame(shsum(M, "18 measured") + shsum(M19, "19 incl. ADANIENSOL")))]
    (RES / f"{stem}_tables.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    M.merge(A, left_index=True, right_index=True).to_csv(RES / f"{stem}_trades.csv", index=False)
    print(f"{len(meas)} measured v12 fade trades; wrote {stem}_tables.md and _trades.csv")


if __name__ == "__main__":
    main()
