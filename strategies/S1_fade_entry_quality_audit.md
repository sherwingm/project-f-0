# S1 fade · peak capture and entry-quality audit (exploratory, numbers only)

Written 23 Oct 2026, before running the analysis. Nothing live changes. The user's brief: measure the sellable peak while
held, how much the exit captured, and which entry conditions go with weak trades.

## Data and labels (fixed now)
- Trades: the 339 live-set trades of `data/results/S1_v12_exit_trades.csv` (fade signals Oct 2024 – Aug 2026; entry
  B = 09:16 candle open + 1 tick; premium ≥ ₹2; lot ₹600–8,000; v12 exit on 1-minute candles; real charges).
- **Peak basis on history: an OHLC PROXY.** The history has 1-minute option candles only, with no bid or ask. The
  while-held peak is the highest candle **high** from 09:17 through the v12 exit minute; the stricter version uses the
  highest candle **close**. Neither is a price a sell was known to fill at, so both are labelled "proxy". The live
  measurement (best bid, `server/peak.py`, from 23 Oct) is the one to trust.
- Peak-opportunity net = selling the trade's lot at the proxy peak, with the same `server/charges.py` legs.
  Capture % = v12 net / peak-opportunity net, only where the latter is > 0. Never clamped.
- Entry-time features (could drive a filter): entry premium; strike distance from the stock's **09:15 open** (a proxy
  for the stock at 09:16); sessions to expiry; the stock's opening gap; its 5- and 20-day run-up before the results; net
  profit YoY / QoQ and revenue YoY. These come from `S1_v10_fade_diag_features.csv`, values known at the time.
- Post-entry features (explain only, never a filter): the stock's day fade after the open; the option's first 1, 3
  and 5 minutes after entry (candle highs and lows: proxy).
- **Not testable on history:** spread and liquidity at entry or exit (no bid/ask history). They are collected live
  from 23 Oct (`entry_quote`, `data/observations/`).

## Groups (exploratory boundaries, fixed now)
- Premium: < ₹3, ₹3–5, ₹5–7, ₹7–10, ₹10–15, ≥ ₹15.
- Strike distance (out of the money, % of the stock): < 1, 1–2, 2–3, 3–5, ≥ 5 (in the money is its own group).
- Sessions to expiry: ≤ 3, 4–7, 8–14, ≥ 15.
- Opening gap in the headline direction (a strong-numbers put: the gap up; a weak-numbers call: the gap down, sign
  flipped): < 0, 0–2 %, 2–5 %, ≥ 5 %.
- Net profit YoY: quartiles within each side.

Per group: n, wins and win %, mean and median v12 net %, total ₹, mean MFE / MAE (proxy), mean capture % where defined,
mean peak-opportunity ₹ against realised ₹, train (before 2025-11-03) and test means, and a date-clustered t.

## Reading rules
- Exploratory only. No threshold is chosen from this. A group with fewer than 20 trades is shown but called
  inconclusive.
- The train/test split influenced earlier exit choices, so the test half is not pristine.
- Correlations between premium, strike distance, days to expiry and gap are reported, so one effect is not counted
  twice.
- Each finding is labelled: observed in the data / plausible, needs a test / cannot be tested yet.
