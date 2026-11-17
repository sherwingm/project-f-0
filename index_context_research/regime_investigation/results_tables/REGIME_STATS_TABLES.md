# Regime statistics, every strategy x condition x class (coordinator recomputation; 17 Nov 2026)

One set of definitions for all agents' class labels: win = net % > 0; percentage = net rupees after slippage and charges / premium paid; rupees separate; top-5 % share = rupees of the best 5 % of trades / the class's total net rupees (blank if the total is not positive, can exceed 100 %); `without top 3` = mean net % without the class's 3 best trades; interval = bootstrap 95 % of the mean resampling trading days; MFE = highest option value after entry through the next close (% above price paid, minute closes); MAE = lowest minute close between entry and exit (% below price paid); duration in trading minutes. Classes under 10 trades carry no numbers. Percent and rupees are never mixed. Labels come from `interim/agent3_regimes`, `agent3b_gift_regimes` (same-contract) and `agent4_external`; definitions in `PREREG_REGIME.md`.

## G1-F
**H1 direction (ret20 quintile, 1 bearish .. 5 bullish)**
- 1: n 36 (17 W / 19 L, win 47 %), mean +18.8 % [-5, +45], median -3.2 %, total Rs 56,384, avg win Rs 6,635 (+84 %), avg loss Rs -2,969 (-40 %), max up mean 101 % (>= +100 % on 50 %), MFE 101 %, MAE -44 %, top-5 % share 48 %, without top 3 +4.2 %
- 2: n 39 (16 W / 23 L, win 41 %), mean +5.2 % [-19, +32], median -31.9 %, total Rs 34,290, avg win Rs 6,778 (+81 %), avg loss Rs -3,224 (-48 %), max up mean 99 % (>= +100 % on 44 %), MFE 99 %, MAE -48 %, top-5 % share 121 %, without top 3 -12.2 %
- 3: n 60 (20 W / 40 L, win 33 %), mean +16.9 % [-10, +48], median -32.6 %, total Rs 63,606, avg win Rs 9,138 (+139 %), avg loss Rs -2,979 (-44 %), max up mean 91 % (>= +100 % on 28 %), MFE 91 %, MAE -52 %, top-5 % share 80 %, without top 3 -1.2 %
- 4: n 13 (4 W / 9 L, win 31 %), mean +18.1 % [-37, +83], median -51.2 %, total Rs 13,639, avg win Rs 11,829 (+165 %), avg loss Rs -3,742 (-47 %), max up mean 131 % (>= +100 % on 46 %), MFE 131 %, MAE -44 %, top-5 % share 129 %, without top 3 -39.1 %
- 5: n 6 too few (n < 10): no numbers

**H1b direction3**
- bearish: n 75 (33 W / 42 L, win 44 %), mean +11.7 % [-5, +29], median -17.3 %, total Rs 90,674, avg win Rs 6,705 (+83 %), avg loss Rs -3,109 (-44 %), max up mean 100 % (>= +100 % on 47 %), MFE 100 %, MAE -46 %, top-5 % share 75 %, without top 3 +2.7 %
- bullish: n 19 (10 W / 9 L, win 53 %), mean +59.5 % [+5, +120], median +35.8 %, total Rs 92,766, avg win Rs 12,644 (+156 %), avg loss Rs -3,742 (-47 %), max up mean 167 % (>= +100 % on 58 %), MFE 167 %, MAE -36 %, top-5 % share 48 %, without top 3 +14.6 %
- sideways: n 60 (20 W / 40 L, win 33 %), mean +16.9 % [-10, +48], median -32.6 %, total Rs 63,606, avg win Rs 9,138 (+139 %), avg loss Rs -2,979 (-44 %), max up mean 91 % (>= +100 % on 28 %), MFE 91 %, MAE -52 %, top-5 % share 80 %, without top 3 -1.2 %

**H2 VIX level (previous close)**
- low: n 108 (37 W / 71 L, win 34 %), mean +11.8 % [-5, +32], median -37.6 %, total Rs 64,172, avg win Rs 7,712 (+122 %), avg loss Rs -3,115 (-46 %), max up mean 101 % (>= +100 % on 37 %), MFE 101 %, MAE -49 %, top-5 % share 162 %, without top 3 +1.8 %
- normal: n 46 (26 W / 20 L, win 57 %), mean +38.1 % [+11, +67], median +7.4 %, total Rs 182,874, avg win Rs 9,427 (+99 %), avg loss Rs -3,112 (-41 %), max up mean 113 % (>= +100 % on 50 %), MFE 113 %, MAE -41 %, top-5 % share 48 %, without top 3 +20.2 %

**H3 VIX 5-day direction**
- falling: n 50 (21 W / 29 L, win 42 %), mean +27.8 % [-3, +61], median -17.7 %, total Rs 85,648, avg win Rs 8,585 (+131 %), avg loss Rs -3,264 (-47 %), max up mean 103 % (>= +100 % on 40 %), MFE 103 %, MAE -45 %, top-5 % share 60 %, without top 3 +7.9 %
- flat: n 72 (28 W / 44 L, win 39 %), mean +16.9 % [-4, +42], median -27.5 %, total Rs 122,678, avg win Rs 9,092 (+113 %), avg loss Rs -2,998 (-44 %), max up mean 100 % (>= +100 % on 35 %), MFE 100 %, MAE -49 %, top-5 % share 82 %, without top 3 +2.3 %
- rising: n 32 (14 W / 18 L, win 44 %), mean +13.1 % [-11, +39], median -10.1 %, total Rs 38,720, avg win Rs 6,828 (+83 %), avg loss Rs -3,160 (-41 %), max up mean 116 % (>= +100 % on 56 %), MFE 116 %, MAE -47 %, top-5 % share 69 %, without top 3 -1.7 %

**H4 sudden VIX expansion**
- no: n 152 (63 W / 89 L, win 41 %), mean +20.3 % [+5, +37], median -18.2 %, total Rs 250,322, avg win Rs 8,420 (+112 %), avg loss Rs -3,148 (-45 %), max up mean 105 % (>= +100 % on 41 %), MFE 105 %, MAE -47 %, top-5 % share 68 %, without top 3 +12.9 %
- yes: n 2 too few (n < 10): no numbers

**H5 actual NIFTY opening gap**
- flat: n 133 (56 W / 77 L, win 42 %), mean +21.8 % [+5, +40], median -17.3 %, total Rs 243,314, avg win Rs 8,568 (+113 %), avg loss Rs -3,071 (-45 %), max up mean 110 % (>= +100 % on 43 %), MFE 110 %, MAE -45 %, top-5 % share 64 %, without top 3 +13.3 %
- gap-down: n 21 (7 W / 14 L, win 33 %), mean +6.4 % [-25, +44], median -51.0 %, total Rs 3,732, avg win Rs 7,240 (+105 %), avg loss Rs -3,353 (-43 %), max up mean 71 % (>= +100 % on 29 %), MFE 71 %, MAE -58 %, top-5 % share 566 %, without top 3 -21.9 %

**H6 S&P previous session (agent 3, stale cache)**
- down: n 51 (18 W / 33 L, win 35 %), mean +19.8 % [-9, +51], median -36.2 %, total Rs 80,013, avg win Rs 10,406 (+138 %), avg loss Rs -3,251 (-45 %), max up mean 103 % (>= +100 % on 33 %), MFE 103 %, MAE -53 %, top-5 % share 105 %, without top 3 -1.0 %
- flat: n 48 (17 W / 31 L, win 35 %), mean +8.0 % [-18, +35], median -46.8 %, total Rs 56,683, avg win Rs 8,619 (+107 %), avg loss Rs -2,898 (-47 %), max up mean 101 % (>= +100 % on 42 %), MFE 101 %, MAE -49 %, top-5 % share 100 %, without top 3 -9.3 %
- up: n 52 (25 W / 27 L, win 48 %), mean +28.1 % [+3, +56], median -5.9 %, total Rs 92,743, avg win Rs 7,161 (+104 %), avg loss Rs -3,196 (-42 %), max up mean 110 % (>= +100 % on 46 %), MFE 110 %, MAE -40 %, top-5 % share 57 %, without top 3 +11.4 %

**H10 GIFT overnight, same-contract (PRIMARY)**
- flat: n 111 (46 W / 65 L, win 41 %), mean +19.4 % [+3, +37], median -17.3 %, total Rs 155,621, avg win Rs 7,465 (+109 %), avg loss Rs -2,888 (-44 %), max up mean 103 % (>= +100 % on 41 %), MFE 103 %, MAE -45 %, top-5 % share 64 %, without top 3 +10.0 %
- gap-down: n 28 (11 W / 17 L, win 39 %), mean +26.7 % [-14, +75], median -34.8 %, total Rs 87,769, avg win Rs 13,380 (+140 %), avg loss Rs -3,495 (-47 %), max up mean 118 % (>= +100 % on 36 %), MFE 118 %, MAE -53 %, top-5 % share 78 %, without top 3 -6.3 %
- gap-up: n 13 (6 W / 7 L, win 46 %), mean +17.5 % [-26, +72], median -11.7 %, total Rs 10,957, avg win Rs 6,653 (+89 %), avg loss Rs -4,137 (-43 %), max up mean 102 % (>= +100 % on 54 %), MFE 102 %, MAE -43 %, top-5 % share 208 %, without top 3 -25.5 %

**H11 indicated vs actual opening, same-contract (PRIMARY)**
- in line: n 102 (35 W / 67 L, win 34 %), mean +8.0 % [-9, +26], median -34.4 %, total Rs 60,122, avg win Rs 7,901 (+110 %), avg loss Rs -3,230 (-45 %), max up mean 91 % (>= +100 % on 38 %), MFE 91 %, MAE -50 %, top-5 % share 158 %, without top 3 -1.0 %
- stronger: n 24 (13 W / 11 L, win 54 %), mean +53.5 % [+8, +107], median +19.7 %, total Rs 141,995, avg win Rs 12,918 (+138 %), avg loss Rs -2,358 (-46 %), max up mean 148 % (>= +100 % on 46 %), MFE 148 %, MAE -42 %, top-5 % share 48 %, without top 3 +15.8 %
- weaker: n 26 (15 W / 11 L, win 58 %), mean +39.5 % [+3, +86], median +6.4 %, total Rs 52,230, avg win Rs 5,733 (+96 %), avg loss Rs -3,070 (-37 %), max up mean 124 % (>= +100 % on 50 %), MFE 124 %, MAE -37 %, top-5 % share 65 %, without top 3 +7.4 %

**H12 Asia pre-entry (agent 3b, mean of available markets)**
- down: n 41 (16 W / 25 L, win 39 %), mean +19.7 % [-12, +55], median -50.9 %, total Rs 71,427, avg win Rs 9,711 (+127 %), avg loss Rs -3,358 (-49 %), max up mean 105 % (>= +100 % on 39 %), MFE 105 %, MAE -55 %, top-5 % share 107 %, without top 3 -4.9 %
- flat: n 64 (28 W / 36 L, win 44 %), mean +17.9 % [-4, +43], median -16.1 %, total Rs 104,064, avg win Rs 7,946 (+100 %), avg loss Rs -3,289 (-46 %), max up mean 97 % (>= +100 % on 39 %), MFE 97 %, MAE -45 %, top-5 % share 78 %, without top 3 +3.6 %
- up: n 47 (19 W / 28 L, win 40 %), mean +25.0 % [-2, +55], median -11.7 %, total Rs 78,856, avg win Rs 8,032 (+117 %), avg loss Rs -2,634 (-38 %), max up mean 118 % (>= +100 % on 47 %), MFE 118 %, MAE -41 %, top-5 % share 67 %, without top 3 +6.2 %

**X01 S&P 500 previous US session**
- down: n 53 (20 W / 33 L, win 38 %), mean +20.0 % [-8, +54], median -31.9 %, total Rs 84,440, avg win Rs 9,587 (+127 %), avg loss Rs -3,251 (-45 %), max up mean 101 % (>= +100 % on 34 %), MFE 101 %, MAE -52 %, top-5 % share 100 %, without top 3 -0.0 %
- flat: n 48 (17 W / 31 L, win 35 %), mean +8.0 % [-18, +35], median -46.8 %, total Rs 56,683, avg win Rs 8,619 (+107 %), avg loss Rs -2,898 (-47 %), max up mean 101 % (>= +100 % on 42 %), MFE 101 %, MAE -49 %, top-5 % share 100 %, without top 3 -9.3 %
- up: n 53 (26 W / 27 L, win 49 %), mean +29.9 % [+6, +57], median -2.0 %, total Rs 105,923, avg win Rs 7,393 (+104 %), avg loss Rs -3,196 (-42 %), max up mean 111 % (>= +100 % on 47 %), MFE 111 %, MAE -40 %, top-5 % share 50 %, without top 3 +13.6 %

**X02 USD/INR previous session (hourly)**
- down: n 15 (6 W / 9 L, win 40 %), mean +36.3 % [-24, +111], median -51.2 %, total Rs 46,113, avg win Rs 14,416 (+168 %), avg loss Rs -4,487 (-51 %), max up mean 140 % (>= +100 % on 40 %), MFE 140 %, MAE -51 %, top-5 % share 96 %, without top 3 -23.5 %
- flat: n 102 (34 W / 68 L, win 33 %), mean +7.4 % [-10, +26], median -39.4 %, total Rs 111,146, avg win Rs 9,442 (+114 %), avg loss Rs -3,086 (-46 %), max up mean 91 % (>= +100 % on 35 %), MFE 91 %, MAE -51 %, top-5 % share 99 %, without top 3 -1.8 %
- up: n 24 (16 W / 8 L, win 67 %), mean +46.1 % [+12, +79], median +20.8 %, total Rs 77,005, avg win Rs 6,294 (+88 %), avg loss Rs -2,963 (-38 %), max up mean 123 % (>= +100 % on 54 %), MFE 123 %, MAE -35 %, top-5 % share 47 %, without top 3 +22.1 %

**X03 Brent previous day (quality-limited)**
- down: n 38 (14 W / 24 L, win 37 %), mean +12.3 % [-19, +50], median -29.2 %, total Rs 40,738, avg win Rs 8,586 (+115 %), avg loss Rs -3,311 (-48 %), max up mean 101 % (>= +100 % on 32 %), MFE 101 %, MAE -49 %, top-5 % share 148 %, without top 3 -11.9 %
- flat: n 74 (33 W / 41 L, win 45 %), mean +30.6 % [+7, +57], median -15.6 %, total Rs 174,820, avg win Rs 9,258 (+126 %), avg loss Rs -3,187 (-46 %), max up mean 115 % (>= +100 % on 49 %), MFE 115 %, MAE -47 %, top-5 % share 43 %, without top 3 +16.6 %
- up: n 41 (16 W / 25 L, win 39 %), mean +8.4 % [-12, +33], median -8.3 %, total Rs 37,695, avg win Rs 6,548 (+81 %), avg loss Rs -2,683 (-38 %), max up mean 91 % (>= +100 % on 37 %), MFE 91 %, MAE -44 %, top-5 % share 119 %, without top 3 -5.9 %

**X04 US VIX spike**
- no_spike: n 132 (55 W / 77 L, win 42 %), mean +19.7 % [+4, +38], median -15.6 %, total Rs 191,479, avg win Rs 7,668 (+109 %), avg loss Rs -2,991 (-44 %), max up mean 103 % (>= +100 % on 41 %), MFE 103 %, MAE -47 %, top-5 % share 66 %, without top 3 +11.7 %
- spike: n 13 (3 W / 10 L, win 23 %), mean +0.3 % [-45, +71], median -51.0 %, total Rs 13,174, avg win Rs 16,283 (+149 %), avg loss Rs -3,568 (-44 %), max up mean 85 % (>= +100 % on 15 %), MFE 85 %, MAE -59 %, top-5 % share 337 %, without top 3 -44.3 %

**X05 Global risk-on / off**
- mixed: n 54 (22 W / 32 L, win 41 %), mean +14.0 % [-9, +38], median -28.1 %, total Rs 71,961, avg win Rs 7,502 (+102 %), avg loss Rs -2,909 (-47 %), max up mean 105 % (>= +100 % on 44 %), MFE 105 %, MAE -47 %, top-5 % share 79 %, without top 3 -0.9 %
- risk_off: n 40 (15 W / 25 L, win 38 %), mean +18.3 % [-10, +50], median -25.2 %, total Rs 48,075, avg win Rs 8,654 (+123 %), avg loss Rs -3,269 (-44 %), max up mean 101 % (>= +100 % on 38 %), MFE 101 %, MAE -51 %, top-5 % share 83 %, without top 3 -5.3 %
- risk_on: n 39 (17 W / 22 L, win 44 %), mean +14.3 % [-9, +41], median -10.4 %, total Rs 50,629, avg win Rs 7,077 (+86 %), avg loss Rs -3,167 (-41 %), max up mean 93 % (>= +100 % on 41 %), MFE 93 %, MAE -41 %, top-5 % share 82 %, without top 3 -1.6 %

**X06 Asia pre-entry (agent 4, needs both markets)**
- down: n 37 (14 W / 23 L, win 38 %), mean +13.7 % [-16, +45], median -50.9 %, total Rs 31,415, avg win Rs 7,875 (+116 %), avg loss Rs -3,428 (-49 %), max up mean 95 % (>= +100 % on 41 %), MFE 95 %, MAE -55 %, top-5 % share 102 %, without top 3 -7.5 %
- flat: n 58 (27 W / 31 L, win 47 %), mean +21.3 % [-3, +47], median -11.0 %, total Rs 116,626, avg win Rs 8,023 (+100 %), avg loss Rs -3,226 (-47 %), max up mean 101 % (>= +100 % on 40 %), MFE 101 %, MAE -45 %, top-5 % share 52 %, without top 3 +5.6 %
- up: n 38 (13 W / 25 L, win 34 %), mean +8.0 % [-16, +36], median -15.0 %, total Rs 22,623, avg win Rs 6,791 (+94 %), avg loss Rs -2,626 (-37 %), max up mean 105 % (>= +100 % on 45 %), MFE 105 %, MAE -41 %, top-5 % share 184 %, without top 3 -10.5 %

**X07 Market breadth, previous session**
- high: n 31 (10 W / 21 L, win 32 %), mean +0.7 % [-27, +36], median -51.2 %, total Rs 37,013, avg win Rs 10,376 (+98 %), avg loss Rs -3,178 (-46 %), max up mean 83 % (>= +100 % on 32 %), MFE 83 %, MAE -57 %, top-5 % share 183 %, without top 3 -23.8 %
- low: n 43 (18 W / 25 L, win 42 %), mean +9.1 % [-13, +33], median -21.4 %, total Rs 46,868, avg win Rs 7,209 (+89 %), avg loss Rs -3,316 (-48 %), max up mean 108 % (>= +100 % on 51 %), MFE 108 %, MAE -49 %, top-5 % share 100 %, without top 3 -3.5 %
- mid: n 79 (35 W / 44 L, win 44 %), mean +33.7 % [+9, +60], median -9.8 %, total Rs 168,051, avg win Rs 8,484 (+128 %), avg loss Rs -2,929 (-42 %), max up mean 113 % (>= +100 % on 39 %), MFE 113 %, MAE -41 %, top-5 % share 41 %, without top 3 +20.7 %

**X08 Sector leadership (Bank minus Nifty)**
- bank_lags: n 24 (14 W / 10 L, win 58 %), mean +36.5 % [-2, +77], median +12.9 %, total Rs 83,768, avg win Rs 8,334 (+97 %), avg loss Rs -3,291 (-49 %), max up mean 96 % (>= +100 % on 42 %), MFE 96 %, MAE -45 %, top-5 % share 46 %, without top 3 +8.2 %
- bank_leads: n 31 (16 W / 15 L, win 52 %), mean +23.3 % [-7, +62], median +7.6 %, total Rs 65,157, avg win Rs 6,760 (+88 %), avg loss Rs -2,867 (-46 %), max up mean 120 % (>= +100 % on 42 %), MFE 120 %, MAE -46 %, top-5 % share 82 %, without top 3 +1.1 %
- in_line: n 98 (33 W / 65 L, win 34 %), mean +15.1 % [-4, +38], median -31.1 %, total Rs 103,008, avg win Rs 9,261 (+130 %), avg loss Rs -3,117 (-43 %), max up mean 103 % (>= +100 % on 41 %), MFE 103 %, MAE -48 %, top-5 % share 85 %, without top 3 +4.1 %

**X09 FII / DII cash (limited window, third party)**
- both_buy: n 15 (1 W / 14 L, win 7 %), mean -29.4 % [-47, -3], median -51.6 %, total Rs -29,621, avg win Rs 9,193 (+128 %), avg loss Rs -2,772 (-41 %), max up mean 82 % (>= +100 % on 27 %), MFE 82 %, MAE -50 %, without top 3 -45.7 %
- diverge: n 44 (21 W / 23 L, win 48 %), mean +34.3 % [+3, +71], median -5.1 %, total Rs 117,057, avg win Rs 8,984 (+124 %), avg loss Rs -3,113 (-48 %), max up mean 121 % (>= +100 % on 41 %), MFE 121 %, MAE -45 %, top-5 % share 49 %, without top 3 +12.8 %

**X10 FII futures level**
- high: n 24 (10 W / 14 L, win 42 %), mean +45.2 % [-4, +100], median -13.2 %, total Rs 70,316, avg win Rs 10,156 (+161 %), avg loss Rs -2,231 (-38 %), max up mean 154 % (>= +100 % on 67 %), MFE 154 %, MAE -39 %, top-5 % share 79 %, without top 3 +4.1 %
- low: n 100 (36 W / 64 L, win 36 %), mean +8.7 % [-9, +26], median -39.4 %, total Rs 79,625, avg win Rs 7,947 (+107 %), avg loss Rs -3,226 (-47 %), max up mean 91 % (>= +100 % on 36 %), MFE 91 %, MAE -51 %, top-5 % share 114 %, without top 3 -0.5 %
- mid: n 29 (17 W / 12 L, win 59 %), mean +38.8 % [+6, +78], median +8.9 %, total Rs 101,991, avg win Rs 8,400 (+95 %), avg loss Rs -3,401 (-40 %), max up mean 114 % (>= +100 % on 38 %), MFE 114 %, MAE -39 %, top-5 % share 43 %, without top 3 +11.9 %

**X11 News tone (GDELT, global)**
- above_median: n 68 (29 W / 39 L, win 43 %), mean +26.2 % [+2, +52], median -12.7 %, total Rs 136,495, avg win Rs 8,475 (+119 %), avg loss Rs -2,802 (-43 %), max up mean 110 % (>= +100 % on 43 %), MFE 110 %, MAE -45 %, top-5 % share 54 %, without top 3 +12.3 %
- below_median: n 80 (33 W / 47 L, win 41 %), mean +18.3 % [-3, +41], median -19.7 %, total Rs 130,723, avg win Rs 8,603 (+110 %), avg loss Rs -3,259 (-46 %), max up mean 104 % (>= +100 % on 41 %), MFE 104 %, MAE -48 %, top-5 % share 75 %, without top 3 +4.8 %

**X12 Scheduled events**
- day_after: n 8 too few (n < 10): no numbers
- day_before: n 6 too few (n < 10): no numbers
- event_day: n 12 (4 W / 8 L, win 33 %), mean -1.4 % [-37, +38], median -29.6 %, total Rs 4,317, avg win Rs 8,726 (+86 %), avg loss Rs -3,823 (-45 %), max up mean 68 % (>= +100 % on 25 %), MFE 68 %, MAE -58 %, top-5 % share 290 %, without top 3 -36.2 %
- none: n 128 (53 W / 75 L, win 41 %), mean +21.9 % [+4, +41], median -17.7 %, total Rs 226,784, avg win Rs 8,551 (+115 %), avg loss Rs -3,019 (-44 %), max up mean 109 % (>= +100 % on 44 %), MFE 109 %, MAE -46 %, top-5 % share 68 %, without top 3 +13.1 %

## G1
**H1 direction (ret20 quintile, 1 bearish .. 5 bullish)**
- 1: n 82 (29 W / 53 L, win 35 %), mean +6.2 % [-12, +26], median -39.4 %, total Rs 3,359, avg win Rs 8,225 (+102 %), avg loss Rs -4,437 (-46 %), max up mean 91 % (>= +100 % on 39 %), MFE 91 %, MAE -50 %, top-5 % share 2067 %, without top 3 -4.2 %
- 2: n 66 (22 W / 44 L, win 33 %), mean -9.6 % [-25, +8], median -51.5 %, total Rs -32,313, avg win Rs 5,884 (+69 %), avg loss Rs -3,676 (-49 %), max up mean 80 % (>= +100 % on 33 %), MFE 80 %, MAE -55 %, without top 3 -20.3 %
- 3: n 75 (23 W / 52 L, win 31 %), mean +9.8 % [-14, +36], median -50.7 %, total Rs 11,760, avg win Rs 8,645 (+136 %), avg loss Rs -3,597 (-46 %), max up mean 86 % (>= +100 % on 25 %), MFE 86 %, MAE -52 %, top-5 % share 533 %, without top 3 -4.9 %
- 4: n 20 (6 W / 14 L, win 30 %), mean +4.2 % [-33, +52], median -51.2 %, total Rs -3,404, avg win Rs 10,169 (+129 %), avg loss Rs -4,601 (-49 %), max up mean 102 % (>= +100 % on 35 %), MFE 102 %, MAE -47 %, without top 3 -31.9 %
- 5: n 16 (9 W / 7 L, win 56 %), mean +45.7 % [-5, +103], median +31.6 %, total Rs 61,045, avg win Rs 11,855 (+123 %), avg loss Rs -6,521 (-54 %), max up mean 130 % (>= +100 % on 44 %), MFE 130 %, MAE -42 %, top-5 % share 73 %, without top 3 +4.7 %

**H1b direction3**
- bearish: n 148 (51 W / 97 L, win 34 %), mean -0.8 % [-13, +12], median -51.0 %, total Rs -28,953, avg win Rs 7,215 (+88 %), avg loss Rs -4,092 (-48 %), max up mean 86 % (>= +100 % on 36 %), MFE 86 %, MAE -53 %, without top 3 -7.1 %
- bullish: n 36 (15 W / 21 L, win 42 %), mean +22.6 % [-10, +59], median -45.0 %, total Rs 57,642, avg win Rs 11,181 (+125 %), avg loss Rs -5,241 (-51 %), max up mean 115 % (>= +100 % on 39 %), MFE 115 %, MAE -45 %, top-5 % share 108 %, without top 3 -2.5 %
- sideways: n 75 (23 W / 52 L, win 31 %), mean +9.8 % [-14, +36], median -50.7 %, total Rs 11,760, avg win Rs 8,645 (+136 %), avg loss Rs -3,597 (-46 %), max up mean 86 % (>= +100 % on 25 %), MFE 86 %, MAE -52 %, top-5 % share 533 %, without top 3 -4.9 %

**H2 VIX level (previous close)**
- high: n 10 (2 W / 8 L, win 20 %), mean -22.1 % [-56, +23], median -50.9 %, total Rs -35,572, avg win Rs 16,821 (+101 %), avg loss Rs -8,652 (-53 %), max up mean 48 % (>= +100 % on 20 %), MFE 48 %, MAE -65 %, without top 3 -56.4 %
- low: n 132 (46 W / 86 L, win 35 %), mean +11.2 % [-5, +30], median -40.7 %, total Rs 60,878, avg win Rs 7,326 (+118 %), avg loss Rs -3,211 (-46 %), max up mean 99 % (>= +100 % on 37 %), MFE 99 %, MAE -49 %, top-5 % share 190 %, without top 3 +3.0 %
- normal: n 117 (41 W / 76 L, win 35 %), mean +1.4 % [-14, +19], median -51.1 %, total Rs 15,143, avg win Rs 8,875 (+94 %), avg loss Rs -4,588 (-49 %), max up mean 84 % (>= +100 % on 31 %), MFE 84 %, MAE -53 %, top-5 % share 963 %, without top 3 -8.1 %

**H3 VIX 5-day direction**
- falling: n 81 (31 W / 50 L, win 38 %), mean +16.5 % [-6, +42], median -38.8 %, total Rs 24,078, avg win Rs 7,531 (+122 %), avg loss Rs -4,188 (-49 %), max up mean 99 % (>= +100 % on 36 %), MFE 99 %, MAE -49 %, top-5 % share 308 %, without top 3 +2.0 %
- flat: n 109 (35 W / 74 L, win 32 %), mean +1.0 % [-15, +19], median -51.1 %, total Rs -1,629, avg win Rs 8,288 (+105 %), avg loss Rs -3,942 (-48 %), max up mean 84 % (>= +100 % on 28 %), MFE 84 %, MAE -53 %, without top 3 -9.0 %
- rising: n 69 (23 W / 46 L, win 33 %), mean -0.3 % [-16, +17], median -40.0 %, total Rs 17,999, avg win Rs 9,172 (+88 %), avg loss Rs -4,195 (-45 %), max up mean 91 % (>= +100 % on 39 %), MFE 91 %, MAE -52 %, top-5 % share 433 %, without top 3 -8.1 %

**H4 sudden VIX expansion**
- no: n 253 (88 W / 165 L, win 35 %), mean +6.1 % [-5, +18], median -50.9 %, total Rs 65,030, avg win Rs 8,269 (+106 %), avg loss Rs -4,016 (-47 %), max up mean 89 % (>= +100 % on 33 %), MFE 89 %, MAE -51 %, top-5 % share 369 %, without top 3 +1.1 %
- yes: n 6 too few (n < 10): no numbers

**H5 actual NIFTY opening gap**
- flat: n 165 (61 W / 104 L, win 37 %), mean +11.5 % [-3, +27], median -32.5 %, total Rs 166,905, avg win Rs 8,673 (+110 %), avg loss Rs -3,482 (-46 %), max up mean 99 % (>= +100 % on 38 %), MFE 99 %, MAE -49 %, top-5 % share 116 %, without top 3 +4.5 %
- gap-down: n 42 (14 W / 28 L, win 33 %), mean +1.8 % [-21, +27], median -51.1 %, total Rs -10,622, avg win Rs 9,717 (+104 %), avg loss Rs -5,238 (-49 %), max up mean 86 % (>= +100 % on 36 %), MFE 86 %, MAE -56 %, without top 3 -13.8 %
- gap-up: n 52 (14 W / 38 L, win 27 %), mean -10.6 % [-33, +18], median -51.2 %, total Rs -115,835, avg win Rs 4,960 (+95 %), avg loss Rs -4,876 (-49 %), max up mean 65 % (>= +100 % on 17 %), MFE 65 %, MAE -56 %, without top 3 -30.0 %

**H6 S&P previous session (agent 3, stale cache)**
- down: n 73 (25 W / 48 L, win 34 %), mean +12.5 % [-10, +37], median -51.0 %, total Rs 78,822, avg win Rs 10,913 (+127 %), avg loss Rs -4,042 (-47 %), max up mean 94 % (>= +100 % on 33 %), MFE 94 %, MAE -53 %, top-5 % share 127 %, without top 3 -2.1 %
- flat: n 81 (23 W / 58 L, win 28 %), mean -2.9 % [-22, +19], median -51.3 %, total Rs -18,634, avg win Rs 8,615 (+112 %), avg loss Rs -3,737 (-48 %), max up mean 85 % (>= +100 % on 31 %), MFE 85 %, MAE -55 %, without top 3 -16.0 %
- up: n 99 (38 W / 61 L, win 38 %), mean +7.4 % [-10, +25], median -38.7 %, total Rs -24,948, avg win Rs 6,472 (+94 %), avg loss Rs -4,441 (-47 %), max up mean 92 % (>= +100 % on 34 %), MFE 92 %, MAE -47 %, without top 3 -2.6 %

**H10 GIFT overnight, same-contract (PRIMARY)**
- flat: n 165 (57 W / 108 L, win 35 %), mean +8.5 % [-5, +24], median -50.8 %, total Rs 66,778, avg win Rs 8,009 (+113 %), avg loss Rs -3,608 (-47 %), max up mean 95 % (>= +100 % on 37 %), MFE 95 %, MAE -51 %, top-5 % share 205 %, without top 3 +1.4 %
- gap-down: n 43 (16 W / 27 L, win 37 %), mean +13.2 % [-15, +46], median -51.0 %, total Rs 65,283, avg win Rs 11,964 (+120 %), avg loss Rs -4,672 (-50 %), max up mean 103 % (>= +100 % on 30 %), MFE 103 %, MAE -52 %, top-5 % share 142 %, without top 3 -8.7 %
- gap-up: n 49 (16 W / 33 L, win 33 %), mean -9.1 % [-29, +14], median -51.1 %, total Rs -84,311, avg win Rs 5,411 (+72 %), avg loss Rs -5,178 (-48 %), max up mean 68 % (>= +100 % on 27 %), MFE 68 %, MAE -52 %, without top 3 -25.3 %

**H11 indicated vs actual opening, same-contract (PRIMARY)**
- in line: n 154 (50 W / 104 L, win 32 %), mean -0.6 % [-13, +13], median -51.0 %, total Rs -29,359, avg win Rs 7,252 (+95 %), avg loss Rs -3,769 (-47 %), max up mean 81 % (>= +100 % on 33 %), MFE 81 %, MAE -52 %, without top 3 -6.8 %
- stronger: n 58 (21 W / 37 L, win 36 %), mean +18.4 % [-8, +51], median -51.1 %, total Rs 87,090, avg win Rs 11,706 (+140 %), avg loss Rs -4,290 (-51 %), max up mean 106 % (>= +100 % on 31 %), MFE 106 %, MAE -52 %, top-5 % share 91 %, without top 3 -1.8 %
- weaker: n 45 (18 W / 27 L, win 40 %), mean +12.1 % [-15, +43], median -29.0 %, total Rs -9,980, avg win Rs 7,005 (+100 %), avg loss Rs -5,040 (-47 %), max up mean 105 % (>= +100 % on 40 %), MFE 105 %, MAE -47 %, without top 3 -7.6 %

**H12 Asia pre-entry (agent 3b, mean of available markets)**
- down: n 61 (21 W / 40 L, win 34 %), mean +8.4 % [-16, +36], median -51.1 %, total Rs 43,126, avg win Rs 10,932 (+123 %), avg loss Rs -4,661 (-52 %), max up mean 94 % (>= +100 % on 38 %), MFE 94 %, MAE -56 %, top-5 % share 234 %, without top 3 -8.2 %
- flat: n 97 (38 W / 59 L, win 39 %), mean +14.2 % [-6, +36], median -42.5 %, total Rs 70,841, avg win Rs 7,823 (+112 %), avg loss Rs -3,838 (-49 %), max up mean 98 % (>= +100 % on 35 %), MFE 98 %, MAE -49 %, top-5 % share 118 %, without top 3 +3.0 %
- up: n 99 (30 W / 69 L, win 30 %), mean -3.7 % [-19, +13], median -48.7 %, total Rs -66,217, avg win Rs 6,922 (+89 %), avg loss Rs -3,969 (-44 %), max up mean 82 % (>= +100 % on 30 %), MFE 82 %, MAE -50 %, without top 3 -13.2 %

**X01 S&P 500 previous US session**
- down: n 76 (27 W / 49 L, win 36 %), mean +11.9 % [-9, +35], median -50.9 %, total Rs 78,454, avg win Rs 10,268 (+119 %), avg loss Rs -4,057 (-47 %), max up mean 93 % (>= +100 % on 33 %), MFE 93 %, MAE -52 %, top-5 % share 128 %, without top 3 -2.1 %
- flat: n 82 (23 W / 59 L, win 28 %), mean -3.4 % [-22, +19], median -51.3 %, total Rs -22,889, avg win Rs 8,615 (+112 %), avg loss Rs -3,746 (-48 %), max up mean 86 % (>= +100 % on 32 %), MFE 86 %, MAE -55 %, without top 3 -16.4 %
- up: n 101 (39 W / 62 L, win 39 %), mean +7.9 % [-9, +26], median -38.7 %, total Rs -15,117, avg win Rs 6,644 (+95 %), avg loss Rs -4,423 (-47 %), max up mean 92 % (>= +100 % on 36 %), MFE 92 %, MAE -48 %, without top 3 -1.9 %

**X02 USD/INR previous session (hourly)**
- down: n 27 (10 W / 17 L, win 37 %), mean +16.1 % [-25, +63], median -51.2 %, total Rs 43,293, avg win Rs 12,502 (+131 %), avg loss Rs -4,808 (-52 %), max up mean 115 % (>= +100 % on 33 %), MFE 115 %, MAE -57 %, top-5 % share 139 %, without top 3 -19.2 %
- flat: n 155 (50 W / 105 L, win 32 %), mean +1.7 % [-12, +16], median -51.0 %, total Rs 66,107, avg win Rs 9,068 (+104 %), avg loss Rs -3,688 (-47 %), max up mean 85 % (>= +100 % on 34 %), MFE 85 %, MAE -52 %, top-5 % share 209 %, without top 3 -4.5 %
- up: n 54 (19 W / 35 L, win 35 %), mean -3.9 % [-22, +17], median -51.1 %, total Rs -68,356, avg win Rs 5,964 (+79 %), avg loss Rs -5,191 (-49 %), max up mean 77 % (>= +100 % on 28 %), MFE 77 %, MAE -52 %, without top 3 -16.7 %

**X03 Brent previous day (quality-limited)**
- down: n 71 (23 W / 48 L, win 32 %), mean +5.8 % [-16, +32], median -51.2 %, total Rs 4,471, avg win Rs 8,603 (+120 %), avg loss Rs -4,029 (-49 %), max up mean 92 % (>= +100 % on 28 %), MFE 92 %, MAE -54 %, top-5 % share 1750 %, without top 3 -10.9 %
- flat: n 107 (41 W / 66 L, win 38 %), mean +14.8 % [-3, +35], median -50.9 %, total Rs 89,752, avg win Rs 8,261 (+115 %), avg loss Rs -3,772 (-48 %), max up mean 99 % (>= +100 % on 41 %), MFE 99 %, MAE -50 %, top-5 % share 119 %, without top 3 +4.8 %
- up: n 78 (25 W / 53 L, win 32 %), mean -5.3 % [-21, +10], median -41.9 %, total Rs -33,161, avg win Rs 7,918 (+80 %), avg loss Rs -4,360 (-46 %), max up mean 80 % (>= +100 % on 29 %), MFE 80 %, MAE -50 %, without top 3 -13.7 %

**X04 US VIX spike**
- no_spike: n 221 (77 W / 144 L, win 35 %), mean +4.8 % [-7, +17], median -50.8 %, total Rs 8,517, avg win Rs 7,523 (+102 %), avg loss Rs -3,964 (-47 %), max up mean 89 % (>= +100 % on 33 %), MFE 89 %, MAE -51 %, top-5 % share 2236 %, without top 3 -0.6 %
- spike: n 21 (5 W / 16 L, win 24 %), mean -3.7 % [-41, +49], median -51.1 %, total Rs 10,072, avg win Rs 15,812 (+138 %), avg loss Rs -4,312 (-48 %), max up mean 88 % (>= +100 % on 24 %), MFE 88 %, MAE -57 %, top-5 % share 685 %, without top 3 -40.0 %

**X05 Global risk-on / off**
- mixed: n 88 (28 W / 60 L, win 32 %), mean +1.0 % [-18, +21], median -51.3 %, total Rs -6,925, avg win Rs 7,737 (+107 %), avg loss Rs -3,726 (-49 %), max up mean 90 % (>= +100 % on 34 %), MFE 90 %, MAE -52 %, without top 3 -11.0 %
- risk_off: n 59 (21 W / 38 L, win 36 %), mean +11.3 % [-13, +38], median -50.9 %, total Rs 54,291, avg win Rs 10,070 (+118 %), avg loss Rs -4,136 (-47 %), max up mean 94 % (>= +100 % on 37 %), MFE 94 %, MAE -52 %, top-5 % share 103 %, without top 3 -4.7 %
- risk_on: n 81 (30 W / 51 L, win 37 %), mean +1.1 % [-16, +19], median -38.8 %, total Rs -46,816, avg win Rs 6,241 (+82 %), avg loss Rs -4,589 (-46 %), max up mean 83 % (>= +100 % on 32 %), MFE 83 %, MAE -48 %, without top 3 -8.7 %

**X06 Asia pre-entry (agent 4, needs both markets)**
- down: n 56 (19 W / 37 L, win 34 %), mean +5.0 % [-18, +30], median -51.1 %, total Rs 12,845, avg win Rs 9,708 (+115 %), avg loss Rs -4,638 (-51 %), max up mean 88 % (>= +100 % on 39 %), MFE 88 %, MAE -55 %, top-5 % share 439 %, without top 3 -9.2 %
- flat: n 89 (36 W / 53 L, win 40 %), mean +16.5 % [-4, +38], median -42.5 %, total Rs 87,079, avg win Rs 7,988 (+114 %), avg loss Rs -3,783 (-50 %), max up mean 101 % (>= +100 % on 36 %), MFE 101 %, MAE -49 %, top-5 % share 96 %, without top 3 +4.4 %
- up: n 83 (24 W / 59 L, win 29 %), mean -10.9 % [-24, +4], median -50.7 %, total Rs -99,375, avg win Rs 5,972 (+69 %), avg loss Rs -4,114 (-43 %), max up mean 74 % (>= +100 % on 29 %), MFE 74 %, MAE -49 %, without top 3 -19.7 %

**X07 Market breadth, previous session**
- high: n 68 (23 W / 45 L, win 34 %), mean -2.3 % [-19, +18], median -51.1 %, total Rs 42,371, avg win Rs 10,221 (+88 %), avg loss Rs -4,282 (-48 %), max up mean 75 % (>= +100 % on 29 %), MFE 75 %, MAE -54 %, top-5 % share 281 %, without top 3 -13.9 %
- low: n 81 (23 W / 58 L, win 28 %), mean -8.1 % [-25, +12], median -51.4 %, total Rs -88,509, avg win Rs 6,892 (+94 %), avg loss Rs -4,259 (-49 %), max up mean 86 % (>= +100 % on 36 %), MFE 86 %, MAE -56 %, without top 3 -18.7 %
- mid: n 109 (43 W / 66 L, win 39 %), mean +21.0 % [+3, +42], median -29.0 %, total Rs 91,471, avg win Rs 7,928 (+124 %), avg loss Rs -3,779 (-46 %), max up mean 104 % (>= +100 % on 35 %), MFE 104 %, MAE -46 %, top-5 % share 105 %, without top 3 +11.3 %

**X08 Sector leadership (Bank minus Nifty)**
- bank_lags: n 51 (19 W / 32 L, win 37 %), mean +2.5 % [-19, +27], median -51.0 %, total Rs -6,420, avg win Rs 8,493 (+93 %), avg loss Rs -5,243 (-51 %), max up mean 77 % (>= +100 % on 25 %), MFE 77 %, MAE -53 %, without top 3 -12.2 %
- bank_leads: n 64 (28 W / 36 L, win 44 %), mean +15.2 % [-7, +40], median -50.7 %, total Rs 72,328, avg win Rs 7,994 (+99 %), avg loss Rs -4,208 (-50 %), max up mean 103 % (>= +100 % on 39 %), MFE 103 %, MAE -50 %, top-5 % share 123 %, without top 3 -1.0 %
- in_line: n 143 (42 W / 101 L, win 29 %), mean +2.6 % [-12, +19], median -51.1 %, total Rs -20,573, avg win Rs 8,317 (+118 %), avg loss Rs -3,662 (-46 %), max up mean 90 % (>= +100 % on 34 %), MFE 90 %, MAE -51 %, without top 3 -5.1 %

**X09 FII / DII cash (limited window, third party)**
- both_buy: n 18 (2 W / 16 L, win 11 %), mean -26.9 % [-45, -1], median -43.9 %, total Rs -39,855, avg win Rs 6,522 (+89 %), avg loss Rs -3,306 (-41 %), max up mean 76 % (>= +100 % on 22 %), MFE 76 %, MAE -49 %, without top 3 -43.5 %
- diverge: n 84 (29 W / 55 L, win 35 %), mean +6.7 % [-13, +29], median -51.0 %, total Rs 28,281, avg win Rs 10,062 (+114 %), avg loss Rs -4,791 (-50 %), max up mean 95 % (>= +100 % on 33 %), MFE 95 %, MAE -54 %, top-5 % share 352 %, without top 3 -5.2 %

**X10 FII futures level**
- high: n 41 (13 W / 28 L, win 32 %), mean +18.6 % [-15, +55], median -51.1 %, total Rs 39,077, avg win Rs 10,155 (+153 %), avg loss Rs -3,319 (-44 %), max up mean 116 % (>= +100 % on 49 %), MFE 116 %, MAE -48 %, top-5 % share 160 %, without top 3 -7.1 %
- low: n 156 (52 W / 104 L, win 33 %), mean -0.5 % [-13, +13], median -51.0 %, total Rs -10,421, avg win Rs 7,992 (+95 %), avg loss Rs -4,096 (-48 %), max up mean 85 % (>= +100 % on 33 %), MFE 85 %, MAE -54 %, without top 3 -6.5 %
- mid: n 60 (24 W / 36 L, win 40 %), mean +14.0 % [-10, +42], median -39.5 %, total Rs 25,007, avg win Rs 7,789 (+106 %), avg loss Rs -4,498 (-48 %), max up mean 90 % (>= +100 % on 25 %), MFE 90 %, MAE -48 %, top-5 % share 187 %, without top 3 -3.8 %

**X11 News tone (GDELT, global)**
- above_median: n 101 (39 W / 62 L, win 39 %), mean +15.2 % [-3, +35], median -30.3 %, total Rs 76,794, avg win Rs 7,687 (+113 %), avg loss Rs -3,597 (-46 %), max up mean 101 % (>= +100 % on 38 %), MFE 101 %, MAE -49 %, top-5 % share 137 %, without top 3 +5.6 %
- below_median: n 147 (48 W / 99 L, win 33 %), mean +1.7 % [-13, +17], median -51.1 %, total Rs -6,204, avg win Rs 8,884 (+104 %), avg loss Rs -4,370 (-48 %), max up mean 85 % (>= +100 % on 31 %), MFE 85 %, MAE -53 %, without top 3 -7.0 %

**X12 Scheduled events**
- day_after: n 13 (4 W / 9 L, win 31 %), mean +7.4 % [-44, +76], median -51.1 %, total Rs -4,844, avg win Rs 9,884 (+144 %), avg loss Rs -4,931 (-53 %), max up mean 81 % (>= +100 % on 31 %), MFE 81 %, MAE -53 %, without top 3 -48.0 %
- day_before: n 10 (3 W / 7 L, win 30 %), mean -21.8 % [-42, +3], median -41.6 %, total Rs -20,181, avg win Rs 1,755 (+29 %), avg loss Rs -3,635 (-44 %), max up mean 60 % (>= +100 % on 10 %), MFE 60 %, MAE -50 %, without top 3 -43.5 %
- event_day: n 15 (6 W / 9 L, win 40 %), mean +0.8 % [-34, +36], median -29.0 %, total Rs 12,261, avg win Rs 8,679 (+76 %), avg loss Rs -4,424 (-49 %), max up mean 73 % (>= +100 % on 27 %), MFE 73 %, MAE -56 %, top-5 % share 102 %, without top 3 -28.9 %
- none: n 221 (76 W / 145 L, win 34 %), mean +6.9 % [-4, +20], median -50.9 %, total Rs 53,213, avg win Rs 8,390 (+110 %), avg loss Rs -4,030 (-47 %), max up mean 93 % (>= +100 % on 35 %), MFE 93 %, MAE -51 %, top-5 % share 418 %, without top 3 +1.3 %

## G1-C
**H1 direction (ret20 quintile, 1 bearish .. 5 bullish)**
- 1: n 75 (20 W / 55 L, win 27 %), mean -12.1 % [-30, +7], median -51.4 %, total Rs -100,603, avg win Rs 9,549 (+94 %), avg loss Rs -5,302 (-51 %), max up mean 68 % (>= +100 % on 21 %), MFE 68 %, MAE -58 %, without top 3 -23.9 %
- 2: n 55 (22 W / 33 L, win 40 %), mean +4.4 % [-15, +25], median -34.3 %, total Rs 73,456, avg win Rs 9,486 (+86 %), avg loss Rs -4,098 (-50 %), max up mean 72 % (>= +100 % on 24 %), MFE 72 %, MAE -49 %, top-5 % share 65 %, without top 3 -6.8 %
- 3: n 64 (22 W / 42 L, win 34 %), mean -6.1 % [-22, +13], median -51.2 %, total Rs 3,050, avg win Rs 8,057 (+75 %), avg loss Rs -4,148 (-49 %), max up mean 55 % (>= +100 % on 17 %), MFE 55 %, MAE -54 %, top-5 % share 2214 %, without top 3 -17.1 %
- 4: n 29 (4 W / 25 L, win 14 %), mean -33.2 % [-50, -8], median -51.4 %, total Rs -78,176, avg win Rs 11,688 (+80 %), avg loss Rs -4,997 (-51 %), max up mean 70 % (>= +100 % on 14 %), MFE 70 %, MAE -66 %, without top 3 -49.1 %
- 5: n 12 (1 W / 11 L, win 8 %), mean -42.8 % [-56, -29], median -51.6 %, total Rs -56,507, avg win Rs 2,222 (+18 %), avg loss Rs -5,339 (-48 %), max up mean 59 % (>= +100 % on 17 %), MFE 59 %, MAE -65 %, without top 3 -55.3 %

**H1b direction3**
- bearish: n 130 (42 W / 88 L, win 32 %), mean -5.1 % [-18, +10], median -51.2 %, total Rs -27,148, avg win Rs 9,516 (+90 %), avg loss Rs -4,850 (-50 %), max up mean 70 % (>= +100 % on 22 %), MFE 70 %, MAE -55 %, without top 3 -11.8 %
- bullish: n 41 (5 W / 36 L, win 12 %), mean -36.0 % [-49, -18], median -51.4 %, total Rs -134,683, avg win Rs 9,795 (+67 %), avg loss Rs -5,102 (-50 %), max up mean 67 % (>= +100 % on 15 %), MFE 67 %, MAE -66 %, without top 3 -47.1 %
- sideways: n 64 (22 W / 42 L, win 34 %), mean -6.1 % [-22, +13], median -51.2 %, total Rs 3,050, avg win Rs 8,057 (+75 %), avg loss Rs -4,148 (-49 %), max up mean 55 % (>= +100 % on 17 %), MFE 55 %, MAE -54 %, top-5 % share 2214 %, without top 3 -17.1 %

**H2 VIX level (previous close)**
- high: n 13 (4 W / 9 L, win 31 %), mean -9.2 % [-49, +42], median -50.9 %, total Rs 6,089, avg win Rs 21,926 (+98 %), avg loss Rs -9,069 (-57 %), max up mean 67 % (>= +100 % on 23 %), MFE 67 %, MAE -56 %, top-5 % share 836 %, without top 3 -48.2 %
- low: n 117 (33 W / 84 L, win 28 %), mean -13.5 % [-25, -1], median -51.4 %, total Rs -99,314, avg win Rs 7,765 (+78 %), avg loss Rs -4,233 (-50 %), max up mean 55 % (>= +100 % on 21 %), MFE 55 %, MAE -56 %, without top 3 -19.3 %
- normal: n 105 (32 W / 73 L, win 30 %), mean -7.9 % [-22, +9], median -51.2 %, total Rs -65,556, avg win Rs 8,811 (+87 %), avg loss Rs -4,760 (-49 %), max up mean 77 % (>= +100 % on 18 %), MFE 77 %, MAE -56 %, without top 3 -16.6 %

**H3 VIX 5-day direction**
- falling: n 61 (22 W / 39 L, win 36 %), mean +0.6 % [-19, +23], median -51.6 %, total Rs 63,144, avg win Rs 10,105 (+91 %), avg loss Rs -4,081 (-50 %), max up mean 62 % (>= +100 % on 18 %), MFE 62 %, MAE -52 %, top-5 % share 161 %, without top 3 -12.7 %
- flat: n 107 (28 W / 79 L, win 26 %), mean -15.6 % [-28, -3], median -51.3 %, total Rs -120,970, avg win Rs 9,284 (+79 %), avg loss Rs -4,822 (-49 %), max up mean 62 % (>= +100 % on 21 %), MFE 62 %, MAE -57 %, without top 3 -23.2 %
- rising: n 67 (19 W / 48 L, win 28 %), mean -13.5 % [-30, +4], median -51.1 %, total Rs -100,955, avg win Rs 7,560 (+80 %), avg loss Rs -5,096 (-51 %), max up mean 72 % (>= +100 % on 18 %), MFE 72 %, MAE -58 %, without top 3 -24.1 %

**H4 sudden VIX expansion**
- no: n 231 (67 W / 164 L, win 29 %), mean -11.1 % [-20, -1], median -51.3 %, total Rs -170,962, avg win Rs 8,912 (+84 %), avg loss Rs -4,683 (-50 %), max up mean 63 % (>= +100 % on 19 %), MFE 63 %, MAE -56 %, without top 3 -15.0 %
- yes: n 4 too few (n < 10): no numbers

**H5 actual NIFTY opening gap**
- flat: n 155 (48 W / 107 L, win 31 %), mean -9.4 % [-21, +3], median -51.2 %, total Rs -118,481, avg win Rs 8,132 (+83 %), avg loss Rs -4,755 (-51 %), max up mean 69 % (>= +100 % on 21 %), MFE 69 %, MAE -55 %, without top 3 -15.2 %
- gap-down: n 43 (11 W / 32 L, win 26 %), mean -11.2 % [-31, +15], median -51.4 %, total Rs 5,306, avg win Rs 14,287 (+95 %), avg loss Rs -4,745 (-48 %), max up mean 57 % (>= +100 % on 16 %), MFE 57 %, MAE -60 %, top-5 % share 1668 %, without top 3 -26.8 %
- gap-up: n 37 (10 W / 27 L, win 27 %), mean -16.1 % [-36, +9], median -51.4 %, total Rs -45,606, avg win Rs 7,839 (+74 %), avg loss Rs -4,593 (-50 %), max up mean 59 % (>= +100 % on 16 %), MFE 59 %, MAE -58 %, without top 3 -31.2 %

**H6 S&P previous session (agent 3, stale cache)**
- down: n 64 (20 W / 44 L, win 31 %), mean -3.0 % [-21, +18], median -50.9 %, total Rs 2,289, avg win Rs 10,539 (+93 %), avg loss Rs -4,738 (-47 %), max up mean 75 % (>= +100 % on 22 %), MFE 75 %, MAE -54 %, top-5 % share 4273 %, without top 3 -15.8 %
- flat: n 76 (25 W / 51 L, win 33 %), mean -13.3 % [-27, +2], median -51.1 %, total Rs -77,386, avg win Rs 6,844 (+62 %), avg loss Rs -4,872 (-50 %), max up mean 66 % (>= +100 % on 16 %), MFE 66 %, MAE -53 %, without top 3 -21.3 %
- up: n 87 (22 W / 65 L, win 25 %), mean -13.9 % [-30, +2], median -51.7 %, total Rs -70,036, avg win Rs 10,347 (+97 %), avg loss Rs -4,580 (-52 %), max up mean 56 % (>= +100 % on 21 %), MFE 56 %, MAE -61 %, without top 3 -23.8 %

**H10 GIFT overnight, same-contract (PRIMARY)**
- flat: n 149 (50 W / 99 L, win 34 %), mean -7.4 % [-19, +4], median -51.1 %, total Rs -39,205, avg win Rs 8,299 (+76 %), avg loss Rs -4,587 (-50 %), max up mean 60 % (>= +100 % on 19 %), MFE 60 %, MAE -55 %, without top 3 -12.9 %
- gap-down: n 33 (6 W / 27 L, win 18 %), mean -16.5 % [-40, +13], median -51.6 %, total Rs -17,085, avg win Rs 18,900 (+130 %), avg loss Rs -4,833 (-49 %), max up mean 98 % (>= +100 % on 24 %), MFE 98 %, MAE -60 %, without top 3 -37.1 %
- gap-up: n 51 (13 W / 38 L, win 25 %), mean -15.4 % [-35, +9], median -51.4 %, total Rs -85,589, avg win Rs 7,505 (+89 %), avg loss Rs -4,820 (-51 %), max up mean 61 % (>= +100 % on 18 %), MFE 61 %, MAE -57 %, without top 3 -30.7 %

**H11 indicated vs actual opening, same-contract (PRIMARY)**
- in line: n 145 (42 W / 103 L, win 29 %), mean -13.0 % [-23, -1], median -51.2 %, total Rs -145,330, avg win Rs 7,724 (+78 %), avg loss Rs -4,561 (-50 %), max up mean 54 % (>= +100 % on 17 %), MFE 54 %, MAE -56 %, without top 3 -19.0 %
- stronger: n 38 (7 W / 31 L, win 18 %), mean -24.0 % [-43, +0], median -52.1 %, total Rs -59,338, avg win Rs 13,038 (+96 %), avg loss Rs -4,858 (-51 %), max up mean 94 % (>= +100 % on 24 %), MFE 94 %, MAE -60 %, without top 3 -41.1 %
- weaker: n 50 (20 W / 30 L, win 40 %), mean +7.2 % [-16, +33], median -44.4 %, total Rs 62,788, avg win Rs 10,511 (+91 %), avg loss Rs -4,914 (-49 %), max up mean 77 % (>= +100 % on 24 %), MFE 77 %, MAE -53 %, top-5 % share 143 %, without top 3 -8.4 %

**H12 Asia pre-entry (agent 3b, mean of available markets)**
- down: n 57 (17 W / 40 L, win 30 %), mean -12.1 % [-30, +10], median -51.6 %, total Rs -41,995, avg win Rs 10,062 (+83 %), avg loss Rs -5,326 (-53 %), max up mean 73 % (>= +100 % on 18 %), MFE 73 %, MAE -57 %, without top 3 -25.3 %
- flat: n 96 (34 W / 62 L, win 35 %), mean -4.3 % [-19, +12], median -51.0 %, total Rs 13,853, avg win Rs 8,700 (+77 %), avg loss Rs -4,548 (-49 %), max up mean 67 % (>= +100 % on 20 %), MFE 67 %, MAE -54 %, top-5 % share 924 %, without top 3 -12.7 %
- up: n 79 (18 W / 61 L, win 23 %), mean -16.2 % [-31, +0], median -51.4 %, total Rs -108,610, avg win Rs 8,836 (+96 %), avg loss Rs -4,388 (-49 %), max up mean 59 % (>= +100 % on 22 %), MFE 59 %, MAE -58 %, without top 3 -26.1 %

**X01 S&P 500 previous US session**
- down: n 66 (21 W / 45 L, win 32 %), mean -0.9 % [-20, +21], median -50.9 %, total Rs 12,865, avg win Rs 10,767 (+97 %), avg loss Rs -4,739 (-47 %), max up mean 77 % (>= +100 % on 23 %), MFE 77 %, MAE -53 %, top-5 % share 760 %, without top 3 -13.2 %
- flat: n 80 (26 W / 54 L, win 32 %), mean -14.6 % [-28, -0], median -51.2 %, total Rs -92,927, avg win Rs 6,621 (+60 %), avg loss Rs -4,909 (-51 %), max up mean 66 % (>= +100 % on 16 %), MFE 66 %, MAE -53 %, without top 3 -22.3 %
- up: n 89 (22 W / 67 L, win 25 %), mean -14.7 % [-30, +2], median -51.6 %, total Rs -78,718, avg win Rs 10,347 (+97 %), avg loss Rs -4,572 (-51 %), max up mean 55 % (>= +100 % on 20 %), MFE 55 %, MAE -61 %, without top 3 -24.4 %

**X02 USD/INR previous session (hourly)**
- down: n 23 (5 W / 18 L, win 22 %), mean -16.0 % [-42, +18], median -51.4 %, total Rs -39,609, avg win Rs 8,174 (+98 %), avg loss Rs -4,471 (-48 %), max up mean 94 % (>= +100 % on 17 %), MFE 94 %, MAE -57 %, without top 3 -40.9 %
- flat: n 147 (49 W / 98 L, win 33 %), mean -4.5 % [-17, +9], median -51.1 %, total Rs -18,146, avg win Rs 9,643 (+90 %), avg loss Rs -5,007 (-52 %), max up mean 63 % (>= +100 % on 22 %), MFE 63 %, MAE -55 %, without top 3 -10.5 %
- up: n 50 (13 W / 37 L, win 26 %), mean -20.2 % [-33, -7], median -51.3 %, total Rs -82,152, avg win Rs 8,106 (+54 %), avg loss Rs -5,068 (-46 %), max up mean 53 % (>= +100 % on 14 %), MFE 53 %, MAE -53 %, without top 3 -26.6 %

**X03 Brent previous day (quality-limited)**
- down: n 58 (18 W / 40 L, win 31 %), mean -10.2 % [-27, +9], median -51.3 %, total Rs -18,288, avg win Rs 9,336 (+77 %), avg loss Rs -4,658 (-49 %), max up mean 58 % (>= +100 % on 17 %), MFE 58 %, MAE -54 %, without top 3 -20.3 %
- flat: n 96 (28 W / 68 L, win 29 %), mean -9.9 % [-24, +5], median -51.2 %, total Rs -29,108, avg win Rs 9,411 (+86 %), avg loss Rs -4,303 (-49 %), max up mean 70 % (>= +100 % on 21 %), MFE 70 %, MAE -57 %, without top 3 -17.9 %
- up: n 80 (22 W / 58 L, win 28 %), mean -12.6 % [-29, +5], median -51.4 %, total Rs -112,763, avg win Rs 8,770 (+89 %), avg loss Rs -5,271 (-51 %), max up mean 63 % (>= +100 % on 20 %), MFE 63 %, MAE -58 %, without top 3 -23.6 %

**X04 US VIX spike**
- no_spike: n 191 (50 W / 141 L, win 26 %), mean -15.3 % [-25, -4], median -51.4 %, total Rs -252,758, avg win Rs 8,593 (+85 %), avg loss Rs -4,840 (-51 %), max up mean 63 % (>= +100 % on 18 %), MFE 63 %, MAE -59 %, without top 3 -20.1 %
- spike: n 23 (11 W / 12 L, win 48 %), mean +25.9 % [-6, +61], median -1.4 %, total Rs 81,423, avg win Rs 11,711 (+99 %), avg loss Rs -3,950 (-41 %), max up mean 84 % (>= +100 % on 26 %), MFE 84 %, MAE -44 %, top-5 % share 49 %, without top 3 +2.0 %

**X05 Global risk-on / off**
- mixed: n 83 (23 W / 60 L, win 28 %), mean -15.0 % [-29, +1], median -51.4 %, total Rs -96,089, avg win Rs 7,939 (+77 %), avg loss Rs -4,645 (-50 %), max up mean 69 % (>= +100 % on 19 %), MFE 69 %, MAE -56 %, without top 3 -24.3 %
- risk_off: n 52 (18 W / 34 L, win 35 %), mean +2.5 % [-19, +25], median -50.9 %, total Rs 38,101, avg win Rs 11,030 (+95 %), avg loss Rs -4,719 (-47 %), max up mean 79 % (>= +100 % on 23 %), MFE 79 %, MAE -52 %, top-5 % share 207 %, without top 3 -11.5 %
- risk_on: n 69 (17 W / 52 L, win 25 %), mean -15.2 % [-32, +4], median -51.6 %, total Rs -92,699, avg win Rs 8,596 (+97 %), avg loss Rs -4,593 (-52 %), max up mean 56 % (>= +100 % on 19 %), MFE 56 %, MAE -62 %, without top 3 -26.8 %

**X06 Asia pre-entry (agent 4, needs both markets)**
- down: n 52 (15 W / 37 L, win 29 %), mean -9.9 % [-30, +12], median -51.6 %, total Rs -19,417, avg win Rs 11,229 (+93 %), avg loss Rs -5,077 (-52 %), max up mean 76 % (>= +100 % on 19 %), MFE 76 %, MAE -57 %, without top 3 -24.4 %
- flat: n 86 (28 W / 58 L, win 33 %), mean -8.3 % [-23, +7], median -51.2 %, total Rs -55,779, avg win Rs 7,418 (+76 %), avg loss Rs -4,543 (-49 %), max up mean 67 % (>= +100 % on 19 %), MFE 67 %, MAE -56 %, without top 3 -17.7 %
- up: n 66 (15 W / 51 L, win 23 %), mean -14.2 % [-31, +6], median -51.4 %, total Rs -75,491, avg win Rs 10,075 (+109 %), avg loss Rs -4,443 (-50 %), max up mean 61 % (>= +100 % on 23 %), MFE 61 %, MAE -59 %, without top 3 -26.1 %

**X07 Market breadth, previous session**
- high: n 62 (23 W / 39 L, win 37 %), mean +3.8 % [-18, +28], median -51.6 %, total Rs 78,061, avg win Rs 12,010 (+101 %), avg loss Rs -5,081 (-54 %), max up mean 88 % (>= +100 % on 23 %), MFE 88 %, MAE -51 %, top-5 % share 136 %, without top 3 -9.9 %
- low: n 82 (27 W / 55 L, win 33 %), mean -5.9 % [-21, +12], median -50.8 %, total Rs -40,874, avg win Rs 8,211 (+82 %), avg loss Rs -4,774 (-49 %), max up mean 65 % (>= +100 % on 22 %), MFE 65 %, MAE -56 %, without top 3 -14.9 %
- mid: n 90 (19 W / 71 L, win 21 %), mean -24.7 % [-36, -14], median -51.4 %, total Rs -190,029, avg win Rs 6,735 (+64 %), avg loss Rs -4,479 (-48 %), max up mean 45 % (>= +100 % on 14 %), MFE 45 %, MAE -60 %, without top 3 -30.1 %

**X08 Sector leadership (Bank minus Nifty)**
- bank_lags: n 55 (13 W / 42 L, win 24 %), mean -22.4 % [-36, -6], median -51.2 %, total Rs -125,841, avg win Rs 6,836 (+60 %), avg loss Rs -5,112 (-48 %), max up mean 51 % (>= +100 % on 15 %), MFE 51 %, MAE -55 %, without top 3 -32.7 %
- bank_leads: n 60 (24 W / 36 L, win 40 %), mean +11.5 % [-11, +36], median -51.0 %, total Rs 137,760, avg win Rs 12,153 (+106 %), avg loss Rs -4,276 (-51 %), max up mean 93 % (>= +100 % on 27 %), MFE 93 %, MAE -53 %, top-5 % share 56 %, without top 3 -2.0 %
- in_line: n 119 (32 W / 87 L, win 27 %), mean -16.3 % [-27, -4], median -51.3 %, total Rs -164,762, avg win Rs 7,667 (+76 %), avg loss Rs -4,714 (-50 %), max up mean 54 % (>= +100 % on 18 %), MFE 54 %, MAE -58 %, without top 3 -22.9 %

**X09 FII / DII cash (limited window, third party)**
- both_buy: n 19 (7 W / 12 L, win 37 %), mean -14.1 % [-35, +10], median -50.9 %, total Rs -13,464, avg win Rs 5,341 (+46 %), avg loss Rs -4,238 (-49 %), max up mean 47 % (>= +100 % on 16 %), MFE 47 %, MAE -54 %, without top 3 -30.9 %
- both_sell: n 4 too few (n < 10): no numbers
- diverge: n 69 (18 W / 51 L, win 26 %), mean -20.8 % [-36, -3], median -51.2 %, total Rs -141,921, avg win Rs 8,563 (+71 %), avg loss Rs -5,805 (-53 %), max up mean 52 % (>= +100 % on 13 %), MFE 52 %, MAE -56 %, without top 3 -31.3 %

**X10 FII futures level**
- high: n 37 (5 W / 32 L, win 14 %), mean -37.5 % [-47, -26], median -51.9 %, total Rs -105,528, avg win Rs 4,183 (+44 %), avg loss Rs -3,951 (-50 %), max up mean 49 % (>= +100 % on 14 %), MFE 49 %, MAE -68 %, without top 3 -46.3 %
- low: n 129 (38 W / 91 L, win 29 %), mean -15.3 % [-26, -3], median -51.3 %, total Rs -207,308, avg win Rs 6,899 (+71 %), avg loss Rs -5,159 (-51 %), max up mean 58 % (>= +100 % on 20 %), MFE 58 %, MAE -56 %, without top 3 -21.4 %
- mid: n 67 (26 W / 41 L, win 39 %), mean +13.3 % [-8, +37], median -37.8 %, total Rs 160,134, avg win Rs 13,186 (+109 %), avg loss Rs -4,456 (-48 %), max up mean 81 % (>= +100 % on 21 %), MFE 81 %, MAE -52 %, top-5 % share 63 %, without top 3 +0.9 %

**X11 News tone (GDELT, global)**
- above_median: n 93 (23 W / 70 L, win 25 %), mean -19.8 % [-33, -7], median -51.7 %, total Rs -123,212, avg win Rs 7,989 (+77 %), avg loss Rs -4,385 (-52 %), max up mean 61 % (>= +100 % on 18 %), MFE 61 %, MAE -59 %, without top 3 -27.3 %
- below_median: n 128 (39 W / 89 L, win 30 %), mean -8.1 % [-21, +6], median -51.2 %, total Rs -69,760, avg win Rs 9,808 (+86 %), avg loss Rs -5,082 (-49 %), max up mean 65 % (>= +100 % on 20 %), MFE 65 %, MAE -56 %, without top 3 -15.1 %

**X12 Scheduled events**
- day_after: n 15 (3 W / 12 L, win 20 %), mean -12.8 % [-46, +36], median -51.1 %, total Rs -16,794, avg win Rs 15,544 (+118 %), avg loss Rs -5,285 (-46 %), max up mean 53 % (>= +100 % on 13 %), MFE 53 %, MAE -58 %, without top 3 -45.5 %
- day_before: n 21 (9 W / 12 L, win 43 %), mean +8.2 % [-25, +46], median -23.9 %, total Rs 27,469, avg win Rs 10,362 (+83 %), avg loss Rs -5,482 (-48 %), max up mean 63 % (>= +100 % on 14 %), MFE 63 %, MAE -53 %, top-5 % share 238 %, without top 3 -21.7 %
- event_day: n 15 (6 W / 9 L, win 40 %), mean -3.9 % [-32, +28], median -51.2 %, total Rs 22,003, avg win Rs 9,600 (+62 %), avg loss Rs -3,955 (-48 %), max up mean 88 % (>= +100 % on 20 %), MFE 88 %, MAE -52 %, top-5 % share 60 %, without top 3 -26.8 %
- none: n 184 (51 W / 133 L, win 28 %), mean -13.3 % [-23, -2], median -51.3 %, total Rs -191,460, avg win Rs 8,400 (+84 %), avg loss Rs -4,661 (-51 %), max up mean 65 % (>= +100 % on 21 %), MFE 65 %, MAE -57 %, without top 3 -18.3 %

## XP
**H1 direction (ret20 quintile, 1 bearish .. 5 bullish)**
- 1: n 33 (9 W / 24 L, win 27 %), mean -11.5 % [-32, +12], median -19.9 %, total Rs -35,026, avg win Rs 6,602 (+73 %), avg loss Rs -3,935 (-43 %), max up mean 48 % (>= +100 % on 18 %), without top 3 -25.4 %
- 2: n 25 (11 W / 14 L, win 44 %), mean +4.9 % [-24, +35], median -7.4 %, total Rs -6,868, avg win Rs 5,679 (+79 %), avg loss Rs -4,953 (-54 %), max up mean 63 % (>= +100 % on 36 %), without top 3 -16.1 %
- 3: n 33 (11 W / 22 L, win 33 %), mean -12.0 % [-33, +11], median -28.0 %, total Rs -46,003, avg win Rs 4,416 (+65 %), avg loss Rs -4,299 (-51 %), max up mean 48 % (>= +100 % on 18 %), without top 3 -26.2 %
- 4: n 10 (3 W / 7 L, win 30 %), mean +8.6 % [-48, +96], median -23.3 %, total Rs 5,105, avg win Rs 10,638 (+138 %), avg loss Rs -3,830 (-47 %), max up mean 61 % (>= +100 % on 10 %), top-5 % share 511 %, without top 3 -47.1 %
- 5: n 6 too few (n < 10): no numbers

**H1b direction3**
- bearish: n 58 (20 W / 38 L, win 34 %), mean -4.4 % [-22, +14], median -14.7 %, total Rs -41,894, avg win Rs 6,094 (+77 %), avg loss Rs -4,310 (-47 %), max up mean 55 % (>= +100 % on 26 %), without top 3 -13.8 %
- bullish: n 16 (5 W / 11 L, win 31 %), mean +5.1 % [-41, +68], median -36.1 %, total Rs 8,261, avg win Rs 10,675 (+126 %), avg loss Rs -4,101 (-50 %), max up mean 61 % (>= +100 % on 12 %), top-5 % share 316 %, without top 3 -38.7 %
- sideways: n 33 (11 W / 22 L, win 33 %), mean -12.0 % [-33, +11], median -28.0 %, total Rs -46,003, avg win Rs 4,416 (+65 %), avg loss Rs -4,299 (-51 %), max up mean 48 % (>= +100 % on 18 %), without top 3 -26.2 %

**H2 VIX level (previous close)**
- high: n 6 too few (n < 10): no numbers
- low: n 51 (18 W / 33 L, win 35 %), mean -4.8 % [-23, +14], median -13.6 %, total Rs -28,664, avg win Rs 4,551 (+68 %), avg loss Rs -3,351 (-45 %), max up mean 52 % (>= +100 % on 22 %), without top 3 -15.3 %
- normal: n 50 (16 W / 34 L, win 32 %), mean -3.2 % [-26, +21], median -30.9 %, total Rs -20,336, avg win Rs 8,164 (+98 %), avg loss Rs -4,440 (-51 %), max up mean 58 % (>= +100 % on 24 %), without top 3 -18.1 %

**H3 VIX 5-day direction**
- falling: n 30 (16 W / 14 L, win 53 %), mean +32.7 % [+2, +69], median +8.0 %, total Rs 70,351, avg win Rs 6,944 (+96 %), avg loss Rs -2,911 (-39 %), max up mean 79 % (>= +100 % on 37 %), top-5 % share 65 %, without top 3 +11.2 %
- flat: n 43 (11 W / 32 L, win 26 %), mean -20.8 % [-38, -2], median -39.1 %, total Rs -88,188, avg win Rs 5,438 (+66 %), avg loss Rs -4,625 (-51 %), max up mean 41 % (>= +100 % on 14 %), without top 3 -31.5 %
- rising: n 34 (9 W / 25 L, win 26 %), mean -19.3 % [-39, +3], median -40.6 %, total Rs -61,798, avg win Rs 5,878 (+69 %), avg loss Rs -4,588 (-51 %), max up mean 46 % (>= +100 % on 18 %), without top 3 -34.6 %

**H4 sudden VIX expansion**
- no: n 105 (35 W / 70 L, win 33 %), mean -4.8 % [-19, +11], median -24.2 %, total Rs -70,607, avg win Rs 6,302 (+82 %), avg loss Rs -4,160 (-48 %), max up mean 54 % (>= +100 % on 22 %), without top 3 -11.9 %
- yes: n 2 too few (n < 10): no numbers

**H5 actual NIFTY opening gap**
- flat: n 78 (28 W / 50 L, win 36 %), mean -2.4 % [-18, +15], median -22.6 %, total Rs -15,754, avg win Rs 5,892 (+78 %), avg loss Rs -3,614 (-47 %), max up mean 52 % (>= +100 % on 19 %), without top 3 -11.8 %
- gap-down: n 15 (5 W / 10 L, win 33 %), mean -8.2 % [-44, +33], median -26.5 %, total Rs -25,475, avg win Rs 7,797 (+88 %), avg loss Rs -6,446 (-56 %), max up mean 58 % (>= +100 % on 27 %), without top 3 -38.1 %
- gap-up: n 14 (3 W / 11 L, win 21 %), mean -18.5 % [-51, +23], median -34.2 %, total Rs -38,406, avg win Rs 6,629 (+88 %), avg loss Rs -5,299 (-48 %), max up mean 56 % (>= +100 % on 29 %), without top 3 -47.6 %

**H6 S&P previous session (agent 3, stale cache)**
- down: n 26 (8 W / 18 L, win 31 %), mean -2.7 % [-38, +40], median -36.7 %, total Rs -29,885, avg win Rs 8,823 (+121 %), avg loss Rs -5,582 (-58 %), max up mean 60 % (>= +100 % on 23 %), without top 3 -32.6 %
- flat: n 33 (12 W / 21 L, win 36 %), mean +1.5 % [-23, +30], median -16.2 %, total Rs 10,661, avg win Rs 7,565 (+89 %), avg loss Rs -3,815 (-49 %), max up mean 61 % (>= +100 % on 30 %), top-5 % share 297 %, without top 3 -15.2 %
- up: n 45 (14 W / 31 L, win 31 %), mean -16.4 % [-30, -2], median -24.2 %, total Rs -78,240, avg win Rs 3,117 (+46 %), avg loss Rs -3,932 (-44 %), max up mean 42 % (>= +100 % on 11 %), without top 3 -23.3 %

**H10 GIFT overnight, same-contract (PRIMARY)**
- flat: n 72 (24 W / 48 L, win 33 %), mean -8.8 % [-23, +7], median -19.4 %, total Rs -62,529, avg win Rs 5,097 (+66 %), avg loss Rs -3,851 (-46 %), max up mean 50 % (>= +100 % on 18 %), without top 3 -16.3 %
- gap-down: n 18 (6 W / 12 L, win 33 %), mean +6.4 % [-35, +58], median -28.5 %, total Rs -2,590, avg win Rs 8,881 (+123 %), avg loss Rs -4,656 (-52 %), max up mean 71 % (>= +100 % on 33 %), without top 3 -32.2 %
- gap-up: n 17 (6 W / 11 L, win 35 %), mean -3.1 % [-39, +37], median -53.2 %, total Rs -14,516, avg win Rs 8,035 (+94 %), avg loss Rs -5,702 (-56 %), max up mean 48 % (>= +100 % on 24 %), without top 3 -32.9 %

**H11 indicated vs actual opening, same-contract (PRIMARY)**
- in line: n 67 (23 W / 44 L, win 34 %), mean -8.3 % [-24, +8], median -24.2 %, total Rs -48,314, avg win Rs 5,220 (+67 %), avg loss Rs -3,827 (-48 %), max up mean 51 % (>= +100 % on 19 %), without top 3 -16.6 %
- stronger: n 19 (6 W / 13 L, win 32 %), mean +7.3 % [-34, +56], median -28.9 %, total Rs -4,436, avg win Rs 8,577 (+125 %), avg loss Rs -4,300 (-47 %), max up mean 68 % (>= +100 % on 26 %), without top 3 -29.6 %
- weaker: n 21 (7 W / 14 L, win 33 %), mean -7.3 % [-37, +23], median -21.0 %, total Rs -26,885, avg win Rs 7,471 (+83 %), avg loss Rs -5,656 (-52 %), max up mean 50 % (>= +100 % on 24 %), without top 3 -26.4 %

**H12 Asia pre-entry (agent 3b, mean of available markets)**
- down: n 25 (9 W / 16 L, win 36 %), mean -0.0 % [-29, +32], median -13.0 %, total Rs -9,691, avg win Rs 8,535 (+92 %), avg loss Rs -5,407 (-52 %), max up mean 62 % (>= +100 % on 32 %), without top 3 -20.4 %
- flat: n 47 (18 W / 29 L, win 38 %), mean +2.5 % [-21, +31], median -21.0 %, total Rs 7,315, avg win Rs 6,350 (+86 %), avg loss Rs -3,689 (-49 %), max up mean 57 % (>= +100 % on 21 %), top-5 % share 697 %, without top 3 -13.2 %
- up: n 35 (9 W / 26 L, win 26 %), mean -19.6 % [-36, -1], median -36.7 %, total Rs -77,259, avg win Rs 3,635 (+56 %), avg loss Rs -4,230 (-46 %), max up mean 43 % (>= +100 % on 14 %), without top 3 -31.3 %

**X01 S&P 500 previous US session**
- down: n 28 (9 W / 19 L, win 32 %), mean -1.4 % [-36, +39], median -36.7 %, total Rs -26,750, avg win Rs 8,740 (+118 %), avg loss Rs -5,548 (-58 %), max up mean 61 % (>= +100 % on 25 %), without top 3 -28.8 %
- flat: n 34 (13 W / 21 L, win 38 %), mean +4.8 % [-23, +34], median -14.6 %, total Rs 21,409, avg win Rs 7,810 (+91 %), avg loss Rs -3,815 (-49 %), max up mean 63 % (>= +100 % on 32 %), top-5 % share 148 %, without top 3 -11.0 %
- up: n 45 (14 W / 31 L, win 31 %), mean -15.4 % [-29, -1], median -19.9 %, total Rs -74,293, avg win Rs 3,117 (+46 %), avg loss Rs -3,804 (-43 %), max up mean 42 % (>= +100 % on 11 %), without top 3 -22.2 %

**X02 USD/INR previous session (hourly)**
- down: n 5 too few (n < 10): no numbers
- flat: n 71 (27 W / 44 L, win 38 %), mean -1.1 % [-18, +18], median -13.6 %, total Rs -16,648, avg win Rs 5,808 (+74 %), avg loss Rs -3,942 (-47 %), max up mean 55 % (>= +100 % on 20 %), without top 3 -11.2 %
- up: n 22 (6 W / 16 L, win 27 %), mean -4.4 % [-38, +33], median -31.6 %, total Rs -23,146, avg win Rs 9,938 (+115 %), avg loss Rs -5,173 (-49 %), max up mean 60 % (>= +100 % on 27 %), without top 3 -31.7 %

**X03 Brent previous day (quality-limited)**
- down: n 25 (7 W / 18 L, win 28 %), mean -19.6 % [-39, +1], median -19.9 %, total Rs -68,269, avg win Rs 2,691 (+43 %), avg loss Rs -4,839 (-44 %), max up mean 44 % (>= +100 % on 12 %), without top 3 -32.6 %
- flat: n 45 (20 W / 25 L, win 44 %), mean +3.5 % [-17, +26], median -7.4 %, total Rs 12,449, avg win Rs 5,675 (+73 %), avg loss Rs -4,042 (-52 %), max up mean 58 % (>= +100 % on 27 %), top-5 % share 301 %, without top 3 -8.0 %
- up: n 37 (9 W / 28 L, win 24 %), mean -6.4 % [-33, +26], median -39.1 %, total Rs -23,816, avg win Rs 10,167 (+125 %), avg loss Rs -4,118 (-49 %), max up mean 55 % (>= +100 % on 22 %), without top 3 -27.4 %

**X04 US VIX spike**
- no_spike: n 92 (28 W / 64 L, win 30 %), mean -7.9 % [-22, +8], median -24.8 %, total Rs -83,358, avg win Rs 5,954 (+80 %), avg loss Rs -3,907 (-47 %), max up mean 52 % (>= +100 % on 20 %), without top 3 -16.1 %
- spike: n 8 too few (n < 10): no numbers

**X05 Global risk-on / off**
- mixed: n 37 (13 W / 24 L, win 35 %), mean +1.4 % [-24, +28], median -21.0 %, total Rs 11,540, avg win Rs 7,988 (+93 %), avg loss Rs -3,846 (-48 %), max up mean 61 % (>= +100 % on 32 %), top-5 % share 274 %, without top 3 -13.4 %
- risk_off: n 22 (7 W / 15 L, win 32 %), mean +1.7 % [-40, +53], median -34.8 %, total Rs -25,897, avg win Rs 8,354 (+128 %), avg loss Rs -5,625 (-57 %), max up mean 65 % (>= +100 % on 27 %), without top 3 -33.9 %
- risk_on: n 37 (11 W / 26 L, win 30 %), mean -17.8 % [-32, -4], median -19.9 %, total Rs -77,610, avg win Rs 2,136 (+40 %), avg loss Rs -3,889 (-42 %), max up mean 39 % (>= +100 % on 8 %), without top 3 -25.8 %

**X06 Asia pre-entry (agent 4, needs both markets)**
- down: n 22 (7 W / 15 L, win 32 %), mean -3.6 % [-36, +32], median -19.8 %, total Rs -22,387, avg win Rs 8,090 (+96 %), avg loss Rs -5,268 (-50 %), max up mean 61 % (>= +100 % on 32 %), without top 3 -27.8 %
- flat: n 42 (15 W / 27 L, win 36 %), mean +1.7 % [-22, +30], median -22.6 %, total Rs -530, avg win Rs 6,432 (+92 %), avg loss Rs -3,593 (-48 %), max up mean 57 % (>= +100 % on 21 %), without top 3 -16.1 %
- up: n 32 (9 W / 23 L, win 28 %), mean -17.6 % [-36, +2], median -35.5 %, total Rs -69,049, avg win Rs 3,635 (+56 %), avg loss Rs -4,425 (-46 %), max up mean 43 % (>= +100 % on 16 %), without top 3 -30.3 %

**X07 Market breadth, previous session**
- high: n 30 (14 W / 16 L, win 47 %), mean +15.9 % [-18, +55], median -18.7 %, total Rs 28,490, avg win Rs 8,064 (+101 %), avg loss Rs -5,275 (-59 %), max up mean 68 % (>= +100 % on 30 %), top-5 % share 160 %, without top 3 -7.5 %
- low: n 33 (8 W / 25 L, win 24 %), mean -22.6 % [-43, +1], median -36.7 %, total Rs -68,047, avg win Rs 5,260 (+65 %), avg loss Rs -4,405 (-50 %), max up mean 45 % (>= +100 % on 15 %), without top 3 -38.9 %
- mid: n 44 (14 W / 30 L, win 32 %), mean -6.8 % [-23, +12], median -16.9 %, total Rs -40,078, avg win Rs 4,919 (+68 %), avg loss Rs -3,631 (-42 %), max up mean 50 % (>= +100 % on 20 %), without top 3 -17.4 %

**X08 Sector leadership (Bank minus Nifty)**
- bank_lags: n 29 (9 W / 20 L, win 31 %), mean -11.8 % [-37, +17], median -39.1 %, total Rs -48,639, avg win Rs 7,030 (+83 %), avg loss Rs -5,595 (-55 %), max up mean 50 % (>= +100 % on 28 %), without top 3 -29.5 %
- bank_leads: n 22 (10 W / 12 L, win 45 %), mean +19.9 % [-15, +65], median -4.7 %, total Rs 29,856, avg win Rs 7,294 (+92 %), avg loss Rs -3,590 (-40 %), max up mean 67 % (>= +100 % on 14 %), top-5 % share 130 %, without top 3 -9.2 %
- in_line: n 56 (17 W / 39 L, win 30 %), mean -11.9 % [-28, +6], median -23.2 %, total Rs -60,852, avg win Rs 5,154 (+71 %), avg loss Rs -3,807 (-48 %), max up mean 50 % (>= +100 % on 21 %), without top 3 -21.6 %

**X09 FII / DII cash (limited window, third party)**
- both_buy: n 9 too few (n < 10): no numbers
- diverge: n 34 (10 W / 24 L, win 29 %), mean -8.3 % [-31, +17], median -32.4 %, total Rs -39,706, avg win Rs 7,684 (+91 %), avg loss Rs -4,856 (-49 %), max up mean 49 % (>= +100 % on 24 %), without top 3 -24.2 %

**X10 FII futures level**
- high: n 17 (7 W / 10 L, win 41 %), mean +1.4 % [-32, +37], median -13.6 %, total Rs 2,099, avg win Rs 4,688 (+72 %), avg loss Rs -3,072 (-48 %), max up mean 56 % (>= +100 % on 18 %), top-5 % share 925 %, without top 3 -27.0 %
- low: n 57 (16 W / 41 L, win 28 %), mean -10.0 % [-28, +9], median -26.5 %, total Rs -55,279, avg win Rs 6,889 (+85 %), avg loss Rs -4,037 (-47 %), max up mean 49 % (>= +100 % on 21 %), without top 3 -20.0 %
- mid: n 32 (13 W / 19 L, win 41 %), mean +1.8 % [-25, +37], median -12.8 %, total Rs -9,833, avg win Rs 6,215 (+78 %), avg loss Rs -4,770 (-50 %), max up mean 61 % (>= +100 % on 25 %), without top 3 -18.8 %

**X11 News tone (GDELT, global)**
- above_median: n 39 (15 W / 24 L, win 38 %), mean +0.3 % [-19, +22], median -17.7 %, total Rs 11,475, avg win Rs 5,989 (+71 %), avg loss Rs -3,265 (-44 %), max up mean 55 % (>= +100 % on 23 %), top-5 % share 240 %, without top 3 -11.9 %
- below_median: n 63 (18 W / 45 L, win 29 %), mean -14.1 % [-32, +6], median -30.4 %, total Rs -115,559, avg win Rs 5,578 (+77 %), avg loss Rs -4,799 (-51 %), max up mean 49 % (>= +100 % on 17 %), without top 3 -26.2 %

**X12 Scheduled events**
- day_after: n 3 too few (n < 10): no numbers
- day_before: n 8 too few (n < 10): no numbers
- event_day: n 7 too few (n < 10): no numbers
- none: n 89 (30 W / 59 L, win 34 %), mean -3.4 % [-19, +14], median -28.0 %, total Rs -40,229, avg win Rs 6,596 (+85 %), avg loss Rs -4,036 (-48 %), max up mean 54 % (>= +100 % on 21 %), without top 3 -11.8 %
