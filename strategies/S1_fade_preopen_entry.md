# S1 fade · buying at the open: research, and two pre-opening-price entries (backtest)

**Pre-registered 2026-10-21**, before any of these numbers is computed. The user: "who said it can't be bought, make it
buy at the price, from the pre bidding it can be bought, go through the research of how to make it possible".
**Nothing live changes.** Descriptive; any rule change is the user's decision.

## What the research found (sources checked by a second agent that tried to refute them)
- **Stock options have no pre-open.** NSE/FAOP/71092 (3 Nov 2025, live 8 Dec 2025) brought the call auction to
  derivatives for **current-month stock and index futures only** (next month in the last 5 sessions). It says the
  pre-open "shall not be applicable" to "Spread & Option contracts on Indices and stocks"; the 7 Sep 2026 revision
  (NSE/FAOP/74970) keeps that. An option order sent in the pre-open is rejected (error 16145). No NSE circular to
  19 Oct 2026, and no SEBI paper, adds options.
- **So a stock option's open is its first trade at 09:15:00 in continuous matching.** NSE matches at the resting order's
  price, and rejects market orders in an option until it has traded that day (NSE/FAOP/51600). So the first print is
  always limit against limit: whichever limit reached the empty book first. That is why it is often far from where
  the option trades seconds later.
- **Retail orders arrive late.** Brokers hold option orders placed before 09:15 (AMOs) and release them at 09:15
  (Zerodha, Upstox; Kotak's Dec 2025 bulletin: option orders refused 09:00-09:08, accepted again from 09:08, sent at
  09:15). Users report fills at 09:15:02 or later; colocated algo firms dominate (SEBI, Aug 2026). A retail order cannot
  count on the opening print. What it can count on is a **price cap** (a limit order), not a fill.
- **NSE itself prices options at the open from the cash pre-open:** the Limit Price Protection reference at the open is a
  Black-Scholes value from the underlying's cash pre-open price (NSE/FAOP/54242; stock options from 6 Feb 2023,
  NSE/FAOP/55344; band ±40 % above ₹50, ±₹20 at or below).
- **The only literal "buy at the pre-open price":** the current-month **stock future** (from 8 Dec 2025) or the stock
  itself, in their call auctions. Everyone matched gets one price. The payoff is linear (no premium cap, a full lot of
  stock, margin).

## Test 1 · a limit order at a fair price, sent for 09:15 (the option)
- **Trades:** the same 409 contracts as `S1_fade_realistic_entry.md` (₹2+ v10 contracts, day 0 Oct 2024 - Sep 2026, with
  a 09:16 candle). The contract is not changed (note: it was picked with day-0 open prices, as before).
- **The limit L**, known before 09:15:
  - S = the stock's day-0 open (the cash pre-open price; eod2 `Open`), on the option's price scale:
    S = spot_prev × eod2 open(day 0) / eod2 close(prev), where spot_prev is the previous session's underlying price
    in the F&O bhavcopy (`backtest_s1_v10.Bhav.spot`), which removes eod2's split adjustment.
  - Black-Scholes (European, no dividend), r = 6.5 %, T = calendar days from day 0 to expiry / 365 (expiry day counts as
    0.5 day if T would be 0).
  - σ = the option's **implied volatility at the previous close** (from its bhavcopy close, spot_prev, T + 1 day) ×
    **c**, the results-day IV drop. **c is fixed before the test** on the 2022-24 v10 fade trades with day 0 before
    2024-10-17 (no overlap): the median of IV(day-0 close) / IV(previous close) for the same contract (day-0 close and
    day-0 spot from the bhavcopy). If an IV cannot be solved (price below intrinsic, etc.), that trade has no L and is
    counted.
  - L = that value rounded **down** to the tick (₹0.05 before 2025-11-03, ₹0.01 from it). L < ₹0.05: no order.
- **Fill (1-minute candles, conservative):** the order is live from the 09:15 candle to the 09:29 candle (then
  cancelled). It fills in the first candle whose **low ≤ L − 1 tick** (the price traded through the limit, so a queue
  ahead of us is not assumed away). Fill price = **min(L, that candle's high)**: the worst price inside that candle we
  would accept. No fill: no trade (counted; what B did on those trades is shown).
- **Exits** (same code as the realistic-entry study): v10 = the 15:19 close − 1 tick; v11 = the −20 % stop (0.80 × fill)
  from the candle **after** the fill candle, filled at min(stop, that candle's open) − 1 tick, else the v10 exit. Real
  charges, no extra % slippage.
- **Primary result:** v11 on the filled trades: N, fill rate, win %, mean and median net % of premium, total ₹,
  date-clustered t, both halves (Oct 2024-Oct 2025, Nov 2025-Sep 2026). Beside it, on the **same filled trades**:
  entry A (opening print + tick) and entry B (09:16 open + tick).
- **Sensitivity (reported, not chosen from):** c = 1 (no IV drop); L × 0.90; L × 1.10; and the fill price = min(L,
  (high + low) / 2) instead of min(L, high).

## Test 2 · the stock future in the pre-open auction (the literal "pre-bidding" route)
- **Trades:** every v10 fade signal with entry = open, 2022-26 (`S1_v10_trades_2022_24.csv` and `S1_v10_trades.csv`, E1
  valid; 870 trades). Put signal → **sell** the future; call signal → **buy** it.
- **Price proxy:** the stock's own day-0 open (the cash pre-open price) to its day-0 close (eod2; NSE's cash close is the
  last-30-minute average, a stand-in for a 15:20 exit). The future's basis barely moves inside one day; futures opens
  are not in the local cache. Gross % = the signed open → close move; net = gross − 0.05 % (round-trip futures charges
  and slippage, fixed now).
- **Report:** N, win %, mean and median net %, date-clustered t, by side and by window (2022-24, 2025-26), and the
  part after 2025-12-08 (when a futures pre-open really existed). Also ₹ per lot (the move × the lot size × the open)
  to show the size of one futures lot against one option lot.
- This is a different instrument with no −20 % stop and much larger risk per lot; a pass would only open a new
  pre-registration, never a live switch.

## Reading rules (fixed now)
- A result counts as real only with t ≥ 2 and the same sign in both halves (test 1) or both windows (test 2).
- Test 1 is compared with B on the same filled trades: the question is whether a fair-price limit beats buying at
  09:16. Test 2 is compared with zero.
- Reported in full, including if nothing is left.

## Addendum 2026-10-21 (before any number): one wording fix
- "T + 1 day" for the previous-close IV means the actual calendar days from the previous session to expiry (a weekend
  counts its days), / 365. Nothing else changes.
