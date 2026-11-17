# Market regime results (coordinator consolidation, 17 Nov 2026)

Scope: explanatory results for **G1-F (154 trades, primary)**; the other strategies are in `STRATEGY_REGIME_COMPARISON.md`; prediction is in `PREDICTIVE_VALIDATION.md`. Conditions and thresholds were fixed in `PREREG_REGIME.md` (incl. Amendment 1) before any strategy return was looked at. **Every statistic below is recomputed with one set of definitions in `results_tables/REGIME_STATS_TABLES.md` (and `regime_stats_all.csv`): n, wins, losses, win rate, mean and median net %, total net Rs, average win and loss (Rs and %), max up (MFE), MAE, duration, top-5 % share, mean without the top 3 trades.** Agents' own tables are in `interim/`. Percent = net rupees after slippage and charges / premium paid in rupees; rupees are separate. Intervals are bootstrap 95 % resampling trading days. Classes under 10 trades carry no conclusion.

## Structural limits of this sample (read first)
- Two years, one market phase (NIFTY from about 22,000 to 26,300 and back). G1-F by its own filters has **no high-VIX trades** (VIX < 17: 108 low, 46 normal, 0 high), **no actual gap-up trades**, only 2 sudden-expansion trades, 6 trades in the strongest direction quintile.
- In the second year 71 of 79 G1-F trades are low-VIX; the VIX-level result cannot be checked there.
- All G1-F effects below about 45 points are invisible in cells of 80 trades (see `RESEARCH_LIMITATIONS.md`).

## Direction (known at the previous close)
Boundaries from NIFTY 2018-01-01 to 2024-09-30: ret20 quintile edges -1.88 %, +0.52 %, +2.57 %, +4.71 %.
- Quintiles 1 to 5 (bearish to bullish): n 36 / 39 / 60 / 13 / 6; mean net % +18.8, +5.2, +16.9, +18.1, (n 6 too few; its raw mean is +149 %); wins 47 / 41 / 33 / 31 %; all intervals span zero.
- Three groups: **bearish n 75 +11.7 % [-5, +29]** (MFE 100 %, MAE -46 %); **sideways n 60 +16.9 %** (MFE 91 %, MAE -52 %); **bullish n 19 +59.5 % [+5, +120]** (win 53 %, median +35.8 %, MFE 167 %, MAE -36 %; without its top 3 trades +14.6 %).
- Kruskal-Wallis p 0.51: **no evidence of a direction effect.** The bullish cell looks better but is 19 trades, six of them in the strongest quintile, and 60 % of its mean is three trades. The 5-day return quintile (robustness item, not in the family) has a better middle quintile (+55 %) and weak extremes; non-monotonic.
- Moving-average structure and 10-session classes: nothing.

## Volatility
VIX edges from the repaired series 2018 to 2024-09: p25 13.51, p75 19.94.
- **Level:** low n 108 +11.8 % (win 34 %, Rs 64,172, MAE -49 %); **normal n 46 +38.1 % [+11, +67]** (win 57 %, Rs 182,874, MAE -41 %, without top 3 +20.2 %); high: none. Kruskal-Wallis p 0.020 (nominal; consolidated Benjamini-Hochberg q 0.37).
  - The normal-VIX advantage is **+5 points in discovery** and comes mostly from 8 later trades (+86 % mean); 2024 H2 reverses; VIX level is confounded with calendar period (normal VIX was more common late in 2026). One trade flips the class edge (2026-01-29, VIX 13.53 vs the 13.51 boundary).
- **5-day direction:** falling n 50 +27.8 %, flat n 72 +16.9 %, rising n 32 +13.1 %; p 0.95.
- **Sudden expansion at the signal:** only 2 trades: untestable.
- US VIX spike (previous session +10 % or more): n 13, +0.3 % (win 23 %) vs no spike n 132 +19.7 %; second year -29 % (n 10); KW p 0.59.
- ATM implied volatility and VIX terciles: see the context study (no significance).

## Overnight and opening
- **GIFT NIFTY (primary: same-contract, open of the 06:30 IST session vs the previous trade date's settlement of the same expiry; correlation with the actual NIFTY 09:15 gap 0.75; on G1-F's own days 0.64):** class sizes gap-down 28, flat 111, gap-up 13 (152 of 154 trades have GIFT data). Mean net % +26.7 [-13, +74], +19.4 [+2, +38], +17.5 [-26, +72]; Kruskal-Wallis p 0.947. **GIFT gap class itself does nothing for G1-F.** All 13 GIFT gap-up trades had a flat actual open (G1-F's filter removes real gap-ups).
- **Indicated vs actual opening (actual NIFTY gap minus the GIFT overnight return):** weaker n 26 +39.5 % [+2, +87] (MAE -37 %); **in line n 102 +8.0 % [-9, +26]** (MFE 91 %, MAE -50 %); stronger n 24 +53.5 % [+8, +107] (MFE 148 %). Kruskal-Wallis p 0.077; "in line" vs the rest -38.1 points (Welch p 0.048). Same sign in both years (-41 / -34 points) and in 4 of 5 half-years; consolidated q 0.49: **a lead, not a result** (see predictive validation).
- The two other GIFT versions (the `prev_settle` column, and the previous-row settlement that is contaminated on 23 monthly roll days) are kept visible in `interim/agent3b_gift_regimes/GIFT_SAMECONTRACT_ADDENDUM.md`; counting all versions as separate tests is the conservative choice used in the correction. With the column version the VIX x GIFT combination had a nominal p of 0.020; with the faithful version it is 0.164, i.e. that p-value came from the VIX effect, not GIFT.
- **Actual opening gap:** flat n 133 +21.8 % [+5, +40]; gap-down n 21 +6.4 % (win 33 %, MAE -58 %); gap-up empty by the strategy's rule. Welch p 0.47.
- **Asia pre-entry (Nikkei and Hang Seng opening gaps):** agent 3b (mean of the available markets, 152 trades): down n 41 +19.7 %, flat n 64 +17.9 %, up n 47 +25.0 %, p 0.58; agent 4 (needs both markets, 133 trades): p 0.85. Nothing.

## Global
S&P 500 previous US session (agent 4, complete): p 0.26 (agent 3's version used a stale cache, NaN for 20 trades and wrong for 2); global risk-on / risk-off p 0.78; USD/INR (hourly, 141 trades): flat n 102 +7.4 %, up n 24 +46.1 % [+12, +79] (win 67 %), down n 15 +36.3 %; **Kruskal-Wallis p 0.042, the only nominal p < 0.05 among Agent 4's 19 tests** (about 1 expected by chance); discovery p 0.070, second half 0.085, the same shape (flat weakest); it is "any large move is better", not a direction. Brent p 0.84 (quality-limited), dollar index 0.93, US 10-year 0.27.

## Institutional
- **FII / DII cash (third party; Dec 2025 to Oct 2026; 59 trades):** both buying n 15, **one winner**, mean -29.4 % [-47, -3] (without top 3 -45.7 %); diverging n 44 +34.3 % [+3, +71] (win 48 %). Kruskal-Wallis p 0.082, Welch p 0.004. Not explained by the previous day's NIFTY direction (+0.07 % vs +0.02 %). The strategy set G1 contains G1-F, so G1's matching result (both buying n 18, -26.9 %) is not independent evidence. Descriptive only.
- **Participant-wise positioning (FII and DII index futures level and change, FII index-options stance):** all p at least 0.10 for G1-F; level terciles drift with the calendar (the second year is almost all one class), so level consistency cannot be tested.

## Market structure, news
- **Breadth (all NSE equities, previous session):** low n 43 +9.1 %, **mid n 79 +33.7 % [+9, +60] (win 44 %, Rs 168,051)**, high n 31 +0.7 %; p 0.25. High breadth in the second year -21.2 % (n 17); high breadth mostly equals a strong previous day. **Sector leadership (Bank minus Nifty):** p 0.52, flips between periods.
- **News and events:** GDELT tone (a global daily machine score, 44 days missing, previous day only) p 0.70; scheduled events (RBI, FOMC, Budget, the 2024 US election): event day n 12 -1.4 %, day before n 6 and day after n 8 (too few); p 0.99. No timestamped news or economic-calendar data other than these dates exists, so 5 / 15 / 30 / 60-minute announcement reactions could not be tested.
- Trending vs range-bound sessions, intraday reversals, failed breakouts as pre-entry conditions: not built (they need minute-level definitions fixed in advance; failed breakouts exist only in hindsight, see the anatomy).

## Combinations
Direction x VIX level, direction x gap, VIX level x gap (pre-registered): only VIX level x gap has a nominal p of 0.039, which is the VIX-level effect again (normal-VIX flat-gap n 40 +42.5 % vs low-VIX flat +12.8 %). Direction x GIFT p 0.74; VIX x GIFT (same-contract) p 0.164. **The three-factor combination is insufficient for every strategy** (G1-F: 4 of 27 cells reach 10 trades). Combinations are therefore **not more informative than single variables**: the only combination signal is a single variable's signal.

## By half-year
G1-F swings widely whatever the regime (the bearish class: 2025 H2 -9.4 % vs 2026 H1 +29.4 %); half-year swings of +64 % (2026 H1) and -5.6 % (2026 H2) are not explained by any condition tested.
