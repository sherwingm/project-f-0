# S3 X1 · NIFTY expiry-day option buy: ATM put bought the evening before, +200 % target, 50 % stop (pre-registered 2026-11-03)

**Why:** the user, 2026-11-03: "we are going to trade on the expiry date near options too", with screenshots of
the NIFTY 03 Nov 2026 23700 call (₹4.25 at 15:25 on 2 Nov → ₹59 on 3 Nov, +1,338 % against the previous close),
and "Yes" to writing the rules down before any run. Buy only, 1 lot.

**What was seen before this page (disclosed):** every expiry day with option prices from Oct 2024 on.
- `data/results/S3_expiry_day_scan.md`: options bought at 09:20 on expiry day, 0-6 strikes out (minute data).
- `data/results/S3_X1_design.md`: the grid below on daily bhavcopy, 2024-10-01 → 2026-10-30, 109 expiry days.
  - Calls lost in every cell (−22 % to −65 % of the premium).
  - Puts were about break-even. The best cell, and the primary here, is the ATM put bought at the previous close with
    a +200 % target: +17.1 % a trade, t 1.45, won 47 %, max up median +80 %, ≥ +100 % on 46 % of days.
  - That cell was picked **after** seeing the grid, so 2024-26 is in-sample. The test is 2022-24, never priced for
    expiry-day NIFTY options in this project (the 2022-24 NIFTY spot was read by B2 stage A and PUT1; no option
    prices).

## Data
- NIFTY option daily rows from the NSE bhavcopy (`options_daily/NIFTY`): open, high, low, close, volume, lot.
- Expiry days: every session where a NIFTY option expires and trades (from the bhavcopy, weekly and monthly).
- Spot: NIFTY 50 1-minute (`index_data.load.spot_1m`) for the strike.
- No option minutes exist before Oct 2024, so the order of the day's low and high is unknown. A day that touched
  both the stop and the target is counted as **stopped** (the worst case); the target-first result is reported
  beside it, not used by the gate.

## Rules (no open parameters)
- **Window:** 2022-01-03 → 2024-09-30. Halves: 2022-01-03 → 2023-05-31 and 2023-06-01 → 2024-09-30.
- **Entry:** the session before the expiry day, at its **closing price** + 1 % slippage, 1 lot of the **at-the-money
  put** (strike nearest NIFTY's last 1-minute close that session, 50-point steps) of the expiring contract.
- **Exit on expiry day:**
  - a sell order resting at **+200 %** of the price paid: filled when the day's high reaches it, at the open − 1 %
    if the day opens above it;
  - a **50 % stop-loss** (added by the user before the run, 2026-11-03: "Keep a 50% SL"): out at half the price
    paid − 1 % when the day's low reaches it, at the open − 1 % if the day opens below it;
  - a day that touched both counts as the stop;
  - otherwise the expiry day's closing price − 1 %.
- **Costs:** 1 % slippage each way, charges from `server/charges.py`, 1 lot: the bhavcopy lot from 2024-07, and
  before it the NSE lot used by D6 (`scanner/s3_d6_d7.lot_for`: 50, then 25 from 2024-04-26), since the 2022-24
  bhavcopy lot column is empty. The lot moves ₹ figures and the flat fees only.
- A day is skipped only if a needed row is missing or the put did not trade the evening before; every skip is
  listed.
- **Max up** (the standing rule): the expiry day's high over the price paid, reported as mean, median and the share
  of days reaching +100 %.

## Gate (all must hold)
1. At least 100 trades.
2. Mean net % of the premium paid > 0.
3. t ≥ 2.
4. Both halves positive.
5. The worst trade (₹) is smaller than the average month's gain (₹).
6. Neighbours positive (all with the 50 % stop): target +100 %; target +300 %; 1 strike out of the money (+200 %).

## Reported, not part of the gate
- The ATM call, same rules (the control).
- The ATM put bought at the expiry day's **open** instead (+200 % target).
- The ATM put with no target (stop only).
- The ATM put with the target and no stop (the rule before the user's change).
- The primary with target-first on days that touched both (the best case), and how many days that was.
- Note: the 2024-26 design grid had no stop; the stop was added before any test-window run, not picked from data.
- By year.

## After the run
- **Pass:** the forward stage only: paper records from the live 1-second NIFTY data (`nifty_1s`), on the real
  bid/ask, at least 30 expiry days, before anything else. Nothing turns on by itself.
- **Fail:** the lead is closed. It is not rescued by changing the window, the strike or the target.
- Run once (`python -m scanner.s3_x1 --run`). The result goes to DECISIONS.md either way.
