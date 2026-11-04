# G1 with the datasheet's bucket filters (in-sample, 2024-10 → 2026-10)

Skip = no trade; double = 2 lots. Return on ₹ paid = total ₹ ÷ total premium paid. t on ₹ a lot per trade.

## Each filter alone, then together

| Version | Trades | Lots | Return on ₹ paid | Mean % a trade | t | Won | Total ₹ | Max drawdown | Worst trade | Year 1 / year 2 |
|---|---|---|---|---|---|---|---|---|---|---|
| G1 as registered (1 lot) | 259 | 259 | +5.5 % | +8.4 % | 1.09 | 42 % | ₹122,592 | ₹-76,224 | ₹-13,324 | +6.9 % / +4.3 % |
| skip day-1 gap ≥ +0.3 % | 207 | 207 | +12.1 % | +13.2 % | 1.99 | 46 % | ₹210,692 | ₹-40,400 | ₹-13,324 | +10.8 % / +13.3 % |
| skip OR width 0.5-0.8 % | 215 | 215 | +12.5 % | +13.3 % | 2.14 | 46 % | ₹221,806 | ₹-49,132 | ₹-13,324 | +15.2 % / +9.9 % |
| skip VIX ≥ 17 | 218 | 218 | +8.1 % | +10.5 % | 1.50 | 43 % | ₹136,421 | ₹-63,761 | ₹-8,756 | +8.6 % / +7.5 % |
| double signal 09:45-11:29 | 259 | 329 | +6.9 % | +8.4 % | 1.09 | 42 % | ₹198,034 | ₹-102,717 | ₹-26,649 | +11.2 % / +3.5 % |
| double VIX 12-14 | 259 | 328 | +8.4 % | +8.4 % | 1.09 | 42 % | ₹233,418 | ₹-91,765 | ₹-13,324 | +10.7 % / +6.3 % |
| skip all three | 154 | 154 | +17.9 % | +18.3 % | 2.56 | 50 % | ₹209,225 | ₹-31,108 | ₹-6,359 | +21.0 % / +14.6 % |
| double either | 259 | 383 | +8.3 % | +8.4 % | 1.09 | 42 % | ₹271,229 | ₹-101,249 | ₹-26,649 | +10.7 % / +6.3 % |
| skip all three + double either | 154 | 239 | +21.9 % | +18.3 % | 2.56 | 50 % | ₹398,266 | ₹-40,019 | ₹-12,415 | +26.7 % / +17.5 % |

## Honest check: buckets picked on year 1 (2024-10 → 2025-09) only, applied to year 2

Rule: a bucket with ≥ 15 year-1 trades and a negative year-1 mean is skipped; one above +15 % is doubled.

- double Day-1 gap at open % [-0.3, 0.0) (year 1 +21.1 %, 36)
- skip Day-1 gap at open % [0.3, 9.0) (year 1 -4.1 %, 28)
- skip OR width % [0.5, 0.8) (year 1 -31.4 %, 20)
- double VIX at signal [12, 14) (year 1 +28.3 %, 33)
- skip VIX at signal [14, 17) (year 1 -0.0 %, 55)
- double Minutes after 09:30 [15, 60) (year 1 +28.1 %, 21)
- skip Prev close vs EMA20 % [-99, -2) (year 1 -5.4 %, 15)
- skip Premium % of spot [0.8, 9.0) (year 1 -5.1 %, 16)
- skip Days to expiry [1, 2) (year 1 -9.9 %, 25)

Year 2, G1 as registered: 131 trades, return on ₹ paid +4.3 %, ₹50,165
Year 2, with the year-1 buckets: 54 trades, 99 lots, return on ₹ paid +7.0 %, ₹54,897

## The five named filters, bucket mean in each year

| Filter | Year 1 trades | Year 1 mean | Year 2 trades | Year 2 mean |
|---|---|---|---|---|
| skip day-1 gap ≥ +0.3 % | 28 | -4.1 % | 24 | -19.2 % |
| skip OR width 0.5-0.8 % | 20 | -31.4 % | 24 | -2.4 % |
| skip VIX ≥ 17 | 14 | -4.9 % | 27 | -1.8 % |
| double signal 09:45-11:29 | 25 | +25.1 % | 45 | +11.2 % |
| double VIX 12-14 | 33 | +28.3 % | 36 | +16.0 % |
