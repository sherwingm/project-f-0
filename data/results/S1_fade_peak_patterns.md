# S1 fade · how the up-moves reach their peak (1-minute candles), and whether an exit can catch more of it

Protocol: `strategies/S1_fade_peak_patterns.md` (learn on train Oct 2024 – Oct 2025, 284 trades; freeze; test once on
Nov 2025 – Aug 2026, 329 trades). Phase A/B by three analyst agents, a rule designer and a skeptic on a train-only copy
of the data; phase C: `data/results/S1_fade_peak_rules_test.md`. Entry = 09:16 open + 1 tick; real charges.

## What the up-moves look like (train)
1. **Two kinds of winner.**
   - Small winners (peak +10 – 40 %) are **quick spikes**: the peak comes a median 3.5 min after entry (live), and the
     peak candle alone makes about a quarter of the gain.
   - Big winners (peak ≥ +100 %) **climb like a staircase over hours**: median 220 min to the peak, 19 new-high candles
     on the way, 11 of 28 peak after 14:00.
2. **Big winners fall back deeply on the way up.** To stay in until the peak, a trail needs a gap of median 38 %
   (p90 65 %) from the high. About **half of them first touch the −20 % stop** (12 of 28 live).
3. **After the peak the price falls fast:** median 9 % below the peak within 1 minute, 16 % within 3, 20 % within 5.
   Selling at the next minute's open would still keep a median 87 % of the peak gain, if the top could be recognised.
4. **The top cannot be recognised from the candles:**
   - pullbacks before the peak are deeper than the first 15 minutes of the fall after it;
   - no volume climax at the peak (peak candle volume 1.49× the previous 10 vs 1.50× for other new highs, p 0.47);
   - "no new high for N minutes" means the peak is in only 50 – 70 % of the time, and by then the price is ~23 % below it;
   - early strength (first 5 – 15 minutes) predicts how big the peak will be, but not how much upside is still left.
5. **The stock's own top lines up with the option's** (within ±1 minute in 86 % of winners), but the stock pulls back
   on the way up as well, so stock signals fire early; none of ~73 stock-based exits beat v12 on train.
6. **v12 sells in the first 1 – 2 minutes after +10 %** (early 1-minute candles range ~6 %, so a 2 % dip comes at once),
   so it catches the quick spikes well and misses the slow staircases.

## Rules built from it (train) and the one test (test half)
| Rule | Idea | Train vs v12 | **Test vs v12** (live, 185) |
|---|---|---|---|
| R2 stall 20 (frozen pick) | sell after 20 min with no new high | +3.6 (one trade) | **−1.65 (FAIL)** |
| R1 range trail | gap = 3 × recent 1-min range | +0.5 | −0.99 |
| R3 half-profit floor | sell when half the open gain is given back | −0.3 | −2.32 |
| R4 half-profit + wick top | R3 + sell after a new-high candle closing ≥ 10 % below its high | +1.4 | −2.29 |
| R5 hold to close | stop only | +2.5 | −3.18 |

On the test half v12 made +3.20 % a trade (+₹48,845, win 56 %); every rule did worse. On the refused set v12 also led
(+3.69 %).

## Conclusion
The peaks are real but cannot be caught with the information available at the time: the big ones need room for deep
pullbacks (and often a −20 % dip) that also lets the many small spikes give back everything, and nothing in price,
volume, time or the stock marks the top as it happens. v12's quick 2 % trail is the best of everything tried. Nothing
live changes.
