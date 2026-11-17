"""Writes DATA_DOWNLOAD_MANIFEST.json: sha256 prefixes, row counts and sources of every downloaded file (raw data is git-ignored)."""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RI = os.path.dirname(HERE)
EX = os.path.join(RI, "external_data")
man = {"downloaded": "2026-11-17", "note": "raw data git-ignored; scripts/fetch_external.py re-fetches it", "files": {}}
for root, _, fs in os.walk(EX):
    for f in sorted(fs):
        if f.startswith("progress_"):
            continue
        p = os.path.join(root, f)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
        try:
            n = sum(1 for _ in open(p, encoding="utf-8")) - 1
        except Exception:
            n = None
        man["files"][os.path.relpath(p, EX).replace(os.sep, "/")] = {"sha256_16": h, "rows": n, "bytes": os.path.getsize(p)}
man["sources"] = {
    "gift_bhavcopy_futures.csv": "https://www.nseix.com/api/content/daily_report/G_T_Bhavcopy_FO_DDMMYY.CSV (NSE International Exchange, public)",
    "nse_index_closes.csv": "https://nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv (NSE, public)",
    "nse_breadth_daily.csv": "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv aggregated per day (NSE, public)",
    "yahoo/*": "https://query1.finance.yahoo.com/v8/finance/chart/<symbol> (Yahoo Finance public chart API; quality caveats in DOWNLOAD_QUALITY_CHECKS.md)",
    "fii_dii_cash_stockezee.csv": "https://www.stockezee.com/fii-dii-historical-data (third-party archive, extracted through the page's month selector on 2026-11-17; verified against NSE's own combined table on 2026-11-17 only; September 2026 absent at source)",
    "not_obtained": "FII / DII cash flows before 2025-12 and for 2026-09 (NSE serves only the latest day; NSDL archive needs form scraping; no verified bulk source found); GIFT 09:00 level and intraday history; timestamped news archive; NIFTY 50 historical constituents"}
json.dump(man, open(os.path.join(RI, "DATA_DOWNLOAD_MANIFEST.json"), "w"), indent=1)
print(len(man["files"]), "files hashed")
