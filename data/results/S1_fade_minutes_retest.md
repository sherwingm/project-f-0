# S1 fade · the live rule on every contract with 1-minute candles

Numbers only. Entry 09:16 open + 1 tick, price >= Rs 2, lot Rs 600-8,000, candles to 15:19. 707 contracts with a 09:16 candle, 339 pass the live rule. Max up / dip are candle high / low as % of the entry.

| exit | period | n | win % | mean % | median % | total Rs | t | mean ex top3 % | max up mean/median % | max dip mean/median % |
|---|---|---|---|---|---|---|---|---|---|---|
| v12 (live) | all | 339 | 55.2 | 2.86 | 5.8 | 68160 | 1.79 | 1.75 | 76 / 44 | -39 / -40 |
| v12 (live) | Oct24-Oct25 | 154 | 53.9 | 2.46 | 4.9 | 19315 | 0.97 | 0.53 | 87 / 40 | -41 / -41 |
| v12 (live) | Nov25-Sep26 | 185 | 56.2 | 3.2 | 6.3 | 48845 | 1.57 | 1.22 | 68 / 47 | -38 / -37 |
| v12 (live) | all, PE only | 243 | 54.7 | 2.51 | 5.7 | 48519 | 1.29 | 0.96 | 79 / 40 | -40 / -41 |
| v12 (live) | all, CE only | 96 | 56.2 | 3.74 | 6.8 | 19641 | 1.39 | 1.42 | 70 / 46 | -37 / -35 |
| v10 (hold to 15:19) | all | 339 | 38.6 | 3.88 | -18.9 | 69018 | 0.78 | -1.27 | 76 / 44 | -39 / -40 |
| v10 (hold to 15:19) | Oct24-Oct25 | 154 | 39 | 10.51 | -22.4 | 71004 | 1.15 | -0.72 | 87 / 40 | -41 / -41 |
| v10 (hold to 15:19) | Nov25-Sep26 | 185 | 38.4 | -1.63 | -17.9 | -1986 | -0.33 | -6.18 | 68 / 47 | -38 / -37 |
| v10 (hold to 15:19) | all, PE only | 243 | 38.7 | 5.47 | -18.9 | 88727 | 0.89 | -0.69 | 79 / 40 | -40 / -41 |
| v10 (hold to 15:19) | all, CE only | 96 | 38.5 | -0.12 | -20.4 | -19709 | -0.01 | -11.6 | 70 / 46 | -37 / -35 |

