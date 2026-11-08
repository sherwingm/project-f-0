# Near Tighty, 2025-10-01 → present (history ends 2026-10-28; 2026-11-08, descriptive)

The user, 2026-11-08: "get the result between the year of 2025 oct to present". A re-cut of the booked Near Tighty trades
(G1's downside opening-range put, 1-3 sessions to expiry); no new simulation. Script `scripts/nt_oct2025_on.py`, file
`results/nt_oct2025_on.csv`. 50 % stop, 0.5 % exit slippage, charges, 1 lot. **Not independent:** the 1-3 session cut was found on
the whole history, this period included; only the live forward run is a real test.

## Max up after entry (no stop, no exit): share of puts reaching each level
| Index | Trades | Followed until | Mean | Median | ≥ +50 % | ≥ +100 % | ≥ +200 % |
|---|---|---|---|---|---|---|---|
| NIFTY | 78 | next 09:16 | +68 % | +35 % | 42 % | **29 %** | 8 % |
| NIFTY | 78 | next close | +111 % | +53 % | 51 % | **40 %** | 21 % |
| SENSEX | 87 | next 09:16 | +67 % | +40 % | 48 % | **26 %** | 3 % |
| SENSEX | 87 | next close | +110 % | +79 % | 61 % | **45 %** | 13 % |

## Booked result, sold at the next 09:16 (Near Tighty's exit), 50 % stop
| Index | Level | Trades | Mean net | Median | Won | t | Total ₹ | Positive months | Without top 5 |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY | **no target** | 78 | **+19.4 %** | −32 % | 44 % | 1.71 | **+77,814** | 8 of 13 | +3.6 % |
| NIFTY | 3x | 78 | +13.9 % | −32 % | 44 % | 1.42 | +46,770 | 8 of 13 | +3.5 % |
| NIFTY | 2x | 78 | +6.2 % | −24 % | 45 % | 0.81 | +11,858 | 9 of 13 | −0.1 % |
| SENSEX | **no target** | 87 | **+11.9 %** | −21 % | 43 % | 1.30 | **+82,096** | 8 of 13 | −0.8 % |
| SENSEX | 3x | 87 | +8.7 % | −21 % | 43 % | 1.08 | +58,551 | 8 of 13 | −0.6 % |
| SENSEX | 2x | 87 | +11.1 % | −14 % | 47 % | 1.58 | +66,086 | 8 of 13 | +5.9 % |

Sold at the next close instead: NIFTY +7.1 % (t 0.57, +₹12,417, stop hit 59 %), SENSEX +8.9 % (t 0.80, +₹58,136, stop hit 55 %).

## This period against the earlier one (sold next 09:16, no target)
| Index | Before 2025-10 | 2025-10 → now | Whole history |
|---|---|---|---|
| NIFTY | +6.0 % (82 trades, t 0.66) | **+19.4 %** (78, t 1.71) | +12.6 % (160, t 1.73) |
| SENSEX | +19.0 % (75, t 1.97) | +11.9 % (87, t 1.30) | +15.2 % (162, t 2.29) |

## Reading
- Both indices are positive in this period on the no-target 09:16 exit, but neither is significant (t 1.71 and 1.30).
- NIFTY improved (+6.0 % → +19.4 %) and SENSEX weakened (+19.0 % → +11.9 %): the two alternate, so the combined picture is steady
  at about +12 to +15 %, not a trend.
- It rests on a few big trades: without the 5 best, NIFTY is +3.6 % and SENSEX −0.8 %.
- The median trade loses (−21 % to −32 %); 31-45 % of trades are stopped.
- Lower sell-at levels (2x, 3x) book less than no target on NIFTY; on SENSEX 2x is close (+11.1 %) with a better median, but
  that is one period of 87 trades.
- No live trade yet: the server's Near Tighty ledger had 0 trades (5 and 6 Nov were upward breakouts; checked 2026-11-08).
