# S1 Arm A and Arm B · HYP-A-02 (minute candles)

Numbers only. Pre-registered: strategies/S1_armab_gemini_hypotheses.md. Arm A and Arm B separate.

## HYP-A-02 · the live 2-session expiry rule (current monthly down to 2 sessions) against the tested 10-session rule (next monthly), same signals, 09:16 entry

### Arm A: 112 near-expiry picks, 98 with minute candles and a 09:16 trade (dropped: {'no_0916_candle': np.int64(7), 'no_data': np.int64(6), 'no candles': np.int64(1)}); 23 paired with the baseline's trade for the same signal, 75 have no baseline trade

| rule | n | win % | mean % | median % | total Rs | PF | max DD Rs |
|---|---|---|---|---|---|---|---|
| baseline (next monthly, >= 10 sessions) | 23 | 17.4 | -12.2 | -55.8 | -25228 | 0.65 | -44846 |
| variant (current monthly, >= 2 sessions) | 23 | 4.3 | -58 | -64.5 | -94359 | 0.05 | -97703 |


Paired difference (variant minus baseline):

| pairs | mean diff % | t | p | half 1 diff | n1 | half 2 diff | n2 |
|---|---|---|---|---|---|---|---|
| 23 | -45.74 | -1.58 | 0.114 | 9.43 | 8 | -75.16 | 15 |


Exit mix baseline {'0_stop': np.int64(15), '1_decay': np.int64(8)}; variant {'0_stop': np.int64(15), '2_t_minus_1': np.int64(8)}; mean sessions held baseline 5.5, variant 1.7; mean sessions to expiry at day 0 4.8.

Picks the baseline did not trade (descriptive only, no pair): n 75, win 13 %, mean -11.9 %, median -63.7 %, total Rs -150,975.

### Arm B: 42 near-expiry picks, 37 with minute candles and a 09:16 trade (dropped: {'no_0916_candle': np.int64(3), 'no_data': np.int64(2)}); 9 paired with the baseline's trade for the same signal, 28 have no baseline trade

| rule | n | win % | mean % | median % | total Rs | PF | max DD Rs |
|---|---|---|---|---|---|---|---|
| baseline (next monthly, >= 10 sessions) | 9 | 22.2 | -1.8 | -52.5 | -6077 | 0.75 | -18990 |
| variant (current monthly, >= 2 sessions) | 9 | 0 | -62.7 | -60.5 | -32530 | 0 | -29046 |


Paired difference (variant minus baseline):

| pairs | mean diff % | t | p | half 1 diff | n1 | half 2 diff | n2 |
|---|---|---|---|---|---|---|---|
| 9 | -60.98 | -1.15 | 0.248 | -13.16 | 2 | -74.64 | 7 |


Exit mix baseline {'0_stop': np.int64(5), '1_decay': np.int64(4)}; variant {'0_stop': np.int64(6), '2_t_minus_1': np.int64(3)}; mean sessions held baseline 6.6, variant 1.2; mean sessions to expiry at day 0 4.3.

Picks the baseline did not trade (descriptive only, no pair): n 28, win 14 %, mean -10.1 %, median -64.6 %, total Rs -68,878.
