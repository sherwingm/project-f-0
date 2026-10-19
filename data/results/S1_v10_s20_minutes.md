# S1 v10 fade · the -20 % stop on 1-minute prices: what the option did after the stop fired

Descriptive. 468 v10 Rs 2+ trades with day-0 minute candles, Oct 2024 - Sep 2026 (Upstox's minute history starts Oct 2024). Entry = day-0 open + 1 tick (the backtest's); stop 0.80 x entry, fired in the first minute whose low <= the stop. Peaks are the highest minute high after the stop's minute, to 15:19, as % of entry.

## After the stop fired

| stopped trades, after the stop fired | value |
|---|---|
| stopped trades | 338 |
| of all | 338 / 468 (72 %) |
| median peak after stop | +3.1 % |
| back to entry (>= 0 %) | 55.6 % |
| >= +20 % | 36.7 % |
| >= +50 % | 22.2 % |
| >= +100 % | 10.1 % |
| closed (15:19) above entry | 22.8 % |
| median 15:19 close | -31.3 % |

## Peak after the stop, distribution

| peak after the stop (vs entry) | trades |
|---|---|
| < -50 % | 11 |
| -50..-20 % | 43 |
| -20..0 % | 99 |
| 0..+20 % | 61 |
| +20..+50 % | 49 |
| +50..+100 % | 42 |
| >= +100 % | 33 |

## When the stop fired

| minute | trades |
|---|---|
| 09:15 | 140 |
| 09:16-09:30 | 110 |
| 09:31-11:00 | 59 |
| 11:01-15:19 | 29 |

## Money: the stop with a real fill vs the 15:20 exit

| exit | total_rs | wins | t |
|---|---|---|---|
| 15:20 (backtest e1_net) | 170405 | 189 | 1.711 |
| -20 % stop on minutes, real fill | 216629 | 115 | 2.373 |
|   of which the stopped trades: 15:20 | -524424 | 74 |  |
|   of which the stopped trades: stop | -478200 | 0 |  |


The stop's fill = min(stop, that minute's open) - 1 tick: a market sell, not the stop level (the daily-data study filled at the level). Trades: data/results/S1_v10_s20_minutes_trades.csv.

## Check: the stop not active in the 09:15 minute (the live bot buys a minute or two after the open)

Computed by hand the same day (2026-10-20), from the same files, with the 09:15 minute's low ignored:

| | stop fired | -20 % stop total | 15:20 total | t (stop) | t (15:20) |
|---|---|---|---|---|---|
| all 468 trades | 316 | **+Rs 2,50,916** | +Rs 1,70,405 | 2.47 | 1.71 |
| Oct-Nov 2024 | | +Rs 31,035 | +Rs 28,565 | | |
| 2025 | | +Rs 92,942 | +Rs 61,891 | | |
| 2026 (to Sep) | | +Rs 1,26,939 | +Rs 79,949 | | |

Descriptive and not pre-registered: a question asked after the daily-data study, on data that study did not have.
It disagrees with the daily study ("no real gain"), which filled stops at the level and could not see the order of
the day's high and low. Any rule change needs its own pre-registration and the user's agreement.
