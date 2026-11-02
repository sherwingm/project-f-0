# S3 PUT1 · NIFTY downside opening-range breakout, puts only, tested on unseen spot (pre-registered 2026-11-02)

**Why:** the execution audit (`data/results/S3_execution_audit_2026-11-02.md`) found the put side of the breakout
ideas better than the call side on 2024-26 options (booked before costs: B1 −0.1 % vs −1.0 %, B2 +0.9 % vs −4.4 %,
P4 +5.5 % vs −7.0 %; held to 15:15: B1 +1.0 %, B2 +3.3 %, P4 +9.6 %). That was found after seeing the data, so it is a
hypothesis. The user chose to test it ("Yes, puts test"). No 2022-24 option minutes exist, so the test is the NIFTY
move a put would ride.

**Already seen on this window (disclosed):** B2 stage A read 2022-01-03 → 2024-09-30 spot for *accepted* breakouts
(15 closes) with the failure exit: puts +0.020 % a trade (306), calls +0.017 % (289); the first breakout with the
failure exit, both sides: +0.003 % (664). This test differs (first breakout, no acceptance, held to 15:15), but the
window is not untouched by breakout studies.

## Rules (no open parameters)
- **Data:** NIFTY 50 spot 1-minute (`index_data.load.spot_1m`, the repaired store), sessions with the usual minimum
  bars (`scanner.s3_regime.MIN_BARS`).
- **Window:** 2022-01-03 → 2024-09-30. Halves: 2022-01-03 → 2023-05-31 and 2023-06-01 → 2024-09-30.
- **Opening range:** high and low of the 09:15-09:29 bars.
- **Signal:** the first 1-minute close outside the range between 09:30 and 13:00 (B1 / P4's breakout, `s3_b2.signal`
  with no acceptance). **Trade only when it is below the low** (a put). A day whose first breakout is upward has no
  trade (no second look).
- **Entry:** the close of the minute after the signal. **Exit:** the 15:15 close.
- **Measure:** the fall of NIFTY, entry → exit, in % (positive = the put's direction).

## Gate (all must hold)
1. At least 150 trades.
2. Mean ≥ +0.10 % a trade (the cost-and-decay hurdle from B1's trades: net ≈ −5.86 + 80.86 × move %, break-even
   ≈ +0.07 %, rounded up as in B2).
3. t ≥ 2 (one trade a day, plain t).
4. Both halves positive.
5. Neighbours positive: opening range 12 minutes and 18 minutes, same rules.

## Reported, not part of the gate
- Calls under the same rules (the control).
- Puts with P4's filters (previous close below its 20-day EMA, India VIX < 14 at the signal minute).
- Puts with the failure exit (the minute after the first close back above the range low, else 15:15).
- By year.

## After the run
- **Pass:** the put side goes to the forward stage only: 30 paper-record trades from the live 1-second NIFTY data
  (`data/index/nifty_1s`), priced on the real option bid/ask, before anything else. Nothing turns on by itself.
- **Fail:** the put lead is closed; it is not rescued by changing the window, the range or the exit.
- Run once. The result goes to DECISIONS.md either way.
