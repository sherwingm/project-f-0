# Near Tighty: max up after entry (history, Oct 2024 → Oct 2026)

Descriptive only. No stop, no target, no exit rule: the put is followed after the entry.
Entry = G1's fill (09:32 – 13:00 on a downside breakout). Max up = highest later minute close vs the price paid.
NT = 1-3 sessions to expiry: 161 trades (160 with a next session). Not NT = 4-5 sessions: 98.

## Share of trades whose put reached each level, NT (1-3 sessions)
| Followed until | n | Mean | Median | ≥ +50 % | ≥ +100 % | ≥ +200 % |
|---|---|---|---|---|---|---|
| End of day 1 (15:29) | 161 | +49 % | +31 % | 34 % | 19 % (31) | 2 % |
| Next session 09:16 (the NT hold) | 160 | +64 % | +35 % | 42 % | 26 % (41) | 5 % |
| Next session close | 160 | +103 % | +57 % | 52 % | 38 % (61) | 17 % |
| Expiry day close | 160 | +137 % | +87 % | 60 % | 48 % (76) | 29 % |

## By days to expiry (≥ +100 %)
| Days to expiry | Day 1 | To next 09:16 | To next close | To expiry |
|---|---|---|---|---|
| 1 | 21 % | 32 % | 46 % | 46 % |
| 2 | 19 % | 24 % | 33 % | 43 % |
| 3 | 17 % | 21 % | 35 % | 54 % |
| 4 (not NT) | 11 % | 13 % | 28 % | 62 % |
| 5 (not NT) | 2 % | 11 % | 20 % | 49 % |

## Reading
- Near expiry the put doubles more often early: within the NT hold (to the next 09:16), 26 % of NT trades reached +100 %
  against 12 % for 4-5 sessions. By the next day's close the gap narrows (38 % vs 24 %). Held to expiry the 4-5 session
  puts catch up (56 %) because they have more time.
- 1 session out is the best early (32 % to the next 09:16, +100 %); the share to the next 09:16 falls as days to expiry rise.
- Both halves agree (≥ +100 % to next 09:16: 22 % then 29 %; to expiry: 45 % then 50 %).
- The G1 stop (50 %) and the next-open exit cut these peaks: G1's booked mean over these trades was +12 %, while the
  puts reached much higher peaks. That is not an exit rule; it only shows the peak is not taken by that exit.

## Limits
- Minute closes, not best bid / ask; peaks inside a minute are not counted. Entry fills carry the engine's slippage.
- History only (in-sample, from G1's own trades, found after looking at G1). The test is the forward paper run.
- Windows that extend past the next session use no exit, so they say nothing about what is bookable.
