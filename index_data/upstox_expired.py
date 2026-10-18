"""§9 Upstox expired-contract backfill: 1-minute candles (with OI) of EXPIRED NIFTY / SENSEX / BANKNIFTY options,
written into the recorder's layout (STORE/options_1m/<underlying>/<expiry>/<date>.parquet, source 'upstox').

    UPSTOX_ANALYTICS_TOKEN=... INDEX_STORE=... python -m index_data.upstox_expired --underlying NIFTY
        [--from 2022-01-01] [--max-minutes 320] [--estimate-only]

Per underlying: the expired expiries from 2022-01-01 (the API lists NIFTY from 2024-10-03) to the last one; per expiry,
the expired option contracts; strikes within ±5 % of the underlying's close at the fetch window's start (the
contract's first listed day is not given by the API: the window starts 28 days before a weekly's expiry and 90 days
before a monthly's, and candles before listing come back empty); 1-minute candles over that window in 28-day calls.
Restart-safe: STORE/upstox_done.json lists the instrument keys already fetched. 429 -> backoff; UDAPI1149 -> stop.
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import date, timedelta

import pandas as pd

from .common import SMALL, STORE, candles_frame, read_json, upsert_parquet, write_json
from .upstox_common import UNDERLYING_KEY, PlusPlanRequired, Upstox

log = logging.getLogger("index_data.upstox_expired")
BAND = 0.05
WINDOW_DAYS = 28


def expiries(u: Upstox, under: str, start: str) -> list[str]:
    b = u.get("/v2/expired-instruments/expiries", {"instrument_key": UNDERLYING_KEY[under]})
    return sorted(e for e in (b.get("data") or []) if e >= start)


def contracts(u: Upstox, under: str, expiry: str) -> list[dict]:
    b = u.get("/v2/expired-instruments/option/contract", {"instrument_key": UNDERLYING_KEY[under], "expiry_date": expiry})
    return b.get("data") or []


def daily_closes(u: Upstox, under: str, start: date, end: date) -> pd.Series:
    out, a = [], start
    while a <= end:
        b = min(end, a + timedelta(days=360))
        body = u.get(f"/v3/historical-candle/{u.q(UNDERLYING_KEY[under])}/days/1/{b}/{a}")
        out += (body.get("data") or {}).get("candles") or []
        a = b + timedelta(days=1)
    f = candles_frame(out)
    return pd.Series(f["close"].values, index=f["timestamp"].dt.strftime("%Y-%m-%d")).sort_index()


def is_monthly(expiry: str, all_exps: list[str]) -> bool:
    same = [e for e in all_exps if e[:7] == expiry[:7]]
    return expiry == max(same)


def window(expiry: str, monthly: bool) -> tuple[date, date]:
    e = date.fromisoformat(expiry)
    return e - timedelta(days=90 if monthly else WINDOW_DAYS), e


def pick(cons: list[dict], ref: float) -> list[dict]:
    return [c for c in cons if c.get("instrument_type") in ("CE", "PE")
            and abs(float(c.get("strike_price") or 0) - ref) <= BAND * ref]


def fetch(u: Upstox, c: dict, a: date, b: date) -> pd.DataFrame:
    rows, s = [], a
    while s <= b:
        t = min(b, s + timedelta(days=WINDOW_DAYS - 1))
        body = u.get(f"/v2/expired-instruments/historical-candle/{u.q(c['instrument_key'])}/1minute/{t}/{s}")
        rows += (body.get("data") or {}).get("candles") or []
        s = t + timedelta(days=1)
    return candles_frame(rows)


def run(under: str, start: str, max_minutes: float, estimate_only: bool, store=STORE) -> dict:
    t0, u = time.monotonic(), Upstox()
    done_file = store / "upstox_done.json"
    done = set(read_json(done_file, []))
    exps = expiries(u, under, start)
    known = read_json(store / "upstox_expiries.json", {}) or {}
    write_json(store / "upstox_expiries.json", {**known, under: exps})        # for the expiry calendar
    if not exps:
        return {"underlying": under, "expiries": 0}
    closes = daily_closes(u, under, date.fromisoformat(exps[0]) - timedelta(days=95), date.fromisoformat(exps[-1]))
    plan, n_calls = [], 0
    for e in exps:
        mon = is_monthly(e, exps)
        a, b = window(e, mon)
        ref = closes[closes.index <= a.isoformat()]
        ref = float(ref.iloc[-1]) if len(ref) else float(closes.iloc[0])
        plan.append((e, mon, a, b, ref))
    est_contracts = {"NIFTY": 92, "BANKNIFTY": 112, "SENSEX": 148}.get(under, 100)
    est_calls = sum(est_contracts * (1 + (b - a).days // WINDOW_DAYS) for _, _, a, b, _ in plan) + len(plan)
    print(f"{under}: {len(exps)} expired expiries {exps[0]} .. {exps[-1]}; estimate ~{est_calls} calls, "
          f"~{est_calls / 0.53 / 3600:.1f} h at the 1,000-per-30-min limit", flush=True)
    res = {"underlying": under, "expiries": len(exps), "first": exps[0], "last": exps[-1], "estimate_calls": est_calls,
           "contracts_done": 0, "contracts_skipped": 0, "rows": 0, "stopped": None}
    if estimate_only:
        return res
    try:
        for e, mon, a, b, ref in plan:
            if time.monotonic() - t0 > max_minutes * 60:
                res["stopped"] = "time budget reached (restart to continue)"
                break
            for c in pick(contracts(u, under, e), ref):
                key = c["instrument_key"]
                if key in done:
                    res["contracts_skipped"] += 1
                    continue
                f = fetch(u, c, a, b)
                if len(f):
                    f = f[f["timestamp"].dt.strftime("%H:%M") >= "09:15"]
                    f.insert(1, "token", str(c.get("exchange_token")))
                    f.insert(2, "trading_symbol", c.get("trading_symbol"))
                    f.insert(3, "strike", float(c.get("strike_price")))
                    f.insert(4, "option_type", c.get("instrument_type"))
                    f["source"] = "upstox"
                    for d, g in f.groupby(f["timestamp"].dt.date):
                        upsert_parquet(store / "options_1m" / under / e / f"{d.isoformat()}.parquet", g,
                                       ["source", "token", "timestamp"])
                    res["rows"] += len(f)
                done.add(key)
                res["contracts_done"] += 1
                if res["contracts_done"] % 50 == 0:
                    write_json(done_file, sorted(done))
                    log.info("%s %s: %d contracts, %d rows, %d calls", under, e, res["contracts_done"], res["rows"], u.calls)
    except PlusPlanRequired as exc:
        res["stopped"] = f"UDAPI1149 (Upstox Plus required): {exc}"
    finally:
        write_json(done_file, sorted(done))
    res.update(calls=u.calls, runtime_s=round(time.monotonic() - t0))
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description="Upstox expired index-option backfill (1-minute)")
    ap.add_argument("--underlying", default="NIFTY", choices=sorted(UNDERLYING_KEY))
    ap.add_argument("--from", dest="start", default="2022-01-01")
    ap.add_argument("--max-minutes", type=float, default=320)
    ap.add_argument("--estimate-only", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    res = run(a.underlying, a.start, a.max_minutes, a.estimate_only)
    st = read_json(SMALL / "status.json", {}) or {}
    up = st.get("upstox_expired") or {}
    up[a.underlying] = res
    write_json(SMALL / "status.json", {**st, "upstox_expired": up})
    print(res)
    if res.get("stopped", "") and str(res["stopped"]).startswith("UDAPI1149"):
        raise SystemExit(res["stopped"])


if __name__ == "__main__":
    main()
