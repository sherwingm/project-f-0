# Which comes first for a market-hours result: NSE, BSE, the news or the stock? (2026-10-06 to 2026-10-19)

Descriptive. NSE and BSE times are the exchanges' own publish times (to the second). News = the earliest Google News item that day about the company's results; a rough guide, since Google's time is when it listed the story. 'Moved 1 %' = the first minute (from 30 min before the first filing) whose close is 1 % or more from the price 31 minutes before. 'Volume jump' = the first minute with 5x the hour's median volume. Company websites have no time stamps, so they cannot be compared.

## Summary

| what | value |
|---|---|
| F&O results first filed in market hours | 15 |
| with a BSE time matched | 12 |
| BSE first | 2 |
| NSE first | 10 |
| same minute or less apart (|gap| <= 1 min) | 2 |
| median gap, BSE - NSE (min) | 4.45 |
| news seen before both exchanges | 12 |
| stock moved 1 % BEFORE the first exchange filing | 3 |
| stock moved 1 % within 0-5 min after it | 7 |
| stock moved 1 % more than 5 min after it | 3 |
| stock did not move 1 % | 2 |
| volume jump BEFORE the first exchange filing | 8 |
| volume jump within 0-5 min after it | 7 |

## Every case

| symbol | day | NSE | BSE | BSE - NSE (min) | news | first source | stock moved 1 % at | moved - first filing (min) | volume jump at | volume jump - first filing (min) | move to 15:20 % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ICICIPRULI | 2026-10-13 | 13:18:24 | 13:30:12 | 11.8 | 07:26 | news | 13:19 | 1 | 12:51 | -27 | -3.29 |
| CANBK | 2026-10-14 | 12:07:56 | 12:08:10 | 0.2 | 07:46 | news | 11:55 | -12 | 11:45 | -22 | 0.85 |
| BHEL | 2026-10-14 | 13:38:41 | 13:35:13 | -3.5 | 09:10 | news | 13:35 | 0 | 13:35 | 0 | 5.05 |
| PETRONET | 2026-10-14 | 15:04:20 |  |  |  | NSE |  |  | 14:43 | -21 | -0.12 |
| MARICO | 2026-10-15 | 11:02:15 |  |  | 10:42 | news | 12:27 | 85 | 10:33 | -29 | -0.8 |
| ICICIPRULI | 2026-10-15 | 11:49:49 |  |  | 11:49 | news |  |  | 11:21 | -28 | -0.52 |
| NESTLEIND | 2026-10-15 | 12:24:54 | 12:35:20 | 10.4 | 07:43 | news | 12:25 | 1 | 12:25 | 1 | -6.66 |
| INDIANB | 2026-10-15 | 12:54:44 | 13:00:18 | 5.6 | 07:43 | news | 12:56 | 2 | 12:35 | -19 | -0.78 |
| POLYCAB | 2026-10-15 | 12:58:53 | 13:05:55 | 7 | 07:43 | news | 13:05 | 7 | 12:58 | 0 | -1.1 |
| HDFCAMC | 2026-10-15 | 14:40:10 | 14:40:48 | 0.6 | 07:43 | news | 14:41 | 1 | 14:41 | 1 | 2.58 |
| FEDERALBNK | 2026-10-16 | 13:20:49 | 13:24:05 | 3.3 | 13:27 | NSE | 13:29 | 9 | 13:03 | -17 | 0.7 |
| UJJIVANSFB | 2026-10-16 | 13:59:31 | 13:55:46 | -3.8 | 14:31 | BSE | 13:54 | -1 | 13:56 | 1 | -3.45 |
| CROMPTON | 2026-10-16 | 14:27:38 | 14:38:41 | 11.1 | 08:05 | news | 14:07 | -20 | 13:57 | -30 | 4.78 |
| UNIONBANK | 2026-10-19 | 12:03:22 | 12:12:46 | 9.4 | 01:00 | news | 12:04 | 1 | 12:03 | 0 | 2.26 |
| ULTRACEMCO | 2026-10-19 | 13:45:47 | 13:47:54 | 2.1 | 07:41 | news | 13:46 | 1 | 13:46 | 1 | -2.59 |

## Read by hand: the news headlines around each filing (Google News, same day)
- **Morning news items are previews** ("Q2 results today", "what to expect"), not the results. The first headline
  **with the numbers** came **0-10 minutes after** the first exchange filing in every case:
  - Canara Bank 12:07, then 12:15;
  - BHEL 13:49;
  - Nestle 12:24 / 12:29;
  - Indian Bank 12:54;
  - Polycab 13:08;
  - HDFC AMC 14:51;
  - Federal Bank 13:27;
  - Ujjivan 14:31;
  - Crompton 14:36;
  - Union Bank 12:03 / 12:07;
  - UltraTech 13:45 / 13:51.
  The "same-minute" ones are auto-written summaries (Kalkine) of the exchange filing.
- **Three rows are not results:** PETRONET 15:04 (a board-meeting date), MARICO 11:02 (no results news that day) and
  the second ICICIPRULI row (10-15). That leaves **12 real cases**.
- **Exchange order** (12 cases with both times):
  - NSE first in 10;
  - BSE first in 2 (BHEL 3.5 min, Ujjivan 3.8 min);
  - BSE was a median 4.5 minutes later.
- **The stock** moved 1 % within 0-2 minutes of the first exchange filing in 8 of 12 cases. Exceptions:
  - Canara Bank moved 12 minutes **before** (volume from 11:45);
  - Crompton moved 20 minutes **before** (volume from 13:57): news reached the market before either exchange
    published it;
  - Federal Bank and Polycab moved 7-9 minutes after.
- **Company websites** give no time stamps, so they cannot be checked this way.
