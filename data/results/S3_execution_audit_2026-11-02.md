# S3 buy ideas · execution audit (2026-11-02, descriptive)

The user's question: "the ideas are really perfect, I think our execution has some error". Read-only checks on the
existing trade files; no rule, page or verdict changes. Code: `scripts/s3_execution_audit_{decomp,fills,hold}.py`.

## 1. Fills against the raw minute files
Every primary-cell trade of P4 (58), B1 (488) and B2 (430) re-priced from the stored option minutes: entry = the close
of the minute after the signal + slippage, exit = the exit minute's close − slippage. **976 of 976 entries and exits
match to the paisa.** Strike, expiry, lot and quantity as the rules say. No engine bug found.

## 2. Where the loss comes from (primary cells, % of premium a trade)
"Before costs" = the option's own price move from the entry minute to the exit minute (no slippage, no charges).

| Idea | Trades | Before costs (mean / median) | Won before costs | Slippage | Charges | Booked |
|---|---|---|---|---|---|---|
| P2 last-half-hour straddle | 52 | −24.0 % / −40.3 % | 29 % | 1.1 % | 9.7 % | −34.8 % |
| P4 ORB + filters | 58 | −0.6 % / −10.4 % | 34 % | 1.1 % | 0.9 % | −2.6 % |
| E1 event straddle | 31 | −4.5 % / −7.5 % | 32 % | 1.0 % | 0.7 % | −6.2 % |
| Q1 quiet straddle | 34 | −0.9 % / −14.2 % | 35 % | 1.0 % | 0.7 % | −2.6 % |
| B1 ORB + volume | 488 | −0.5 % / −13.6 % | 32 % | 1.1 % | 0.9 % | −2.5 % |
| G1 gap follow | 33 | −2.5 % / −16.9 % | 24 % | 1.1 % | 0.7 % | −4.3 % |
| B2 accepted ORB | 430 | −1.8 % / −7.8 % | 26 % | 1.2 % | 0.9 % | −3.8 % |

Costs are about 2 % a trade (P2: 11 %, a cheap straddle with 4 orders). **Before any cost every idea is already at or
below zero**, so cheaper execution alone cannot make one pay.

## 3. Exits, days to expiry, side (P4 / B1 / B2, before costs)
- **Holding to 15:15 with no stop or trail** instead of the rules: P4 −1.2 %, B1 −1.4 %, B2 −1.8 % (booked −0.6 /
  −0.5 / −1.8 %). The stop and trail are not what loses the money.
- **Days to expiry** (B1 / B2 / P4 as booked): 1-2 days −4.6 / −4.2 / −6.4 %; 3-4 days +3.9 / −3.3 / +3.3 %;
  5-6 days −0.1 / +1.1 / +4.1 %; 7-8 days +0.3 / −1.0 / −0.3 %. The last two sessions before expiry are the worst.
- **Calls vs puts** (booked): B1 −1.0 / −0.1 %, B2 −4.4 / +0.9 %, P4 −7.0 / +5.5 %. Puts do better in all three, but
  these are largely the same breakout days, so it is one observation, not three.

## Reading
Execution is priced correctly and costs are small. The loss is in the price move itself: on most days the bought
option does not rise enough. The two leads (skip 1-2 days to expiry; puts only) were found after seeing the data, so
they are hypotheses: each needs its own page written first and a test on data these trades have not seen (NIFTY
2022-24 spot for the put side; the forward 1-second record for days to expiry, which spot alone cannot price).
