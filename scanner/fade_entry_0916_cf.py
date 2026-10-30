"""S1 fade · 09:15 vs 09:16 entry counterfactual (read-only; strategies/S1_fade_0916_entry_counterfactual.md).

    python -m scanner.fade_entry_0916_cf <paper_ledger.json> <observations_dir> <entry_probe_dir> [stem] [walk_0916_dir]

Inputs are copies: the server's ledger, its bid/ask record (data/observations/<day>.jsonl) and the entry probe
(data/entry_probe/<day>.json). For every bought v12 fade signal it keeps the actual 09:15 trade, builds a 09:16
entry from the first eligible recorded ask at or after 09:16:00, and applies the v12 exit on the recorded bids that
follow. Prices are observed quotes; sales are simulated at the observed bid (no order model). Nothing is interpolated:
a trade whose entry or exit cannot be decided from the records is "unavailable". Writes data/results/<stem>.md and
<stem>_trades.csv (default stem S1_fade_0916_counterfactual).
"""
from __future__ import annotations

import json
import math
import statistics as stt
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from scipy.stats import t as student_t

from server import charges as ch
from server.fade import BAND, MAX_SPREAD, MIN_PREMIUM, PROBE_STRIKES, walk, walk_path

from .build import ROOT
from .fade_entry_quality import md_table
from .stats import clustered_t

RES = ROOT / "data" / "results"
STOP, TRAIL_ON, GAP = 0.80, 1.10, 0.02          # v12 (strategies/S1_v12_fade_trail2.md)
T16, T16_LAST = "09:16:00", "09:20:00"          # the 09:16 entry: first eligible row in [09:16:00, 09:20:00]
# the re-run's pre-registered decision (strategies/S1_fade_0916_rerun_prereg.md, written 30 Oct 2026)
PREREG = "strategies/S1_fade_0916_rerun_prereg.md"
FRESH_FROM = "2026-10-28"                       # today's books only from here (the first-trade-today gate, 32595932)
N_DECIDE, N_FINAL = 30, 60                      # the two looks: at 30 fresh-book pairs, once more at 60 if inconclusive
P1_PTS, P2_T, P2_DAYS, P3_PTS, P4_STOPS = 5.0, 2.0, 6, 2.5, 3
CLOSE_PTS, CLOSE_T = 2.0, 1.0
C1_MIN, C2_MIN, C3_MIN = 5, 2, 10                          # fewer pairs than this: the check is "too few", not a failure
EOD_AT = "15:20:00"


def sec(t: str) -> float:
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def hhmmss(iso: str) -> str:
    return iso[11:19]


# ------------------------------------------------------------------------------------------------- the records
def stream(c: dict, obs: list[dict], probe: dict | None) -> list[dict]:
    """Every recorded book of the trade's contract: probe rows (same symbol and strike) and observation rows (this
    position id, held and after-exit), sorted by time. Times are 'HH:MM:SS[.fff]' on the trade day."""
    out = []
    if probe:
        cols = probe["cols"]
        for r in probe["rows"]:
            d = dict(zip(cols, r))
            if d["symbol"] == c["symbol"] and d["strike"] == c["strike"]:
                out.append({"t": d["t"], "bid": d["bid"], "ask": d["ask"], "bid_qty": d["bid_qty"],
                            "ask_qty": d["ask_qty"], "ltt": d["ltt"], "src": "probe"})
    for r in obs:
        if r["id"] == c["id"]:
            out.append({"t": hhmmss(r["t"]), "bid": r["bid"], "ask": r["ask"], "bid_qty": r["bid_qty"],
                        "ask_qty": r["ask_qty"], "ltt": r["ltt"], "src": "obs-" + r["phase"], "via": r.get("via")})
    return sorted(out, key=lambda x: sec(x["t"]))


def eligible(r: dict, day: str, qty: int) -> tuple[bool, str]:
    b, a = r.get("bid"), r.get("ask")
    if not b or not a or b <= 0 or a <= 0:
        return False, "no two-sided quote"
    if a < b:
        return False, "crossed"
    if not r.get("ltt") or not str(r["ltt"]).startswith(day):
        return False, "stale (no trade today)"
    if a < MIN_PREMIUM:
        return False, "ask below Rs 2"
    if a - b > MAX_SPREAD * a:
        return False, "spread above 10 % of the ask"
    if not BAND[0] <= a * qty <= BAND[1]:
        return False, "lot outside Rs 600-8,000"
    return True, ""


def exit_v12(rows: list[dict], e: float, after: dict, eod_bid: float | None) -> dict:
    """v12 on the recorded bids after the entry row. Returns reason, price, time, how it was decided. As live
    (server/fade.py): levels rounded to 4 dp, and no stop or trail check from 15:20:00 (the 15:20 sale)."""
    on, peak, stop, start = False, None, round(STOP * e, 4), round(TRAIL_ON * e, 4)
    for r in rows:
        b = r.get("bid")
        if not b or sec(r["t"]) >= sec(EOD_AT):
            continue
        if not on:
            if b <= stop:
                return {"reason": "stop", "price": b, "t": r["t"], "by": "rows", "src": r["src"]}
            if b >= start:
                on, peak = True, b
                continue
        else:
            peak = max(peak, b)
            if b <= round(peak * (1 - GAP), 4):
                return {"reason": "trail", "price": b, "t": r["t"], "by": "rows", "src": r["src"]}
    lo, hi = (after.get("low_bid") or {}).get("price"), (after.get("peak_bid") or {}).get("price")
    if not on and lo is not None and hi is not None and lo > stop and hi < start and eod_bid:
        return {"reason": "eod", "price": eod_bid, "t": "15:20", "by": "extremes test", "src": "shadow_v10 fill"}
    return {"reason": None, "price": None, "t": None,
            "by": "unresolved (trail on at coverage end)" if on else "unresolved (extremes do not rule out a trigger)",
            "src": None}


def first_min_dip(rows: list[dict], t0: str, e: float) -> float | None:
    w = [r["bid"] for r in rows if r.get("bid") and 0 < sec(r["t"]) - sec(t0) <= 60]
    return round((min(w) / e - 1) * 100, 1) if w else None


def walk_same(c: dict, probe: dict | None, t: str, spot: float | None) -> str:
    """Would the live walk at time t have chosen this strike? From the probe's standing books (first 8 strikes)."""
    if not probe or not spot:
        return "unknown"
    sig = next((s for s in probe["signals"] if s["symbol"] == c["symbol"]), None)
    if not sig or not sig.get("strikes"):
        return "unknown"
    cols, book = probe["cols"], {}
    for r in probe["rows"]:
        d = dict(zip(cols, r))
        if d["symbol"] == c["symbol"] and sec(d["t"]) <= sec(t):
            book[d["strike"]] = d
    path = walk_path(sig["strikes"], spot, sig["side"])

    def q(k):
        d = book.get(k)
        if not d or not d["bid"] or not d["ask"]:
            return None
        return {"depth": {"bid": [[d["bid"], d["bid_qty"]]], "ask": [[d["ask"], d["ask_qty"]]]}, "lot_size": c["qty"]}
    got = walk(sig["strikes"], spot, sig["side"], q)
    if isinstance(got, tuple):
        if got[0] == c["strike"]:
            unseen = [k for k in path[:path.index(c["strike"])] if k not in book]
            return "unknown" if unseen else "yes"
        return f"no ({got[0]:g})"
    return "unknown" if c["strike"] in path[PROBE_STRIKES:] else f"no ({got})"


def net(c: dict, e: float, x: float) -> float:
    return round((x - e) * c["qty"] - ch.round_trip(c["instrument"], "BUY", c["qty"], e, x)["total"], 2)


# ------------------------------------------------------------------------------------------------ per trade
def one(c: dict, obs: list[dict], probe: dict | None) -> dict:
    day, qty, e15, t15 = c["opened_at"][:10], c["qty"], c["entry"]["price"], hhmmss(c["opened_at"])
    rows = stream(c, obs, probe)
    r_ = c["rule"]
    eod = (r_.get("shadow_v10") or {}).get("fill")
    after = c.get("after") or {}
    m = {"day": day, "symbol": c["symbol"], "type": c["instrument"], "strike": c["strike"], "qty": qty,
         "rows": len(rows), "probe_rows": sum(r["src"] == "probe" for r in rows),
         "e15_time": t15, "e15_price": e15, "x15_time": hhmmss(c["closed_at"]), "x15_price": c["exit"]["price"],
         "x15_reason": c["reason"].replace("fade_", ""), "net15": c["net_pnl"], "net15_pct": c["return_pct"],
         "dip15_1min_pct": first_min_dip(rows, t15, e15)}
    # the engine on the actual 09:15 entry (same execution assumptions as the 09:16 simulation); v12 checks the stop
    # and the trail only from 09:16, so rows before 09:16:00 are not used
    rp = exit_v12([r for r in rows if sec(r["t"]) >= max(math.floor(sec(t15)) + 1, sec(T16))], e15, after, eod)
    m.update({"replay15_reason": rp["reason"], "replay15_price": rp["price"], "replay15_time": rp["t"],
              "replay15_net": net(c, e15, rp["price"]) if rp["price"] else None})
    if t15 >= T16:
        m.update({"status": "unchanged", "e16_time": t15, "e16_price": e15, "e16_src": "actual", "e16_skipped": "",
                  "size_ok": True, "x16_reason": m["x15_reason"], "x16_price": m["x15_price"], "x16_time": m["x15_time"],
                  "x16_by": "actual", "net16": m["net15"], "net16_pct": m["net15_pct"], "dip16_1min_pct": m["dip15_1min_pct"],
                  "walk_same": "n/a", "stand_e16_price": None, "stand_net16": None})
        return m
    skipped, ent = [], None
    for r in rows:
        if T16 <= r["t"] <= T16_LAST + ".999":
            ok, why = eligible(r, day, qty)
            if ok:
                ent = r
                break
            skipped.append(f"{r['t'][:8]} {why}")
    m["e16_skipped"] = "; ".join(skipped[:3]) + (f" (+{len(skipped) - 3})" if len(skipped) > 3 else "")
    if ent is None:
        m.update({"status": "unavailable: no eligible quote 09:16-09:20", "e16_time": None, "e16_price": None})
        return m
    e16, t16 = ent["ask"], ent["t"]
    x = exit_v12([r for r in rows if sec(r["t"]) > sec(t16)], e16, after, eod)
    spot = (c.get("entry_quote") or {}).get("spot") or r_.get("spot_at_entry")
    pr = [r for r in (probe or {}).get("rows", []) if r[1] == c["symbol"] and r[3] == c["strike"] and r[0] <= t16]
    if pr and pr[-1][13]:
        spot = pr[-1][13]
    m.update({"e16_time": t16[:8], "e16_price": e16, "e16_src": ent["src"], "size_ok": (ent.get("ask_qty") or 0) >= qty,
              "e16_1s_source": ent["src"] == "probe" or ent.get("via") == "live best bid (1-s exit check)",
              "e16_vs_e15_pct": round((e16 / e15 - 1) * 100, 1), "dip16_1min_pct": first_min_dip(rows, t16, e16),
              "walk_same": walk_same(c, probe, t16, spot),
              "x16_reason": x["reason"], "x16_price": x["price"], "x16_time": (x["t"] or "")[:8] or None, "x16_by": x["by"],
              "x16_src": x["src"]})
    if x["price"] is None:
        m["status"] = "unavailable: exit " + x["by"]
        return m
    m["status"] = "available"
    m["net16"] = net(c, e16, x["price"])
    m["net16_pct"] = round(m["net16"] / (e16 * qty) * 100, 2)
    m["diff_net"] = round(m["net16"] - m["net15"], 2)
    m["exit_shift_min"] = round((sec(m["x16_time"] if x["t"] != "15:20" else "15:20:00") - sec(m["x15_time"])) / 60, 1)
    # standing-book variant: the book in force at 09:16:00 if the probe was polling this contract
    st_rows = [r for r in rows if r["src"] == "probe" and r["t"] <= T16]
    if st_rows and eligible(st_rows[-1], day, qty)[0]:
        s0 = st_rows[-1]
        xs = exit_v12([r for r in rows if sec(r["t"]) > sec(T16)], s0["ask"], after, eod)
        m["stand_e16_price"] = s0["ask"]
        m["stand_net16"] = net(c, s0["ask"], xs["price"]) if xs["price"] else None
    return m


# ------------------------------------------------------------------- the recorded 09:16 walk choice (from 2 Nov 2026)
def walk_choice(day: str, w16: dict | None, obs: list[dict], booked: dict[str, dict]) -> list[dict]:
    """The secondary analysis (PREREG): each signal's recorded 09:16 choice (data/walk_0916/<day>.json) bought at its
    recorded ask; v12 on its own follow rows (phase walk_0916) after the choice and before 15:20:00; else 15:20 at the
    bid of the last follow row at or before 15:20:00, when the follow reached 15:20. Paired with the booked trade."""
    out = []
    for sym, p in sorted(((w16 or {}).get("picks") or {}).items()):
        m = {"day": day, "symbol": sym, "w_status": p.get("status"), "w_time": (p.get("decided_at") or "")[:8] or None,
             "w_strike": p.get("strike"), "w_ask": p.get("ask"), "w_why": p.get("why") or p.get("last_why")}
        c = booked.get(sym)
        if c:
            m.update(strike=c["strike"], net15=c["net_pnl"], net15_pct=c["return_pct"],
                     x15_reason=c["reason"].replace("fade_", ""))
        out.append(m)
        if p.get("status") != "chosen":
            continue
        m["same_strike"] = (p["strike"] == c["strike"]) if c else None
        e, qty, t0, f = p["ask"], int(p["lot"]) * int(p.get("lots") or 1), p["decided_at"][:8], p.get("follow") or {}
        rows = sorted(({"t": hhmmss(r["t"]), "bid": r.get("bid"), "src": "obs-walk_0916"} for r in obs
                       if r.get("id") == p["id"] and r.get("phase") == "walk_0916"), key=lambda r: sec(r["t"]))
        m.update(w_qty=qty, w_rows=len(rows), w_follow_last=f.get("last"), w_kotak_polls=f.get("kotak_polls"))
        x = exit_v12([r for r in rows if sec(t0) < sec(r["t"]) < sec(EOD_AT)], e, {}, None)
        if x["price"] is None and (f.get("last") or "") >= EOD_AT:
            stand = [r for r in rows if sec(r["t"]) <= sec(EOD_AT)]        # the book standing at 15:20:00
            if stand and stand[-1]["bid"]:
                x = {"reason": "eod", "price": stand[-1]["bid"], "t": EOD_AT, "by": "rows", "src": "obs-walk_0916"}
        m.update(w_reason=x["reason"], w_exit=x["price"], w_exit_time=(x["t"] or "")[:8] or None, w_by=x["by"])
        if x["price"] is not None:
            m["w_net"] = net({"qty": qty, "instrument": p["side"]}, e, x["price"])
            m["w_net_pct"] = round(m["w_net"] / (e * qty) * 100, 2)
            if c:
                m["w_diff_pts"] = round(m["w_net_pct"] - c["return_pct"], 2)
    return out


# ------------------------------------------------------------------------------------------------ summaries
def summ(d: pd.DataFrame, net_col: str, pct_col: str, reason_col: str, label: str) -> dict:
    v = d.dropna(subset=[net_col])
    if v.empty:
        return {"method": label, "n": 0}
    w, l = v[v[net_col] > 0], v[v[net_col] < 0]
    cum = v.sort_values(["day", "e15_time"])[net_col].cumsum()
    return {"method": label, "n": len(v), "mean net %": round(v[pct_col].mean(), 2),
            "median net %": round(v[pct_col].median(), 2), "wins": len(w), "win %": round(len(w) / len(v) * 100, 1),
            "total net Rs": round(v[net_col].sum()), "avg win Rs": round(w[net_col].mean()) if len(w) else None,
            "avg loss Rs": round(l[net_col].mean()) if len(l) else None,
            "stop / trail / 15:20": f"{(v[reason_col] == 'stop').sum()} / {(v[reason_col] == 'trail').sum()} / "
                                    f"{v[reason_col].isin(['eod', 'eod (15:20)']).sum()}",
            "max drawdown Rs": round((cum - cum.cummax().clip(lower=0)).min())}


def block(d: pd.DataFrame, title: str) -> list[str]:
    a = d[d.status.isin(["available", "unchanged"])].copy()
    a["replay15_pct"] = a.replay15_net / (a.e15_price * a.qty) * 100
    rows = [summ(a, "net15", "net15_pct", "x15_reason", "09:15 actual (booked)"),
            summ(a, "replay15_net", "replay15_pct", "replay15_reason", "09:15 replayed (same engine)"),
            summ(a, "net16", "net16_pct", "x16_reason", "09:16 simulated")]
    out = [f"\n### {title}\n", f"Signals {len(d)}; available pairs {len(a)} "
           f"(changed {int((a.status == 'available').sum())}, unchanged {int((a.status == 'unchanged').sum())}); "
           f"unavailable {len(d) - len(a)}.\n", md_table(pd.DataFrame(rows))]
    if len(a) > 1:
        dif = (a.net16_pct - a.net15_pct)
        sd = stt.stdev(dif) if len(dif) > 1 else 0
        ch_ = a[a.status == "available"]
        out.append("\n" + md_table(pd.DataFrame([{
            "mean pts (net %)": round(dif.mean(), 2), "paired t (scale only)": round(dif.mean() / (sd / math.sqrt(len(dif))), 2) if sd else None,
            "09:16 minus 09:15 actual, total Rs": round((a.net16 - a.net15).sum()),
            "09:16 better / worse / same": f"{int((a.net16 > a.net15).sum())} / {int((a.net16 < a.net15).sum())} / {int((a.net16 == a.net15).sum())}",
            "09:16 minus 09:15 replayed, total Rs": round((a.net16 - a.replay15_net).sum()),
            "mean entry diff % (changed)": round(ch_.e16_vs_e15_pct.mean(), 1) if len(ch_) else None,
            "median 1-min dip 09:15 / 09:16 (changed)": f"{ch_.dip15_1min_pct.median()} / {ch_.dip16_1min_pct.median()}" if len(ch_) else None,
            "median exit shift min (changed)": ch_.exit_shift_min.median() if len(ch_) else None}])))
    return out


def decision(D: pd.DataFrame, W: pd.DataFrame) -> tuple[list[str], dict]:
    """The pre-registered decision (PREREG) on the fresh-book pairs, net % of the premium first and rupees after.
    Two fixed looks: look 1 uses the pairs up to the first trade day on which they reach N_DECIDE; only if that is
    INCONCLUSIVE, look 2 uses the pairs up to the day they reach N_FINAL. Before look 1 the numbers are information."""
    allp = D[(D.day >= FRESH_FROM) & D.status.isin(["available", "unchanged"])].copy()
    cum = allp.groupby("day").size().sort_index().cumsum()
    d1 = cum[cum >= N_DECIDE].index.min() if (cum >= N_DECIDE).any() else None
    d2 = cum[cum >= N_FINAL].index.min() if (cum >= N_FINAL).any() else None
    if d1 is None:
        return _judge(allp, D, W, 0, None)
    out, info = _judge(allp[allp.day <= d1], D, W, 1, d1)
    if info["verdict"].startswith("INCONCLUSIVE") and d2 is not None:
        out2, info = _judge(allp[allp.day <= d2], D, W, 2, d2)
        out += out2
    return out, info


def _judge(a: pd.DataFrame, D: pd.DataFrame, W: pd.DataFrame, look: int, upto: str | None) -> tuple[list[str], dict]:
    a = a.copy()
    n, days = len(a), int(a.day.nunique())
    head = f"look {look}, pairs to {upto}" if look else "before look 1"
    out = [f"\n## Pre-registered decision ({PREREG}), {head}\n",
           f"Fresh-book pairs (trade day >= {FRESH_FROM}): {n} on {days} days "
           f"(changed {int((a.status == 'available').sum())}, unchanged {int((a.status == 'unchanged').sum())}); "
           f"unavailable {int(((D.day >= FRESH_FROM) & D.status.str.startswith('unavailable')).sum())}.\n"]
    if n < 2:
        return out + ["Too few pairs to compute.\n"], {"verdict": "too few", "n": n}
    a["d_pts"] = a.net16_pct - a.net15_pct
    mean, t = float(a.d_pts.mean()), clustered_t(a.d_pts.tolist(), a.day.tolist())
    big = a.loc[a.d_pts.idxmax()]                       # the largest positive contributor
    rest = a.drop(index=big.name)
    avoided = int(((a.x15_reason == "stop") & (a.x16_reason != "stop")).sum())
    added = int(((a.x16_reason == "stop") & (a.x15_reason != "stop")).sum())
    chg = a[a.status == "available"]
    same = {(d, s) for d, s, v in zip(W.day, W.symbol, W.same_strike) if str(v) == "True"} if "same_strike" in W else set()
    c1 = chg[(chg.walk_same == "yes") | pd.Series([(d, s) in same for d, s in zip(chg.day, chg.symbol)], index=chg.index,
                                                  dtype=bool)]
    tcrit = round(float(student_t.ppf(0.975, days - 1)), 2) if days >= 2 else None    # small-cluster t, df = days - 1
    c2 = (chg.net16_pct - chg.replay15_net / (chg.e15_price * chg.qty) * 100).dropna()
    w = W[(W.day >= FRESH_FROM) & W.w_diff_pts.notna()] if len(W) and "w_diff_pts" in W else W.iloc[0:0]

    def sign(x, k, need):
        return "too few" if k < need else ("pass" if x > 0 else "fail")
    crit = [
        {"check": "P1 size: mean difference, pts of the premium", "value": round(mean, 2), "need": f">= +{P1_PTS:g}",
         "result": "pass" if mean >= P1_PTS else "fail"},
        {"check": "P2 reliability: date-clustered t (days)", "value": f"{t} ({days} days)",
         "need": f">= max({P2_T:g}, t-crit {tcrit}) on >= {P2_DAYS} days",
         "result": "pass" if t is not None and t >= max(P2_T, tcrit or 0) and days >= P2_DAYS else "fail"},
        {"check": f"P3 without the largest difference ({big.symbol} {big.day}, {big.d_pts:+.1f} pts)",
         "value": round(float(rest.d_pts.mean()), 2) if len(rest) else None, "need": f">= +{P3_PTS:g}",
         "result": "pass" if len(rest) and rest.d_pts.mean() >= P3_PTS else "fail"},
        {"check": "P4 stops avoided minus stops added", "value": f"{avoided} - {added} = {avoided - added}",
         "need": f">= {P4_STOPS}", "result": "pass" if avoided - added >= P4_STOPS else "fail"},
        {"check": "C1 same strike at 09:16: mean difference, pts", "value": round(float(c1.d_pts.mean()), 2) if len(c1) else None,
         "need": f"> 0 ({len(c1)} pairs, needs {C1_MIN})", "result": sign(c1.d_pts.mean() if len(c1) else 0, len(c1), C1_MIN)},
        {"check": "C2 vs the 09:15 trade replayed by the same engine, pts", "value": round(float(c2.mean()), 2) if len(c2) else None,
         "need": f"> 0 ({len(c2)} changed pairs, needs {C2_MIN})", "result": sign(c2.mean() if len(c2) else 0, len(c2), C2_MIN)},
        {"check": "C3 recorded walk choice vs booked, pts", "value": round(float(w.w_diff_pts.mean()), 2) if len(w) else None,
         "need": f"> 0 ({len(w)} pairs, needs {C3_MIN})", "result": sign(w.w_diff_pts.mean() if len(w) else 0, len(w), C3_MIN)}]
    ps, cs = [c["result"] for c in crit[:4]], [c["result"] for c in crit[4:]]
    if look == 0:
        verdict = f"NOT A DECISION: {n} fresh-book pairs (< {N_DECIDE}); the numbers are for information only"
    elif all(r == "pass" for r in ps) and "fail" not in cs:
        verdict = "PASS: the evidence supports a forward test of a 09:16 entry (a proposal; nothing changes without approval)"
    elif mean < CLOSE_PTS or t is None or t < CLOSE_T:
        verdict = "CLOSE: no material 09:16 effect; the 09:15 entry stays"
    elif look == 1:
        verdict = f"INCONCLUSIVE: one more re-run at {N_FINAL} fresh-book pairs, same rules"
    else:
        verdict = f"CLOSE: still not a pass at {N_FINAL} pairs (the last look); the 09:15 entry stays"
    out += [md_table(pd.DataFrame(crit)), "\n" + md_table(pd.DataFrame([{
        "median difference, pts": round(float(a.d_pts.median()), 2),
        "09:16 better / worse / same": f"{int((a.d_pts > 0).sum())} / {int((a.d_pts < 0).sum())} / {int((a.d_pts == 0).sum())}",
        "09:16 minus 09:15, total Rs (second: the stakes differ)": round(float((a.net16 - a.net15).sum()))}])),
        f"\n**Verdict:** {verdict}\n"]
    return out, {"verdict": verdict, "look": look, "upto": upto, "n": n, "days": days, "mean_pts": round(mean, 2), "t": t,
                 "criteria": {c["check"].split(" ")[0]: c["result"] for c in crit}}


def main() -> None:
    led, od, pdir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    stem = sys.argv[4] if len(sys.argv) > 4 else "S1_fade_0916_counterfactual"
    wdir = Path(sys.argv[5]) if len(sys.argv) > 5 else pdir.parent / "walk_0916"
    L = json.loads(led.read_text(encoding="utf-8"))
    v12 = [c for c in L["closed"] if (c.get("rule") or {}).get("version") == "v12" and "F" in c["rule"].get("arms", [])]
    ms = []
    for c in sorted(v12, key=lambda c: c["opened_at"]):
        day = c["opened_at"][:10]
        of, pf = od / f"{day}.jsonl", pdir / f"{day}.json"
        obs = [json.loads(x) for x in of.read_text(encoding="utf-8").splitlines() if x.strip()] if of.exists() else []
        probe = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else None
        ms.append(one(c, obs, probe))
    D = pd.DataFrame(ms)
    ok = (D.status == "available") & (D.size_ok == True) & (D.x16_by == "rows")  # noqa: E712
    D["comparable"] = (D.status == "unchanged") | (ok & (D.e16_src == "probe"))
    # added after the first run (methodology "Changes"): also accept the server's own 1-second exit-check row
    D["comparable_1s"] = (D.status == "unchanged") | (ok & (D.e16_1s_source == True))  # noqa: E712
    m2829 = D.day >= FRESH_FROM                         # was 28-29 Oct only (the first run had no later day)
    ws = []                                             # the recorded 09:16 walk choices (from 2 Nov 2026)
    for wf in sorted(wdir.glob("*.json")) if wdir.is_dir() else []:
        day = wf.stem
        of = od / f"{day}.jsonl"
        obs = [json.loads(x) for x in of.read_text(encoding="utf-8").splitlines() if x.strip()] if of.exists() else []
        booked = {c["symbol"]: c for c in v12 if c["opened_at"][:10] == day}
        ws += walk_choice(day, json.loads(wf.read_text(encoding="utf-8")), obs, booked)
    W = pd.DataFrame(ws)
    dec, verdict = decision(D, W)

    def biggest(mask):
        av = D[mask & (D.status == "available")]
        return av.loc[av.diff_net.abs().idxmax(), "symbol"] if len(av) else None
    big, big2829 = biggest(D.day >= "2026-10-27"), biggest(m2829)
    out = ["# S1 fade · 09:15 vs 09:16 entry counterfactual: tables (scanner/fade_entry_0916_cf.py)\n",
           f"Ledger saved_at {L.get('saved_at')}. Method: strategies/S1_fade_0916_entry_counterfactual.md. "
           "09:16 prices are OBSERVED asks; 09:16 exits are SIMULATED at observed bids (not fills).\n",
           *dec,
           "## Per trade\n",
           md_table(D[["day", "symbol", "type", "strike", "qty", "status", "e15_time", "e15_price", "x15_reason", "x15_time",
                       "x15_price", "net15", "e16_time", "e16_price", "e16_src", "size_ok", "walk_same", "x16_reason",
                       "x16_time", "x16_price", "x16_by", "net16", "diff_net", "replay15_reason", "replay15_net",
                       "dip15_1min_pct", "dip16_1min_pct", "comparable", "comparable_1s"]]),
           "\n## Skipped rows before the 09:16 entry (first 3)\n",
           md_table(D[D.e16_skipped.fillna("") != ""][["symbol", "e16_skipped"]]),
           "\n## Groups\n"]
    out += block(D[D.day >= "2026-10-27"], "All measured days (27 Oct on)")
    out += block(D, "All signals incl. ADANIENSOL (23 Oct)")
    out += block(D[m2829], f"Fresh books only ({FRESH_FROM} on)")
    out += block(D[D.day == "2026-10-27"], "27 Oct only (previous-day books)")
    out += block(D[D.day == "2026-10-23"], "23 Oct ADANIENSOL only")
    out += ["\n## Robustness\n"]
    if big:
        out += block(D[(D.day >= "2026-10-27") & (D.symbol != big)], f"27 Oct on, without the largest difference ({big})")
    if big2829:
        out += block(D[m2829 & (D.symbol != big2829)], f"Fresh books, without the largest difference ({big2829})")
    out += block(D[(D.day >= "2026-10-27") & D.comparable], "27 Oct on, valid comparable quotes only (as committed)")
    out += block(D[m2829 & D.comparable], "Fresh books, valid comparable quotes only (as committed)")
    out += block(D[(D.day >= "2026-10-27") & D.comparable_1s], "27 Oct on, comparable incl. 1-s exit-check rows (post hoc)")
    out += block(D[m2829 & D.comparable_1s], "Fresh books, comparable incl. 1-s exit-check rows (post hoc)")
    sb = D[D.stand_net16.notna()]
    out += ["\n### Standing-book variant (book in force at 09:16:00, probe-polled contracts)\n",
            md_table(sb[["day", "symbol", "e16_price", "stand_e16_price", "net16", "stand_net16", "net15"]]) if len(sb) else "none\n"]
    if len(W):
        cols = [c for c in ["day", "symbol", "w_status", "w_time", "w_strike", "strike", "same_strike", "w_ask", "w_qty",
                            "w_reason", "w_exit_time", "w_exit", "w_by", "w_net", "w_net_pct", "net15_pct", "w_diff_pts",
                            "w_rows", "w_follow_last", "w_kotak_polls", "w_why"] if c in W]
        out += ["\n## The recorded 09:16 walk choice (secondary, data/walk_0916)\n", md_table(W[cols])]
        W.to_csv(RES / f"{stem}_walk_choice.csv", index=False)
    (RES / f"{stem}.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    D.to_csv(RES / f"{stem}_trades.csv", index=False)
    print(f"{len(D)} signals; {int((D.status == 'available').sum())} changed, {int((D.status == 'unchanged').sum())} "
          f"unchanged, {int(D.status.str.startswith('unavailable').sum())} unavailable; largest diff {big}")
    print(f"decision: {verdict['verdict']}")


if __name__ == "__main__":
    main()
