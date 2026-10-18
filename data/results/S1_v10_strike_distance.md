# S1 v10 fade · strike distance study

Descriptive only (strategies/S1_v10_strike_distance_study.md). Not out of sample. Same signals, expiry, entry, same-day exit and costs as the v10 backtest; only the strike changes. 'One step closer' and 'at the money' may break the Rs 600-8,000 lot budget (see 'lots over Rs 8,000').

Answer: NO, a closer strike does not make the fade better. Keep v10's strike walk.
Checked: the baseline reproduces the v10 backtest exactly (436 / 434 trades); 60 sampled trades rebuilt from the bhavcopy price files with no mismatch.
- Cap 3 % / cap 5 % (inside the Rs 600-8,000 budget): on the trades they keep, the strike is the same; they only drop the far-strike trades. With the open entry those dropped trades made +3 % to +12 %, so the caps cut the winners: worse in both periods.
- One step closer: about 14-17 points worse a trade with the open entry (t -8.6 / -9.7), and worse in rupees with both entries. Clearly worse.
- At the money (costs about Rs 19,000-21,000 a lot, over the budget): 7.6-7.8 points worse with the open entry, but 6.9-7.5 points better with the VWAP entry. Still a loss with the VWAP entry (-5.9 % / -6.5 % a trade), so not a fix.
- Why: far strikes lose more often but their wins are much bigger (the cheap option multiplies a big fade). At the money wins about as often (38-40 % of trades vs 37-40 %) and one step closer less often (30-33 %), and both give up those big wins.
- What it shows instead: v10's profit depends on buying at the open price. With the realistic VWAP entry every strike rule loses money (-6 % to -20 % a trade). The live paper run (since 15 Oct) decides whether real fills are close to the open.


## Is a variant better? (the pre-registered guard)

| variant | better in both windows, both entries, % and Rs | pooled t (open entry, net %) | t >= 1 in each window | dropped trades lost (caps only) | BETTER |
|---|---|---|---|---|---|
| cap 3 % | False |  | False | False | no |
| cap 5 % | False |  | False | False | no |
| one step closer | False | -12.938 | False | n/a | no |
| at the money | False | -5.204 | False | n/a | no |

## Same signals: variant minus baseline (same-day exit)

| variant | window | entry | paired signals | same strike as baseline | diff net % (variant - baseline) | t (net %) | diff net Rs | t (net Rs) | baseline trades it drops | dropped trades' baseline net % | dropped trades' baseline net Rs total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cap 3 % | 2022-24 | open | 149 | 149 | 0 |  | 0 |  | 287 | 3.22 | 9,723 |
| cap 3 % | 2022-24 | vwap | 166 | 166 | 0 |  | 0 |  | 265 | -10.83 | -187,941 |
| cap 3 % | 2025-26 | open | 157 | 157 | 0 |  | 0 |  | 277 | 8.81 | 122,977 |
| cap 3 % | 2025-26 | vwap | 167 | 167 | 0 |  | 0 |  | 269 | -11.58 | -208,851 |
| cap 5 % | 2022-24 | open | 243 | 243 | 0 |  | 0 |  | 193 | 6.99 | 47,789 |
| cap 5 % | 2022-24 | vwap | 257 | 257 | 0 |  | 0 |  | 174 | -11.91 | -135,046 |
| cap 5 % | 2025-26 | open | 261 | 261 | 0 |  | 0 |  | 173 | 12.28 | 102,124 |
| cap 5 % | 2025-26 | vwap | 259 | 259 | 0 |  | 0 |  | 177 | -10.51 | -122,245 |
| one step closer | 2022-24 | open | 373 | 51 | -16.91 | -8.617 | -1369 | -11.265 | 63 | -11.79 | -46,544 |
| one step closer | 2022-24 | vwap | 371 | 74 | 0.28 | 0.782 | -166 | -4.772 | 60 | -15.46 | -52,170 |
| one step closer | 2025-26 | open | 405 | 44 | -14.42 | -9.68 | -1285 | -11.296 | 29 | 7.05 | 5,936 |
| one step closer | 2025-26 | vwap | 413 | 79 | 0.86 | 3.032 | -181 | -5.476 | 23 | -9.21 | -13,580 |
| at the money | 2022-24 | open | 430 | 54 | -7.59 | -3.622 | -678 | -2.011 | 6 | -27.53 | -10,536 |
| at the money | 2022-24 | vwap | 426 | 77 | 6.86 | 8.708 | 610 | 3.026 | 5 | -29.14 | -6,999 |
| at the money | 2025-26 | open | 434 | 44 | -7.76 | -3.737 | -158 | -0.458 | 0 |  |  |
| at the money | 2025-26 | vwap | 436 | 80 | 7.53 | 13.78 | 630 | 3.684 | 0 |  |  |

## Every variant, window, entry and side

| window | variant | entry | side | trades | mean net % | median net % | hit % | t | mean net Rs | total net Rs | mean lot cost Rs | lots over Rs 8,000 | median % OTM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022-24 | baseline | open | PE | 318 | 3.69 | -21.87 | 35.5 | 0.708 | -33 | -10592 | 6342 | 0 | 4.47 |
| 2022-24 | baseline | open | CE | 118 | 3.21 | -11.31 | 39 | 0.539 | 295 | 34782 | 6293 | 0 | 3.81 |
| 2022-24 | baseline | open | all | 436 | 3.56 | -17.49 | 36.5 | 0.905 | 55 | 24190 | 6329 | 0 | 4.4 |
| 2022-24 | cap 3 % | open | PE | 103 | 5.88 | -24.4 | 38.8 | 0.663 | -3 | -272 | 6059 | 0 | 1.15 |
| 2022-24 | cap 3 % | open | CE | 46 | 0.51 | -8.73 | 43.5 | 0.048 | 320 | 14740 | 5868 | 0 | 1.37 |
| 2022-24 | cap 3 % | open | all | 149 | 4.22 | -18.09 | 40.3 | 0.606 | 97 | 14468 | 6000 | 0 | 1.19 |
| 2022-24 | cap 5 % | open | PE | 177 | 2.19 | -18.06 | 36.2 | 0.359 | -128 | -22571 | 6266 | 0 | 2.5 |
| 2022-24 | cap 5 % | open | CE | 66 | -2.8 | -11.31 | 39.4 | -0.354 | -16 | -1028 | 6096 | 0 | 2.41 |
| 2022-24 | cap 5 % | open | all | 243 | 0.84 | -16.53 | 37 | 0.171 | -97 | -23599 | 6220 | 0 | 2.46 |
| 2022-24 | one step closer | open | PE | 274 | -11.92 | -25.24 | 27.7 | -2.844 | -1367 | -374574 | 9555 | 242 | 2.95 |
| 2022-24 | one step closer | open | CE | 99 | -7.56 | -24.47 | 34.3 | -1.276 | -660 | -65315 | 9235 | 80 | 2.04 |
| 2022-24 | one step closer | open | all | 373 | -10.76 | -24.76 | 29.5 | -3.268 | -1179 | -439889 | 9470 | 322 | 2.69 |
| 2022-24 | at the money | open | PE | 390 | -3.19 | -14.55 | 36.7 | -1.052 | -688 | -268474 | 21644 | 351 | 0.02 |
| 2022-24 | at the money | open | CE | 136 | -4.24 | -10.69 | 41.9 | -0.884 | -253 | -34473 | 18406 | 116 | 0 |
| 2022-24 | at the money | open | all | 526 | -3.46 | -13.8 | 38 | -1.409 | -576 | -302946 | 20807 | 467 | 0.01 |
| 2022-24 | baseline | vwap | PE | 315 | -14.12 | -16.39 | 23.5 | -9.136 | -829 | -261247 | 6440 | 0 | 4.04 |
| 2022-24 | baseline | vwap | CE | 116 | -14.55 | -15.1 | 25 | -6.676 | -837 | -97117 | 6397 | 0 | 4.39 |
| 2022-24 | baseline | vwap | all | 431 | -14.24 | -15.75 | 23.9 | -10.876 | -831 | -358364 | 6429 | 0 | 4.15 |
| 2022-24 | cap 3 % | vwap | PE | 126 | -20.58 | -22.32 | 15.1 | -7.474 | -1104 | -139101 | 5923 | 0 | 0.91 |
| 2022-24 | cap 3 % | vwap | CE | 40 | -16.85 | -17.37 | 25 | -5.158 | -783 | -31322 | 5739 | 0 | 0.83 |
| 2022-24 | cap 3 % | vwap | all | 166 | -19.68 | -20.94 | 17.5 | -8.724 | -1027 | -170423 | 5879 | 0 | 0.91 |
| 2022-24 | cap 5 % | vwap | PE | 191 | -15.94 | -18.72 | 21.5 | -7.291 | -890 | -170084 | 6221 | 0 | 1.74 |
| 2022-24 | cap 5 % | vwap | CE | 66 | -15.46 | -14.54 | 24.2 | -6.303 | -807 | -53234 | 6126 | 0 | 1.96 |
| 2022-24 | cap 5 % | vwap | all | 257 | -15.81 | -17.98 | 22.2 | -8.805 | -869 | -223318 | 6196 | 0 | 1.77 |
| 2022-24 | one step closer | vwap | PE | 277 | -14.04 | -15.09 | 25.6 | -8.969 | -1013 | -280482 | 8381 | 223 | 2.4 |
| 2022-24 | one step closer | vwap | CE | 94 | -12.96 | -13.78 | 23.4 | -5.979 | -929 | -87286 | 8155 | 74 | 3.01 |
| 2022-24 | one step closer | vwap | all | 371 | -13.77 | -14.84 | 25.1 | -10.559 | -991 | -367768 | 8323 | 297 | 2.49 |
| 2022-24 | at the money | vwap | PE | 387 | -6 | -6.85 | 35.9 | -4.322 | 88 | 34109 | 21009 | 327 | 0.03 |
| 2022-24 | at the money | vwap | CE | 129 | -5.53 | -10.69 | 34.9 | -2.436 | 1 | 87 | 18907 | 106 | 0 |
| 2022-24 | at the money | vwap | all | 516 | -5.88 | -7.54 | 35.7 | -5.128 | 66 | 34196 | 20484 | 433 | 0.01 |
| 2025-26 | baseline | open | PE | 322 | 7.06 | -15.96 | 40.7 | 1.289 | 392 | 126231 | 6370 | 0 | 4.05 |
| 2025-26 | baseline | open | CE | 112 | 1.55 | -22.57 | 38.4 | 0.201 | -1 | -68 | 6238 | 0 | 4.33 |
| 2025-26 | baseline | open | all | 434 | 5.63 | -17.02 | 40.1 | 1.345 | 291 | 126164 | 6336 | 0 | 4.12 |
| 2025-26 | cap 3 % | open | PE | 115 | -2.01 | -29.73 | 35.7 | -0.231 | 12 | 1380 | 6402 | 0 | 1.43 |
| 2025-26 | cap 3 % | open | CE | 42 | 5.65 | -23.96 | 42.9 | 0.4 | 43 | 1806 | 5815 | 0 | 1.61 |
| 2025-26 | cap 3 % | open | all | 157 | 0.04 | -29.66 | 37.6 | 0.006 | 20 | 3186 | 6245 | 0 | 1.43 |
| 2025-26 | cap 5 % | open | PE | 197 | 0.63 | -19.7 | 38.1 | 0.099 | 103 | 20223 | 6398 | 0 | 2.63 |
| 2025-26 | cap 5 % | open | CE | 64 | 3.06 | -26.62 | 39.1 | 0.276 | 60 | 3817 | 6147 | 0 | 2.29 |
| 2025-26 | cap 5 % | open | all | 261 | 1.23 | -20.79 | 38.3 | 0.239 | 92 | 24040 | 6336 | 0 | 2.44 |
| 2025-26 | one step closer | open | PE | 299 | -7.64 | -25.92 | 32.8 | -1.625 | -864 | -258472 | 9637 | 268 | 2.62 |
| 2025-26 | one step closer | open | CE | 106 | -12.42 | -30.19 | 32.1 | -2.03 | -1337 | -141737 | 9493 | 93 | 2.6 |
| 2025-26 | one step closer | open | all | 405 | -8.89 | -27.44 | 32.6 | -2.522 | -988 | -400210 | 9599 | 361 | 2.62 |
| 2025-26 | at the money | open | PE | 362 | -1.41 | -11.63 | 40.9 | -0.386 | 232 | 84155 | 19237 | 331 | 0.01 |
| 2025-26 | at the money | open | CE | 125 | -6.76 | -16.46 | 38.4 | -1.414 | -605 | -75626 | 17468 | 111 | 0.02 |
| 2025-26 | at the money | open | all | 487 | -2.78 | -13.69 | 40.2 | -1.052 | 18 | 8529 | 18783 | 442 | 0.02 |
| 2025-26 | baseline | vwap | PE | 326 | -13.53 | -14.18 | 26.7 | -8.72 | -806 | -262639 | 6555 | 0 | 3.96 |
| 2025-26 | baseline | vwap | CE | 110 | -18.72 | -19.12 | 20 | -6.76 | -1235 | -135843 | 6592 | 0 | 3.92 |
| 2025-26 | baseline | vwap | all | 436 | -14.84 | -15.75 | 25 | -12.71 | -914 | -398482 | 6565 | 0 | 3.92 |
| 2025-26 | cap 3 % | vwap | PE | 122 | -20.13 | -22.76 | 20.5 | -8.23 | -1104 | -134735 | 6022 | 0 | 0.79 |
| 2025-26 | cap 3 % | vwap | CE | 45 | -19.97 | -24.9 | 17.8 | -4.235 | -1220 | -54896 | 6282 | 0 | 0.74 |
| 2025-26 | cap 3 % | vwap | all | 167 | -20.09 | -22.86 | 19.8 | -10.074 | -1136 | -189631 | 6092 | 0 | 0.75 |
| 2025-26 | cap 5 % | vwap | PE | 188 | -16.71 | -18.87 | 25 | -7.87 | -960 | -180389 | 6314 | 0 | 1.96 |
| 2025-26 | cap 5 % | vwap | CE | 71 | -20.69 | -23.04 | 16.9 | -6.033 | -1350 | -95848 | 6484 | 0 | 1.84 |
| 2025-26 | cap 5 % | vwap | all | 259 | -17.8 | -20.56 | 22.8 | -10.354 | -1067 | -276237 | 6361 | 0 | 1.94 |
| 2025-26 | one step closer | vwap | PE | 309 | -13.23 | -14.44 | 28.5 | -8.57 | -1004 | -310174 | 8546 | 253 | 2.54 |
| 2025-26 | one step closer | vwap | CE | 104 | -17.47 | -17.31 | 20.2 | -6.053 | -1436 | -149319 | 8461 | 81 | 2.51 |
| 2025-26 | one step closer | vwap | all | 413 | -14.3 | -14.99 | 26.4 | -12.084 | -1113 | -459493 | 8525 | 334 | 2.53 |
| 2025-26 | at the money | vwap | PE | 354 | -5.53 | -6.1 | 40.1 | -3.566 | 177 | 62600 | 19698 | 298 | 0.02 |
| 2025-26 | at the money | vwap | CE | 119 | -9.46 | -11.9 | 33.6 | -3.44 | -750 | -89248 | 18195 | 95 | 0.03 |
| 2025-26 | at the money | vwap | all | 473 | -6.52 | -8.34 | 38.5 | -5.757 | -56 | -26648 | 19320 | 393 | 0.03 |
