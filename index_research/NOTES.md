# Resume log for the index research program (newest last)
Status of each study: TODO / RUNNING / DONE (verdict). Keep this file current so a new session can resume without repeating work.

- 14 Nov: PROGRAM.md written and committed before any number.
- R01 gap-and-go (NIFTY / BANKNIFTY / SENSEX, 45 cells): DONE, 0 discovery passes. Best: NIFTY gap >= 1 % follow +0.19 % a trade, t 1.46 (n 42).
- R02 overnight / intraday drift: DONE. overnight after an up day passed discovery on all 3 indices (t 2.3-2.9) but FAILED validation (mean without the best 5 % negative, t 1.4-1.7).
- R02b overnight on real futures 2018-2021: DONE, 0 passes (mean -0.02 to -0.04 % after 0.02 % slippage a side + charges; gross about +0.03 %).
- R03 IB breakout / liquidity sweep: DONE, 0 passes (sweep stop is very tight by construction: win 1-15 %).
- R07 pre-event short straddle / strangle: DONE, 16 events in D (too few to test); means -3 to -13 % of credit.
- R10 pairs (4 bank pairs): DONE, 0 passes (best SBIN-ICICIBANK raw +1.1 %, t 1.7).
- R11 daily ML walk-forward: DONE, 0 passes (rf_all +0.056 %, t 1.71).
- R13 intraday momentum: DONE, 0 passes; significantly NEGATIVE after costs on all 3 indices (t -2.5 to -3.7), but gross is about 0: costs (about 0.034 % a trade in D: 2 points of slippage, the 0.0125 % futures STT, exchange, stamp, brokerage) are the whole loss; the reverse would lose too.
- R14 trend filters: DONE, 0 passes (few spells: 4-55).
- R15 reversal: DONE, 0 passes.
- R16 VIX spikes: DONE, 7 episodes a cell in D (too few).
- R17 calendar: DONE. turn-of-month passed discovery (+0.61 %, t 2.54, n 71) but FAILED validation (+0.47 %, t 1.21, n 48). L not opened.
- R18 NIFTY/BANKNIFTY ratio: DONE, n 23, 0 passes.
- RUNNING: R04, R05, R06, R08, R09. TODO: R19 (after R09 builds the bhavcopy cache), combinations (none to combine yet), robustness for any passer, final report.
- R06 overnight short straddle / iron fly / long straddle 15:15 -> 09:16 (NIFTY minutes): DONE, 0 passes. Short straddle -1.1 % of credit (t -0.79; gross about +2 %, costs about 3 %); iron fly -3.1 % (t -3.2); long straddle -4.8 % (t -3.6). VIX 12-18 and VoV filters made it worse, not better.
- Disclosure (14 Nov): to measure the cost drag, the pooled (all cells together) net and gross per period of R01, R02, R03, R13 were printed, including the L period. No cell-level L number was looked at. Pooled gross per trade: R01 D +0.039 / V +0.041 / L -0.004 %; R02 +0.030 / +0.021 / -0.006 %; R03 +0.020 / +0.027 / +0.012 %; R13 +0.007 / -0.003 / -0.011 %. Net is lower by the costs (about 0.035 % before Apr 2026, about 0.06 % after the 0.05 % futures STT).
- R08 expiry choice for G1 / G1-C signals (near vs next weekly, ATM vs 1 ITM): DONE, 0 passes. The next weekly lifts the win rate (puts 38 -> 46 %, calls 30 -> 36 %) and the median (-51 % -> -4 % for puts) but not the mean (puts +8.4 % near ATM vs +7.0 % next ATM, t 1.0-1.4; calls -4.4 % vs -2.4 %). The "buy next week to beat theta" claim changes the shape of the result, not the edge.
- R04 Supertrend pullback (60-min trend, 5-min flip, ADX filter): DONE, 0 passes (best NIFTY ADX>25 +0.035 %, t 1.15).
- R05 TWAP-deviation mean reversion: DONE, 0 passes; fading a 2.5-3 sd stretch LOSES even before costs (t -1.7 to -4.3; gross about -0.025 %): stretched intraday moves tend to continue a little, by less than the cost of a trade. The RSI filter leaves 2-13 trades (unusable).
- R09 weekly ATM straddle held to expiry, VIX-percentile / VoV filters, NIFTY + BANKNIFTY 2018-2021 (20 cells): DONE, 0 passes. Unfiltered short -2.2 % (NIFTY) / -0.9 % (BANKNIFTY) of credit. The direction of the VoV claim shows up but is not significant: short when VoV is low +6.6 % / +6.2 % (t 0.8); long when VoV is high +10.2 % NIFTY (t 0.86). Short when VIX percentile > 70 loses (-11 %).
- X1 (Amendment A3, exploratory) VoV switch on V 2022-01 to 2024-09: NIFTY -4.3 % of the premium a trade (t -0.67, 142), BANKNIFTY -4.5 % (t -0.79). Both halves of the switch lose; the 2018-2021 pattern did not repeat. Closed.
- R19 calendar straddle (sell near weekly, buy next weekly, NIFTY 2018-2021): DONE, 0 passes; loses -4.7 % of the far premium a trade (t -2.55), low-VIX cell -6.7 % (t -2.34): the "calendars in low VIX" claim fails.
- R12 combinations: NOT RUN by rule; no study produced a validation passer to combine (PROGRAM.md R12).
- PROGRAM COMPLETE (14 Nov): 19 studies + 1 exploration; 0 candidates. Final write-up in REPORT.md.
- COMBINATIONS (Amendment A4, 14 Nov): 13 cells (10 filter mixes, 3 portfolios), NIFTY50. 5 passed discovery (overnight after up day alone; + trend filter; and the three portfolios, which lean on that same component); ALL 5 failed validation (2024-01 to 2025-09): overnight after up day +0.039 % (t 1.61, negative without the best 5 %), + trend +0.035 % (t 1.36), portfolios +0.005 to +0.020 % (t 0.2-0.7, negative at 2x costs). Turn-of-month, ML and trend filters added nothing in discovery. L not opened. 0 candidates.
