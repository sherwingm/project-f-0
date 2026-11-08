# Which method gets a good result (2026-11-08; every number is in the file named beside it)

All history, in-sample, descriptive unless it says forward. Max up first, then the booked result. Full table:
`results/method_scoreboard.csv`.

## The short answer
1. **Only one family is positive: the downside opening-range put** (G1, G1-F, Near Tighty). Everything else we tried loses
   after costs or cannot be traded by a buy-only account.
2. **Best so far: G1-F** (G1 skipping day-1 gap ≥ +0.3 %, range width 0.5-0.8 %, VIX ≥ 17): +18.3 % a trade, t 2.73
   (154 trades, Oct 2024 → Oct 2026). Caution: those three filters were picked from the same trades, so this is flattered.
3. **None of it is proven.** G1, G1-F and Near Tighty each need 30 forward paper trades. As of 2026-11-08 the live server
   (checked) has booked **0 trades**: 5 and 6 Nov both broke upward, and all three trade only downside breakouts.

## Max up after entry (put reaches +100 % = doubles), history
| Method | Trades | To next 09:16 | To next close | Booked (sold next 09:16) |
|---|---|---|---|---|
| G1-F (live main) | 132 | **23 %** | **38 %** | **+18.3 %, t 2.73** |
| Near Tighty (G1, 1-3 sessions) | 160 | **26 %** | 38 % | +12.6 %, t 1.73 |
| G1 (all) | 226 | 20 % | 31 % | +8.4 %, t 1.72 |
| SENSEX G1-F put | 149 | 21 % | 43 % | not booked yet |
| NIFTY call mirror (up-breakout call) | 144 | 6 % | 19 % | weak (earlier B2 / PUT1 calls lost) |
| SENSEX call mirror | 132 | 11 % | 18 % | weak |
| N1 (breakout either way, expiry day / day before) | 208 | 25 % same day | n/a | **−24.0 %, t −4.63** |
| Buy every expiry day, no signal (NIFTY 09:20) | 7,455 | 30-53 % by expiry | n/a | calls −19 to −32 %, puts mixed |

## What does NOT work (each tried, each in its own file)
- **Buying by days to expiry alone** (NIFTY and stock options): +100 % is common but holding loses; "sell at +100 %" loses more.
- **A 09:20 feature that picks the winners:** 9 features, 108 cells, none significant (best t 1.26, carried by 3 rally days).
- **Expiry-day blasts:** the best option of the day doubles on ~80 % of days and goes 10x on ~1 in 7, but you only see the side
  afterwards; a fixed option doubles on 30-49 % and is still 2x at 15:15 on 5-23 %. Rupee test: sell-at-2x lost in 14 of 16 cells.
- **N1 (breakout either way on expiry day):** −24 %, 75 % stopped. Dead on history.
- **Add-ons to G1:** breakout score 0-7, holding-pattern search, IV-crush: none ranks the max up.
- **The independent expiry study (36,600 tests):** no direction edge; the size of the next move is predictable but already priced.
- **Option selling:** wins often but the worst day wipes out months (P7 −₹22,884); not allowed for a buy-only account.

## Sell-at levels (1.5x, 2x, 3x, 5x, 10x)
Tested on Near Tighty (`near_tighty_research/reports/NT_TARGETS.md`): **no target is best** (+12.6 %); 5x +12.0 %, 3x +7.9 %,
2x +4.9 %, 1.5x −3.8 %. A lower level cuts the few trades that run (8 of 160 reached 3x, avg +290 %). The 5 best trades earn more
than the whole total (without them +3.1 %).

## Which exit: next 09:16 or next close? (depends on the filter)
| Set | Sold next 09:16 | Sold next close | Stop hit at 09:16 / close |
|---|---|---|---|
| Near Tighty (160) | **+12.6 %**, +₹1.08 lakh | +5.7 %, −₹10.6k | 42 % / 61 % |
| G1 all (259) | +8.4 %, +₹1.23 lakh | +5.5 %, +₹0.40 lakh | 33 % / 52 % |
| G1-F (154) | +18.3 %, +₹2.09 lakh | +19.7 %, +₹2.47 lakh | 28 % / 42 % |
The close shows the higher peak, but more trades are stopped by then. For G1-F the two are about equal; for Near Tighty and
unfiltered G1 the 09:16 exit books more. (G1 / G1-F sell at the next close since 2026-11-06; Near Tighty at 09:16.)

## Still open (the search for the max)
1. **Forward results:** 30 trades each for G1, G1-F and Near Tighty (0 booked so far). The only real test.
2. **SENSEX put side:** max up as good as NIFTY's (43 % reach +100 % by the next close); booked result and a forward run not done.
3. **Upside blasts are not covered:** every live method is a put on a downside break; the call mirror is much weaker on max up.
4. **Whether the three G1-F filters hold up** on data they were not picked from (only the forward run can say).
5. **Exit choice per filter set** (table above): decide only on forward data, not on this history.
