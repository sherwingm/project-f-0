"""Read-only probe: does Upstox's expired-instruments API cover STOCK options (not only indices), with 1-minute candles?

    UPSTOX_ANALYTICS_TOKEN=... python -m index_data.probe_stock_expired

For a few stocks: the expired expiries listed, the put contracts of one 2025 monthly expiry, and one contract's 1-minute
candles on its last days. Prints only (nothing is saved). Asked for by the S1 v10 Rs 0.50-1 study (minute data for a
trailing stop).
"""
from __future__ import annotations

from datetime import date, timedelta

from .upstox_common import Upstox

STOCKS = {"FEDERALBNK": "INE171A01029", "YESBANK": "INE528G01035", "NHPC": "INE848E01016"}


def main() -> None:
    u = Upstox()
    for sym, isin in STOCKS.items():
        key = f"NSE_EQ|{isin}"
        try:
            ex = (u.get("/v2/expired-instruments/expiries", {"instrument_key": key}).get("data")) or []
        except BaseException as exc:                             # noqa: BLE001 - a probe reports every failure
            print(f"{sym}: expiries error: {exc}")
            continue
        print(f"{sym}: {len(ex)} expired expiries, {ex[:2]} .. {ex[-2:]}")
        pick = next((e for e in ex if e.startswith("2025-0")), ex[0] if ex else None)
        if not pick:
            continue
        try:
            cs = (u.get("/v2/expired-instruments/option/contract",
                        {"instrument_key": key, "expiry_date": pick}).get("data")) or []
        except BaseException as exc:                             # noqa: BLE001
            print(f"{sym} {pick}: contracts error: {exc}")
            continue
        puts = [c for c in cs if c.get("instrument_type") == "PE"]
        print(f"{sym} {pick}: {len(cs)} contracts ({len(puts)} puts); sample: "
              f"{[(c.get('trading_symbol'), c.get('instrument_key')) for c in puts[:2]]}")
        if not puts:
            continue
        c = puts[len(puts) // 2]
        to, frm = date.fromisoformat(pick), date.fromisoformat(pick) - timedelta(days=4)
        try:
            rows = ((u.get(f"/v2/expired-instruments/historical-candle/{u.q(c['instrument_key'])}/1minute/{to}/{frm}")
                     .get("data") or {}).get("candles")) or []
        except BaseException as exc:                             # noqa: BLE001
            print(f"{sym} {c.get('trading_symbol')}: candles error: {exc}")
            continue
        print(f"{sym} {c.get('trading_symbol')}: {len(rows)} one-minute candles {frm} .. {to}; "
              f"first {rows[-1] if rows else None}; last {rows[0] if rows else None}")


if __name__ == "__main__":
    main()
