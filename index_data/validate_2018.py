"""Checks the 2018-2020 NIFTY / BANKNIFTY daily bhavcopy before it joins the store (Workstream A step 1).

    python -m index_data.validate_2018 <new options_daily dir> <store options_daily dir> <index_close_daily.parquet>

Prints: files and date range; schema and dtypes against the stored 2021-01 file; sessions against NSE's official index
close days (every session present, no extra days); duplicate keys; non-positive or missing closes; per-session NIFTY
expiries and whether a liquid ATM pair exists (both legs >= 100 contracts); the 2020-12 / 2021-01 seam.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

KEYS = ["TradDt", "FinInstrmTp", "XpryDt", "StrkPric", "OptnTp"]


def main(new_dir: str, store_dir: str, closes: str) -> None:
    new, store = Path(new_dir), Path(store_dir)
    ref = pd.read_parquet(store / "NIFTY" / "2021-01.parquet")
    ic = pd.read_parquet(closes)
    nse_days = set(ic.loc[(ic["index"] == "NIFTY50") & (ic["date"] >= "2018-01-01") & (ic["date"] <= "2020-12-31"), "date"])
    for u in ("NIFTY", "BANKNIFTY"):
        files = sorted((new / u).glob("*.parquet"))
        d = pd.concat(pd.read_parquet(f) for f in files)
        print(f"\n== {u}: {len(files)} files {files[0].stem} → {files[-1].stem}, {len(d):,} rows")
        print("schema same as stored 2021-01:", list(d.columns) == list(ref.columns),
              "| dtype mismatches:", {c: (str(d[c].dtype), str(ref[c].dtype)) for c in ref.columns if str(d[c].dtype) != str(ref[c].dtype)})
        days = set(d["TradDt"])
        print(f"sessions {len(days)} ({min(days)} → {max(days)}); NSE index-close days {len(nse_days)}; "
              f"missing vs NSE: {sorted(nse_days - days)}; extra: {sorted(days - nse_days)}")
        print("duplicate keys:", int(d.duplicated(KEYS).sum()))
        o = d[d["FinInstrmTp"] == "IDO"]
        print(f"options rows {len(o):,}; ClsPric missing {int(o['ClsPric'].isna().sum())}, <= 0 {int((o['ClsPric'] <= 0).sum())}; "
              f"traded rows (vol > 0) {(o['TtlTradgVol'] > 0).mean() * 100:.0f} %")
        print("futures sessions:", d.loc[d["FinInstrmTp"] == "IDF", "TradDt"].nunique())
        if u == "NIFTY":
            liq = o[o["TtlTradgVol"] >= 100]
            pairs = liq.groupby(["TradDt", "XpryDt", "StrkPric"])["OptnTp"].nunique()
            ok_days = set(pairs[pairs == 2].reset_index()["TradDt"])
            print(f"sessions with a liquid CE+PE pair on some expiry: {len(ok_days)} / {len(days)}; without: {sorted(days - ok_days)[:10]}")
            ne = o.groupby("TradDt")["XpryDt"].nunique()
            print(f"expiries listed per session: min {ne.min()}, median {int(ne.median())}, max {ne.max()}")
            wk = sorted(set(o["XpryDt"]))
            print(f"first expiries: {wk[:3]}; first weekly-looking (non-last-Thursday) expiry:",
                  next((e for e in wk if pd.Timestamp(e) + pd.Timedelta(days=7) <= pd.Timestamp(e).to_period('M').end_time.normalize()
                        and pd.Timestamp(e).year >= 2019), None))
    s20 = pd.read_parquet(new / "NIFTY" / "2020-12.parquet")
    s21 = ref
    print(f"\nseam: last 2020 session {s20['TradDt'].max()}, first stored 2021 session {s21['TradDt'].min()}; "
          f"NIFTY lot in stored 2021-01 rows: {sorted(s21['NewBrdLotQty'].dropna().unique())[:3] or 'empty (old format)'}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
