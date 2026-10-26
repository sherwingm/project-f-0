# S3 R1 · SENSEX replication of the late-expiry premium: summary

Mean effect (R1a 5 lots net > 0 with t >= 2, and R1b < 0): **DOES NOT REPLICATE**.

| Cell | Trades | Net % | t | Win rate | Gate |
|---|---|---|---|---|---|
| R1a_1lot | 50 | -6.5 % | -0.52 | 56 % | FAIL |
| R1a_5lots | 50 | -2.7 % | -0.22 | 56 % | FAIL |
| R1b | 49 | -20.6 % | -1.69 | 24 % | FAIL |
| R1c | 49 | -8.7 % | -0.66 | 53 % | FAIL |
| R1d_1lot | 187 | -1.5 % | -3.74 | 32 % | FAIL |
| R1d_5lots | 187 | -1.0 % | -2.49 | 34 % | FAIL |

## Overlap with NIFTY expiry days

- R1a_1lot: 2 days are also NIFTY expiries (2024-10-31, 2024-11-14); without them 48 trades, -7.8 % (t -0.60).
- R1a_5lots: 2 days are also NIFTY expiries (2024-10-31, 2024-11-14); without them 48 trades, -4.0 % (t -0.31).
- R1b: 2 days are also NIFTY expiries (2024-10-31, 2024-11-14); without them 47 trades, -19.6 % (t -1.55).
- R1c: 2 days are also NIFTY expiries (2024-10-31, 2024-11-14); without them 47 trades, -10.0 % (t -0.73).

## Placebo: the same short straddle on non-expiry days, by sessions left to the expiry

| Cell | Sessions to expiry | Trades | Net % of credit | t |
|---|---|---|---|---|
| R1d_1lot | all | 187 | -1.5 % | -3.74 |
| R1d_1lot | 0 | 1 | -1.2 % | nan |
| R1d_1lot | 1 | 50 | +0.9 % | 1.05 |
| R1d_1lot | 2 | 47 | -2.5 % | -2.51 |
| R1d_1lot | 3+ | 89 | -2.4 % | -5.73 |
| R1d_5lots | all | 187 | -1.0 % | -2.49 |
| R1d_5lots | 0 | 1 | -0.4 % | nan |
| R1d_5lots | 1 | 50 | +1.6 % | 1.86 |
| R1d_5lots | 2 | 47 | -2.0 % | -1.99 |
| R1d_5lots | 3+ | 89 | -2.0 % | -4.81 |
