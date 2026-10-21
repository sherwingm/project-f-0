# S1 fade · refused sub-Rs 2 signals bought anyway if the listing-day price was < Rs 10 / < Rs 7 (v12 exit)

Pre-registered: strategies/S1_refused_listing_price.md. 274 refused contracts (realistic entry under Rs 2, Oct 2024 - Aug 2026, no lot cap), listing price found for 274. Same-day v12 exit, real charges.

## The test

| rule | n | mean % | t | half 1 mean % | half 2 mean % | pass |
|---|---|---|---|---|---|---|
| listing price < Rs 10 | 180 | -4.09 | -1.333 | -10.56 | 1.7 | False |
| listing price < Rs 7 | 153 | -2.88 | -0.86 | -8.05 | 1.96 | False |

## Groups

| group | period | n | win % | mean % | median % | total Rs | t |
|---|---|---|---|---|---|---|---|
| all refused (B < Rs 2) | all | 274 | 44.9 | -4.4 | -6 | -14545 | -1.778 |
| all refused (B < Rs 2) | Oct24-Oct25 | 130 | 36.9 | -10.13 | -24.5 | -23173 | -2.64 |
| all refused (B < Rs 2) | Nov25-Sep26 | 144 | 52.1 | 0.77 | 1.6 | 8628 | 0.291 |
| listing price < Rs 10 | all | 180 | 43.9 | -4.09 | -8.2 | -19153 | -1.333 |
| listing price < Rs 10 | Oct24-Oct25 | 85 | 35.3 | -10.56 | -25.9 | -22365 | -2.202 |
| listing price < Rs 10 | Nov25-Sep26 | 95 | 51.6 | 1.7 | 1.9 | 3212 | 0.525 |
| listing price < Rs 7 | all | 153 | 45.8 | -2.88 | -5.3 | -12615 | -0.86 |
| listing price < Rs 7 | Oct24-Oct25 | 74 | 36.5 | -8.05 | -25.2 | -18549 | -1.535 |
| listing price < Rs 7 | Nov25-Sep26 | 79 | 54.4 | 1.96 | 2.7 | 5934 | 0.527 |
| listing price >= Rs 10 | all | 94 | 46.8 | -4.99 | -4 | 4608 | -1.371 |
| listing price >= Rs 10 | Oct24-Oct25 | 45 | 40 | -9.3 | -19 | -808 | -1.566 |
| listing price >= Rs 10 | Nov25-Sep26 | 49 | 53.1 | -1.02 | 1.2 | 5416 | -0.237 |
