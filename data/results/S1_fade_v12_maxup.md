# S1 fade · v12 max up / max dip while held and after the sale (minute candles)

Numbers only, descriptive. 314 fade trades, entry 09:16 open + 1 tick. All as % of the entry fill, from candle highs and lows (upper bounds on a bid).

| group | n | held max up mean / median | held max dip mean / median | after-sale peak mean / median | 15:19 close mean / median | day high mean / median | v12 price change before charges, mean / median |
|---|---|---|---|---|---|---|---|
| all v12 trades | 314 | 24 / 17 | -15 / -14 | 66 / 37 | 5 / -17 | 71 / 44 | 4.6 / 7.2 |
| sold by: stop | 124 | 5 / 2 | -28 / -26 | 32 / 4 | -17 / -36 | 41 / 9 | -22.4 / -20.4 |
| sold by: trail | 190 | 36 / 29 | -7 / -5 | 88 / 53 | 19 / 1 | 91 / 56 | 22.2 / 15.2 |
| sold by: 15:19 close | 0 | nan / nan | nan / nan | - | nan / nan | nan / nan | nan / nan |
| side PE | 226 | 24 / 17 | -15 / -14 | 66 / 35 | 5 / -17 | 72 / 40 | 4.4 / 7.1 |
| side CE | 88 | 24 / 19 | -16 / -14 | 64 / 41 | 4 / -19 | 71 / 46 | 4.8 / 7.2 |


Trades reaching a level (of 314):

| level | held max up | after-sale peak | day high |
|---|---|---|---|
| >= 25 % | 112 | 193 | 206 |
| >= 50 % | 35 | 127 | 134 |
| >= 100 % | 7 | 62 | 62 |


Later sessions (carry candles exist for 312 trades, 10 later days on median): peak after day 0 mean 141 %, median 54 %; >= 100 % in 128 trades.
