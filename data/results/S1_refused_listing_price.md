# S1 fade · refused sub-Rs 2 signals bought anyway if the listing-day price was < Rs 10 / < Rs 7 (v12 exit)

Pre-registered: strategies/S1_refused_listing_price.md. 274 refused contracts (realistic entry under Rs 2, Oct 2024 - Aug 2026), listing price found for 274. As many lots as cost <= Rs 8,000 (at least 1). Same-day v12 exit, real charges.

## The test

| rule | n | mean % | t | half 1 mean % | half 2 mean % | pass |
|---|---|---|---|---|---|---|
| listing price < Rs 10 | 180 | -1.82 | -0.594 | -8.15 | 3.85 | False |
| listing price < Rs 7 | 153 | -0.7 | -0.207 | -5.74 | 4.03 | False |

## Groups

| group | period | n | win % | mean % | median % | total Rs | t |
|---|---|---|---|---|---|---|---|
| all refused (B < Rs 2) | all | 274 | 46.7 | -1.57 | -4.8 | -26089 | -0.638 |
| all refused (B < Rs 2) | Oct24-Oct25 | 130 | 36.9 | -7.39 | -23.6 | -65453 | -1.941 |
| all refused (B < Rs 2) | Nov25-Sep26 | 144 | 55.6 | 3.69 | 3.9 | 39364 | 1.407 |
| listing price < Rs 10 | all | 180 | 45.6 | -1.82 | -7.4 | -14402 | -0.594 |
| listing price < Rs 10 | Oct24-Oct25 | 85 | 35.3 | -8.15 | -24 | -42902 | -1.696 |
| listing price < Rs 10 | Nov25-Sep26 | 95 | 54.7 | 3.85 | 4.1 | 28499 | 1.192 |
| listing price < Rs 7 | all | 153 | 47.1 | -0.7 | -5.3 | 1377 | -0.207 |
| listing price < Rs 7 | Oct24-Oct25 | 74 | 36.5 | -5.74 | -23.8 | -22235 | -1.088 |
| listing price < Rs 7 | Nov25-Sep26 | 79 | 57 | 4.03 | 4.6 | 23612 | 1.081 |
| listing price >= Rs 10 | all | 94 | 48.9 | -1.08 | -0.9 | -11687 | -0.305 |
| listing price >= Rs 10 | Oct24-Oct25 | 45 | 40 | -5.95 | -19 | -22551 | -1.045 |
| listing price >= Rs 10 | Nov25-Sep26 | 49 | 57.1 | 3.39 | 3.8 | 10864 | 0.795 |
