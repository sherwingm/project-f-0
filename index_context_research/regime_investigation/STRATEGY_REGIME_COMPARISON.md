# Strategy comparison under the same conditions (coordinator, 17 Nov 2026)

G1-F, G1 puts, G1-C calls and the XP expiry-day straddle, same class definitions (`PREREG_REGIME.md`). Full statistics: `results_tables/REGIME_STATS_TABLES.md`. **Dependence warning:** G1-F is a strict subset of G1 (all 154 trades appear in G1); G1 puts and G1-C calls are the two sides of the same daily breakout on different days; XP shares 61 dates with G1, 38 with G1-F and 45 with G1-C. Agreement between G1 and G1-F is therefore not independent confirmation. Nothing here creates a switching system or recommends replacing a strategy.

## Direction (ret20 groups; n, mean net % [95 % interval])
- **G1-F:** bearish 75 +11.7 [-5, +29]; sideways 60 +16.9; bullish 19 +59.5 [+5, +120]. KW p 0.51.
- **G1 puts (259):** bearish 148 **-0.8** [-13, +12] (win 34 %, Rs -28,953); sideways 75 +9.8; bullish 36 **+22.6** [-10, +59]. **Puts did NOT do better in bearish regimes** here; the best puts were after bullish run-ups. All intervals include zero; KW p 0.20 (smallest in the family).
- **G1-C calls (235):** bearish 130 -5.1 %; sideways 64 -6.1 %; **bullish 41 -36.0 % [-49, -18]** (win 12 %, Rs -134,683; without its top 3 trades -47.1 %). By ret20 quintile: 1: -12.1, 2: +4.4, 3: -6.1, 4: **-33.2**, 5: **-42.8** (n 12). **Calls did not do better in bullish regimes; they did much worse.** Welch bearish vs bullish p 0.005 whole sample, 0.10 in discovery, 0.012 in the second year, the same sign in both years (-33.4 / -27.7 points); the omnibus Kruskal-Wallis is 0.255, so it did not pass the pre-registered correction. **An unconfirmed lead, in the direction opposite to the usual expectation that calls suit strong markets** (an overnight call after a strong run-up is the buyer of an extended market).
- **XP (107, all on expiry days):** bearish 58 -4.4; sideways 33 -12.0; bullish 16 +5.1. Nothing.

## Volatility
- **VIX level:** G1-F low +11.8 / normal +38.1 (no high). G1: low n 132 +11.2 %, normal 117 +1.4 %, **high n 10 -22.1 %** (win 20 %, too thin). G1-C: low 117 -13.5 % [-25, -1], normal 105 -7.9 %, high 13 -9.2 %. XP: low 51 -4.8 %, normal 50 -3.2 %, high 6 (too few). G1's weakness in high VIX matches the stress audit (-12.1 % in its VIX high tercile) but the high cell here is 10 trades.
- **XP VIX direction** (falling / flat / rising): falling n 30 **+32.7 %** [+2, +69] (win 53 %); flat n 43 -20.8 %; rising n 34 -19.3 %. In discovery the pattern was striking (falling +83 %, n 14; KW p 0.00016, passed the correction) but **it reversed in the second year** (falling -11.2 %, n 16; class difference -0.4 points): a time-specific result, not a stable one. It is the same reversal found in the earlier context study.
- **US VIX spike (previous session +10 %):** G1-C calls spike n 23 **+25.9 %** [-6, +61] (win 48 %) vs no spike n 191 -15.3 % (without top 3 +2.0 %); KW p 0.006 whole sample, 0.018 in the second year, same direction in both years. G1-F puts spike n 13 +0.3 % vs +19.7 % (second year -29 %, n 10). The opposite signs for calls and puts after a US volatility spike are consistent with calls benefiting from a rebound and puts from continued weakness, but both cells are small and **it is a hypothesis, not a finding**.

## Overnight
- **GIFT overnight class:** G1-F nothing under the faithful same-contract definition (p 0.947). With the `prev_settle` column version (kept visible, not primary) the secondary sets showed: G1 gap-up n 28 -25.1 % vs flat +9.9 % (p 0.16); G1-C gap-down n 17 -32.7 % (win 12 %) vs -8.7 % (p 0.93); XP flat n 90 +29.2 points better than 17 non-flat days (p 0.071). The same-contract rerun found nothing under p 0.1 for G1 and XP and nothing for G1-C's GIFT class (its only hit is the indicated-vs-actual test below).
- **Indicated vs actual opening:** G1-F "in line" worst (-38.1 points, p 0.048; q 0.49). G1: in line n 154 -0.6 %, stronger n 58 +18.4 %, weaker n 45 +12.1 % (nothing under p 0.1). **G1-C: weaker n 50 +7.2 % [-16, +33] vs stronger n 38 -24.0 % vs in line n 145 -13.0 % (KW p 0.039; second-year stronger -43.7 %): the opposite of G1-F's pattern** (stronger or weaker both helped G1-F; for calls a stronger actual open than GIFT hurt).

## Institutional and other external
- **FII / DII cash (limited window):** G1-F both buying n 15 -29.4 % (1 winner) vs diverging n 44 +34.3 %; G1 both buying n 18 -26.9 % vs diverging n 84 +6.7 % (G1 contains G1-F). G1-C and XP: no pattern.
- **Participant OI:** the significant-looking cells for G1 (DII level, p 0.034) and G1-C (FII futures level, p 0.003) are calendar effects: the "low" / "high" class exists only in discovery.
- **USD/INR:** G1-F KW p 0.042 (see results). Not seen in the others.
- **Sector leadership:** G1-C bank-leads vs lags Welch p 0.021 whole sample, KW p 0.54.

## Do strategies have conditions where each looks better?
- **G1-F:** the closest are "normal VIX" and "mid breadth" and "FII / DII diverging" and "cash open not in line with GIFT". All are nominal, cell-limited, partly period-confounded and none survives the correction (smallest consolidated q 0.37).
- **G1 puts:** none; their results track the market's era more than any condition tested.
- **G1-C calls:** a persistent unfavourable condition after bullish run-ups (a lead), and a favourable US-VIX-spike cell (a lead).
- **XP:** a discovery-period VIX-falling pattern that did not persist; Tuesday expiries (-11.0 %, n 55) vs Thursday (+5.0 %, n 45), intervals include zero.
Because the strategies are not independent of one another and each has under 260 trades, none of this supports a rule to prefer one strategy over another or to switch between them.
