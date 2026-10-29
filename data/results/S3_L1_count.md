# S3 L1 step 2: India VIX above 22 and rising, 2018-01 -> 2025-09 (2026-10-29)

Definition (fixed before counting, closes only): VIX close(d) > 22.00 and VIX close(d) > VIX close(d - 5 sessions).
Source of record: NSE official India VIX close (`ind_close_all`), index-data commit above. `python -m scanner.s3_l1 count`:

```
sessions 2018-01-01 → 2025-09-30: 1913
qualifying days (NSE official VIX): 146  by year: {2019: 16, 2020: 59, 2021: 34, 2022: 30, 2024: 6, 2025: 1}
qualifying days (vix_daily, yfinance): 145; only official: [datetime.date(2021, 1, 27)]; only yfinance: []
VIX official vs yfinance on 1896 common days: max |diff| 1.010, >0.05 on 3 days
sessions without official VIX: []
```

Gate: at least 30 qualifying days -> 146, so L1 research continues. No option price was read for this count.
