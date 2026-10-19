"""Read-only probe: can Upstox or Kotak give 1-minute candles for STOCK options that expired before Oct 2024?

    UPSTOX_ANALYTICS_TOKEN=... KOTAK_CONSUMER_KEY=... python -m index_data.probe_old_options

The docs (read 2026-10-19) leave three questions open; each check prints what came back. Prints only, saves nothing.
  U1  Upstox expired option contracts for an expiry NOT in its list (FEDERALBNK 2024-09-26, 2023-01-25).
  U2  Upstox v3 historical candles (minutes "available from January, 2022") for an expired key it does list
      (FEDERALBNK, Oct 2024), in the expired-key form and the bare form.
  U3  Upstox expired candles for a key built from NSE's own token of a Sep 2024 contract (NSE UDiFF bhavcopy
      FinInstrmId), in case the expiry list is shorter than the data.
  K1  Kotak historical_data for the same NSE tokens (an Oct 2024 contract Upstox lists, and the Sep 2024 one).
"""
from __future__ import annotations

import io
import zipfile
from datetime import date

import pandas as pd
import requests

from .upstox_common import Upstox

ISIN = "INE171A01029"                                            # FEDERALBNK
UDIFF = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv.zip"
NSE_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*", "Referer": "https://www.nseindia.com/"}


def show(label: str, fn) -> object:
    try:
        out = fn()
        print(f"[{label}] {out if not isinstance(out, list) else f'{len(out)} rows; first {out[:1]}; last {out[-1:]}'}")
        return out
    except Exception as exc:                                     # noqa: BLE001 - a probe reports every failure
        print(f"[{label}] ERROR {str(exc)[:300]}")
        return None


def nse_token(day: date, sym: str, expiry: str, side: str, near: float) -> tuple[str, float] | None:
    """NSE's FinInstrmId for `sym`'s `side` option of `expiry` nearest `near`, from that day's UDiFF bhavcopy."""
    r = requests.get(UDIFF.format(ymd=day.strftime("%Y%m%d")), headers=NSE_HEADERS, timeout=60)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        df = pd.read_csv(zf.open(zf.namelist()[0]))
    df = df[(df["TckrSymb"] == sym) & (df["OptnTp"] == side) & (df["XpryDt"].astype(str).str[:10] == expiry)]
    row = df.iloc[(df["StrkPric"] - near).abs().argsort().iloc[0]]
    return str(int(row["FinInstrmId"])), float(row["StrkPric"])


def main() -> None:
    u = Upstox()
    key = f"NSE_EQ|{ISIN}"
    for exp in ("2024-09-26", "2023-01-25"):
        show(f"U1 contracts {exp}", lambda e=exp: len((u.get("/v2/expired-instruments/option/contract",
                                                             {"instrument_key": key, "expiry_date": e}).get("data")) or []))
    oct_ = (u.get("/v2/expired-instruments/option/contract", {"instrument_key": key, "expiry_date": "2024-10-31"})
            .get("data")) or []
    c = next((x for x in oct_ if x.get("instrument_type") == "PE" and abs(float(x.get("strike_price", 0)) - 200) < 1e-6),
             oct_[0] if oct_ else None)
    print("Oct 2024 contract:", c and (c.get("trading_symbol"), c.get("instrument_key"), c.get("exchange_token")))
    if c:
        ek = c["instrument_key"]
        bare = "|".join(ek.split("|")[:2])
        for k_ in (ek, bare):
            show(f"U2 v3 minutes {k_}", lambda k_=k_: ((u.get(f"/v3/historical-candle/{u.q(k_)}/minutes/1/2024-10-25/2024-10-21")
                                                         .get("data") or {}).get("candles") or []))
    tok = show("NSE token, FEDERALBNK Sep 2024 PE near 190", lambda: nse_token(date(2024, 9, 2), "FEDERALBNK",
                                                                                "2024-09-26", "PE", 190))
    if tok:
        built = f"NSE_FO|{tok[0]}|26-09-2024"
        show(f"U3 expired candles {built}", lambda: ((u.get(f"/v2/expired-instruments/historical-candle/{u.q(built)}/"
                                                           "1minute/2024-09-03/2024-09-02").get("data") or {}).get("candles") or []))
        show(f"U3 v3 minutes NSE_FO|{tok[0]}", lambda: ((u.get(f"/v3/historical-candle/{u.q('NSE_FO|' + tok[0])}/minutes/1/"
                                                              "2024-09-03/2024-09-02").get("data") or {}).get("candles") or []))
    try:
        from .common import Kotak
        k = Kotak()
    except BaseException as exc:                                 # noqa: BLE001
        print("[K] no Kotak client:", str(exc)[:200])
        return
    if c and c.get("exchange_token"):
        show(f"K1 Kotak nse_fo|{c['exchange_token']} (Oct 2024)", lambda: k.history(f"nse_fo|{c['exchange_token']}",
                                                                                   "1min", "2024-10-21", "2024-10-25"))
    if tok:
        show(f"K1 Kotak nse_fo|{tok[0]} (Sep 2024)", lambda: k.history(f"nse_fo|{tok[0]}", "1min", "2024-09-02", "2024-09-03"))
    show("K control: FEDERALBNK equity 1min 2024-09-02", lambda: k.history("nse_cm|FEDERALBNK-EQ", "1min", "2024-09-02",
                                                                          "2024-09-02"))


if __name__ == "__main__":
    main()
