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
