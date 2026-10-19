# S1 v10 fade · a separate rule for options priced ₹0.50–1: +20 % target with a trailing stop (minute data)

**Pre-registered 2026-10-19**, before any minute candle is fetched and before any number is computed. The user's
idea, in order: a separate rule for the ₹0.50–1 band first, and if it works, the same rule for ₹1–2. Their choices:
"+20% target, trail before it", trailing levels "10/20/30%", "check minute history first", the "strike priced
₹0.50–1" sample, and "1" (minute data only, choose on 2025, test once on 2026). Descriptive. **The live v10 rule
(₹2 floor, 15:20 exit) is not changed**; any change needs the user's agreement and goes into DECISIONS.md.

## Why
The sub-₹2 study (`strategies/S1_v10_subfloor_entry.md`) found that v10's sub-₹2 trades lose money under realistic
tick costs (−₹52,517 on 140 trades). The ₹0.50–1 band lost −₹38k on 35 trades. A +50 % target made the sub-₹2 set
worse. This tests whether a quick profit-take with a trailing stop wins in that band, using minute prices so the
order of highs and lows is real.

## Trades
- Every S1 v10 fade signal with day 0 in **2025-01-01 → 2026-09-25**: the signal list, side, expiry and previous close
  from `S1_v10_trades_floor0p05.csv`. That run's walk reaches every signal except those with no strike or expiry.
- The option: from v10's start strike (the strike nearest the previous close; a tie: the higher for puts, the lower
  for calls), walk away from the money. Take the first strike with **day-0 open + 1 tick in [₹0.50, ₹1.00)**, ≥ 50
  contracts on day 0, and one lot at that price within ₹600–8,000 (day-0 option file). None: no trade, counted.
- One lot.

## Minute data
- Upstox expired-instruments 1-minute candles of that contract on day 0 (`index_data/fetch_band_minutes.py`, run on
  GitHub, where the token is). It covers stock options from the Oct 2024 expiries
  (`index_data/probe_stock_expired.py`, 2026-10-19). A contract without candles is excluded and counted.

## Prices and costs (tick-based, as the sub-₹2 study)
- **Entry:** the close of the 09:15 minute + 2 ticks (₹0.10), standing for the ask + 1 tick, bought in the first
  minute. If the 09:15 minute is missing, the first minute up to 09:20; none, excluded.
- **Target:** entry × 1.20, rounded up to the tick. It fills at the target in the first minute after entry whose
  high ≥ target + 1 tick.
- **Trailing stop:** the peak is the highest minute high since entry, the entry counting as the first peak. The stop
  is peak × (1 − trail), checked against the minute's low **before** the minute's high updates the peak. It fills at
  the stop − 2 ticks (a market sell into the bid), not below ₹0.05 and not above that minute's open (a gap down fills
  at the open − 2 ticks).
- **Both in one minute:** if a minute touches both the stop and the target, the stop is taken (worst case).
- **Else** the close of the 15:19 minute − 2 ticks (the 15:20 sale), not below 0.
- Charges: `server/charges.py` on both orders (₹20 brokerage an order, STT, exchange, SEBI, stamp, GST).

## Variants (fixed now)
- **Baseline:** no target, no stop, the 15:20 sale.
- **R10, R20, R30:** +20 % target with a 10 %, 20 % or 30 % trailing stop.

## Choose, then test once (fixed now)
- **Choose on 2025** (day 0 2025-01-01 → 2025-12-31): of R10 / R20 / R30, the one with the highest **total net ₹**.
  A tie goes to the wider trail.
- **Test on 2026** (day 0 2026-01-01 → 2026-09-25): the chosen rule only, run once. The other two are shown for
  information only.
- **Pass (the rule wins in ₹0.50–1):** on 2026, the chosen rule's total net ₹ > 0, **and** its mean net % per trade
  > 0 with a date-clustered t ≥ 2, **and** it beats the baseline's total net ₹ on 2026.
- If it passes, the same rule, with no new choice, is tested next on the ₹1–2 band under its own pre-registration.
  If it fails, the ₹1–2 step is not run on this rule.

## Report
Per window (2025 choose, 2026 test) and variant: N, win rate, mean and median net % per trade, total net ₹, max
drawdown, date-clustered t, and exit-reason shares (target / stop / 15:20). Also the funnel: signals; with a ₹0.50–1
strike; lot in band; minute candles found.

## Known limits
- About 75 trades a window. t ≥ 2 on ~75 trades needs a large edge, so a fail is the likely outcome even if the rule
  helps a little.
- At ₹0.50–1 one tick is 5–10 % of the price. A 10 % trailing stop is about one to two ticks, so it is mostly a
  test of noise.
- Minute candles show trades, not quotes. The ±2 ticks stand in for the spread.
- Choosing the strike uses the day's opening price, which is known at 09:15. Entry is the 09:15 minute's close.
- Not out of sample in the strict sense: the 2025-26 fade trades were seen pooled in earlier studies (not split this
  way, and not with minute prices).
