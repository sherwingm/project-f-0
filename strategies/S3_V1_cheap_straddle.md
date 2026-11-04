# S3 V1 · buy the NIFTY ATM straddle only when options are cheap (pre-registered 2026-11-04)

**Why:** the user, 2026-11-04: "Back to our strategy in the rest of finding the edge" and "Start v1". Eight buy-only
ideas (E1, Q1, B1, G1, P4, B2, PUT1, X1) all tried to call the direction or the big day and failed. An option buyer
pays the implied move and earns the move NIFTY then makes; sellers are usually paid for the risk, so the buyer starts
behind. V1 buys only on the days the price implies **less** movement than NIFTY has been making. Buy only, 1 lot of
each leg. The user said on 2026-11-03 not to use 2022-24 data any more, so the test is the later half of the option
minute data.

**What was seen before this page (disclosed):** `data/results/S3_V1_design.md`, 2024-10-01 → 2025-09-30.
- Expensive straddles lost heavily: ratio10 ≥ 1.1 held to expiry −28.6 % (09:45) and −29.6 % (14:45) a trade.
- Cheap ones were near break-even. The primary below: 80 trades, +6.8 %, median −6.3 %, t over expiries 1.00 (39
  expiries), max up median +34 %, ≥ +100 % on 19 %. Holding only to the next session lost in every band.
- The test window's option minutes were used before by B2, P4 halves, PUT1 and the max-up tables, but never to price
  implied against realized movement.

## Definitions (all known at the entry minute)
- **Straddle:** buy the ATM call and the ATM put (strike nearest NIFTY's entry-minute close, 50-point steps) of the
  nearest weekly expiry with at least one session after the entry day (`scanner.s3_p4.expiry_after`).
- **IV:** the mean of the call's and the put's Black-Scholes implied vol on spot at the entry minute
  (`scanner.fade_preopen_entry.iv`, calendar time to 15:30 on expiry).
- **Session variance:** the sum of squared 5-minute log returns of NIFTY 50 in a session plus its squared overnight
  gap.
- **ratio10:** √(IV² × time to expiry) ÷ √(mean session variance of the 10 sessions before the entry day × sessions
  left, counting the rest of today and every session up to and including the expiry day). It's the move the price
  implies to expiry over the move at the last 10 sessions' pace. Below 1 means cheap.

## Rules (no open parameters)
- **Window:** 2025-10-01 → 2026-10-30. Halves: → 2026-03-31 and 2026-04-01 →.
- **Entry:** every session at **14:45**, when **ratio10 < 1.0**, at the minute's close + slippage (engine:
  `scanner/s3_engine.py`, 0.5 %, or 1 % at 2+ strikes out and outside 09:30-15:00).
- **Exit:** the expiry day's **15:15** close − slippage. No stop, no target (none was designed; max up is reported).
- **Costs:** charges from `server/charges.py`, 1 lot (bhavcopy lot). Overlapping trades are allowed (one a day).
- Max up while held is reported, split by days to expiry (0-3, 4+).

## Claim 1, cheap straddles make money: gate (all must hold)
1. At least 60 trades.
2. Mean net % of the premium > 0.
3. t over expiries ≥ 2 (each expiry's mean counts once, since trades held to one expiry overlap).
4. Both halves positive.
5. At 2× costs the mean is still > 0.
6. Neighbours positive: ratio10 < 0.9; ratio10 < 1.1; ratio5 < 1.0; entry 09:45 with ratio10 < 1.0.

## Claim 2, expensive straddles lose (a filter for every later buy idea)
- 14:45, ratio10 ≥ 1.1, held to expiry: **confirmed** if ≥ 30 trades, mean < 0 and t over expiries ≤ −2.
- If confirmed, later buy ideas may add "not when ratio10 ≥ 1.1" as a pre-registered filter. It changes nothing in
  S1, S2 or the live system.

## After the run
- **Claim 1 passes:** only the forward stage: paper records from the live 1-second NIFTY data (`nifty_1s`), on the
  real bid / ask, at least 30 expiries. Nothing turns on by itself.
- **Claim 1 fails:** the cheap-straddle lead is closed. It is not rescued by changing the cutoff, entry or window.
- Run once (`python -m scanner.s3_v1 --run`). The result goes to DECISIONS.md either way.
