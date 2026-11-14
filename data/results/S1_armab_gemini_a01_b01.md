# S1 Arm A and Arm B · Gemini-handoff hypotheses (minute candles)

Numbers only. Pre-registered: strategies/S1_armab_gemini_hypotheses.md. Arm A and Arm B separate. Holm over the three hypotheses is applied when all three are in (see the end).

## HYP-A-01 · entry at the 15:20 average price (day +1) instead of the 09:16 open

### Arm A: 138 paired trades (dropped 2: {'outside price/lot band': np.int64(2)})

Baseline reproduced exactly on 138 of 138 trades.

| rule | n | win % | mean % | median % | total Rs | PF | max DD Rs |
|---|---|---|---|---|---|---|---|
| baseline (09:16 entry, 50 % option stop) | 138 | 10.1 | -24.1 | -58.5 | -254108 | 0.52 | -259113 |
| variant | 138 | 12.3 | -18.1 | -58.5 | -180502 | 0.63 | -227074 |


Paired difference (variant minus baseline):

| pairs | mean diff % | t | p | half 1 diff | n1 | half 2 diff | n2 |
|---|---|---|---|---|---|---|---|
| 138 | 6.04 | 1.7 | 0.089 | -3.11 | 43 | 10.19 | 95 |


Exit mix baseline {'0_stop': np.int64(98), '1_decay': np.int64(34), '2_t_minus_1': np.int64(6)}; variant {'0_stop': np.int64(98), '1_decay': np.int64(35), '2_t_minus_1': np.int64(5)}; mean sessions held baseline 4.5, variant 4.9.

### Arm B: 55 paired trades (dropped 0: {})

Baseline reproduced exactly on 55 of 55 trades.

| rule | n | win % | mean % | median % | total Rs | PF | max DD Rs |
|---|---|---|---|---|---|---|---|
| baseline (09:16 entry, 50 % option stop) | 55 | 12.7 | -19.1 | -55.4 | -61305 | 0.66 | -83557 |
| variant | 55 | 16.4 | -11 | -57 | -43451 | 0.76 | -70239 |


Paired difference (variant minus baseline):

| pairs | mean diff % | t | p | half 1 diff | n1 | half 2 diff | n2 |
|---|---|---|---|---|---|---|---|
| 55 | 8.03 | 1.46 | 0.144 | 2.84 | 11 | 9.33 | 44 |


Exit mix baseline {'0_stop': np.int64(33), '1_decay': np.int64(18), '2_t_minus_1': np.int64(4)}; variant {'0_stop': np.int64(36), '1_decay': np.int64(16), '2_t_minus_1': np.int64(3)}; mean sessions held baseline 5.1, variant 5.4.

## HYP-B-01 · underlying-stock stop (close below the day-0 low) instead of the 50 % option stop

### Arm A: 140 paired trades (dropped 0: {})

Baseline reproduced exactly on 140 of 140 trades.

| rule | n | win % | mean % | median % | total Rs | PF | max DD Rs |
|---|---|---|---|---|---|---|---|
| baseline (09:16 entry, 50 % option stop) | 140 | 10 | -24.4 | -58.5 | -262840 | 0.51 | -267845 |
| variant | 140 | 11.4 | -22.6 | -60 | -256299 | 0.54 | -249446 |


Paired difference (variant minus baseline):

| pairs | mean diff % | t | p | half 1 diff | n1 | half 2 diff | n2 |
|---|---|---|---|---|---|---|---|
| 140 | 1.74 | 0.45 | 0.654 | 5.62 | 44 | -0.05 | 96 |


Exit mix baseline {'0_stop': np.int64(99), '1_decay': np.int64(35), '2_t_minus_1': np.int64(6)}; variant {'1_decay': np.int64(89), '0_ustop': np.int64(43), '2_t_minus_1': np.int64(8)}; mean sessions held baseline 4.5, variant 5.1.

On the baseline's 99 stopped trades alone: baseline mean -63.7 %, variant mean -59.8 %, paired difference +3.9 points.

### Arm B: 55 paired trades (dropped 0: {})

Baseline reproduced exactly on 55 of 55 trades.

| rule | n | win % | mean % | median % | total Rs | PF | max DD Rs |
|---|---|---|---|---|---|---|---|
| baseline (09:16 entry, 50 % option stop) | 55 | 12.7 | -19.1 | -55.4 | -61305 | 0.66 | -83557 |
| variant | 55 | 14.5 | -14.3 | -56.8 | -49801 | 0.75 | -97771 |


Paired difference (variant minus baseline):

| pairs | mean diff % | t | p | half 1 diff | n1 | half 2 diff | n2 |
|---|---|---|---|---|---|---|---|
| 55 | 4.74 | 0.48 | 0.628 | 38.3 | 11 | -3.64 | 44 |


Exit mix baseline {'0_stop': np.int64(33), '1_decay': np.int64(18), '2_t_minus_1': np.int64(4)}; variant {'1_decay': np.int64(37), '0_ustop': np.int64(14), '2_t_minus_1': np.int64(4)}; mean sessions held baseline 5.1, variant 5.8.

On the baseline's 33 stopped trades alone: baseline mean -62.5 %, variant mean -50.1 %, paired difference +12.3 points.
