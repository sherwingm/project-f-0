# S1 strike choice, 09:16 volume rule, next strike (fade v12; arms A / B next strike)

Numbers only. Pre-registered: strategies/S1_strike_choice_minutes.md. Entry 09:16 open + 1 tick, v12 exit, 1-minute Upstox candles; ban-day signals dropped (1). Train before 2025-11-03, test from it.

## Test 1 · which strike (v12)

| strike rule | n | win % | mean % | median % | total Rs | t | mean without top 3 % | lot over Rs 8,000 % | mean lot Rs | paired n | diff vs pick (points) | diff t | diff train | diff test | Rs vs pick | beats the pick |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ITM2 | 365 | 58.9 | 0.75 | 6.77 | 165070 | 0.776 | 0.45 | 93.4 | 25870 | 327 | -2.45 | -2.241 | -2.28 | -2.6 | 97,625 | no |
| ITM1 | 425 | 60.9 | 1.14 | 6.58 | 208601 | 1.195 | 0.91 | 89.9 | 22018 | 371 | -0.66 | -0.711 | 0.34 | -1.5 | 173,856 | no |
| ATM | 440 | 60.7 | 2.18 | 7.08 | 154613 | 2.285 | 1.93 | 83.9 | 18500 | 386 | -0.56 | -0.606 | 0.19 | -1.19 | 118,006 | no |
| walk -1 | 345 | 57.1 | 2.6 | 5.68 | 87190 | 1.802 | 1.51 | 68.4 | 9462 | 307 | -0.2 | -0.241 | 0.93 | -1.12 | 25,586 | no |
| pick | 401 | 56.6 | 3.61 | 6.29 | 107843 | 2.556 | 2.93 | 22.2 | 6835 |  |  |  |  |  |  |  |
| walk +1 | 379 | 54.4 | 0.73 | 2.74 | 21926 | 0.474 | 0.15 | 9.5 | 5286 | 341 | -1.69 | -1.689 | -1.78 | -1.62 | -42,709 | no |
| walk +2 | 319 | 52 | 1.64 | 4.13 | 24329 | 0.954 | 0.87 | 3.8 | 4039 | 294 | -0.77 | -0.928 | -1.7 | -0.07 | -46,841 | no |
| walk +3 | 296 | 50 | 2.22 | 0 | 19972 | 0.883 | -0.92 | 1.4 | 3137 | 265 | 1.69 | 0.727 | 0.71 | 2.41 | -22,523 | no |


Pass: paired diff > 0 with t >= 2, > 0 in both halves, and more Rs. No lot cap on the alternatives.

## Test 2 · a volume rule known at 09:16 (v12)

| rule | half | n | win % | mean % | median % | total Rs | t | mean without top 3 % | picks changed |
|---|---|---|---|---|---|---|---|---|---|
| today: >= 50 contracts on the whole day (not known at 09:16) | train | 185 | 55.1 | 3.35 | 5.64 | 44355 | 1.473 | 2.26 |  |
| today: >= 50 contracts on the whole day (not known at 09:16) | test | 216 | 57.9 | 3.82 | 6.98 | 63488 | 2.173 | 2.19 |  |
| 09:15 volume >= 1 lots | train | 191 | 57.1 | 5.29 | 5.81 | 51629 | 1.978 | 2.64 | 104 |
| 09:15 volume >= 1 lots | test | 231 | 57.1 | 3.17 | 6.29 | 56664 | 2.046 | 1.63 | 128 |
| 09:15 volume >= 2 lots | train | 177 | 57.6 | 3.92 | 5.81 | 37080 | 1.905 | 2.91 | 100 |
| 09:15 volume >= 2 lots | test | 227 | 57.7 | 3.28 | 6.32 | 57429 | 2.096 | 1.72 | 128 |
| 09:15 volume >= 5 lots | train | 168 | 58.3 | 3.88 | 6.04 | 37847 | 1.909 | 2.82 | 96 |
| 09:15 volume >= 5 lots | test | 219 | 57.5 | 3.3 | 6.32 | 52963 | 2.03 | 1.91 | 126 |
| 09:15 volume >= 10 lots | train | 164 | 58.5 | 3.71 | 6.04 | 33756 | 1.832 | 2.62 | 91 |
| 09:15 volume >= 10 lots | test | 207 | 56 | 2.87 | 5.95 | 40572 | 1.627 | 1.39 | 119 |
| 09:15 volume >= 25 lots | train | 148 | 58.8 | 3.7 | 6.22 | 30271 | 1.683 | 2.49 | 86 |
| 09:15 volume >= 25 lots | test | 185 | 55.7 | 2.54 | 5.5 | 34516 | 1.377 | 0.88 | 111 |


Train picks X = 1 (highest train mean). Judge its test row against today's test row.

Signals without a trade per rule:

| rule | dropped | signals |
|---|---|---|
| 09:15 volume >= 1 lots | beyond the fetch | 29 |
| 09:15 volume >= 1 lots | no strike passed | 8 |
| 09:15 volume >= 1 lots | premium below 2 | 9 |
| 09:15 volume >= 10 lots | beyond the fetch | 71 |
| 09:15 volume >= 10 lots | no strike passed | 13 |
| 09:15 volume >= 10 lots | premium below 2 | 13 |
| 09:15 volume >= 2 lots | beyond the fetch | 42 |
| 09:15 volume >= 2 lots | no strike passed | 10 |
| 09:15 volume >= 2 lots | premium below 2 | 12 |
| 09:15 volume >= 25 lots | beyond the fetch | 108 |
| 09:15 volume >= 25 lots | no strike passed | 16 |
| 09:15 volume >= 25 lots | premium below 2 | 11 |
| 09:15 volume >= 5 lots | beyond the fetch | 55 |
| 09:15 volume >= 5 lots | no strike passed | 12 |
| 09:15 volume >= 5 lots | premium below 2 | 14 |

## Test 3 · next strike when the pick has no 09:16 trade

Fade: 59 signals had no 09:16 candle on the pick; next strike found for 43.

| set | n | win % | mean % | median % | total Rs | t | mean without top 3 % |
|---|---|---|---|---|---|---|---|
| fade, the added next-strike trades | 43 | 51.2 | -1.68 | 2.41 | -8630 | -0.436 | -5.54 |
| fade, the 409 picks + the added | 444 | 56.1 | 3.09 | 5.96 | 99213 | 2.377 | 2.48 |
| fade, the picks alone | 401 | 56.6 | 3.61 | 6.29 | 107843 | 2.556 | 2.93 |


## Test 3 · arms A / B, the trades dropped for no 09:16 candle

77 dropped trades; next strike up fetched for 54 stock-days.

| set | arm | variant | added n | added win % | added mean % | added median % | added total Rs | added t | added mean without top 3 % | with the old trades: n | with the old: mean % | old alone: mean % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| next strike up | A | LIVE-CLOSE | 17 | 11.8 | -14.7 | -63.86 | -12038 | -0.493 | -64.07 | 157 | -23.31 | -24.36 |
| next strike up | A | LIVE-INTRA | 17 | 11.8 | -6.72 | -55.72 | -945 | -0.233 | -54.24 | 157 | -26.43 | -28.82 |
| next strike up | A | H8 | 17 | 17.6 | -34.93 | -87.15 | -34352 | -1.414 | -79.98 | 159 | -18.14 | -16.13 |
| next strike up | A | H11 | 17 | 11.8 | -43.79 | -87.77 | -42574 | -1.756 | -85.76 | 157 | -20.22 | -17.35 |
| next strike up | A | S8 | 17 | 11.8 | -32.68 | -87.15 | -29452 | -1.043 | -84.9 | 156 | -24.14 | -23.09 |
| next strike up | B | LIVE-CLOSE | 9 | 11.1 | -26.86 | -63.86 | -13419 | -0.766 | -67.45 | 64 | -20.17 | -19.07 |
| next strike up | B | LIVE-INTRA | 9 | 11.1 | -19.23 | -54.44 | -9124 | -0.566 | -52.96 | 64 | -30.05 | -31.82 |
| next strike up | B | H8 | 9 | 22.2 | -26.4 | -86.08 | -11571 | -0.685 | -88.05 | 63 | -25.26 | -25.07 |
| next strike up | B | H11 | 9 | 11.1 | -44.55 | -85.88 | -22914 | -1.248 | -88.2 | 63 | -19.49 | -15.31 |
| next strike up | B | S8 | 9 | 11.1 | -42.89 | -86.08 | -22431 | -1.149 | -87.34 | 63 | -5.86 | 0.31 |
| same strike, first candle 09:16-09:30 | A | LIVE-CLOSE | 41 | 12.2 | -11.99 | -56.38 | -48839 | -0.633 | -43.67 | 181 | -21.55 | -24.36 |
| same strike, first candle 09:16-09:30 | A | LIVE-INTRA | 41 | 4.9 | -36.22 | -54.16 | -110828 | -3.508 | -51.34 | 181 | -30.5 | -28.82 |
| same strike, first candle 09:16-09:30 | A | H8 | 40 | 20 | -17.19 | -75.06 | -71131 | -0.661 | -45.28 | 182 | -16.36 | -16.13 |
| same strike, first candle 09:16-09:30 | A | H11 | 38 | 21.1 | -28.77 | -77.8 | -86171 | -1.333 | -54.33 | 178 | -19.79 | -17.35 |
| same strike, first candle 09:16-09:30 | A | S8 | 40 | 15 | -10.23 | -75.8 | -44163 | -0.28 | -54.34 | 179 | -20.22 | -23.09 |
| same strike, first candle 09:16-09:30 | B | LIVE-CLOSE | 16 | 12.5 | -16.76 | -57.52 | -26924 | -0.652 | -56.47 | 71 | -18.55 | -19.07 |
| same strike, first candle 09:16-09:30 | B | LIVE-INTRA | 16 | 12.5 | -10.91 | -54.35 | -20226 | -0.438 | -49.26 | 71 | -27.11 | -31.82 |
| same strike, first candle 09:16-09:30 | B | H8 | 15 | 26.7 | -12.39 | -75.52 | -20987 | -0.39 | -69.59 | 69 | -22.31 | -25.07 |
| same strike, first candle 09:16-09:30 | B | H11 | 15 | 26.7 | -31.43 | -85.46 | -39756 | -1.11 | -77.55 | 69 | -18.82 | -15.31 |
| same strike, first candle 09:16-09:30 | B | S8 | 15 | 13.3 | -31.79 | -75.52 | -41322 | -1.089 | -78.7 | 69 | -6.66 | 0.31 |
