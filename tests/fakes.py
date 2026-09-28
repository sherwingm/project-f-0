"""Test doubles: a fake Kotak Neo SDK client that answers with the documented payloads, and a
scrip master loaded from in-memory frames instead of Kotak's daily CSVs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from server.kotak import EPOCH_OFFSET, KotakProvider, KotakSession

IST = timezone(timedelta(hours=5, minutes=30))
EXPIRY = "2026-09-29"


def kotak_expiry(iso: str) -> int:
    """Scrip-master pExpiryDate for an ISO date (Kotak's epoch offset undone)."""
    d = datetime.strptime(iso, "%Y-%m-%d").replace(hour=15, minute=30, tzinfo=IST)
    return int(d.timestamp()) - EPOCH_OFFSET


def depth(buy: list[tuple[str, str]], sell: list[tuple[str, str]]) -> dict:
    lv = lambda p, q: {"price": p, "quantity": q, "orders": "1"}
    return {"buy": [lv(p, q) for p, q in buy], "sell": [lv(p, q) for p, q in sell]}


def kotak_quote(segment: str, token: str, symbol: str, ltp: str, oi: str = "0", prev_close: str = "0",
                dep: dict | None = None) -> dict:
    return {"exchange_token": token, "display_symbol": symbol, "exchange": segment, "ltp": ltp,
            "last_volume": "30043533", "open_int": oi, "lstup_time": "1790150400",
            "ohlc": {"open": ltp, "high": ltp, "low": ltp, "close": prev_close}, "depth": dep or {"buy": [], "sell": []}}


class FakeNeo:
    """quotes() returns the book entries for the requested tokens, as Kotak's REST API does."""

    def __init__(self, book: dict[str, dict]):
        self.book = book
        self.calls: list[list[dict]] = []

    def quotes(self, instrument_tokens=None, quote_type=None):
        self.calls.append(instrument_tokens)
        if len(instrument_tokens) >= 50:                  # the live API refuses 50 (checked 2026-09-28)
            return {"fault": {"code": "400", "description": "Please set the Neo symbol max value to 50."}}
        return [self.book[i["instrument_token"]] for i in instrument_tokens if i["instrument_token"] in self.book]

    def option_chain(self, **kwargs):
        return {"data": {}}


def reliance_book() -> dict[str, dict]:
    return {
        "2885": kotak_quote("nse_cm", "2885", "RELIANCE-EQ", "1243.9000", prev_close="1226.4000",
                            dep=depth([("1243.8500", "1733"), ("1243.8000", "900"), ("0", "0")],
                                      [("1243.9500", "550"), ("1244.0000", "1200")])),
        "35001": kotak_quote("nse_fo", "35001", "RELIANCE26SEPFUT", "1248.1000", oi="12345678",
                             dep=depth([("1248.0000", "1000"), ("1247.9000", "1500")],
                                       [("1248.2000", "500"), ("1248.3000", "2000"), ("1248.2500", "750")])),
        "40001": kotak_quote("nse_fo", "40001", "RELIANCE26SEP1300CE", "4.1000", oi="2500000",
                             dep=depth([("4.0500", "1500")], [("4.2000", "2000")])),
    }


def kotak_provider(book: dict[str, dict] | None = None) -> tuple[KotakProvider, FakeNeo]:
    session = KotakSession("test-consumer-key")
    fake = FakeNeo(book or reliance_book())
    session._client = fake
    p = KotakProvider(session, chain_calls_per_poll=0)
    p.master.ingest_cm(pd.DataFrame([{"pSymbol": "2885", "pTrdSymbol": "RELIANCE-EQ"}]))
    exp = kotak_expiry(EXPIRY)
    fo = [
        {"pSymbol": "35001", "pSymbolName": "RELIANCE", "pTrdSymbol": "RELIANCE26SEPFUT", "pOptionType": "XX",
         "pInstType": "FUTSTK", "lLotSize": 500, "dStrikePrice;": -1, "pExpiryDate": exp},
        {"pSymbol": "40001", "pSymbolName": "RELIANCE", "pTrdSymbol": "RELIANCE26SEP1300CE", "pOptionType": "CE",
         "pInstType": "OPTSTK", "lLotSize": 500, "dStrikePrice;": 130000, "pExpiryDate": exp},
    ]
    p.master.ingest_fo(pd.DataFrame(fo))
    p.master.loaded = True
    return p, fake
