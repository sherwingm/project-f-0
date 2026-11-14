# Index strategy research program: report (14 Nov 2026)

Plan: `PROGRAM.md` (commit `86ecff412`, before any number) with Amendments A1 (`898a647c0`) and A2 (`30c347368`). Resume log: `NOTES.md`.
Scripts: `scripts/lib.py`, `spot_studies.py` (R01-R05), `option_studies.py` (R06-R08), `daily_studies.py` (R02b, R09, R19), `stat_studies.py` (R10, R11), `more_studies.py` (R13-R18).
Results: `results/<study>_discovery.csv`, `_validation.csv` (only where a cell passed discovery), `_trades.csv`, `_log.txt`.
Research only: nothing live changed, no order, no sealed data, the 13 Nov prospective holdout not used.

## The answer
**No strategy family produced a candidate.** 19 studies (about 190 pre-named cells) plus one labelled exploration on NIFTY, BANKNIFTY and SENSEX: 4 cells passed the first (discovery) test and **all 4 failed validation**; none reached the robustness battery or the late period. Nothing here is profitable on the evidence, and nothing is proposed for paper trading.
Why, in one line each:
- **Costs are larger than the edges.** Index-futures intraday ideas earn +0.00 to +0.04 % a trade before costs; costs are about 0.035 % a round trip (about 0.06 % since the April 2026 futures STT). Option-selling ideas earn about +2 % of the credit before costs and pay about 3 %.
- **What looks like an edge does not repeat** in the next period (turn of the month, overnight drift after an up day).
- **Bought options lose to decay** unless the move is large; changing the expiry or strike changes the shape of the result, not the mean.

## Study by study (discovery period first; % = net per trade after costs, of notional for futures, of credit / premium for options)
- **R01 Gap-and-go** (report's 11.5-year claim; NIFTY, BANKNIFTY, SENSEX; 45 cells): 0 pass. Best NIFTY gap >= 1 % follow +0.19 % (t 1.46, n 42); gap 0.75 % +0.07 %; the "skip when 2.5 % above SMA20" filter changes little; fading gaps loses.
- **R02 Overnight / intraday drift** (24 cells): overnight long after an up day passed discovery on all three indices (+0.08 %, t 2.3-2.9) and **failed validation** (+0.04 to +0.05 %, t 1.4-1.7, negative without the best 5 % of trades). Intraday long loses, most when VIX is high (-0.17 %, t -2.6).
- **R02b Overnight on the real future 2018-2021** (follow-up): -0.02 to -0.04 % (gross about +0.03 %): the index-based overnight effect does not survive real futures prices and costs.
- **R03 Initial-balance breakout / liquidity sweep** (15 cells): 0 pass. IB breakout about 0; the sweep fade loses (its stop sits within 0.1 % and is hit most of the time).
- **R04 Supertrend pullback** (6 cells): 0 pass (best +0.035 %, t 1.15).
- **R05 TWAP mean reversion** (12 cells): 0 pass; loses even before costs (t down to -4.3): stretched intraday moves continue slightly.
- **R06 Overnight option selling, VolGuard-like** (9 cells, NIFTY minutes): 0 pass. Short straddle -1.1 % of credit (gross about +2 %), iron fly -3.1 %, long straddle -4.8 %. The VIX 12-18 and VoV filters made it worse.
- **R07 Pre-event short straddle / strangle** (RBI, Budget, FOMC; 4 cells): 16 events in discovery, too few to test; -3 % to -13 % of credit.
- **R08 Next-week expiry for G1 / G1-C signals** (8 cells): 0 pass. The next weekly lifts the win rate and median (puts: median -51 % -> -4 %) but not the mean (+8.4 % -> +7.0 %).
- **R09 Weekly ATM straddle held to expiry with VIX-percentile / VoV filters, NIFTY and BANKNIFTY 2018-2021** (20 cells): 0 pass. Unfiltered short -2.2 % / -0.9 % of credit. The VoV idea points the right way but is not significant: short when VoV is low +6.6 % / +6.2 % (t 0.8), long when VoV is high +10.2 % on NIFTY (t 0.86). Selling when the VIX percentile is above 70 loses (-11 %). Exploration X1 (labelled post-hoc): the 'VoV switch' read on 2022-01 to 2024-09 loses (NIFTY -4.3 %, BANKNIFTY -4.5 % a trade); the pattern did not repeat.
- **R10 Bank-stock pairs** (8 cells): 0 pass (best SBIN-ICICIBANK +1.1 % a trade, t 1.7; the ADF filter leaves 10-18 trades).
- **R11 Daily ML walk-forward** (logistic, random forest; 4 cells): 0 pass (random forest +0.056 %, t 1.71).
- **R13 Intraday momentum** (Gao et al.; 9 cells): 0 pass; net significantly negative (t -2.5 to -3.7) because the last half-hour moves less than the costs; gross about 0, so the reverse loses too.
- **R14 Trend filters** (SMA200, 50/200 cross, Donchian; 4 cells): 0 pass (4-55 holding spells; buy and hold made 89 % in 2012-2017).
- **R15 Short-term reversal** (RSI(2), 3-day runs; 4 cells): 0 pass.
- **R16 VIX spike buying** (3 cells): 7 episodes each in discovery: too few.
- **R17 Calendar anomalies** (3 cells): turn of the month passed discovery (+0.61 % a trade, t 2.54, 71 months) and **failed validation** (+0.47 %, t 1.21, 48 months). Monday short and the weekend effect: nothing.
- **R18 NIFTY / BANKNIFTY ratio** (1 cell): 23 trades, t 0.41.
- **R19 Calendar straddle** (sell the near weekly, buy the next weekly, NIFTY 2018-2021; 2 cells): loses -4.7 % of the far premium a trade (t -2.55); in low VIX -6.7 % (t -2.34). The "calendars when VIX is low" claim fails.
- **R12 Combinations:** not run, by rule: no study produced a validation passer to combine.

## Failed approaches: most likely reasons (from their own numbers)
1. **Cost floor.** NIFTY futures cost about 0.035 % a round trip in 2021-2025 and about 0.06 % after April 2026 (futures STT 0.05 % on sales). Intraday drifts, breakouts and momentum on the index are below that.
2. **Decay and spread on bought options:** a long option needs a move larger than its premium; the median bought option in every buy study loses 15-50 %.
3. **Selling premium overnight or around events:** the premium is there before costs, but four legs of slippage and charges on a 1-lot NIFTY position are larger, and the tails (gaps) are fat.
4. **Small samples:** event and VIX-spike studies have 7-16 events in each period; nothing can be concluded from them either way.
5. **Regime dependence:** the best-looking cells (overnight after an up day, turn of the month) were positive in 2021-2023 and weaker after.

## Integrity notes
- Pre-registered before numbers; amendments disclosed what had been seen. Cells added after a number: R02b (labelled a follow-up of R02).
- One disclosure: to measure cost drag, pooled (all cells together) net and gross per period of R01, R02, R03, R13 were printed, including the late period (no cell-level late number). Recorded in `NOTES.md`.
- The index is used as a proxy for its future (basis ignored intraday); R02b checks the overnight case on real futures.
- Not testable with our data: BANKNIFTY option minutes, futures minutes, any bid/ask, tick data, an event calendar before Oct 2024, a cash-futures arbitrage book. The Jane Street order describes manipulation, not a strategy, and is not tested.
- Selling structures and futures were researched only because the user asked for every family; trading them would need a separate decision (buy-only since 30 Oct, margin).
