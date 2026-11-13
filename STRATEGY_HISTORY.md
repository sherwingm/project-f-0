# Strategy history (draft, 13 Nov 2026, not yet committed)

One section per strategy. No strategy here is described as validated or production-ready. All numbers are quoted from `DECISIONS.md`, strategy pages, `PROGRESS.md` or `stress_audit/results/STRESS_REPORT.md`; nothing was re-run for this document.
Reading rule: "in-sample" = chosen or tuned on the same data it is measured on. "Insufficient evidence" = the confidence interval of the mean contains zero.

## S1 (stock options around quarterly results)
**Idea.** Quarterly results move a stock; an option can ride that move. Buy only, 1 lot (Rs 600 to 8,000), NSE F&O stocks.

### Versions v2 to v9 (stock-level then calls), closed
- v2 weak-sector results-miss put spread: closed at the signal (no drift, t -0.7). v3 strength score: closed (wrong direction, t -2.34).
- v4, v5, v6, v7 results-beat calls: the stock drifted up after beats in 2021-24 (futures diagnostic +1.6 % to +3.7 % over 20 sessions, t 3 to 4) but the calls lost after decay and costs (v6 arm A -19.0 %, t -2.32; v7 near-expiry trades lost most).
- v8 used the 2025-26 holdout on the user's choice (14 Oct): the drift did not persist; live rules arm S -27.6 % (t -3.42), arm A -3.3 %, arm B -14.5 %.
- v9 calls on results day: the stock moves against the headline from the open (strong numbers fall, t -5.7); options 0 of 48 groups pass.
- Weaknesses: no trial counter; daily-candle tests; strikes/budget bands changed between versions (v5 Rs 10,000 to 30,000; v6 on Rs 600 to 8,000). Status: closed.

### Arms A and B (reference strategies)
- Arm A: call on every results beat; arm B: call on a beat in a strong sector. Live paper from 14 Oct (rule trades, bought at open and at close).
- History on daily data: A -3.3 % (172 trades, t -0.25), B -14.5 %. On 1-minute candles (10 Nov): A -24.4 % (t -2.2, n 140), B -19.1 % (n 55); with an intraday 50 % stop worse; H8 / H11 / S8 variants all <= 0 or t < 1. **No variant passes.**
- Study of 405 arm A trades: the loss comes from the entry (stocks that do not follow through), not the exit. Status: reference only; no live change.

### S1 v10 fade (results-day fade; strong numbers -> put, weak -> call, same day)
- Idea from v9. Paper from 15 Oct. Backtest 2025-26 (descriptive): +5.6 % a trade, t 1.33; entry at VWAP instead of the open -> -14.9 %. 2022-24: +3.6 %, t 0.9.
- 16 / 17 Oct: eight trades missed their same-day exit when the server slept; closed on Monday; carry rule retired.
- Diagnostics: the fade is mostly a first-15-minutes effect; no consistent pre-entry feature; one weak lead (puts with NP YoY 10 to 25 % lose), judged chance level.

### S1 v11 (v10 + -20 % stop) and v12 (v11 + trail)
- v11 live from 21 Oct on 1-minute evidence (468 trades, descriptive): stop +Rs 2.51 lakh (t 2.47) vs 15:20 +Rs 1.70 lakh (t 1.71). Taken **before** the pre-registered 30-trade test.
- v12 live from 22 Oct: trail on at +10 % (bid >= 1.10 x entry), sell at 2 % below the highest bid. Backtest 2025-26 (362 trades): +3.25 % a trade, t 2.18, vs v11 +0.23 %; page: not proven, 2 % gap picked after seeing results.
- Minute re-test (10 Nov, 339 trades with minutes, entry 09:16 open + tick): v12 +2.86 %, t 1.79, +1.75 % without the top 3; v10 hold +3.88 %, t 0.78.
- **Stress audit (13 Nov):** removed edge at 2 % slippage (-1.13 %), one-candle-later entry (-1.53 %), worst case -7.64 %; high-first ordering +0.23 %; bracket -2.33 % to +5.42 %; interval -0.35 to 5.92 %; strike-pick look-ahead; no sealed holdout; 71 variants.
- **Live paper:** 58 closed v12 trades to 9 Nov: mean -5.69 %, 47 % won (descriptive; previously inspected).
- Shadow tracks (np25, fd2, trail, t100, s20, fd2): started; outcomes not found in the files read.
- **Status: paper only; insufficient evidence; execution assumptions unrealistic; overfitting risk high; out-of-sample inadequate.**
- **Needs:** the 30-trade live review result (not located), the 1-second recorder to settle intrabar order, headline net of slippage, the prospective holdout.

## S2 (stock options from price and futures-OI build-up)
- Step 1 screen (48 cells, 2021-26): 1 passes (short build-up, +0.62 % over 5 sessions, t 3.17). Step 2 bought put: -14.2 % of premium (t -2.71); the Rs 600 to 8,000 band puts the strike too far from the money. Screen B: 0 of 8 tests pass; parts not testable (futures series failed the pre-registered check; not loosened).
- Status: closed. Lead noted: weak-result stocks tend to rise (the fade's call side).

## S3 index options (NIFTY first, SENSEX replication)
### Round 1, expiry-day structures (P1 to P7, closed 23 Oct)
- P1 iron fly, P2 long straddle (t -3.08, the only independent primary with |t| >= 2), P2s short fly, P3 condor, P4 ORB long, P6 naked short straddle (+15 % after fixes but fails t, halves, worst day), P7 fly 5 lots (same). P5 not testable.
- D4 tail study: P6 would have averaged -28 % of the credit over 2021-24. R1 on SENSEX: does not replicate. Short-premium selling is also outside the user's "buy only" (30 Oct) choice.
### Round 2, buy pods (closed 30 Oct, re-run on repaired spot)
- E1 event straddle -6.2 % (31 trades), Q1 squeeze straddle -2.6 %, B1 ORB + volume -2.5 % (488 trades, volume test not selective), G1-gap -4.3 %. SENSEX: nothing replicates. Max up descriptive: medians +6 % to +14 % while booked -9 % to -18 %.
### Further closed studies
- L1 VIX-rising straddle (+7.8 % but t 0.64, carried by one trade), D6R short vol 2018-21, B2 accepted breakout (-3.8 %, t -2.75), PUT1 (spot -0.006 %), X1 expiry-day put (-8.9 %), V1 cheap straddle (-10.9 %). N1 near-expiry ORB: pre-registered forward test.

## G1 (NIFTY downside ORB put, held overnight)
- **Rule:** opening range 09:15 to 09:29; first 1-minute close outside it 09:30 to 13:00; only a close **below** the low trades; ATM put of the nearest weekly after today at the next minute's last ask; stop bid <= 50 % of price paid; else sold at the first quote of the next session's 15:29 (changed from 09:16 on 6 Nov by the user).
- **Origin:** the best of seven in-sample PUT1 variants (+8.4 %, t 1.72, 259 trades). The earlier spot test of the same breakout idea (2022-24) failed (-0.006 %), so the 2024-26 put advantage did not appear on earlier years.
- **History (live-style replay, in-sample):** 259 trades, +5.54 %, t 0.94, +Rs 41k; fails at 2x costs; max drawdown -Rs 114k, not recovered. Without the best three trades about zero. Loses in high-VIX periods (-12 %) and 2026 H2. Only the overnight hold works (all same-day exits negative).
- **Live paper:** 1 of 30 trades: bought 9 Nov at Rs 289.85, sold 11 Nov first quote at Rs 78.70 (-73.2 %; the stop was at Rs 144.93).
- Searches for anything that predicts follow-through (score x10 methods, formation shapes, 5 years of spot, FII/DII x3, news tone, heavyweights, holding patterns, IV crush, minimum break size): **none found**. Breakout score 0 to 7 is record-only.
- **Status:** paper baseline; insufficient evidence. **Needs:** 30 live trades judged on the gate (mean > 0, still > 0 at 2x costs, t >= 2, both halves positive, worst loss < average month).

## G1-F (G1 with three filters; the main track since 6 Nov)
- Filters: day-1 gap < +0.3 %, range width not 0.5 to 0.8 %, VIX < 17. Chosen from nine bucket tables on the same 154 trades.
- History (in-sample): +19.7 % a trade, t 2.41, +Rs 2.47 lakh (+Rs 2.13 lakh at 2x costs), win 41 %, median -18 %, max drawdown -Rs 41.6k, 7 of 23 months negative; positive in 27 of 27 neighbours and under every stress (combined +16.8 %); concentrated: top 5 % of trades make 36 % of profit; fades year on year (+25 % -> +14 %).
- Passes its 30-trade gate at 60 to 150 trades, not at 30. **Live: 0 of 30 trades** (G1-F skipped the one live signal: gap +0.31 %, width 0.72 %, VIX 18).
- **Status:** the best-looking result with the weakest evidence; in-sample. **Needs:** live trades only; do not call it validated before review sizes are met.

## G1-C (call mirror; 12 Nov)
- Built at the user's request although the 9 Nov record says the call mirror is not supported (calls lose about 11 % a trade, at every strike). No filters, no score; own ledger and 30-trade gate. Live 1 of 30: -50.75 %, same day. Status: paper, expected to fail.

## XP (NIFTY expiry-day straddle log)
- ATM CE + PE at 09:16 asks, +20 % target on the pair else 15:15; log only; 40-day gate. History replay (107 expiry days): -11.0 %, t -2.70. Live 1 of 40: -72.5 %. Status: log; history says it loses.

## Near Tighty (NT) (separate track, only summarised)
- Same entry and exit as G1 but only when the expiry is 1 to 3 sessions away; paper since 4 / 5 Nov; SENSEX added 8 Nov. The rule was found after the fact (in-sample +5.6 % / +19.2 % by year, 161 trades, t 1.71). Forward 30-trade verdict pending. Not deep-dived here by the project's own instruction (kept out of the index chat).

## Independent expiry research (`expiry_research/`)
- 2018 to now with a sealed final period (not opened here): no direction edge (AUC 0.44 to 0.56); size partly predictable (volatility clustering) but a long ATM straddle loses; later pods consistent.

## Strategies that influenced decisions most
1. v9's reversal finding -> created the fade (S1 v10).
2. 1-minute data availability (Oct 2024) -> turned the stop from "no help" to "helps" on minutes (v11), and opened S3.
3. The call/put asymmetry in 2024-26 (puts better than calls everywhere) -> G1 puts only; it fails on 2022-24 spot, so it may be period-specific.
4. The failure of all selling structures -> user's "buy only" decision (30 Oct).
