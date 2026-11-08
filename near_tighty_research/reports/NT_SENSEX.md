# Near Tighty on SENSEX: booked result (2026-11-08, history, descriptive)

The user, 2026-11-08: "SENSEX ... put compute for this", then "this is near tighty why the g1-f is here". So this is **Near Tighty
only**: the G1 downside opening-range put, traded only when the expiry is 1-3 sessions away. No G1-F filter is used. History
only (Oct 2024 → Oct 2026, in-sample, the 1-3 session cut was found on these trades). Script `scripts/nt_sensex_booked.py`;
data `data/nt_sensex_booked_trades.csv`, `results/nt_sensex_booked_summary.csv`. Same booking code as `nt_targets.py`:
minute closes, 50 % stop, 0.5 % exit slippage, charges, SENSEX lot fixed at 20 (the repo convention).

## Max up after entry, SENSEX NT (162 trades; no stop, no exit)
Reaches +100 % (doubles): **25 %** by the next 09:16, **44 %** by the next close (NIFTY NT: 26 % / 38 %).

## Booked result, SENSEX NT vs NIFTY NT (50 % stop kept)
| Set | Exit | Mean net | Median | Won | t | Total ₹ (1 lot) | Half 1 / Half 2 | Stop hit |
|---|---|---|---|---|---|---|---|---|
| **SENSEX NT** (162) | next 09:16, no target | **+15.2 %** | −16 % | 44 % | 2.29 | **+1,73,760** | +19.0 / +11.9 | 34 % |
| SENSEX NT | next close | +17.9 % | −51 % | 36 % | 1.98 | +2,02,183 | +28.3 / +8.9 | 56 % |
| NIFTY NT (160) | next 09:16, no target | +12.6 % | −21 % | 41 % | 1.73 | +1,07,740 | +6.0 / +19.4 | 42 % |
| NIFTY NT | next close | +5.7 % | −51 % | 29 % | 0.67 | −10,638 | +4.4 / +7.1 | 61 % |
| SENSEX 4-5 sessions (101) | next 09:16 | +5.4 % | | | 0.99 | +39,264 | | 17 % |

## Sell-at levels, SENSEX NT, next 09:16
| Level | Mean net | t | Total ₹ |
|---|---|---|---|
| 2x | +10.8 % | 2.14 | +1,09,446 |
| 3x | +12.3 % | 2.09 | +1,33,659 |
| no target | **+15.2 %** | 2.29 | **+1,73,760** |
Same lesson as NIFTY: a lower level gives money back (6 of 162 reached 3x and averaged +276 %).

## Reading
- SENSEX NT is positive on both halves and a little stronger than NIFTY NT (t 2.29 vs 1.73), and less dependent on a few trades:
  without its 5 best trades the mean is +7.8 % (NIFTY NT +3.1 %).
- By sessions to expiry (next 09:16): 1 session +2 %, 2 sessions +14 %, 3 sessions +28 %: the gain sits at 2-3 sessions, not 1.
- Next close books a little more than 09:16 on SENSEX (+17.9 % vs +15.2 %) but the opposite on NIFTY; the stop is hit on 56 % by then.
- The weekly SENSEX expiry is Tuesday-Thursday; the count uses NSE session days.

## Limits
Minute closes, not bid / ask. SENSEX has no lot table in the store (fixed 20; the real lot was 10 before Nov 2024), so the ₹ totals
are approximate; the % are not. Charges use NSE rates. In-sample: only a forward run can confirm it. **Nothing live trades SENSEX:**
Near Tighty on the server is NIFTY only.
