# Test scorecard (from `consolidated_tests.csv`, audit 18 Nov 2026)

p = chance that a difference this big appears if the condition does nothing (Kruskal-Wallis across the classes). q = p after the multiple-test correction (Benjamini-Hochberg 10 %). **A test passes only if q < 0.10.** Nominal pass = p < 0.05 before correction. Lower p = better.

## G1-F (main, 49 rows incl. 13 robustness items not in the correction)
Tests in the correction: 36. Nominal p<0.05: 4 (chance expects 1.8). Passed the correction: 0. Best p 0.0203 (q 0.367). Worst p 0.985.

| rank | test | what was cut | p | q | result |
|---|---|---|---|---|---|
| 1 | R1_ret5: robustness (agent-marked) |  | 0.015 |  | robustness (outside correction) |
| 2 | C2_VIXxGIFT: COMBO VIX x GIFT (column version) |  | 0.020 | 0.37 | nominal only |
| 3 | H2: VIX level (low / normal / high) | VIX below 13.51 low, 13.51 to 19.94 normal, above 19.94 high | 0.020 | 0.37 | nominal only |
| 4 | R2_ivsa_prevrow: GIFT prev_settle column |  | 0.031 |  | robustness (outside correction) |
| 5 | H9: COMBO VIX level x gap | VIX 3 x gap 3 | 0.039 | 0.37 | nominal only |
| 6 | X02: USD/INR move | USD/INR hourly change beyond +/-0.2 % | 0.042 | 0.37 | nominal only |
| 7 | H11_samecontract: GIFT vs actual open (same contract) | actual gap minus GIFT return beyond +/-0.2 pts | 0.077 | 0.49 | fail |
| 8 | H15: FII/DII cash (both buying vs diverging) |  | 0.082 | 0.49 | fail |
| 9 | X08: FII futures long share (level) |  | 0.103 | 0.53 | fail |
| 10 | X10: DII futures long share (level) |  | 0.133 | 0.60 | fail |
| 11 | C2_VIXxGIFT_samecontract: COMBO VIX x GIFT (same contract) |  | 0.164 | 0.66 | fail |
| 12 | H7: COMBO direction x VIX level | direction 3 x VIX 3 | 0.209 | 0.68 | fail |
| 13 | X13: FII options stance (change) |  | 0.230 | 0.68 | fail |
| 14 | H14: Breadth (advancers share, low / mid / high) | advance share <= 25th / >= 75th percentile | 0.249 | 0.68 | fail |
| 15 | X01: S&P 500 previous session | beyond +/-0.3 % | 0.260 | 0.68 | fail |
| 16 | X06: US 10-year yield |  | 0.265 | 0.68 | fail |
| 17 | H6: US S&P overnight (down / flat / up) | S&P move beyond +/-0.3 % | 0.304 | 0.73 | fail |
| 18 | X12: FII options stance (level) |  | 0.330 | 0.74 | fail |
| 19 | R2_ret10: robustness (agent-marked) |  | 0.341 |  | robustness (outside correction) |
| 20 | R3_ma: robustness (agent-marked) |  | 0.377 |  | robustness (outside correction) |
| 21 | X1_dir3: robustness (agent-marked) |  | 0.397 |  | robustness (outside correction) |
| 22 | S02: FII cash net sign previous session (third party) |  | 0.401 |  | robustness (outside correction) |
| 23 | X09: FII futures long share (change) |  | 0.448 | 0.90 | fail |
| 24 | X04: US VIX spike (+10 %) | US VIX +10 % or more | 0.449 | 0.90 | fail |
| 25 | H1: Direction (20-day return, 5 classes) | ret20 edges -1.88 / +0.52 / +2.57 / +4.71 %; 3 groups: bearish (Q1-2), sideways (Q3), bullish (Q4-5) | 0.511 | 0.91 | fail |
| 26 | X07: Sector leadership (Bank minus Nifty) | Bank minus Nifty beyond +/-0.3 pts | 0.519 | 0.91 | fail |
| 27 | H12_samecontract: Asia (same contract run) | Asia gap beyond +/-0.3 % | 0.583 |  | robustness (outside correction) |
| 28 | H12: Asia opening gaps (Nikkei, Hang Seng) | Asia gap beyond +/-0.3 % | 0.583 | 0.91 | fail |
| 29 | X11: DII futures long share (change) |  | 0.603 | 0.91 | fail |
| 30 | R1_gift_prevsettlecol_samecontract: GIFT same-contract open/prev settlement |  | 0.609 |  | robustness (outside correction) |
| 31 | H10: GIFT overnight class | GIFT return beyond +/-0.3 % | 0.609 | 0.91 | fail |
| 32 | H11: GIFT vs actual open (weaker / in line / stronger) | actual gap minus GIFT return beyond +/-0.2 pts | 0.628 | 0.91 | fail |
| 33 | R2_ivsa_prevsettlecol_samecontract: GIFT same-contract open/prev settlement |  | 0.628 |  | robustness (outside correction) |
| 34 | H5: Opening gap (down / flat / up) | gap beyond +/-0.3 % | 0.630 | 0.91 | fail |
| 35 | R1_gift_prevrow: GIFT prev_settle column |  | 0.685 |  | robustness (outside correction) |
| 36 | X14: GDELT news tone |  | 0.702 | 0.94 | fail |
| 37 | C1_dir3xGIFT_samecontract: COMBO direction x GIFT (same contract) |  | 0.743 | 0.94 | fail |
| 38 | H8: COMBO direction x gap | direction 3 x gap 3 | 0.770 | 0.94 | fail |
| 39 | H13: Global risk-on / risk-off | US up and Asia not down = on; US down and Asia not up = off | 0.775 | 0.94 | fail |
| 40 | C1_dir3xGIFT: COMBO direction x GIFT |  | 0.787 | 0.94 | fail |
| 41 | X03: Brent oil | Brent beyond +/-1 % | 0.835 | 0.95 | fail |
| 42 | H12: Asia opening gaps (Nikkei, Hang Seng) | Asia gap beyond +/-0.3 % | 0.849 | 0.95 | fail |
| 43 | S01: Brent excluding days where daily and hourly closes differ by >2 % (rob |  | 0.849 |  | robustness (outside correction) |
| 44 | X05: Dollar index |  | 0.927 | 0.97 | fail |
| 45 | H3: VIX direction (falling / flat / rising) | VIX 5-day change beyond +/-5 % | 0.946 | 0.97 | fail |
| 46 | H10_samecontract: GIFT overnight class (same contract) | GIFT return beyond +/-0.3 % | 0.947 | 0.97 | fail |
| 47 | X15: Scheduled events (RBI/Budget/FOMC/election) |  | 0.985 | 0.99 | fail |

## G1 puts
Tests in the correction: 36. Nominal p<0.05: 1 (chance expects 1.8). Passed the correction: 0. Best p 0.0343 (q 0.929). Worst p 0.998.

| rank | test | what was cut | p | q | result |
|---|---|---|---|---|---|
| 1 | X10: DII futures long share (level) |  | 0.034 | 0.93 | nominal only |
| 2 | R1_ret5: robustness (agent-marked) |  | 0.040 |  | robustness (outside correction) |
| 3 | X13: FII options stance (change) |  | 0.082 | 0.93 | fail |
| 4 | H10: GIFT overnight class | GIFT return beyond +/-0.3 % | 0.160 | 0.93 | fail |
| 5 | R1_gift_prevsettlecol_samecontract: GIFT same-contract open/prev settlement |  | 0.160 |  | robustness (outside correction) |

## G1-C calls
Tests in the correction: 36. Nominal p<0.05: 3 (chance expects 1.8). Passed the correction: 0. Best p 0.0028 (q 0.101). Worst p 0.930.

| rank | test | what was cut | p | q | result |
|---|---|---|---|---|---|
| 1 | X08: FII futures long share (level) |  | 0.003 | 0.10 | nominal only |
| 2 | X04: US VIX spike (+10 %) | US VIX +10 % or more | 0.006 | 0.11 | nominal only |
| 3 | H11_samecontract: GIFT vs actual open (same contract) | actual gap minus GIFT return beyond +/-0.2 pts | 0.039 | 0.47 | nominal only |
| 4 | R2_ivsa_prevrow: GIFT prev_settle column |  | 0.046 |  | robustness (outside correction) |
| 5 | H13: Global risk-on / risk-off | US up and Asia not down = on; US down and Asia not up = off | 0.093 | 0.71 | fail |

## XP straddle
Tests in the correction: 32. Nominal p<0.05: 1 (chance expects 1.6). Passed the correction: 0. Best p 0.0105 (q 0.338). Worst p 0.990.

| rank | test | what was cut | p | q | result |
|---|---|---|---|---|---|
| 1 | H3: VIX direction (falling / flat / rising) | VIX 5-day change beyond +/-5 % | 0.011 | 0.34 | nominal only |
| 2 | X14: GDELT news tone |  | 0.145 | 0.99 | fail |
| 3 | X12: FII options stance (level) |  | 0.163 | 0.99 | fail |
| 4 | X07: Sector leadership (Bank minus Nifty) | Bank minus Nifty beyond +/-0.3 pts | 0.238 | 0.99 | fail |
| 5 | R1_ret5: robustness (agent-marked) |  | 0.270 |  | robustness (outside correction) |
