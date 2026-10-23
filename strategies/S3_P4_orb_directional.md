# S3 P4 · NIFTY opening-range breakout, long ATM option with a trailing stop

Pre-registered 2026-10-23, before any P4 run. Rules: DECISIONS.md "S3 · index options". Engine: `scanner/s3_engine.py`.
Source: the user's research note, Section 4 pod "Directional": long calls or puts on an opening-range breakout, active
when VIX < 14 and the trend state agrees, trailing stop, no sell-side STT until the exit.

**Counts before the run** (spot and VIX only, no option returns; test window, 247 sessions):
- 15-minute opening range: 245 breakout days; the trend agrees on 122; VIX < 14 on 117; **both on 60**.
- 30-minute opening range: 231, 108, 110, **both 47**.

So the research's filters stay in the primary cell.

## Trade (primary cell)
- **Opening range:** NIFTY spot high and low over 09:15-09:29 (15 minutes).
- **Signal:** the first 1-minute spot close above the range high (→ call) or below the range low (→ put), 09:30-13:00.
  Only the first breakout of the day counts; there is no second trade.
- **Filters:**
  - **trend:** call only if the previous close is above its 20-day EMA, put only if below (daily bars from the
    1-minute spot, up to the previous close);
  - **VIX:** below 14 at the signal minute.

  If either fails, there is no trade that day. Event days are traded (long premium) and reported on the side.
- **Entry:** the minute after the signal minute. Buy 1 lot of the ATM option (the strike nearest the spot at that
  minute) of the nearest weekly expiry with at least one session left after the trade day (on an expiry day, the
  next expiry).
- **Exit**, the first of:
  - stop: value ≤ 75 % of the premium paid (−25 %);
  - trailing stop: once in profit, value ≤ 75 % of the highest value since entry (25 % below the peak);
  - time: 15:15.

  Marks are each minute's last traded close.
- **Fills and costs:** engine defaults (the minute close, 0.5 % slippage; 1 % before 09:30 or from 15:00) plus
  `server/charges.py`.
- **Measure:** net % of the premium paid and net ₹.

## Grid (reported in full; the gate is judged on the primary cell)
- Opening range: 15 · 30 minutes.
- Trail: 20 · 25 · 30 %.
- Initial stop: 20 · 25 · 30 % · none.

All cells use both filters. Side reports for the primary: no filters, trend only, VIX only; and calls vs puts.

## Gate (test window 2024-10-01 → 2025-09-30), all of
- Net mean per trade > 0, and still > 0 at 2× costs.
- t ≥ 2.
- Positive in each half.
- The worst trade is smaller (in ₹) than the average month's net profit.
- The neighbours (trail 20 % and 30 %, stop 20 % and 30 %; the rest as the primary) each net positive.
- At least 30 trades.

**Holdout 2025-10-01 → latest**, once, only if the gate passes and after an independent review. It passes if the net
mean is > 0 and the Sharpe is within 30 % of the test window's.
