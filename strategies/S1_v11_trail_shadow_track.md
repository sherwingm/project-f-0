# S1 v11 fade · shadow tag "trail": the −20 % stop plus a trailing stop (start +10 %, gap 5 %) (tag only)

**Pre-registered 2026-10-21**, before any live trade carries the tag. The user's decision: "add a shadow tag on live fade
trades recording what a −20 % stop + trailing stop (start +10 %, gap 5 %) exit would have done; no change to the trades;
review at 30 closed trades." **The trades do not change.** Every fade trade is still bought and sold by v11.

## Why
`data/results/S1_fade_trail20_grid.md` (realistic entry, 409 trades): v11 + a trail starting at +10 % with a 5 % gap made
+3.4 % a trade (t 2.5, win rate 56 %) against v11's +2.5 % (t 0.9), but the gain over v11 on the test half was +2.0
points with t 0.8: the pre-registered test failed. A tag measures it on live prices.

## The tag (`rule.shadow_trail` on each fade position, from the first trade after deploy)
- Polls on the entry day from 09:16 to before 15:20, on the contract's **best bid** (as v11's stop):
  - **Start:** the first poll whose bid ≥ 1.10 × entry switches the trail on; the peak = the highest bid seen from
    that poll on.
  - **Exit:** once on, the first poll whose bid ≤ 0.95 × the peak sells (in the shadow) at that bid. Its net is
    computed with real charges on both orders.
  - Before the trail is on, the −20 % stop is v11's own: if v11 stops the trade, the shadow is **the same** as the
    real result. Once on, the trail level (≥ 1.045 × entry) is always above the stop, so the trail sells first.
  - Still on and not hit by 15:20, or never switched on: **the same** as v11's real exit.
- Statuses: `open` → `active` (trail on) → `done` (shadow sold, with fill, net, time) or `same`.

## Review at 30 closed tagged trades
- Report: real v11 vs the shadow (closed, wins, mean net % of premium, total ₹), the number of trail exits, and the
  date-clustered t of (shadow − real) per trade.
- "The trail would have helped" only if the shadow's total ₹ > the real total ₹ **and** the mean difference > 0.
  Then the user is asked whether to make it a rule (a new version, its own DECISIONS.md entry). Otherwise the tag is
  dropped. 30 trades is a small sample: a look, not proof.

## Differences from the backtest (known now)
The backtest used 1-minute candle highs and lows (trades); live uses the best bid at each poll (about every 30 s). A
5 % gap sits close to the bid–ask spread of cheap options, so live shadow fills can be worse than the backtest's.
