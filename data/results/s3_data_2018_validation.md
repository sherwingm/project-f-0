# NIFTY / BANKNIFTY daily bhavcopy 2018-01 -> 2020-12: download and validation (2026-10-29)

Downloaded with `python -m index_data.bhavcopy_ohlc --from 2018-01-01 --to 2020-12-31` (the same code as the 2021+ store):
737 sessions fetched + 3 from a first test run = 740, 44 weekdays returned 404 (exchange holidays), 0 errors, 3,565,998 index rows
across all indices (only NIFTY and BANKNIFTY are stored). Pushed to the `index-data` branch as commit 5cffec2f (72 monthly files).
Trading days checked against NSE official index-close files (`index_data/index_close.py`).

Output of `python -m index_data.validate_2018`:

```

== NIFTY: 36 files 2018-01 → 2020-12, 2,070,399 rows
schema same as stored 2021-01: True | dtype mismatches: {}
sessions 740 (2018-01-01 → 2020-12-31); NSE index-close days 740; missing vs NSE: []; extra: []
duplicate keys: 0
options rows 2,068,179; ClsPric missing 0, <= 0 0; traded rows (vol > 0) 13 %
futures sessions: 740
sessions with a liquid CE+PE pair on some expiry: 740 / 740; without: []
expiries listed per session: min 14, median 21, max 21
first expiries: ['2018-01-25', '2018-02-22', '2018-03-28']; first weekly-looking (non-last-Thursday) expiry: 2019-02-14

== BANKNIFTY: 36 files 2018-01 → 2020-12, 1,019,814 rows
schema same as stored 2021-01: True | dtype mismatches: {}
sessions 740 (2018-01-01 → 2020-12-31); NSE index-close days 740; missing vs NSE: []; extra: []
duplicate keys: 0
options rows 1,017,594; ClsPric missing 0, <= 0 0; traded rows (vol > 0) 19 %
futures sessions: 740

seam: last 2020 session 2020-12-31, first stored 2021 session 2021-01-01; NIFTY lot in stored 2021-01 rows: empty (old format)
```

Notes: 13 % of NIFTY option rows traded (vol > 0); the rest are listed far strikes with a carried price, which the
studies never use (they require volume). Lot (NewBrdLotQty) is empty in old-format files; studies take it from NSE
circular 28/2021 (75, then 50 for expiries from 2021-07-29).
