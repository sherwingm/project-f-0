# S1 fade · buying at the open: a fair-price limit (option) and the stock future's pre-open

Pre-registered: strategies/S1_fade_preopen_entry.md (research summary there). Descriptive; nothing live changes. t is date-clustered; real only with t >= 2 and the same sign in both halves/windows.

## Calibration

c (day-0 close IV / previous close IV, median) = **0.922** from 384 of 384 2022-24 fade trades (day 0 before 2024-10-17).

## Test 1 · limit at a fair price, v11 exit (409 of 409 trades got an L)

| variant | period | fills | entry | n | win % | mean % | median % | total Rs | t |
|---|---|---|---|---|---|---|---|---|---|
| main | all | 262 / 409 | limit L | 262 | 24.8 | -1.66 | -21.2 | -51382 | -0.483 |
| main | all | 262 / 409 | B 09:16 (same trades) | 262 | 20.2 | -1.42 | -21.2 | -53294 | -0.413 |
| main | all | 262 / 409 | A opening print (same trades) | 262 | 23.3 | -2.12 | -21.2 | -68996 | -0.534 |
| main | Oct24-Oct25 | 113 / 189 | limit L | 113 | 22.1 | -4.39 | -22.3 | -48132 | -0.725 |
| main | Oct24-Oct25 | 113 / 189 | B 09:16 (same trades) | 113 | 22.1 | 0.88 | -21.5 | -20762 | 0.128 |
| main | Oct24-Oct25 | 113 / 189 | A opening print (same trades) | 113 | 23 | -8.82 | -22 | -74818 | -1.611 |
| main | Nov25-Sep26 | 149 / 220 | limit L | 149 | 26.8 | 0.4 | -21 | -3250 | 0.102 |
| main | Nov25-Sep26 | 149 / 220 | B 09:16 (same trades) | 149 | 18.8 | -3.16 | -21 | -32533 | -1.006 |
| main | Nov25-Sep26 | 149 / 220 | A opening print (same trades) | 149 | 23.5 | 2.95 | -21.1 | 5821 | 0.538 |
| c=1 | all | 338 / 409 | limit L | 338 | 22.5 | 0.41 | -21.2 | -880 | 0.118 |
| c=1 | Oct24-Oct25 | 152 / 189 | limit L | 152 | 23.7 | 2.41 | -21.8 | 10999 | 0.389 |
| c=1 | Nov25-Sep26 | 186 / 220 | limit L | 186 | 21.5 | -1.22 | -21 | -11880 | -0.317 |
| Lx0.90 | all | 210 / 409 | limit L | 210 | 22.4 | -1.41 | -21.3 | -30034 | -0.327 |
| Lx0.90 | Oct24-Oct25 | 100 / 189 | limit L | 100 | 21 | -1.56 | -22.1 | -29989 | -0.213 |
| Lx0.90 | Nov25-Sep26 | 110 / 220 | limit L | 110 | 23.6 | -1.28 | -21.1 | -45 | -0.259 |
| Lx1.10 | all | 295 / 409 | limit L | 295 | 22 | -1.19 | -21.2 | -47861 | -0.361 |
| Lx1.10 | Oct24-Oct25 | 132 / 189 | limit L | 132 | 23.5 | -0.7 | -21.7 | -24135 | -0.124 |
| Lx1.10 | Nov25-Sep26 | 163 / 220 | limit L | 163 | 20.9 | -1.59 | -21.1 | -23726 | -0.408 |
| mid fill | all | 262 / 409 | limit L | 262 | 27.1 | 3.28 | -21.2 | 51775 | 0.934 |
| mid fill | Oct24-Oct25 | 113 / 189 | limit L | 113 | 24.8 | 1.34 | -21.6 | 2584 | 0.211 |
| mid fill | Nov25-Sep26 | 149 / 220 | limit L | 149 | 28.9 | 4.76 | -21 | 49191 | 1.231 |

### Test 1, v10 exit (main variant)

| exit | entry | n | win % | mean % | median % | total Rs | t |
|---|---|---|---|---|---|---|---|
| v10 | limit L | 262 | 40.1 | 0.38 | -20.2 | -20260 | 0.084 |
| v10 | B (same trades) | 262 | 34.4 | -3.24 | -25 | -90920 | -0.73 |

### The trades the limit did not fill (what B did on them)

| group | entry | n | win % | mean % | median % | total Rs | t |
|---|---|---|---|---|---|---|---|
| not filled | B v11 | 147 | 36.7 | 9.41 | -20.8 | 118877 | 1.706 |

### Prices

| measure | value |
|---|---|
| fill vs B entry, median % | -3.3 |
| fill below B entry, share % | 57.6 |
| L vs the opening print A, median % | -17.3 |
| filled in the 09:15 candle, share % | 78.2 |
| no L (no IV / no eod2) | 0 |

## Test 2 · stock future at the pre-open price, open -> close, net of 0.05 %

| group | n | win % | mean net % | median net % | t | mean Rs per lot | total Rs (1 lot each) | median lot value Rs |
|---|---|---|---|---|---|---|---|---|
| all | 868 | 58.9 | 0.456 | 0.607 | 4.228 | 3323 | 2884238 | 689008 |
| puts -> sell future | 638 | 58.2 | 0.386 | 0.532 | 2.743 | 3168 | 2021437 | 721044 |
| calls -> buy future | 230 | 60.9 | 0.652 | 0.748 | 2.795 | 3751 | 862801 | 593829 |
| 2022-24 | 434 | 58.3 | 0.317 | 0.47 | 2.077 | 2625 | 1139432 | 731636 |
| 2025-26 | 434 | 59.4 | 0.595 | 0.746 | 3.907 | 4020 | 1744806 | 652922 |
| from 2025-12-08 (futures pre-open live) | 220 | 59.5 | 0.611 | 0.894 | 2.79 | 4272 | 939734 | 667000 |


2 trades without eod2 prices. Proxy: the stock's own open and close.

## Independent verification (4 agents, 2026-10-21; checks after the result, not pre-registered)

**Test 1 (option limit):** no code bug; 8 hand-checked trades match to the paisa; BS/IV match a textbook to 1e-12;
c = 0.922 reproduced. The sign is fragile (a less pessimistic fill price gives +3.6 %, t 1.05), but no variant reaches
t 2. Unfilled trades did better under B (+9.4 % vs −1.4 %), mostly from 3 big winners. **Verdict: no edge.**

**Test 2 (stock at the pre-open auction price, fade side, to the close):** the arithmetic reproduces exactly
(+0.456 %, t 4.23). By the pre-registered rule (0.05 % cost) it passes. But:
- **Real costs are about double.** Futures charges at today's rates are 0.064 % of value (STT 0.05 % on the sell leg),
  plus slippage 0.04 % → 0.104 %. Net +0.40 %, t 3.7 overall, but **2022-24 t 1.72** (fails the both-windows rule);
  2025-26 +0.54 %, t 3.6.
- **Market-adjusted** (minus signed NIFTY 500 open→close), with real costs: 2022-24 t 1.37; 2025-26 t 3.42. The short-heavy
  book (638 of 868 are puts) picks up intraday market drift.
- **Almost all of it is the first minute after the auction:** auction price → 09:16 open +0.39 % (t 7.6); 09:16 → 15:19
  +0.11 % (t 1.1). Entering at the 09:16 open: +0.06 % net (t 0.6). So it exists **only** for an order filled in the
  pre-open call auction. The exit (15:20 sell vs official close) changes nothing.
- **Half of it is generic gap reversal.** Gap-matched non-results days give +0.18 % gross for the same side. Excess over
  that: +0.33 % (t 3.0) raw, +0.21 % (t 2.0) market-adjusted, and not significant in 2022-24 (t 1.15 / 0.29). On the 76 %
  of trades where the side agrees with the gap (strong → gap up → short) the excess is ≈ 0; it comes from the 24 % where
  the side goes with the gap.
- **The instrument:** stock futures have had a pre-open auction only since 2025-12-08 (220 trades: +0.56 %, t 2.5 with
  real costs). Before that the only route is a cash intraday short/long placed in the cash pre-open. The futures'
  own auction prices are not in the local data, so the futures route itself is untested. The cash auctions are thin
  (2022 H1 median 32 lots matched), so a 1-lot order can move the price.
- 2023 lost money (−0.16 % net, 156 trades). All 1,053 signals (before the option filter): +0.50 %, t 5.2 (0.05 % cost).

**Verdict:** a real but fragile effect: the cash auction price overshoots on results mornings and pulls back within a
minute. Capturing it needs a fill **in the auction itself**, in the stock (cash) or, since Dec 2025, the current-month
stock future, with linear risk (one futures lot ≈ ₹6.9 L of stock vs a ₹600-8,000 option premium). Not established
for 2022-24 after real costs; about half is not specific to results. No rule changes.
