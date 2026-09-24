"""eod2 file names: renamed NSE symbols map to the file eod2 keeps their history under; a 404 is logged once."""
import logging

import pytest
import requests

from scanner import equity
from scanner.equity import EOD2_ALIASES, eod2_filename, load_symbol

CSV = "Date,Open,High,Low,Close,Volume,Series\n2026-09-18,1,1,1,395.0,10,EQ\n"


class Resp:
    def __init__(self, status, text=""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error")


def test_renamed_symbols_use_the_new_file_and_others_are_unchanged():
    assert eod2_filename("TATAMOTORS") == "tmpv" and eod2_filename("LTIM") == "ltm"
    assert eod2_filename("MCDOWELL-N") == "unitdspr" and eod2_filename("L&TFH") == "ltf"
    assert eod2_filename("M&M") == "m&m" and eod2_filename("BAJAJ-AUTO") == "bajaj-auto"
    assert "HDFC" not in EOD2_ALIASES and "IDFC" not in EOD2_ALIASES            # mergers, not renames


def test_alias_reads_the_local_file(tmp_path):
    (tmp_path / "tmpv.csv").write_text(CSV, encoding="utf-8")
    assert float(load_symbol("TATAMOTORS", tmp_path)["Close"].iloc[-1]) == 395.0


def test_a_404_is_logged_once_per_symbol_and_still_raises(tmp_path, monkeypatch, caplog):
    urls = []
    monkeypatch.setattr(equity.requests, "get", lambda url, timeout: urls.append(url) or Resp(404))
    monkeypatch.setattr(equity, "_MISSING", set())
    with caplog.at_level(logging.WARNING, logger="scanner.equity"):
        for _ in range(2):
            with pytest.raises(requests.HTTPError):
                load_symbol("GONE", tmp_path)
    assert urls[0].endswith("/daily/gone.csv") and len(urls) == 2
    hits = [r.getMessage() for r in caplog.records if "GONE" in r.getMessage()]
    assert len(hits) == 1 and "EOD2_ALIASES" in hits[0]


def test_alias_is_fetched_under_the_new_name(tmp_path, monkeypatch):
    urls = []
    monkeypatch.setattr(equity.requests, "get", lambda url, timeout: urls.append(url) or Resp(200, CSV))
    load_symbol("LTIM", tmp_path)
    assert urls == [equity.RAW_BASE.format(name="ltm")] and (tmp_path / "ltm.csv").exists()
