# Near Tighty: which sell-at level (1.5x, 2x, 3x, 5x, 10x) books the best result (2026-11-07, history, descriptive)

The user, 2026-11-07: "show me the 2x, 3x etc which makes the good returns". History only (G1's trades, Oct 2024 → Oct 2026,
found after looking at G1), minute closes, in-sample. Script `scripts/nt_targets.py`, data `data/nt_target_trades.csv`,
`results/nt_target_summary.csv`. NT = 1-3 sessions to expiry (160 trades with a next session). G1's 50 % stop is kept in every row;
a target is a resting sell at target × the price paid. Slippage 0.5 % on the exit, charges from `server/charges.py`, 1 lot.

## Max up after entry, NT (the measure; no stop, no exit)
| Followed until | Mean | Median | ≥ 1.5x | ≥ 2x | ≥ 3x | ≥ 5x | ≥ 10x |
|---|---|---|---|---|---|---|---|
| End of day 1 | +49 % | +31 % | 34 % | 19 % | 2 % | 0 % | 0 % |
| Next 09:16 (what NT sells at) | +64 % | +35 % | 42 % | 26 % (41) | 5 % (8) | 1 % (1) | 0 % |
| Next close (what G1 sells at) | +103 % | +57 % | 52 % | 38 % (61) | 17 % (27) | 4 % (6) | 0 % |

## Booked result by sell-at level, NT, sold at the next 09:16 (today's NT exit)
| Level | Mean net | Median | Won | t | Total ₹ | Half 1 / Half 2 | Target reached | Stop hit |
|---|---|---|---|---|---|---|---|---|
| 1.5x | −3.8 % | −7 % | 48 % | −1.01 | −65,563 | −1.2 / −6.5 | 39 % | 39 % |
| 2x | +4.9 % | −18 % | 42 % | 0.96 | +19,499 | +3.6 / +6.2 | 25 % | 41 % |
| 3x | +7.9 % | −21 % | 41 % | 1.31 | +43,915 | +2.2 / +13.9 | 5 % | 42 % |
| 5x | +12.0 % | −21 % | 41 % | 1.70 | +97,592 | +4.9 / +19.4 | 1 % | 42 % |
| 10x / none | **+12.6 %** | −21 % | 41 % | 1.73 | **+107,740** | +6.0 / +19.4 | 0 % | 42 % |

## Reading
- **No target is best** (5x and 10x are the same trades: almost none reach them). Every lower level gives money back:
  2x −8 points, 3x −5 points, 1.5x is negative. The few trades that run pay for the rest: 8 of 160 reached 3x and
  averaged +290 %.
- **It rests on a few trades.** The 5 best trades made ₹1.50 lakh of the ₹1.08 lakh total; without them the mean is +3.1 %.
  t 1.73 is not significant, both halves are positive.
- **Next 09:16 beats the next close** on booked results. NT: +12.6 % (+₹1.08 lakh) at 09:16 vs +5.7 % (−₹10.6k) at the
  next close, because the stop is hit on 61 % by then (42 % by 09:16). All 259 G1 trades: +8.8 % vs +5.8 % (stop 33 % vs 52 %).
  The next close shows the higher peak (see above), but the stop takes the trade first. G1 / G1-F sell at the next close since 2026-11-06.
- 4-5 sessions (not NT) at 09:16: no target +2.6 %, 2x +4.0 %, t ≤ 0.8: nothing there either way.

## Limits
Minute closes, not bid / ask: a stop or target inside a minute is not seen, and the fill is assumed at the level. In-sample
(the 1-3 session cut was found on these trades). The forward paper run is the test.
