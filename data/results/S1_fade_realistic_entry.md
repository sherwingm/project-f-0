# S1 fade · the backtest with a realistic entry (09:16 candle open + 1 tick)

Pre-registered: strategies/S1_fade_realistic_entry.md. Descriptive; nothing live changes. Same 409 contracts for A and B (59 excluded: no 09:16 candle). Same exit code for both; real charges, no extra % slippage. t is date-clustered.

## A (old entry) vs B (new entry), v10 and v11 exits

| entry | exit | n | win % | mean % | median % | total Rs | t |
|---|---|---|---|---|---|---|---|
| A old (backtest open) | v10 | 409 | 42.5 | 12.72 | -13.52 | 289512 | 2.599 |
| A old (backtest open) | v11 | 409 | 31.1 | 13.77 | -21.09 | 323464 | 3.003 |
| B new (09:16 open + tick) | v10 | 409 | 41.3 | 3.21 | -16.22 | 103545 | 0.849 |
| B new (09:16 open + tick) | v11 | 409 | 26.2 | 2.47 | -21.03 | 65583 | 0.876 |

## B by window

| window | exit | n | win % | mean % | median % | total Rs | t |
|---|---|---|---|---|---|---|---|
| Oct24-Oct25 | v10 | 189 | 39.7 | 3.97 | -20.8 | 39481 | 0.62 |
| Oct24-Oct25 | v11 | 189 | 25.4 | 3.34 | -21.35 | 25706 | 0.638 |
| Nov25-Sep26 | v10 | 220 | 42.7 | 2.56 | -13.04 | 64064 | 0.583 |
| Nov25-Sep26 | v11 | 220 | 26.8 | 1.73 | -20.91 | 39877 | 0.635 |

## B and the rules (fill >= Rs 2, one lot Rs 600-8,000)

| set | n | win % | mean % | median % | total Rs | t | exit |
|---|---|---|---|---|---|---|---|
| all B trades | 409 | 26.2 | 2.47 | -21.03 | 65583 | 0.876 | v11 |
| fail the rules at B (fill < 2 or lot Rs outside 600-8000) | 97 | 26.8 | 2.84 | -20.75 | 29483 | 0.427 | v11 |
| B trades that pass the rules | 312 | 26 | 2.36 | -21.16 | 36100 | 0.752 | v11 |
| B trades that pass the rules | 312 | 39.4 | 1.63 | -18.42 | 12189 | 0.37 | v10 |

## The odd trades of the old entry, under B

| group (picked under A) | n | A mean % | B mean % |
|---|---|---|---|
| lost -30..-85 % under A (v11) | 56 | -44.6 | 1.7 |
| first candle closed >= +20 % over A entry | 106 | 71.1 | 1.6 |
| won >= +300 % under A (v11) | 8 | 447.6 | 122 |

## How far B is from A

| B entry vs A entry | % |
|---|---|
| median | 0 |
| share B > A by 20 %+ | 25.7 |
| share B < A by 20 %+ | 18.3 |
| share within +-5 % | 23.7 |
