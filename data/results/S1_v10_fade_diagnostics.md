# S1 v10 fade · diagnostics

Descriptive only (strategies/S1_v10_fade_diagnostics.md and its 2026-10-18 addendum). Not out of sample. 123 bucket tests were run; by chance alone about 3.5 would come out 'consistent' (N >= 30 and >= 15 dates in both windows, same sign, |t| >= 1 in each, |pooled t| >= 2); STRONG needs |pooled t| >= 3.54 (Bonferroni 5 % for 123 tests). Found: 11 pass (6 of them STRONG).

Fade trades: 864 (2022-24 430, 2025-26 434); results filings (Q6): 2489 (2022-24 1340, 2025-26 1149).

## Answers (verified)

Bottom line: S1 v10 stays as it is. No new rule is proven. The one lead (puts with profit growth of only 10-25 % do worse) is weak: it fails with the realistic VWAP entry in 2025-26 and is no better than chance across the measures tested. It is a watch item, not a new version yet.
Checked by 3 independent agents (each rebuilt the numbers from the raw files with their own code and tried to disprove them) plus a completeness critic. All 9 headline claims survived: no claim had a majority against it, and only one agent objected to one claim (C8). The wording below includes their corrections.

Q1 · Do heavy losers fail because the option never moved up? PARTLY: 1 in 3 losers.
- 32-35 % of losers never rose even 10 % above the entry price. That holds for calls and puts, in 2022-24 and 2025-26 alike. They are the worst losers, about -52 % each and 37-46 % of all rupees lost.
- In 71-83 % of those, the stock moved WITH the numbers from the day-0 open. The stock went the wrong way; the option did not fail on its own.
- Another 1 in 3 losers rose 30 % or more first, then gave it all back.
- When the stock faded, the option won 57-66 % of the time. When it did not, the option won only 4-5 %. That is close to automatic for a bought option. With the realistic VWAP entry, faded trades win only 33-43 %.
- Strike distance: even when the stock faded, the losing options had farther strikes. Median distance from the stock: puts 7.0 % vs 5.4 % for the winners, calls 8.0 % vs 5.6 %. A far strike needs a bigger fade to pay.

Q2 · Does a stock that already fell make the put worse, better, or is it the market (NIFTY 50)?
- Already fell: NO difference. The average looked better (+11 % / +21 % a trade), but that comes from a few big winners. Medians, trimmed means and the VWAP entry show no difference. A call on a stock that already rose has too few trades (20 per period) to judge.
- The market on day 0: YES, a big effect. Puts averaged about -21 % / -22 % on days NIFTY rose more than 0.3 % from the open, against +17 % / +37 % on days it fell. Calls show the opposite pattern.
  - The gap between up and down days is solid. It holds with medians, trimming, dropping the biggest day and the VWAP entry.
  - The "won +17 % / +37 %" level rests on a few big winners: the median on NIFTY-down days is about -4 % / +2 %.
  - NIFTY's day is only known after the close, so it cannot be a buy rule.
- Market share of the fade: for calls, and for puts in 2025-26, the fade is the stock's own move. For puts in 2022-24, about a third of the small fade was the market. The overall average near zero is partly puts and calls cancelling out.
- Sector: for puts, about half of the stock's fade is shared with its sector peers that day. Calls keep their fade.

Q3 · Should there be a rule on NP YoY %, NP QoQ % or revenue YoY %?
- NP YoY for puts: a WEAK lead, not proven.
  - Puts with profit growth of only 10-25 % lost about -12 % (2022-24) and -8 % (2025-26) a trade. Puts above 25 % made about +11 % and +16 %. Both periods point the same way (pooled t -3.5), and EPS growth of 10-25 % shows the same.
  - But with the VWAP entry the gap holds only in 2022-24, not 2025-26 (t -1.0). Trimming the extremes halves the 2025-26 gap.
  - About 105 tested measures are known before entry. About 3 would pass by chance, and this lead (with its EPS twin) is the only one that passed. So it may be luck.
- Across about 2,100 results filings with numbers, the biggest numbers fade most on day 0. Profit up more than 100 %: the stock fell about -1.1 % (net of NIFTY) from the open. Profit down more than 50 %: it rose about +1.0 %. Up 10-25 %: almost no fade. The curve is not perfectly smooth; in 2025-26 the 0-10 % band also fell.
- NP YoY for calls: profit down more than 50 % looked best, but not reliably. UNCLEAR.
- NP QoQ: NO. No band stands out in either period.
- Revenue YoY: NO for puts. For calls, falling revenue helped only the stock's own move, not the option's. UNCLEAR.

Q4 · "If the run is already done, then for sure it does the opposite"? NO.
- After a big run (more than 8 % in 20 sessions), day 0 moved opposite only 54-56 % of the time in the most favourable version. Other versions give 41-55 %. The average was 0.1-0.2 %, not significant. That is a coin flip, not "for sure".
- What does hold: right after results, the stock first jumps WITH the numbers, before our 09:15 entry. Profit up more than 100 %: about +1.7 % before entry, then -1.1 % from the open. The day-0 fade gives back only part of that first jump.

Q4b · Do we need other measures than the three result numbers? Mostly NO.
- Tested, known before 09:15, and nothing reliable for the option: pre-run, gap, the move already seen before entry, 52-week place, volume, futures OI build-up, filing time, NP QoQ, revenue, EPS QoQ, days to expiry.
- On the stock's own move (not the option), strike distance, EPS and revenue bands pass, so they are worth watching. NIFTY's own pre-open move was not tested.

Your 9 stocks (picked with hindsight, so illustrations, not proof):
- The January 2025 puts that lost all had weak profit growth, in the 10-25 % band: POLYCAB +11.5 %, SONACOMS +12.8 %, ADANIPORTS +14 % and BAJFINANCE +18 %.
- 4 of the 5 losing puts had also fallen 8-10 % in the 20 sessions before.
- POLYCAB and SONACOMS had already dropped about 6 % before the 09:15 entry, so the fade happened before we bought, and then they bounced from the open.
- BEL (profit +52 %) lost on 31 Jan 2025, when NIFTY rose +0.9 % and only 2 of the 8 fade trades won.
- OBEROIRLTY put +292 % (profit +72 %, NIFTY -1.7 % that day). BPCL put +128 % (Aug 2025, profit +141 %).
- BOSCHLTD call -27 % (profit -11.5 %, only just weak).


## Buckets that pass the guard (option net % or the stock's own fade)

| question | measure | side | bucket | n 2022-24 | dates 2022-24 | mean 2022-24 | rest 2022-24 | median 2022-24 | hit % 2022-24 | t 2022-24 | detectable diff 2022-24 | vwap mean 2022-24 | stock fade 2022-24 | stock fade rest 2022-24 | n 2025-26 | dates 2025-26 | mean 2025-26 | rest 2025-26 | median 2025-26 | hit % 2025-26 | t 2025-26 | detectable diff 2025-26 | vwap mean 2025-26 | stock fade 2025-26 | stock fade rest 2025-26 | pooled t | vwap pooled t | stock fade pooled t | enough both (N>=30, dates>=15) | verdict | only with the open entry | stock fade verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q2 | NIFTY day-0 open->close | PE | down < -0.3 % | 106 | 63 | 17 | -3.4 | -4.2 | 46 | 1.834 | 22 | -2.1 | 1.09 | -0.18 | 93 | 43 | 36.9 | -5.1 | 2.3 | 53 | 2.968 | 28 | -3.7 | 1.68 | 0.2 | 3.396 | 6.962 | 5.052 | True | consistent |  | STRONG |
| Q2 | NIFTY day-0 open->close | PE | up > +0.3 % | 86 | 41 | -21.1 | 12.7 | -36.5 | 21 | -3.593 | 19 | -25.6 | -0.57 | 0.55 | 86 | 35 | -22.3 | 17.7 | -32.8 | 26 | -4.601 | 17 | -22.2 | -0.43 | 1.01 | -5.794 | -7.304 | -4.301 | True | STRONG |  | STRONG |
| Q2 | NIFTY day-0 open->close | CE | down < -0.3 % | 42 | 34 | -9.1 | 11.4 | -28.7 | 36 | -1.66 | 25 | -21.9 | -0.51 | 1.44 | 37 | 24 | -18 | 11.2 | -41.7 | 24 | -1.924 | 30 | -26.6 | -0.58 | 1.34 | -2.534 | -3.883 | -3.912 | True | consistent |  | STRONG |
| Q2 | NIFTY day-0 close->close | PE | down < -0.3 % | 90 | 55 | 18.1 | -2.4 | -10.3 | 44 | 1.668 | 25 | -4.3 | 0.77 | 0.04 | 112 | 49 | 35.2 | -7.9 | 10.7 | 54 | 3.714 | 23 | -1.6 | 1.74 | 0.03 | 3.806 | 6.401 | 4.479 | True | STRONG |  | STRONG |
| Q2 | NIFTY day-0 close->close | CE | down < -0.3 % | 39 | 31 | -11.5 | 11.9 | -27.5 | 31 | -1.991 | 23 | -21.6 | -0.74 | 1.48 | 39 | 27 | -13 | 9.3 | -41.7 | 28 | -1.434 | 31 | -28.7 | -0.34 | 1.26 | -2.422 | -4.617 | -3.946 | True | consistent |  | STRONG |
| Q2 | NIFTY day-0 close->close | CE | up > +0.3 % | 45 | 34 | 21.2 | -7.1 | -2.9 | 49 | 2.268 | 25 | -1.1 | 1.82 | 0.02 | 36 | 27 | 5 | -0.1 | -5 | 44 | 0.341 | 30 | -10 | 1.2 | 0.47 | 1.845 | 4.717 | 2.76 | True |  |  | consistent |
| Q4 | NP YoY (puts) | PE | 10-25 % | 104 | 82 | -12.3 | 11.2 | -27.9 | 27 | -2.387 | 20 | -21.1 | -0.29 | 0.5 | 116 | 83 | -8.2 | 15.6 | -17.5 | 39 | -2.586 | 18 | -14.5 | 0.1 | 0.92 | -3.516 | -3.345 | -3.085 | True | consistent |  | consistent |
| Q4 | NP YoY (puts) | PE | > 100 % | 44 | 40 | 17.7 | 1.1 | -20.1 | 41 | 0.874 | 38 | -9.2 | 0.9 | 0.14 | 52 | 41 | 29.8 | 2.7 | -10 | 42 | 1.601 | 34 | -14.8 | 1.61 | 0.44 | 1.75 | 0.518 | 2.452 | True |  |  | consistent |
| Q4 | Revenue YoY (calls) | CE | < 0 % | 35 | 35 | 9.5 | 1.5 | -15.2 | 40 | 0.526 | 30 | -11.5 | 1.3 | 0.48 | 42 | 36 | 27.4 | -14 | 8.2 | 52 | 2.532 | 33 | -12.1 | 1.85 | 0.02 | 2.162 | 1.599 | 2.708 | True |  |  | consistent |
| Q7 | EPS YoY (puts) | PE | 10-25 % | 103 | 80 | -7 | 8.8 | -27.3 | 29 | -1.647 | 19 | -19.7 | -0.07 | 0.4 | 98 | 71 | -9.8 | 14.7 | -22.2 | 37 | -2.747 | 18 | -15.1 | 0.09 | 0.88 | -3.107 | -3.017 | -2.656 | True | consistent |  | consistent |
| Q7 | EPS YoY (puts) | PE | > 50 % | 106 | 83 | 12.7 | -1 | -8.4 | 44 | 1.175 | 23 | -9.2 | 0.57 | 0.08 | 105 | 68 | 17.2 | 2.3 | -16.8 | 40 | 1.174 | 25 | -12.7 | 1.12 | 0.4 | 1.661 | 1.696 | 2.068 | True |  |  | consistent |
| Q7 | Strike distance (% OTM) | PE | < 2 % | 72 | 56 | -3.3 | 5.5 | -34 | 33 | -0.673 | 26 | -19.7 | -0.33 | 0.41 | 78 | 59 | -7.6 | 11.7 | -32.5 | 29 | -1.974 | 20 | -12.6 | -0.41 | 0.96 | -1.872 | -1.235 | -4.112 | True |  |  | STRONG |
| Q7 | Strike distance (% OTM) | PE | > 5 % | 141 | 92 | 5.6 | 1.7 | -25.2 | 35 | 0.372 | 21 | -13.2 | 0.63 | -0.07 | 125 | 80 | 17.2 | 0.6 | -8.5 | 45 | 1.478 | 22 | -13.1 | 1.33 | 0.18 | 1.308 | -0.017 | 3.174 | True |  |  | consistent |
| Q7 | Sector day 0 | PE | down < -0.5 % | 70 | 49 | 26.8 | -2.3 | -2.8 | 49 | 1.965 | 30 | -3.2 | 1.11 | -0.05 | 95 | 53 | 38 | -9.1 | 12.2 | 58 | 3.733 | 25 | -3.4 | 1.72 | -0.04 | 4.029 | 5.291 | 4.649 | True | STRONG |  | STRONG |
| Q7 | Sector day 0 | PE | flat | 108 | 75 | 11.6 | 0.7 | -17.2 | 40 | 0.938 | 23 | -12.3 | 0.88 | -0.16 | 101 | 66 | 2.4 | 8.4 | -16 | 42 | -0.594 | 20 | -12.1 | 1.04 | 0.27 | 0.243 | 0.605 | 3.379 | True |  |  | consistent |
| Q7 | Sector day 0 | PE | up > +0.5 % | 106 | 71 | -16.5 | 17.6 | -35.5 | 25 | -3.406 | 20 | -21.6 | -1 | 0.97 | 95 | 49 | -21.2 | 19.6 | -42.2 | 21 | -3.738 | 22 | -22.2 | -1.19 | 1.37 | -5.052 | -6.384 | -8.048 | True | STRONG |  | STRONG |
| Q7 | Sector day 0 | CE | down < -0.5 % | 32 | 29 | -27.9 | 17.7 | -31.7 | 22 | -3.764 | 24 | -27 | -1.31 | 1.86 | 35 | 26 | -26.1 | 17.1 | -45.4 | 17 | -2.83 | 31 | -29.7 | -1.04 | 1.59 | -4.663 | -5.749 | -5.624 | True | STRONG |  | STRONG |
| Q7 | Sector day 0 | CE | up > +0.5 % | 45 | 37 | 29.8 | -21.6 | 4.7 | 53 | 3.985 | 26 | -2.1 | 2.53 | -0.72 | 36 | 29 | 17 | -4.7 | 3.6 | 53 | 1.431 | 30 | -7.9 | 1.88 | 0.1 | 3.83 | 4.831 | 5.345 | True | STRONG |  | STRONG |

## Coverage: what was counted, left out or blanked

| window | item | count |
|---|---|---|
| 2022-24 | fade trades (open entry, same-day exit) | 436 |
| 2022-24 |   left out: special session (Muhurat / short) | 6 |
| 2022-24 |   kept but flagged: full special session / budget day | 1 |
| 2022-24 |   no NIFTY day-0 open | 0 |
| 2022-24 |   no stock day-0 prices (eod2) | 1 |
| 2022-24 |   a feature blanked by a > 20 % one-day move | 6 |
| 2022-24 |   no beta | 0 |
| 2022-24 |     blanked: ADANIENT 2023-02-15 (pre5,pre20,pre60,pos52) | 1 |
| 2022-24 |     blanked: ADANIENT 2023-05-05 (pre60,pos52) | 1 |
| 2022-24 |     blanked: ADANIENT 2023-11-03 (pos52) | 1 |
| 2022-24 |     blanked: ADANIENT 2024-02-02 (pos52) | 1 |
| 2022-24 |     blanked: POLYCAB 2024-05-13 (pos52) | 1 |
| 2022-24 |     blanked: ADANIPORTS 2024-08-02 (pre60,pos52) | 1 |
| 2022-24 |   no same-contract VWAP | 8 |
| 2022-24 |   filing slot: pre-open day 0 | 5 |
| 2022-24 |   filing slot: in session day -1 | 166 |
| 2022-24 |   filing slot: after close day -1 | 230 |
| 2022-24 |   filing slot: non-session day / earlier | 35 |
| 2022-24 |   filing slot: time unknown | 0 |
| 2022-24 | results filings of F&O stocks (Q6) | 1358 |
| 2022-24 |   left out: special session | 18 |
| 2022-24 |   with all three numbers (Q4 curves) | 1101 |
| 2022-24 |   filed in session day -1 | 454 |
| 2025-26 | fade trades (open entry, same-day exit) | 434 |
| 2025-26 |   left out: special session (Muhurat / short) | 0 |
| 2025-26 |   kept but flagged: full special session / budget day | 10 |
| 2025-26 |   no NIFTY day-0 open | 0 |
| 2025-26 |   no stock day-0 prices (eod2) | 0 |
| 2025-26 |   a feature blanked by a > 20 % one-day move | 17 |
| 2025-26 |   no beta | 0 |
| 2025-26 |     blanked: OFSS 2025-01-16 (pos52) | 1 |
| 2025-26 |     blanked: ADANIENT 2025-01-31 (pre60,pos52) | 1 |
| 2025-26 |     blanked: ADANIPORTS 2025-01-31 (pos52) | 1 |
| 2025-26 |     blanked: RECLTD 2025-02-07 (pos52) | 1 |
| 2025-26 |     blanked: PFC 2025-02-13 (pos52) | 1 |
| 2025-26 |     blanked: INDUSINDBK 2025-05-22 (pre60,pos52) | 1 |
| 2025-26 |     blanked: ADANIENT 2025-08-01 (pos52) | 1 |
| 2025-26 |     blanked: SIEMENS 2025-08-11 (pos52) | 1 |
| 2025-26 |     blanked: KEI 2025-10-16 (pos52) | 1 |
| 2025-26 |     blanked: INDUSINDBK 2025-10-20 (pos52) | 1 |
| 2025-26 |     blanked: PGEL 2025-11-14 (pos52) | 1 |
| 2025-26 |     blanked: PGEL 2026-02-03 (pos52) | 1 |
| 2025-26 |     blanked: TMPV 2026-02-06 (pos52) | 1 |
| 2025-26 |     blanked: SIEMENS 2026-02-09 (pos52) | 1 |
| 2025-26 |     blanked: PGEL 2026-08-07 (pos52) | 1 |
| 2025-26 |     blanked: KAYNES 2026-08-10 (pre60,pos52) | 1 |
| 2025-26 |     blanked: TMPV 2026-08-14 (pos52) | 1 |
| 2025-26 |   no same-contract VWAP | 0 |
| 2025-26 |   filing slot: pre-open day 0 | 2 |
| 2025-26 |   filing slot: in session day -1 | 155 |
| 2025-26 |   filing slot: after close day -1 | 245 |
| 2025-26 |   filing slot: non-session day / earlier | 32 |
| 2025-26 |   filing slot: time unknown | 0 |
| 2025-26 | results filings of F&O stocks (Q6) | 1149 |
| 2025-26 |   left out: special session | 0 |
| 2025-26 |   with all three numbers (Q4 curves) | 985 |
| 2025-26 |   filed in session day -1 | 373 |

## Q1 · Losers: never up (peak < +10 %), round trip (peak >= +30 %, then a loss), other

| window | side | trades | losers | losers % | never up: n | never up: share of losers % | never up: share of rupees lost % | never up: mean net % | never up: stock faded % | never up: stock best move % (median) | never up: stock day range % (median) | never up: strike OTM at open % (median) | never up: sessions to expiry (median) | round trip: n | round trip: share of losers % | round trip: share of rupees lost % | round trip: mean net % | round trip: stock faded % | round trip: stock best move % (median) | round trip: stock day range % (median) | round trip: strike OTM at open % (median) | round trip: sessions to expiry (median) | other: n | other: share of losers % | other: share of rupees lost % | other: mean net % | other: stock faded % | other: stock best move % (median) | other: stock day range % (median) | other: strike OTM at open % (median) | other: sessions to expiry (median) | never up: option high <= entry (n) | winners: stock best move % (median) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022-24 | PE | 315 | 204 | 64.8 | 69 | 33.8 | 43.8 | -52.3 | 20.3 | 0.65 | 4.1 | 5.34 | 15 | 70 | 34.3 | 26.4 | -34.9 | 50 | 2.06 | 3.79 | 5.02 | 12 | 65 | 31.9 | 29.8 | -38.5 | 44.6 | 1.54 | 3.77 | 6.44 | 15 | 34 | 3.46 |
| 2022-24 | CE | 115 | 69 | 60 | 24 | 34.8 | 45.9 | -54.5 | 29.2 | 0.77 | 3.97 | 6.37 | 12 | 26 | 37.7 | 21.4 | -25.1 | 53.8 | 2.87 | 4.76 | 5.84 | 15.5 | 19 | 27.5 | 32.7 | -39.8 | 36.8 | 1.65 | 3.35 | 5.27 | 13 | 15 | 3.91 |
| 2025-26 | PE | 322 | 191 | 59.3 | 62 | 32.5 | 40.7 | -51.6 | 21 | 0.9 | 3.96 | 5.91 | 14 | 81 | 42.4 | 30.7 | -33.2 | 49.4 | 2.43 | 4.08 | 4.5 | 8 | 48 | 25.1 | 28.6 | -46 | 22.9 | 1.46 | 4.13 | 4.52 | 10.5 | 33 | 3.73 |
| 2025-26 | CE | 112 | 69 | 61.6 | 23 | 33.3 | 36.7 | -51.5 | 17.4 | 0.89 | 3.19 | 6.08 | 14 | 22 | 31.9 | 23.6 | -34.1 | 68.2 | 2.66 | 5.3 | 6.83 | 11 | 24 | 34.8 | 39.7 | -46.8 | 41.7 | 1.46 | 4.49 | 6.56 | 15 | 10 | 4.29 |

## Q1 · Did the stock fade? Did the option win? (2x2)

| window | side | stock faded | option won | n | share % | mean net % | mean stock fade % | median stock best move % | median strike OTM at open % | median sessions to expiry |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-24 | PE | yes | yes | 104 | 33.1 | 88.6 | 3.12 | 3.51 | 5.43 | 12 |
| 2022-24 | PE | yes | no | 78 | 24.8 | -25.9 | 1.15 | 2.42 | 6.98 | 14 |
| 2022-24 | PE | no | yes | 7 | 2.2 | 60.6 | -2.42 | 0.9 | 5.14 | 12 |
| 2022-24 | PE | no | no | 125 | 39.8 | -52.2 | -2.57 | 0.78 | 5.06 | 14 |
| 2022-24 | CE | yes | yes | 44 | 38.3 | 72 | 3.76 | 4.01 | 5.55 | 15 |
| 2022-24 | CE | yes | no | 28 | 24.3 | -23.3 | 1.26 | 2.87 | 7.95 | 15 |
| 2022-24 | CE | no | yes | 2 | 1.7 | 2.5 | -1.49 | 2.14 | 6.71 | 22 |
| 2022-24 | CE | no | no | 41 | 35.7 | -50.4 | -2.78 | 0.9 | 5.51 | 13 |
| 2025-26 | PE | yes | yes | 126 | 39.1 | 80 | 3.39 | 3.85 | 5.2 | 12 |
| 2025-26 | PE | yes | no | 64 | 19.9 | -22.9 | 1.36 | 2.93 | 4.89 | 9 |
| 2025-26 | PE | no | yes | 5 | 1.6 | 58 | -1.16 | 0.35 | 3.64 | 21 |
| 2025-26 | PE | no | no | 127 | 39.4 | -52.2 | -2.42 | 1.01 | 4.51 | 11 |
| 2025-26 | CE | yes | yes | 41 | 36.6 | 77.8 | 3.56 | 4.41 | 5.56 | 12 |
| 2025-26 | CE | yes | no | 29 | 25.9 | -29.5 | 1.33 | 2.66 | 8.06 | 11 |
| 2025-26 | CE | no | yes | 2 | 1.8 | 21.9 | -0.25 | 1.13 | 4.05 | 13 |
| 2025-26 | CE | no | no | 40 | 35.7 | -55 | -2.63 | 1.05 | 6.09 | 13.5 |

## Q2 · The stock's fade: raw, net of NIFTY 50 (beta 1 and beta), net of its sector

| window | side | measure | n | dates | mean | median | hit_pct | t |
|---|---|---|---|---|---|---|---|---|
| 2022-24 | PE | stock fade, raw (open->close) | 314 | 169 | 0.24 | 0.46 | 58 | 1.238 |
| 2022-24 | PE | stock fade net of NIFTY, beta 1 (open->close) | 314 | 169 | 0.16 | 0.43 | 56.1 | 0.878 |
| 2022-24 | PE | stock fade net of beta x NIFTY (open->close) | 314 | 169 | 0.17 | 0.37 | 56.7 | 0.909 |
| 2022-24 | PE | stock fade net of its sector (open->close) | 285 | 162 | 0.11 | 0.29 | 54 | 0.602 |
| 2022-24 | PE | stock fade net of its sector (close->close, includes the gap) | 284 | 161 | -0.77 | -0.44 | 44 | -3.483 |
| 2022-24 | PE | option net % of premium (open entry) | 315 | 170 | 3.46 | -22.76 | 35.2 | 0.658 |
| 2022-24 | PE | the market's part: sign x beta x NIFTY open->close | 315 | 170 | 0.08 | 0 | 50.8 | 1.292 |
| 2022-24 | PE | beta (250 sessions) | 315 | 170 | 0.97 | 0.95 | 100 | 49.515 |
| 2022-24 | CE | stock fade, raw (open->close) | 115 | 92 | 0.73 | 0.85 | 62.6 | 2.065 |
| 2022-24 | CE | stock fade net of NIFTY, beta 1 (open->close) | 115 | 92 | 0.83 | 0.71 | 66.1 | 2.508 |
| 2022-24 | CE | stock fade net of beta x NIFTY (open->close) | 115 | 92 | 0.85 | 0.79 | 65.2 | 2.578 |
| 2022-24 | CE | stock fade net of its sector (open->close) | 96 | 78 | 0.89 | 0.79 | 63.5 | 2.534 |
| 2022-24 | CE | stock fade net of its sector (close->close, includes the gap) | 96 | 78 | -0.83 | -0.49 | 44.8 | -2.01 |
| 2022-24 | CE | option net % of premium (open entry) | 115 | 92 | 3.95 | -10.32 | 40 | 0.648 |
| 2022-24 | CE | the market's part: sign x beta x NIFTY open->close | 115 | 92 | -0.12 | -0.05 | 48.7 | -1.399 |
| 2022-24 | CE | beta (250 sessions) | 115 | 92 | 0.98 | 0.89 | 100 | 27.674 |
| 2022-24 | all | stock fade, raw (open->close) | 429 | 199 | 0.37 | 0.58 | 59.2 | 2.416 |
| 2022-24 | all | stock fade net of NIFTY, beta 1 (open->close) | 429 | 199 | 0.34 | 0.49 | 58.7 | 2.314 |
| 2022-24 | all | stock fade net of beta x NIFTY (open->close) | 429 | 199 | 0.35 | 0.53 | 59 | 2.383 |
| 2022-24 | all | stock fade net of its sector (open->close) | 381 | 190 | 0.31 | 0.41 | 56.4 | 1.981 |
| 2022-24 | all | stock fade net of its sector (close->close, includes the gap) | 380 | 189 | -0.78 | -0.45 | 44.2 | -4.137 |
| 2022-24 | all | option net % of premium (open entry) | 430 | 200 | 3.59 | -18.08 | 36.5 | 0.9 |
| 2022-24 | all | the market's part: sign x beta x NIFTY open->close | 430 | 200 | 0.02 | 0 | 50.2 | 0.606 |
| 2022-24 | all | beta (250 sessions) | 430 | 200 | 0.97 | 0.93 | 100 | 54.832 |
| 2025-26 | PE | stock fade, raw (open->close) | 322 | 137 | 0.63 | 0.82 | 59 | 3.087 |
| 2025-26 | PE | stock fade net of NIFTY, beta 1 (open->close) | 322 | 137 | 0.58 | 0.78 | 61.2 | 3.227 |
| 2025-26 | PE | stock fade net of beta x NIFTY (open->close) | 322 | 137 | 0.56 | 0.71 | 60.9 | 3.188 |
| 2025-26 | PE | stock fade net of its sector (open->close) | 291 | 133 | 0.29 | 0.47 | 58.8 | 1.722 |
| 2025-26 | PE | stock fade net of its sector (close->close, includes the gap) | 291 | 133 | -0.57 | -0.41 | 47.1 | -2.554 |
| 2025-26 | PE | option net % of premium (open entry) | 322 | 137 | 7.06 | -15.96 | 40.7 | 1.289 |
| 2025-26 | PE | the market's part: sign x beta x NIFTY open->close | 322 | 137 | 0.06 | 0 | 50.3 | 0.916 |
| 2025-26 | PE | beta (250 sessions) | 322 | 137 | 1.09 | 1.09 | 99.4 | 53.55 |
| 2025-26 | CE | stock fade, raw (open->close) | 112 | 78 | 0.7 | 0.75 | 62.5 | 2.232 |
| 2025-26 | CE | stock fade net of NIFTY, beta 1 (open->close) | 112 | 78 | 0.78 | 0.79 | 63.4 | 2.749 |
| 2025-26 | CE | stock fade net of beta x NIFTY (open->close) | 112 | 78 | 0.82 | 0.84 | 64.3 | 2.944 |
| 2025-26 | CE | stock fade net of its sector (open->close) | 105 | 75 | 0.74 | 0.59 | 61 | 2.662 |
| 2025-26 | CE | stock fade net of its sector (close->close, includes the gap) | 105 | 75 | -0.75 | -0.42 | 42.9 | -2.03 |
| 2025-26 | CE | option net % of premium (open entry) | 112 | 78 | 1.55 | -22.57 | 38.4 | 0.201 |
| 2025-26 | CE | the market's part: sign x beta x NIFTY open->close | 112 | 78 | -0.12 | 0.02 | 52.7 | -1.068 |
| 2025-26 | CE | beta (250 sessions) | 112 | 78 | 1.14 | 1.17 | 100 | 38.747 |
| 2025-26 | all | stock fade, raw (open->close) | 434 | 152 | 0.65 | 0.8 | 59.9 | 4.235 |
| 2025-26 | all | stock fade net of NIFTY, beta 1 (open->close) | 434 | 152 | 0.63 | 0.79 | 61.8 | 4.338 |
| 2025-26 | all | stock fade net of beta x NIFTY (open->close) | 434 | 152 | 0.63 | 0.77 | 61.8 | 4.377 |
| 2025-26 | all | stock fade net of its sector (open->close) | 396 | 149 | 0.41 | 0.54 | 59.3 | 2.9 |
| 2025-26 | all | stock fade net of its sector (close->close, includes the gap) | 396 | 149 | -0.62 | -0.41 | 46 | -3.323 |
| 2025-26 | all | option net % of premium (open entry) | 434 | 152 | 5.63 | -17.02 | 40.1 | 1.345 |
| 2025-26 | all | the market's part: sign x beta x NIFTY open->close | 434 | 152 | 0.02 | 0.01 | 50.9 | 0.405 |
| 2025-26 | all | beta (250 sessions) | 434 | 152 | 1.11 | 1.1 | 99.5 | 66.153 |

## Q2-Q4, Q7 · Every bucket vs the rest of its side (net % of premium, open entry)

| question | measure | side | bucket | n 2022-24 | dates 2022-24 | mean 2022-24 | rest 2022-24 | median 2022-24 | hit % 2022-24 | t 2022-24 | detectable diff 2022-24 | vwap mean 2022-24 | stock fade 2022-24 | stock fade rest 2022-24 | n 2025-26 | dates 2025-26 | mean 2025-26 | rest 2025-26 | median 2025-26 | hit % 2025-26 | t 2025-26 | detectable diff 2025-26 | vwap mean 2025-26 | stock fade 2025-26 | stock fade rest 2025-26 | pooled t | vwap pooled t | stock fade pooled t | enough both (N>=30, dates>=15) | verdict | only with the open entry | stock fade verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q2 | NIFTY day-0 open->close | PE | down < -0.3 % | 106 | 63 | 17 | -3.4 | -4.2 | 46 | 1.834 | 22 | -2.1 | 1.09 | -0.18 | 93 | 43 | 36.9 | -5.1 | 2.3 | 53 | 2.968 | 28 | -3.7 | 1.68 | 0.2 | 3.396 | 6.962 | 5.052 | True | consistent |  | STRONG |
| Q2 | NIFTY day-0 open->close | PE | flat | 123 | 66 | 8.9 | -0.1 | -22.8 | 36 | 0.808 | 22 | -15.8 | 0.09 | 0.34 | 143 | 59 | 5.3 | 8.5 | -13 | 42 | -0.306 | 21 | -12.3 | 0.58 | 0.67 | 0.355 | -0.694 | -0.575 | True |  |  |  |
| Q2 | NIFTY day-0 open->close | PE | up > +0.3 % | 86 | 41 | -21.1 | 12.7 | -36.5 | 21 | -3.593 | 19 | -25.6 | -0.57 | 0.55 | 86 | 35 | -22.3 | 17.7 | -32.8 | 26 | -4.601 | 17 | -22.2 | -0.43 | 1.01 | -5.794 | -7.304 | -4.301 | True | STRONG |  | STRONG |
| Q2 | NIFTY day-0 open->close | CE | down < -0.3 % | 42 | 34 | -9.1 | 11.4 | -28.7 | 36 | -1.66 | 25 | -21.9 | -0.51 | 1.44 | 37 | 24 | -18 | 11.2 | -41.7 | 24 | -1.924 | 30 | -26.6 | -0.58 | 1.34 | -2.534 | -3.883 | -3.912 | True | consistent |  | STRONG |
| Q2 | NIFTY day-0 open->close | CE | flat | 38 | 33 | 2.1 | 4.9 | -11.9 | 34 | -0.215 | 26 | -16.3 | 0.71 | 0.74 | 46 | 34 | 11.9 | -5.6 | -13.8 | 43 | 1.153 | 30 | -15.2 | 1.26 | 0.31 | 0.663 | -0.108 | 1.049 | True |  |  |  |
| Q2 | NIFTY day-0 open->close | CE | up > +0.3 % | 35 | 25 | 21.6 | -3.8 | 2.3 | 51 | 1.962 | 26 | 1.4 | 2.23 | 0.07 | 29 | 20 | 10.1 | -1.4 | -3.8 | 48 | 0.605 | 38 | -11 | 1.46 | 0.44 | 1.815 | 4.183 | 3.457 | False |  |  |  |
| Q2 | NIFTY day-0 close->close | PE | down < -0.3 % | 90 | 55 | 18.1 | -2.4 | -10.3 | 44 | 1.668 | 25 | -4.3 | 0.77 | 0.04 | 112 | 49 | 35.2 | -7.9 | 10.7 | 54 | 3.714 | 23 | -1.6 | 1.74 | 0.03 | 3.806 | 6.401 | 4.479 | True | STRONG |  | STRONG |
| Q2 | NIFTY day-0 close->close | PE | flat | 118 | 58 | -2.1 | 6.8 | -24.2 | 34 | -0.886 | 20 | -15.2 | 0.03 | 0.37 | 102 | 47 | -6.2 | 13.2 | -20.5 | 36 | -1.964 | 20 | -16 | 0.42 | 0.72 | -2.015 | -1.626 | -1.16 | True |  |  |  |
| Q2 | NIFTY day-0 close->close | PE | up > +0.3 % | 107 | 57 | -2.7 | 6.6 | -28.2 | 29 | -0.82 | 23 | -20.1 | 0.05 | 0.35 | 108 | 41 | -9.6 | 15.5 | -29.7 | 31 | -2.365 | 21 | -20.4 | -0.34 | 1.11 | -2.252 | -5.274 | -2.93 | True |  |  |  |
| Q2 | NIFTY day-0 close->close | CE | down < -0.3 % | 39 | 31 | -11.5 | 11.9 | -27.5 | 31 | -1.991 | 23 | -21.6 | -0.74 | 1.48 | 39 | 27 | -13 | 9.3 | -41.7 | 28 | -1.434 | 31 | -28.7 | -0.34 | 1.26 | -2.422 | -4.617 | -3.946 | True | consistent |  | STRONG |
| Q2 | NIFTY day-0 close->close | CE | flat | 31 | 27 | -1.7 | 6.1 | -7.1 | 39 | -0.543 | 29 | -19.3 | 0.98 | 0.64 | 37 | 24 | 13.5 | -4.4 | -14.5 | 43 | 1.016 | 35 | -14.2 | 1.31 | 0.4 | 0.334 | -0.573 | 1.28 | True |  |  |  |
| Q2 | NIFTY day-0 close->close | CE | up > +0.3 % | 45 | 34 | 21.2 | -7.1 | -2.9 | 49 | 2.268 | 25 | -1.1 | 1.82 | 0.02 | 36 | 27 | 5 | -0.1 | -5 | 44 | 0.341 | 30 | -10 | 1.2 | 0.47 | 1.845 | 4.717 | 2.76 | True |  |  | consistent |
| Q3 | Pre-run 20 sessions | PE | fell > 5 % | 66 | 52 | 11.3 | 1.6 | -25.7 | 38 | 0.769 | 25 | -14 | 0.17 | 0.26 | 53 | 36 | 21.2 | 4.3 | -16.4 | 45 | 0.906 | 37 | -11.8 | 0.53 | 0.65 | 1.184 | 0.088 | -0.272 | True |  |  |  |
| Q3 | Pre-run 20 sessions | PE | -5 to +5 % | 139 | 100 | -0.6 | 7 | -23.5 | 36 | -0.73 | 21 | -15.3 | -0.04 | 0.47 | 166 | 101 | 8 | 6 | -16.1 | 43 | 0.221 | 18 | -12.7 | 0.76 | 0.48 | -0.36 | -0.704 | -0.382 | True |  |  |  |
| Q3 | Pre-run 20 sessions | PE | rose > 5 % | 108 | 78 | 4.4 | 3.3 | -19.7 | 33 | 0.105 | 22 | -11.7 | 0.64 | 0.03 | 103 | 68 | -1.8 | 11.2 | -15.6 | 34 | -1.234 | 21 | -12.4 | 0.45 | 0.71 | -0.798 | 0.725 | 0.615 | True |  |  |  |
| Q3 | Pre-run 20 sessions | CE | fell > 5 % | 50 | 41 | 11.4 | -1.8 | -3.4 | 46 | 0.98 | 27 | -8.5 | 1.48 | 0.15 | 33 | 28 | 1.2 | 1.7 | -20.8 | 39 | -0.034 | 27 | -16.9 | 0.96 | 0.59 | 0.669 | 1.272 | 1.792 | True |  |  |  |
| Q3 | Pre-run 20 sessions | CE | -5 to +5 % | 45 | 41 | -8.6 | 12.1 | -15.2 | 33 | -1.554 | 27 | -15.6 | 0.07 | 1.15 | 59 | 46 | 0.5 | 2.7 | -19.5 | 37 | -0.149 | 29 | -19.1 | 0.53 | 0.9 | -1.204 | -1.055 | -1.549 | True |  |  |  |
| Q3 | Pre-run 20 sessions | CE | rose > 5 % | 20 | 20 | 13.6 | 1.9 | -16.5 | 40 | 0.611 | 38 | -17.7 | 0.33 | 0.81 | 20 | 19 | 5.1 | 0.8 | -31.7 | 40 | 0.216 | 40 | -15.8 | 0.79 | 0.68 | 0.585 | -0.318 | -0.319 | False |  |  |  |
| Q3 | Pre-run 5 sessions | PE | fell > 3 % | 65 | 48 | -3.3 | 5.8 | -28.2 | 31 | -0.744 | 25 | -16.3 | -0.15 | 0.36 | 50 | 41 | 12.1 | 6.1 | -3.8 | 50 | 0.521 | 23 | -12 | 0.76 | 0.6 | -0.158 | -0.525 | -0.431 | True |  |  |  |
| Q3 | Pre-run 5 sessions | PE | -3 to +3 % | 172 | 122 | 10.8 | -4.6 | -24.2 | 37 | 1.537 | 20 | -13.7 | 0.37 | 0.12 | 186 | 105 | 2.8 | 12.9 | -17.2 | 40 | -0.834 | 24 | -13.5 | 0.51 | 0.78 | 0.497 | -0.445 | -0.014 | True |  |  |  |
| Q3 | Pre-run 5 sessions | PE | rose > 3 % | 74 | 51 | -5.8 | 6.9 | -15.1 | 36 | -1.499 | 17 | -11.8 | 0.36 | 0.22 | 86 | 66 | 13.3 | 4.8 | -16.4 | 36 | 0.702 | 24 | -10.5 | 0.79 | 0.57 | -0.564 | 1.061 | 0.554 | True |  |  |  |
| Q3 | Pre-run 5 sessions | CE | fell > 3 % | 39 | 35 | -4 | 3.8 | -15.2 | 33 | -0.546 | 29 | -17.8 | 0.89 | 0.53 | 23 | 20 | -3.1 | 2.7 | -26.1 | 26 | -0.337 | 34 | -20.7 | 0.16 | 0.84 | -0.624 | -1.272 | -0.269 | False |  |  |  |
| Q3 | Pre-run 5 sessions | CE | -3 to +3 % | 59 | 55 | 1.5 | 0.7 | -11.4 | 44 | 0.065 | 27 | -11.3 | 0.51 | 0.82 | 69 | 54 | 3.5 | -1.5 | -14.5 | 43 | 0.353 | 28 | -16 | 1.07 | 0.12 | 0.296 | 1.528 | 0.713 | True |  |  |  |
| Q3 | Pre-run 5 sessions | CE | rose > 3 % | 14 | 14 | 13.7 | -0.7 | -7.4 | 36 | 0.71 | 40 | -13.6 | 0.62 | 0.66 | 20 | 19 | 0.3 | 1.8 | -43.5 | 35 | -0.071 | 43 | -21.3 | 0.07 | 0.84 | 0.452 | -0.416 | -0.663 | False |  |  |  |
| Q3 | Pre-run 20, net of NIFTY | PE | fell > 5 % | 47 | 41 | 12.9 | 2 | -26.3 | 38 | 0.586 | 37 | -13 | 0.16 | 0.26 | 53 | 43 | 17.9 | 4.9 | -12.8 | 49 | 0.885 | 29 | -8.1 | 0.85 | 0.58 | 1.04 | 0.894 | 0.134 | True |  |  |  |
| Q3 | Pre-run 20, net of NIFTY | PE | -5 to +5 % | 175 | 124 | -1.8 | 10.7 | -22.8 | 34 | -1.279 | 20 | -15.6 | 0.13 | 0.39 | 192 | 111 | 7.3 | 6.7 | -16.3 | 40 | 0.07 | 18 | -13 | 0.59 | 0.68 | -0.855 | -1.242 | -0.641 | True |  |  |  |
| Q3 | Pre-run 20, net of NIFTY | PE | rose > 5 % | 91 | 72 | 9.5 | 1.3 | -21.1 | 36 | 0.746 | 22 | -10.7 | 0.51 | 0.13 | 77 | 56 | -1.1 | 9.6 | -15.6 | 36 | -0.886 | 24 | -14 | 0.56 | 0.65 | -0.099 | 0.634 | 0.469 | True |  |  |  |
| Q3 | Pre-run 20, net of NIFTY | CE | fell > 5 % | 40 | 33 | 7.7 | 1.9 | -5.5 | 40 | 0.421 | 27 | -8.8 | 1.58 | 0.27 | 30 | 27 | -4.7 | 3.8 | -22 | 37 | -0.715 | 24 | -15.6 | 0.7 | 0.7 | -0.208 | 1.481 | 1.236 | True |  |  |  |
| Q3 | Pre-run 20, net of NIFTY | CE | -5 to +5 % | 59 | 53 | -0.9 | 9 | -14.7 | 37 | -0.715 | 28 | -14.2 | 0.32 | 1.16 | 64 | 51 | 2 | 1 | -22.8 | 38 | 0.082 | 25 | -18.6 | 0.7 | 0.7 | -0.448 | -0.658 | -0.821 | True |  |  |  |
| Q3 | Pre-run 20, net of NIFTY | CE | rose > 5 % | 16 | 16 | 12.3 | 2.6 | -5.7 | 50 | 0.499 | 39 | -18.5 | 0.09 | 0.83 | 18 | 17 | 10.4 | -0.1 | -26.6 | 44 | 0.479 | 44 | -19.1 | 0.7 | 0.7 | 0.692 | -0.781 | -0.598 | False |  |  |  |
| Q3 | Pre-run 5, net of NIFTY | PE | fell > 3 % | 43 | 35 | 2.4 | 4.1 | -12.7 | 40 | -0.114 | 30 | -12.2 | 0.46 | 0.22 | 41 | 37 | 16 | 5.8 | -1.8 | 49 | 0.826 | 25 | -10.7 | 0.77 | 0.6 | 0.503 | 0.587 | 0.431 | True |  |  |  |
| Q3 | Pre-run 5, net of NIFTY | PE | -3 to +3 % | 201 | 136 | 9.8 | -6.9 | -22.8 | 35 | 1.621 | 21 | -13.4 | 0.25 | 0.26 | 211 | 112 | 2.5 | 15.7 | -16.4 | 41 | -1.003 | 26 | -13.6 | 0.53 | 0.81 | 0.437 | -0.303 | -0.447 | True |  |  |  |
| Q3 | Pre-run 5, net of NIFTY | PE | rose > 3 % | 67 | 51 | -12.9 | 8.5 | -26 | 33 | -2.443 | 18 | -16.3 | 0.13 | 0.29 | 70 | 58 | 15.5 | 4.7 | -16.4 | 34 | 0.751 | 29 | -10.1 | 0.83 | 0.57 | -1.196 | -0.348 | 0.126 | True |  |  |  |
| Q3 | Pre-run 5, net of NIFTY | CE | fell > 3 % | 31 | 26 | -4.7 | 3.3 | -20.7 | 32 | -0.497 | 32 | -15.6 | 0.7 | 0.64 | 21 | 20 | -0.9 | 2.1 | -17 | 33 | -0.179 | 33 | -19.1 | 0.5 | 0.75 | -0.478 | -0.47 | -0.162 | False |  |  |  |
| Q3 | Pre-run 5, net of NIFTY | CE | -3 to +3 % | 67 | 64 | 2.3 | -0.7 | -10.3 | 43 | 0.21 | 28 | -12.7 | 0.71 | 0.58 | 74 | 56 | 7.8 | -10.5 | -17.5 | 43 | 1.271 | 29 | -15.8 | 1.06 | 0.01 | 1.047 | 1.331 | 1.271 | True |  |  |  |
| Q3 | Pre-run 5, net of NIFTY | CE | rose > 3 % | 14 | 14 | 8.3 | 0.1 | -7.4 | 36 | 0.427 | 39 | -16.1 | 0.31 | 0.71 | 17 | 16 | -22.5 | 5.9 | -45.4 | 24 | -1.578 | 36 | -25.4 | -0.61 | 0.94 | -0.814 | -1.272 | -1.647 | False |  |  |  |
| Q3 | Day-0 gap at the open | PE | gap down <= -2 % | 7 | 7 | -2.9 | 3.7 | -21.3 | 43 | -0.308 | 43 | -27.3 | 0.19 | 0.24 | 23 | 21 | 14.1 | 6.5 | 5.9 | 57 | 0.51 | 30 | -12 | 1.38 | 0.57 | 0.143 | -1.027 | 0.802 | False |  |  |  |
| Q3 | Day-0 gap at the open | PE | -2 to +2 % | 224 | 142 | 1.5 | 8.5 | -21.4 | 35 | -0.552 | 25 | -12.5 | 0.18 | 0.4 | 226 | 118 | 9.8 | 0.7 | -8.9 | 43 | 0.811 | 22 | -11.4 | 0.85 | 0.1 | 0.183 | 1.679 | 0.899 | True |  |  |  |
| Q3 | Day-0 gap at the open | PE | gap up >= +2 % | 82 | 63 | 9.5 | 1.4 | -25.8 | 37 | 0.604 | 27 | -16.1 | 0.42 | 0.18 | 73 | 56 | -3.6 | 10.2 | -33.2 | 27 | -1.017 | 27 | -15.9 | -0.3 | 0.9 | -0.292 | -1.441 | -1.344 | True |  |  |  |
| Q3 | Day-0 gap at the open | CE | gap down <= -2 % | 40 | 35 | -4.6 | 8.5 | -18.6 | 40 | -0.926 | 28 | -14.4 | 1.06 | 0.55 | 43 | 34 | 6.6 | -1.6 | -31.4 | 35 | 0.475 | 35 | -19.1 | 0.83 | 0.63 | -0.319 | -0.652 | 0.622 | True |  |  |  |
| Q3 | Day-0 gap at the open | CE | -2 to +2 % | 71 | 64 | 7.5 | -1.8 | -10.3 | 39 | 0.675 | 28 | -11.7 | 0.43 | 1.2 | 60 | 49 | -4 | 7.9 | -17.2 | 40 | -0.742 | 32 | -16.4 | 0.62 | 0.8 | -0.047 | 0.951 | -0.847 | True |  |  |  |
| Q3 | Day-0 gap at the open | CE | gap up >= +2 % | 4 | 4 | 26.3 | 3.2 | 2.4 | 50 | 0.652 | 71 | -20.9 | 2.63 | 0.66 | 9 | 8 | 14.2 | 0.4 | -6.1 | 44 | 0.498 | 55 | -22.2 | 0.68 | 0.7 | 0.813 | -0.957 | 0.771 | False |  |  |  |
| Q3 | Place in 52-week range | PE | near the low | 29 | 27 | -9.5 | 5.5 | -32.3 | 21 | -0.712 | 42 | -17.6 | -0.63 | 0.34 | 62 | 51 | -0.4 | 7.6 | -13.4 | 44 | -0.827 | 19 | -12.6 | 0.57 | 0.65 | -1.088 | -0.619 | -1.278 | False |  |  |  |
| Q3 | Place in 52-week range | PE | middle | 88 | 68 | -1.2 | 6.2 | -22 | 35 | -0.664 | 22 | -14.2 | 0.05 | 0.33 | 106 | 72 | 13.3 | 2.4 | -15.9 | 42 | 1.081 | 20 | -8.4 | 0.88 | 0.51 | 0.295 | 0.979 | 0.189 | True |  |  |  |
| Q3 | Place in 52-week range | PE | near the high | 192 | 115 | 8.5 | -3.3 | -18.2 | 39 | 1.043 | 23 | -13.1 | 0.47 | -0.12 | 148 | 96 | 3.6 | 8.2 | -16.6 | 39 | -0.547 | 17 | -15.2 | 0.48 | 0.76 | 0.351 | -0.735 | 0.566 | True |  |  |  |
| Q3 | Place in 52-week range | CE | near the low | 43 | 39 | 11.6 | -0.4 | -2.9 | 49 | 0.845 | 29 | -6.8 | 1.08 | 0.51 | 45 | 41 | -2.1 | 0.2 | -27.1 | 38 | -0.161 | 29 | -15.7 | 0.77 | 0.32 | 0.484 | 2.128 | 0.974 | True |  |  |  |
| Q3 | Place in 52-week range | CE | middle | 28 | 27 | -10.5 | 8.9 | -13.5 | 36 | -1.607 | 24 | -14.1 | 0.6 | 0.77 | 33 | 29 | -4.3 | 0.8 | -17.6 | 39 | -0.378 | 27 | -25.8 | -0.11 | 0.82 | -1.404 | -1.817 | -1.07 | False |  |  |  |
| Q3 | Place in 52-week range | CE | near the high | 43 | 39 | 6.2 | 2.9 | -19.3 | 35 | 0.232 | 28 | -18.1 | 0.46 | 0.89 | 23 | 23 | 6.6 | -3.1 | -30.2 | 35 | 0.465 | 42 | -13.3 | 0.93 | 0.39 | 0.493 | -0.425 | 0.064 | False |  |  |  |
| Q4 | NP YoY (puts) | PE | 10-25 % | 104 | 82 | -12.3 | 11.2 | -27.9 | 27 | -2.387 | 20 | -21.1 | -0.29 | 0.5 | 116 | 83 | -8.2 | 15.6 | -17.5 | 39 | -2.586 | 18 | -14.5 | 0.1 | 0.92 | -3.516 | -3.345 | -3.085 | True | consistent |  | consistent |
| Q4 | NP YoY (puts) | PE | 25-50 % | 91 | 71 | 10.1 | 0.8 | -16.3 | 35 | 0.689 | 27 | -11.2 | 0.24 | 0.25 | 79 | 61 | 3.8 | 8.1 | -8.8 | 39 | -0.481 | 18 | -10.9 | 0.41 | 0.7 | 0.147 | 1.111 | -0.567 | True |  |  |  |
| Q4 | NP YoY (puts) | PE | 50-100 % | 76 | 62 | 8.7 | 1.8 | -9.2 | 43 | 0.565 | 25 | -9.5 | 0.59 | 0.13 | 75 | 60 | 18.3 | 3.6 | -21.3 | 44 | 1.247 | 24 | -9.4 | 0.98 | 0.52 | 1.281 | 2.06 | 1.575 | True |  |  |  |
| Q4 | NP YoY (puts) | PE | > 100 % | 44 | 40 | 17.7 | 1.1 | -20.1 | 41 | 0.874 | 38 | -9.2 | 0.9 | 0.14 | 52 | 41 | 29.8 | 2.7 | -10 | 42 | 1.601 | 34 | -14.8 | 1.61 | 0.44 | 1.75 | 0.518 | 2.452 | True |  |  | consistent |
| Q4 | NP QoQ (puts) | PE | 0-10 % | 111 | 86 | 2.6 | 3.9 | -23.5 | 37 | -0.129 | 20 | -13 | 0.33 | 0.2 | 96 | 72 | 2.5 | 9 | -9.9 | 42 | -0.697 | 19 | -13.1 | 0.31 | 0.76 | -0.584 | 0.066 | -0.603 | True |  |  |  |
| Q4 | NP QoQ (puts) | PE | 10-30 % | 95 | 81 | 6.4 | 2.2 | -16.1 | 37 | 0.352 | 24 | -12.4 | 0.35 | 0.2 | 114 | 86 | -3.3 | 12.7 | -20.7 | 38 | -1.709 | 19 | -13.1 | 0.56 | 0.66 | -0.96 | 0.238 | 0.037 | True |  |  |  |
| Q4 | NP QoQ (puts) | PE | > 30 % | 109 | 82 | 1.7 | 4.4 | -27.1 | 32 | -0.239 | 22 | -15.9 | 0.06 | 0.34 | 112 | 73 | 21.5 | -0.7 | -11 | 43 | 1.654 | 27 | -11.3 | 0.96 | 0.45 | 1.001 | -0.389 | 0.345 | True |  |  |  |
| Q4 | Revenue YoY (puts) | PE | 0-10 % | 72 | 59 | -7.6 | 6.7 | -27.5 | 32 | -1.441 | 20 | -15.2 | 0.28 | 0.23 | 66 | 60 | 2.2 | 8.3 | -7.9 | 41 | -0.621 | 20 | -9.4 | 0.56 | 0.64 | -1.458 | 0.357 | -0.081 | True |  |  |  |
| Q4 | Revenue YoY (puts) | PE | 10-20 % | 83 | 70 | -3.6 | 6 | -25.7 | 34 | -0.943 | 20 | -16 | 0.21 | 0.25 | 113 | 76 | 6.5 | 7.4 | -17.3 | 41 | -0.08 | 21 | -11.9 | 0.29 | 0.81 | -0.723 | -0.544 | -0.995 | True |  |  |  |
| Q4 | Revenue YoY (puts) | PE | > 20 % | 160 | 117 | 12.1 | -5.5 | -15.6 | 38 | 1.943 | 18 | -12 | 0.24 | 0.25 | 143 | 92 | 9.7 | 4.9 | -16.3 | 41 | 0.451 | 21 | -14.3 | 0.92 | 0.39 | 1.693 | 0.23 | 0.957 | True |  |  |  |
| Q4 | NP YoY (calls) | CE | < -50 % | 46 | 41 | 21.2 | -7.5 | -1.8 | 50 | 2.089 | 28 | -7.8 | 1.35 | 0.31 | 31 | 26 | 6.5 | -0.4 | -30.2 | 32 | 0.344 | 40 | -21.1 | 0.98 | 0.6 | 1.72 | 0.743 | 1.447 | True |  |  |  |
| Q4 | NP YoY (calls) | CE | -25 to -50 % | 39 | 39 | -12.8 | 12.6 | -28.6 | 33 | -2.11 | 24 | -15.3 | 0.15 | 1.02 | 42 | 37 | -3.5 | 4.6 | -17.9 | 40 | -0.562 | 29 | -19.4 | 0.41 | 0.88 | -1.889 | -0.929 | -1.324 | True |  |  |  |
| Q4 | NP YoY (calls) | CE | -10 to -25 % | 30 | 28 | -0.6 | 5.6 | -7.9 | 33 | -0.515 | 24 | -17.7 | 0.52 | 0.8 | 39 | 35 | 3 | 0.8 | -27.1 | 41 | 0.139 | 32 | -13.7 | 0.8 | 0.65 | -0.266 | -0.071 | -0.197 | True |  |  |  |
| Q4 | NP QoQ (calls) | CE | < -30 % | 66 | 57 | 1.6 | 7.1 | -13.3 | 39 | -0.439 | 25 | -11.3 | 0.62 | 0.87 | 55 | 46 | -0.9 | 3.9 | -30.6 | 35 | -0.314 | 31 | -21 | 0.49 | 0.91 | -0.532 | -0.294 | -0.712 | True |  |  |  |
| Q4 | NP QoQ (calls) | CE | -10 to -30 % | 35 | 31 | 6.7 | 2.7 | -3.8 | 40 | 0.284 | 28 | -14.5 | 0.96 | 0.63 | 38 | 34 | 11.3 | -3.5 | -15.7 | 45 | 0.928 | 32 | -12.2 | 1.1 | 0.5 | 0.857 | 0.934 | 0.912 | True |  |  |  |
| Q4 | NP QoQ (calls) | CE | 0 to -10 % | 14 | 14 | 8.1 | 3.4 | -10.7 | 43 | 0.281 | 34 | -16.6 | 0.66 | 0.74 | 19 | 19 | -11 | 4.1 | -27.1 | 37 | -0.823 | 37 | -20.3 | 0.53 | 0.74 | -0.383 | -1.013 | -0.269 | False |  |  |  |
| Q4 | Revenue YoY (calls) | CE | < 0 % | 35 | 35 | 9.5 | 1.5 | -15.2 | 40 | 0.526 | 30 | -11.5 | 1.3 | 0.48 | 42 | 36 | 27.4 | -14 | 8.2 | 52 | 2.532 | 33 | -12.1 | 1.85 | 0.02 | 2.162 | 1.599 | 2.708 | True |  |  | consistent |
| Q4 | Revenue YoY (calls) | CE | 0-10 % | 39 | 36 | -7.9 | 10 | -7.1 | 36 | -1.601 | 22 | -20.2 | 0.67 | 0.76 | 35 | 33 | -3.7 | 3.9 | -17.6 | 37 | -0.503 | 30 | -17.8 | 0.24 | 0.91 | -1.488 | -1.764 | -0.839 | True |  |  |  |
| Q4 | Revenue YoY (calls) | CE | > 10 % | 41 | 38 | 10.5 | 0.3 | -10.3 | 44 | 0.702 | 29 | -7.2 | 0.29 | 0.97 | 35 | 30 | -24.3 | 13.3 | -35 | 23 | -3.08 | 24 | -24.9 | -0.2 | 1.11 | -1.681 | -0.517 | -2.063 | True |  |  |  |
| Q7 | EPS YoY (puts) | PE | 10-25 % | 103 | 80 | -7 | 8.8 | -27.3 | 29 | -1.647 | 19 | -19.7 | -0.07 | 0.4 | 98 | 71 | -9.8 | 14.7 | -22.2 | 37 | -2.747 | 18 | -15.1 | 0.09 | 0.88 | -3.107 | -3.017 | -2.656 | True | consistent |  | consistent |
| Q7 | EPS YoY (puts) | PE | 25-50 % | 87 | 68 | -1.4 | 5.6 | -28.8 | 31 | -0.625 | 22 | -11.8 | 0.04 | 0.32 | 71 | 56 | 7.4 | 7.1 | -7.3 | 41 | 0.029 | 18 | -11.8 | 0.39 | 0.71 | -0.421 | 0.661 | -1.111 | True |  |  |  |
| Q7 | EPS YoY (puts) | PE | > 50 % | 106 | 83 | 12.7 | -1 | -8.4 | 44 | 1.175 | 23 | -9.2 | 0.57 | 0.08 | 105 | 68 | 17.2 | 2.3 | -16.8 | 40 | 1.174 | 25 | -12.7 | 1.12 | 0.4 | 1.661 | 1.696 | 2.068 | True |  |  | consistent |
| Q7 | EPS YoY (calls) | CE | < -50 % | 46 | 40 | 20.8 | -7.3 | -1.8 | 50 | 2.053 | 27 | -8 | 1.37 | 0.3 | 37 | 30 | 6.1 | -0.7 | -30.2 | 38 | 0.384 | 36 | -19.1 | 0.7 | 0.71 | 1.723 | 0.986 | 1.15 | True |  |  |  |
| Q7 | EPS YoY (calls) | CE | -25 to -50 % | 37 | 37 | -11.1 | 11.1 | -27.5 | 32 | -1.827 | 24 | -16 | 0.1 | 1.02 | 37 | 33 | -5.1 | 4.8 | -19.5 | 38 | -0.666 | 30 | -20.7 | 0.48 | 0.81 | -1.763 | -1.348 | -1.175 | True |  |  |  |
| Q7 | EPS YoY (calls) | CE | -10 to -25 % | 27 | 26 | -1.7 | 5.7 | -4.5 | 33 | -0.576 | 26 | -18.1 | 0.51 | 0.79 | 34 | 31 | 7.3 | -1 | -21.3 | 41 | 0.507 | 33 | -13.4 | 1.11 | 0.53 | -0.049 | -0.06 | 0.342 | False |  |  |  |
| Q7 | EPS QoQ (puts) | PE | 0-10 % | 105 | 82 | 6.7 | 1.9 | -18.1 | 39 | 0.463 | 21 | -12.5 | 0.4 | 0.17 | 88 | 66 | 7.1 | 7.1 | -7.1 | 43 | 0.001 | 12 | -12.5 | 0.38 | 0.72 | 0.328 | 0.415 | -0.171 | True |  |  |  |
| Q7 | EPS QoQ (puts) | PE | 10-30 % | 97 | 79 | -3.4 | 6.5 | -21.3 | 35 | -0.861 | 23 | -13.5 | 0.07 | 0.32 | 105 | 80 | -8.6 | 14.6 | -21.3 | 36 | -2.476 | 19 | -13.5 | 0.38 | 0.74 | -2.36 | -0.243 | -1.09 | True |  |  |  |
| Q7 | EPS QoQ (puts) | PE | > 30 % | 102 | 80 | 3.4 | 3.5 | -25.2 | 32 | -0.009 | 23 | -15.7 | 0.11 | 0.31 | 111 | 73 | 19.6 | 0.5 | -13 | 42 | 1.457 | 26 | -11.9 | 0.81 | 0.53 | 1.024 | -0.476 | 0.141 | True |  |  |  |
| Q7 | EPS QoQ (calls) | CE | < -30 % | 62 | 54 | 2.7 | 5.8 | -13.3 | 40 | -0.25 | 25 | -11.3 | 0.64 | 0.82 | 55 | 49 | 1.8 | 3.3 | -30.2 | 38 | -0.094 | 31 | -19.7 | 0.57 | 0.99 | -0.243 | -0.21 | -0.662 | True |  |  |  |
| Q7 | EPS QoQ (calls) | CE | -10 to -30 % | 35 | 31 | 9 | 1.9 | -3.1 | 43 | 0.511 | 28 | -13.2 | 1.14 | 0.53 | 34 | 32 | 11.7 | -1.5 | -16 | 44 | 0.781 | 34 | -12.3 | 1.25 | 0.57 | 0.914 | 0.967 | 1.213 | True |  |  |  |
| Q7 | EPS QoQ (calls) | CE | 0 to -10 % | 14 | 14 | 8.2 | 3.5 | -10.7 | 43 | 0.278 | 34 | -16.2 | 0.59 | 0.74 | 19 | 19 | -8.1 | 4.8 | -17 | 37 | -0.721 | 36 | -19 | 0.67 | 0.8 | -0.313 | -0.887 | -0.275 | False |  |  |  |
| Q7 | Volume ratio day -1 | PE | < 1x | 140 | 99 | 18.3 | -8.5 | -15.7 | 38 | 2.254 | 24 | -12.8 | 0.53 | 0.02 | 163 | 99 | 4.8 | 9.4 | -17.1 | 40 | -0.45 | 21 | -13 | 0.55 | 0.7 | 1.276 | 0.203 | 0.717 | True |  |  |  |
| Q7 | Volume ratio day -1 | PE | 1-2x | 145 | 99 | -5.6 | 11.2 | -25.1 | 34 | -1.578 | 21 | -14.1 | 0.16 | 0.32 | 139 | 89 | 9.4 | 5.3 | -13.9 | 41 | 0.377 | 22 | -12.6 | 0.67 | 0.59 | -0.849 | -0.161 | -0.165 | True |  |  |  |
| Q7 | Volume ratio day -1 | PE | > 2x | 29 | 28 | -23 | 6.2 | -30 | 31 | -2.726 | 21 | -17.4 | -0.69 | 0.34 | 20 | 18 | 9.5 | 6.9 | -13.5 | 40 | 0.134 | 39 | -7.6 | 0.93 | 0.61 | -1.833 | -0.097 | -0.563 | False |  |  |  |
| Q7 | Volume ratio day -1 | CE | < 1x | 48 | 43 | 7.2 | 1.6 | -8 | 44 | 0.435 | 26 | -10.8 | 0.74 | 0.72 | 61 | 50 | 3.3 | -0.5 | -17 | 43 | 0.266 | 28 | -16.8 | 0.91 | 0.46 | 0.496 | 0.894 | 0.483 | True |  |  |  |
| Q7 | Volume ratio day -1 | CE | 1-2x | 57 | 53 | 2.6 | 5.3 | -10.3 | 37 | -0.224 | 24 | -13.8 | 0.62 | 0.84 | 45 | 37 | -4.1 | 5.3 | -29.8 | 33 | -0.622 | 30 | -18.7 | 0.45 | 0.87 | -0.598 | -0.468 | -0.665 | True |  |  |  |
| Q7 | Volume ratio day -1 | CE | > 2x | 10 | 9 | -4.1 | 4.7 | -29.6 | 40 | -0.454 | 39 | -18 | 1.29 | 0.67 | 6 | 6 | 26.1 | 0.2 | -34 | 33 | 0.498 | 104 | -23.2 | 0.57 | 0.71 | 0.031 | -1.1 | 0.462 | False |  |  |  |
| Q7 | Futures OI 5-session change | PE | <= -5 % | 57 | 39 | -5.7 | 5.5 | -23.9 | 23 | -1.008 | 22 | -13.5 | -0.17 | 0.33 | 55 | 40 | 1.1 | 7.7 | -23.6 | 40 | -0.643 | 21 | -12.8 | 0.34 | 0.66 | -1.167 | -0.013 | -1.225 | True |  |  |  |
| Q7 | Futures OI 5-session change | PE | -5 to +5 % | 126 | 91 | 10.4 | -1.2 | -17.1 | 40 | 1.099 | 21 | -12.4 | 0.29 | 0.21 | 142 | 94 | 9.7 | 4 | -13.4 | 41 | 0.563 | 20 | -11.3 | 0.7 | 0.53 | 1.175 | 1.015 | 0.498 | True |  |  |  |
| Q7 | Futures OI 5-session change | PE | > +5 % | 132 | 98 | 0.8 | 5.4 | -24.4 | 36 | -0.447 | 21 | -15.3 | 0.38 | 0.15 | 124 | 78 | 5.4 | 7.3 | -16.8 | 40 | -0.191 | 20 | -13.7 | 0.62 | 0.6 | -0.451 | -1.084 | 0.49 | True |  |  |  |
| Q7 | Futures OI 5-session change | CE | <= -5 % | 17 | 16 | 1.6 | 4.4 | -7.1 | 41 | -0.165 | 33 | -19 | 0.56 | 0.76 | 26 | 22 | 3.1 | 1.1 | -33 | 35 | 0.106 | 38 | -23 | -0.12 | 0.95 | -0.042 | -1.788 | -1.114 | False |  |  |  |
| Q7 | Futures OI 5-session change | CE | -5 to +5 % | 55 | 48 | 17.1 | -8.1 | -4.5 | 47 | 2.057 | 25 | -7.2 | 1.26 | 0.24 | 49 | 40 | -14.6 | 14.1 | -26.1 | 39 | -2.096 | 27 | -22.8 | 0.12 | 1.16 | -0.028 | 0.043 | -0.074 | True |  |  |  |
| Q7 | Futures OI 5-session change | CE | > +5 % | 43 | 39 | -12 | 13.5 | -20.7 | 30 | -2.018 | 25 | -17.4 | 0.12 | 1.09 | 37 | 30 | 21.9 | -8.5 | -17.5 | 41 | 1.627 | 37 | -7.8 | 2.05 | 0.04 | -0.276 | 0.902 | 1.269 | True |  |  |  |
| Q7 | Strike distance (% OTM) | PE | < 2 % | 72 | 56 | -3.3 | 5.5 | -34 | 33 | -0.673 | 26 | -19.7 | -0.33 | 0.41 | 78 | 59 | -7.6 | 11.7 | -32.5 | 29 | -1.974 | 20 | -12.6 | -0.41 | 0.96 | -1.872 | -1.235 | -4.112 | True |  |  | STRONG |
| Q7 | Strike distance (% OTM) | PE | 2-5 % | 102 | 79 | 5.3 | 2.6 | -15.1 | 37 | 0.285 | 19 | -10.7 | 0.12 | 0.3 | 119 | 82 | 6 | 7.7 | -16.3 | 44 | -0.199 | 16 | -11.6 | 0.56 | 0.66 | 0.061 | 1.268 | -0.561 | True |  |  |  |
| Q7 | Strike distance (% OTM) | PE | > 5 % | 141 | 92 | 5.6 | 1.7 | -25.2 | 35 | 0.372 | 21 | -13.2 | 0.63 | -0.07 | 125 | 80 | 17.2 | 0.6 | -8.5 | 45 | 1.478 | 22 | -13.1 | 1.33 | 0.18 | 1.308 | -0.017 | 3.174 | True |  |  | consistent |
| Q7 | Strike distance (% OTM) | CE | < 2 % | 28 | 26 | -11.3 | 8.8 | -13.2 | 46 | -1.317 | 31 | -16 | -1.19 | 1.34 | 28 | 22 | -2.7 | 3 | -37.2 | 32 | -0.273 | 42 | -23.2 | 0.45 | 0.79 | -1.124 | -1.339 | -2.377 | False |  |  |  |
| Q7 | Strike distance (% OTM) | CE | 2-5 % | 35 | 34 | 5.9 | 3.1 | -10.3 | 37 | 0.186 | 30 | -15.2 | 0.48 | 0.84 | 36 | 35 | 7.6 | -1.3 | -3.1 | 44 | 0.58 | 31 | -14.2 | 0.69 | 0.71 | 0.542 | 0.346 | -0.401 | True |  |  |  |
| Q7 | Strike distance (% OTM) | CE | > 5 % | 52 | 44 | 10.8 | -1.7 | -11.4 | 38 | 1.062 | 24 | -9.9 | 1.92 | -0.26 | 48 | 38 | -0.5 | 3.1 | -20.7 | 38 | -0.244 | 29 | -17.6 | 0.86 | 0.59 | 0.578 | 0.952 | 2.72 | True |  |  |  |
| Q7 | Sessions to expiry | PE | <= 5 | 62 | 31 | 32.6 | -3.7 | -13.8 | 47 | 2.072 | 35 | -15.6 | 0.94 | 0.07 | 56 | 27 | 21.2 | 4.1 | -33.2 | 38 | 0.804 | 43 | -12.4 | 1 | 0.55 | 2.034 | -0.353 | 1.776 | True |  |  |  |
| Q7 | Sessions to expiry | PE | 6-15 | 130 | 74 | -4.2 | 8.8 | -26.1 | 31 | -1.276 | 20 | -14.9 | 0.21 | 0.27 | 169 | 72 | 5.5 | 8.8 | -16.4 | 43 | -0.295 | 22 | -13.8 | 0.58 | 0.67 | -1.111 | -0.998 | -0.255 | True |  |  |  |
| Q7 | Sessions to expiry | PE | > 15 | 123 | 65 | -3.1 | 7.7 | -16.3 | 34 | -1.128 | 19 | -11.8 | -0.07 | 0.45 | 97 | 38 | 1.6 | 9.4 | -13 | 39 | -0.764 | 20 | -10.2 | 0.48 | 0.69 | -1.338 | 1.428 | -1.248 | True |  |  |  |
| Q7 | Sessions to expiry | CE | <= 5 | 21 | 15 | -1 | 5.1 | -34.7 | 33 | -0.33 | 37 | -20.5 | -0.16 | 0.93 | 12 | 8 | 0.2 | 1.7 | 12.3 | 50 | -0.082 | 38 | -23.7 | 1.17 | 0.65 | -0.291 | -1.306 | -0.441 | False |  |  |  |
| Q7 | Sessions to expiry | CE | 6-15 | 42 | 37 | -0.2 | 6.3 | -17.2 | 36 | -0.496 | 26 | -12 | 0.2 | 1.03 | 62 | 44 | 12.6 | -12.1 | -19.2 | 40 | 1.703 | 29 | -14.9 | 1.11 | 0.19 | 0.853 | 1.193 | 0.211 | True |  |  |  |
| Q7 | Sessions to expiry | CE | > 15 | 52 | 40 | 9.3 | -0.5 | -3.6 | 46 | 0.821 | 24 | -10.7 | 1.51 | 0.08 | 38 | 26 | -16 | 10.6 | -29.6 | 32 | -1.955 | 27 | -20.9 | -0.11 | 1.12 | -0.802 | -0.015 | 0.185 | True |  |  |  |
| Q7 | Sector day 0 | PE | down < -0.5 % | 70 | 49 | 26.8 | -2.3 | -2.8 | 49 | 1.965 | 30 | -3.2 | 1.11 | -0.05 | 95 | 53 | 38 | -9.1 | 12.2 | 58 | 3.733 | 25 | -3.4 | 1.72 | -0.04 | 4.029 | 5.291 | 4.649 | True | STRONG |  | STRONG |
| Q7 | Sector day 0 | PE | flat | 108 | 75 | 11.6 | 0.7 | -17.2 | 40 | 0.938 | 23 | -12.3 | 0.88 | -0.16 | 101 | 66 | 2.4 | 8.4 | -16 | 42 | -0.594 | 20 | -12.1 | 1.04 | 0.27 | 0.243 | 0.605 | 3.379 | True |  |  | consistent |
| Q7 | Sector day 0 | PE | up > +0.5 % | 106 | 71 | -16.5 | 17.6 | -35.5 | 25 | -3.406 | 20 | -21.6 | -1 | 0.97 | 95 | 49 | -21.2 | 19.6 | -42.2 | 21 | -3.738 | 22 | -22.2 | -1.19 | 1.37 | -5.052 | -6.384 | -8.048 | True | STRONG |  | STRONG |
| Q7 | Sector day 0 | CE | down < -0.5 % | 32 | 29 | -27.9 | 17.7 | -31.7 | 22 | -3.764 | 24 | -27 | -1.31 | 1.86 | 35 | 26 | -26.1 | 17.1 | -45.4 | 17 | -2.83 | 31 | -29.7 | -1.04 | 1.59 | -4.663 | -5.749 | -5.624 | True | STRONG |  | STRONG |
| Q7 | Sector day 0 | CE | flat | 19 | 18 | -10.8 | 5.8 | -35.7 | 32 | -1.097 | 30 | -16.2 | 0.28 | 0.93 | 34 | 31 | 17.3 | -4.3 | -8.5 | 47 | 1.211 | 36 | -12.5 | 1.28 | 0.44 | 0.081 | 0.43 | 0.292 | False |  |  |  |
| Q7 | Sector day 0 | CE | up > +0.5 % | 45 | 37 | 29.8 | -21.6 | 4.7 | 53 | 3.985 | 26 | -2.1 | 2.53 | -0.72 | 36 | 29 | 17 | -4.7 | 3.6 | 53 | 1.431 | 30 | -7.9 | 1.88 | 0.1 | 3.83 | 4.831 | 5.345 | True | STRONG |  | STRONG |
| Q7 | Filing time | PE | pre-open day 0 | 4 | 4 | -11.9 | 3.7 | -30.4 | 25 | -0.452 | 69 | -33.1 | -2.05 | 0.27 | 1 | 1 | 95.7 | 6.8 | 95.7 | 100 |  |  | 22.8 | 6.29 | 0.61 |  |  |  | False |  |  |  |
| Q7 | Filing time | PE | in session day -1 | 120 | 85 | -0.1 | 5.7 | -19.9 | 33 | -0.586 | 20 | -14.2 | 0.28 | 0.22 | 121 | 76 | 9.1 | 5.8 | -15.6 | 42 | 0.327 | 20 | -8.8 | 0.62 | 0.63 | -0.183 | 0.974 | 0.088 | True |  |  |  |
| Q7 | Filing time | PE | after close day -1 | 164 | 113 | 3.2 | 3.8 | -25.1 | 37 | -0.064 | 19 | -13.7 | 0.1 | 0.4 | 176 | 109 | 7.9 | 6 | -16.6 | 40 | 0.181 | 21 | -14.6 | 0.7 | 0.54 | 0.083 | -0.892 | -0.236 | True |  |  |  |
| Q7 | Filing time | PE | non-session day / earlier | 27 | 24 | 23.5 | 1.6 | -26.3 | 37 | 0.794 | 55 | -9.9 | 1.33 | 0.14 | 24 | 18 | -13 | 8.7 | -13 | 33 | -2.448 | 18 | -16.4 | -0.14 | 0.69 | -1.17 | -0.136 | -0.202 | False |  |  |  |
| Q7 | Filing time | CE | pre-open day 0 | 1 | 1 | 27.1 | 3.8 | 27.1 | 100 |  |  | 21.8 | 3.19 | 0.71 | 1 | 1 | -50.4 | 2 | -50.4 | 0 |  |  | -49 | 0.72 | 0.7 |  |  |  | False |  |  |  |
| Q7 | Filing time | CE | in session day -1 | 45 | 41 | 11.1 | -0.6 | -8.2 | 33 | 0.863 | 27 | -12.8 | 1.01 | 0.55 | 34 | 30 | -1.9 | 3 | -9.1 | 44 | -0.343 | 29 | -17.4 | 0.3 | 0.88 | 0.368 | 0.133 | -0.151 | True |  |  |  |
| Q7 | Filing time | CE | after close day -1 | 61 | 53 | 5.2 | 2.6 | -3.1 | 48 | 0.2 | 26 | -11.6 | 0.75 | 0.7 | 69 | 54 | 3.6 | -1.7 | -26.1 | 36 | 0.36 | 30 | -18.2 | 0.92 | 0.36 | 0.396 | 0.326 | 0.634 | True |  |  |  |
| Q7 | Filing time | CE | non-session day / earlier | 8 | 8 | -48.2 | 7.9 | -38.8 | 12 | -4.139 | 27 | -27.9 | -1.36 | 0.88 | 8 | 7 | 4.9 | 1.3 | -17.2 | 38 | 0.125 | 58 | -13.4 | 0.54 | 0.72 | -2.838 | -0.998 | -1.231 | False |  |  |  |
| Q7 | Reaction before entry | PE | <= -2 % | 23 | 22 | 6.2 | 3.3 | -23.5 | 35 | 0.19 | 30 | -20.6 | 0.92 | 0.19 | 41 | 36 | 15.2 | 5.9 | -1.8 | 49 | 0.594 | 32 | -6.7 | 1.24 | 0.54 | 0.554 | -0.235 | 1.944 | False |  |  |  |
| Q7 | Reaction before entry | PE | -2 to +2 % | 170 | 118 | 0.7 | 6.8 | -26.7 | 34 | -0.547 | 22 | -12.1 | 0.21 | 0.28 | 166 | 105 | 3.9 | 10.5 | -17.1 | 40 | -0.615 | 21 | -14.4 | 0.71 | 0.54 | -0.822 | -0.049 | 0.183 | True |  |  |  |
| Q7 | Reaction before entry | PE | >= +2 % | 120 | 83 | 7 | 1.4 | -17.2 | 38 | 0.532 | 21 | -14.8 | 0.15 | 0.3 | 115 | 77 | 8.7 | 6.1 | -16.2 | 39 | 0.231 | 23 | -11.7 | 0.29 | 0.81 | 0.54 | -0.136 | -1.1 | True |  |  |  |
| Q7 | Reaction before entry | CE | <= -2 % | 50 | 40 | 3.8 | 4.1 | -11.1 | 42 | -0.022 | 25 | -15 | 0.95 | 0.56 | 55 | 44 | 2.6 | 0.6 | -30.6 | 36 | 0.126 | 31 | -19.7 | 0.66 | 0.75 | 0.074 | -1.099 | 0.291 | True |  |  |  |
| Q7 | Reaction before entry | CE | -2 to +2 % | 56 | 52 | 4.3 | 3.7 | -12.5 | 39 | 0.047 | 26 | -11.1 | 0.41 | 1.03 | 43 | 37 | 1.1 | 1.8 | -17.5 | 42 | -0.05 | 30 | -15.7 | 0.8 | 0.64 | -0.002 | 1.037 | -0.455 | True |  |  |  |
| Q7 | Reaction before entry | CE | >= +2 % | 9 | 9 | 2.9 | 4 | -8.2 | 33 | -0.064 | 37 | -12.1 | 1.48 | 0.66 | 14 | 13 | -1 | 1.9 | -22.4 | 36 | -0.138 | 42 | -17.6 | 0.57 | 0.72 | -0.143 | 0.192 | 0.468 | False |  |  |  |

## Q4 · All filings with numbers: the stock's day-0 move by NP YoY / NP QoQ / revenue YoY bin (a fade = good numbers fall, bad numbers rise)

| number | window | bin | filings | dates | reaction before entry, net of NIFTY % | t (before entry) | day-0 open->close, net of NIFTY % | t (day 0) | day 0 up % |
|---|---|---|---|---|---|---|---|---|---|
| NP YoY % | 2022-24 | < -50 | 90 | 70 | -1.9 | -5.058 | 0.98 | 2.82 | 63.3 |
| NP YoY % | 2022-24 | -50 to -25 | 80 | 70 | -1.22 | -3.439 | 0.24 | 0.587 | 55 |
| NP YoY % | 2022-24 | -25 to -10 | 74 | 61 | -1.09 | -3.68 | -0.03 | -0.08 | 47.3 |
| NP YoY % | 2022-24 | -10 to 0 | 71 | 65 | -0.81 | -3.387 | -0.15 | -0.493 | 47.9 |
| NP YoY % | 2022-24 | 0 to 10 | 150 | 112 | -0.29 | -1.28 | 0.05 | 0.258 | 48.7 |
| NP YoY % | 2022-24 | 10 to 25 | 219 | 138 | 0.46 | 2.841 | 0.23 | 1.214 | 48.9 |
| NP YoY % | 2022-24 | 25 to 50 | 193 | 125 | 0.92 | 4.714 | -0.25 | -1.225 | 42 |
| NP YoY % | 2022-24 | 50 to 100 | 141 | 107 | 1.14 | 4.281 | -0.5 | -1.858 | 40.4 |
| NP YoY % | 2022-24 | > 100 | 113 | 86 | 1.7 | 4.523 | -1.06 | -3.405 | 34.5 |
| NP YoY % | 2025-26 | < -50 | 66 | 48 | -2.23 | -5.746 | 0.97 | 2.571 | 66.7 |
| NP YoY % | 2025-26 | -50 to -25 | 69 | 56 | -1.25 | -3.507 | 0.44 | 1.27 | 63.8 |
| NP YoY % | 2025-26 | -25 to -10 | 71 | 52 | -0.98 | -1.948 | 0.53 | 1.617 | 62 |
| NP YoY % | 2025-26 | -10 to 0 | 89 | 66 | -0.64 | -2.306 | -0.14 | -0.48 | 50.6 |
| NP YoY % | 2025-26 | 0 to 10 | 147 | 86 | -0.33 | -1.407 | -0.51 | -2.127 | 37.4 |
| NP YoY % | 2025-26 | 10 to 25 | 214 | 117 | 0.43 | 2.114 | -0.11 | -0.553 | 44.4 |
| NP YoY % | 2025-26 | 25 to 50 | 162 | 102 | 0.98 | 4.931 | -0.38 | -1.383 | 42 |
| NP YoY % | 2025-26 | 50 to 100 | 116 | 81 | 0.92 | 1.52 | -0.78 | -2.728 | 38.8 |
| NP YoY % | 2025-26 | > 100 | 94 | 68 | 1.57 | 5.192 | -1.18 | -3.022 | 37.2 |
| NP QoQ % | 2022-24 | < -30 | 156 | 117 | -1.32 | -4.952 | 0.13 | 0.463 | 52.6 |
| NP QoQ % | 2022-24 | -30 to -10 | 169 | 124 | -0.51 | -2.27 | 0.39 | 1.504 | 55 |
| NP QoQ % | 2022-24 | -10 to 0 | 171 | 122 | -0.62 | -3.073 | 0.02 | 0.107 | 50.9 |
| NP QoQ % | 2022-24 | 0 to 10 | 242 | 151 | 0.27 | 1.621 | -0.19 | -0.993 | 42.6 |
| NP QoQ % | 2022-24 | 10 to 30 | 192 | 138 | 0.99 | 4.932 | -0.26 | -1.168 | 41.7 |
| NP QoQ % | 2022-24 | > 30 | 244 | 142 | 1.43 | 6.214 | -0.21 | -1.091 | 41.4 |
| NP QoQ % | 2025-26 | < -30 | 149 | 89 | -1.39 | -4.382 | 0.13 | 0.494 | 51.7 |
| NP QoQ % | 2025-26 | -30 to -10 | 147 | 95 | -0.36 | -1.604 | -0.06 | -0.233 | 51.7 |
| NP QoQ % | 2025-26 | -10 to 0 | 144 | 91 | 0.03 | 0.136 | -0.41 | -1.823 | 43.8 |
| NP QoQ % | 2025-26 | 0 to 10 | 207 | 114 | 0.11 | 0.513 | -0.21 | -0.895 | 45.9 |
| NP QoQ % | 2025-26 | 10 to 30 | 181 | 109 | 0.39 | 0.959 | -0.21 | -1.039 | 44.2 |
| NP QoQ % | 2025-26 | > 30 | 215 | 105 | 1.09 | 5.296 | -0.64 | -2.512 | 39.5 |
| Revenue YoY % | 2022-24 | < 0 | 163 | 114 | -0.96 | -3.587 | 0.39 | 1.414 | 53.4 |
| Revenue YoY % | 2022-24 | 0 to 10 | 337 | 180 | -0.04 | -0.277 | 0.07 | 0.457 | 49.3 |
| Revenue YoY % | 2022-24 | 10 to 20 | 290 | 163 | 0.27 | 1.575 | -0.12 | -0.755 | 46.2 |
| Revenue YoY % | 2022-24 | > 20 | 386 | 197 | 0.81 | 4.435 | -0.35 | -1.749 | 41.2 |
| Revenue YoY % | 2025-26 | < 0 | 141 | 85 | -1.85 | -3.911 | 0.44 | 1.514 | 61 |
| Revenue YoY % | 2025-26 | 0 to 10 | 324 | 136 | 0.03 | 0.167 | -0.21 | -1.465 | 44.1 |
| Revenue YoY % | 2025-26 | 10 to 20 | 318 | 130 | 0.25 | 1.492 | -0.29 | -1.665 | 44 |
| Revenue YoY % | 2025-26 | > 20 | 285 | 121 | 1.06 | 5.613 | -0.58 | -2.319 | 42.5 |

## Q6 · All results filings of F&O stocks: does day 0 move opposite to the pre-run?

| window | pre-run | reaction | run size | n | dates | mean | median | hit_pct | t | moved opposite % |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-24 | pre5 | day-0 open->close | run < 3 % | 743 | 256 | -0.03 | 0.06 | 50.3 | -0.261 | 50.3 |
| 2022-24 | pre5 | day-0 open->close | run 3-8 % | 490 | 211 | 0.24 | 0.29 | 54.9 | 1.582 | 54.9 |
| 2022-24 | pre5 | day-0 open->close | run > 8 % | 85 | 66 | 0.56 | 0.73 | 60 | 1.097 | 60 |
| 2022-24 | pre5 | close before filing -> day-0 close | run < 3 % | 743 | 256 | -0.21 | 0.08 | 50.7 | -1.328 | 50.7 |
| 2022-24 | pre5 | close before filing -> day-0 close | run 3-8 % | 490 | 211 | -0.02 | -0.01 | 49.6 | -0.108 | 49.6 |
| 2022-24 | pre5 | close before filing -> day-0 close | run > 8 % | 85 | 66 | 0.35 | -0.27 | 48.2 | 0.51 | 48.2 |
| 2022-24 | pre20 | day-0 open->close | run < 3 % | 391 | 196 | 0.12 | 0.07 | 50.9 | 0.764 | 50.9 |
| 2022-24 | pre20 | day-0 open->close | run 3-8 % | 532 | 234 | 0.18 | 0.27 | 53.9 | 1.34 | 53.9 |
| 2022-24 | pre20 | day-0 open->close | run > 8 % | 404 | 190 | 0.19 | 0.37 | 55.2 | 0.984 | 55.2 |
| 2022-24 | pre20 | close before filing -> day-0 close | run < 3 % | 391 | 196 | 0.01 | 0.08 | 50.6 | 0.03 | 50.6 |
| 2022-24 | pre20 | close before filing -> day-0 close | run 3-8 % | 532 | 234 | -0.14 | -0.01 | 49.8 | -0.711 | 49.8 |
| 2022-24 | pre20 | close before filing -> day-0 close | run > 8 % | 404 | 190 | -0.2 | 0.04 | 50.5 | -0.75 | 50.5 |
| 2022-24 | pre5_net | day-0 open->close, net of NIFTY | run < 3 % | 843 | 261 | 0.1 | -0.01 | 49.7 | 0.943 | 49.7 |
| 2022-24 | pre5_net | day-0 open->close, net of NIFTY | run 3-8 % | 435 | 200 | 0.23 | 0.28 | 54.3 | 1.465 | 54.3 |
| 2022-24 | pre5_net | day-0 open->close, net of NIFTY | run > 8 % | 45 | 41 | 0.41 | 0.74 | 62.2 | 0.599 | 62.2 |
| 2022-24 | pre5_net | close before filing -> day-0 close, net of NIFTY | run < 3 % | 843 | 261 | 0.01 | 0.25 | 52.8 | 0.08 | 52.8 |
| 2022-24 | pre5_net | close before filing -> day-0 close, net of NIFTY | run 3-8 % | 435 | 200 | -0.25 | -0.01 | 49.9 | -1.145 | 49.9 |
| 2022-24 | pre5_net | close before filing -> day-0 close, net of NIFTY | run > 8 % | 45 | 41 | -0.41 | -0.68 | 46.7 | -0.397 | 46.7 |
| 2022-24 | pre20_net | day-0 open->close, net of NIFTY | run < 3 % | 477 | 212 | -0.19 | -0.21 | 45.9 | -1.327 | 45.9 |
| 2022-24 | pre20_net | day-0 open->close, net of NIFTY | run 3-8 % | 545 | 231 | 0.19 | 0.23 | 53.9 | 1.476 | 53.9 |
| 2022-24 | pre20_net | day-0 open->close, net of NIFTY | run > 8 % | 306 | 168 | 0.08 | 0.15 | 52.3 | 0.373 | 52.3 |
| 2022-24 | pre20_net | close before filing -> day-0 close, net of NIFTY | run < 3 % | 477 | 212 | -0.49 | -0.48 | 45.5 | -2.226 | 45.5 |
| 2022-24 | pre20_net | close before filing -> day-0 close, net of NIFTY | run 3-8 % | 545 | 231 | -0.19 | 0.21 | 50.8 | -1.067 | 50.8 |
| 2022-24 | pre20_net | close before filing -> day-0 close, net of NIFTY | run > 8 % | 306 | 168 | -0.42 | -0.2 | 48.4 | -1.43 | 48.4 |
| 2025-26 | pre5 | day-0 open->close | run < 3 % | 687 | 159 | 0.02 | 0.06 | 51.1 | 0.148 | 51.1 |
| 2025-26 | pre5 | day-0 open->close | run 3-8 % | 403 | 154 | 0.12 | 0.15 | 52.9 | 0.692 | 52.9 |
| 2025-26 | pre5 | day-0 open->close | run > 8 % | 58 | 48 | 0.66 | 0.16 | 53.4 | 1.008 | 53.4 |
| 2025-26 | pre5 | close before filing -> day-0 close | run < 3 % | 687 | 159 | -0.22 | 0.07 | 50.8 | -1.34 | 50.8 |
| 2025-26 | pre5 | close before filing -> day-0 close | run 3-8 % | 403 | 154 | -0.27 | -0.17 | 48.4 | -1.013 | 48.4 |
| 2025-26 | pre5 | close before filing -> day-0 close | run > 8 % | 58 | 48 | -0.69 | -0.99 | 41.4 | -0.784 | 41.4 |
| 2025-26 | pre20 | day-0 open->close | run < 3 % | 402 | 148 | 0.08 | -0.01 | 49.8 | 0.46 | 49.8 |
| 2025-26 | pre20 | day-0 open->close | run 3-8 % | 437 | 145 | 0.21 | 0.04 | 51.3 | 1.504 | 51.3 |
| 2025-26 | pre20 | day-0 open->close | run > 8 % | 309 | 134 | 0.11 | 0.28 | 56 | 0.426 | 56 |
| 2025-26 | pre20 | close before filing -> day-0 close | run < 3 % | 402 | 148 | 0.11 | -0.03 | 49.5 | 0.5 | 49.5 |
| 2025-26 | pre20 | close before filing -> day-0 close | run 3-8 % | 437 | 145 | 0.05 | 0.03 | 50.3 | 0.212 | 50.3 |
| 2025-26 | pre20 | close before filing -> day-0 close | run > 8 % | 309 | 134 | -0.15 | -0.19 | 48.2 | -0.398 | 48.2 |
| 2025-26 | pre5_net | day-0 open->close, net of NIFTY | run < 3 % | 741 | 167 | -0.25 | -0.09 | 48.6 | -2.149 | 48.6 |
| 2025-26 | pre5_net | day-0 open->close, net of NIFTY | run 3-8 % | 358 | 147 | 0.34 | 0.34 | 55.6 | 2.228 | 55.6 |
| 2025-26 | pre5_net | day-0 open->close, net of NIFTY | run > 8 % | 49 | 41 | 0.62 | 0.75 | 57.1 | 0.86 | 57.1 |
| 2025-26 | pre5_net | close before filing -> day-0 close, net of NIFTY | run < 3 % | 741 | 167 | -0.44 | -0.2 | 48.4 | -2.458 | 48.4 |
| 2025-26 | pre5_net | close before filing -> day-0 close, net of NIFTY | run 3-8 % | 358 | 147 | -0 | -0.16 | 47.5 | -0.025 | 47.5 |
| 2025-26 | pre5_net | close before filing -> day-0 close, net of NIFTY | run > 8 % | 49 | 41 | -0.49 | -0.03 | 49 | -0.484 | 49 |
| 2025-26 | pre20_net | day-0 open->close, net of NIFTY | run < 3 % | 455 | 154 | 0.04 | 0.2 | 53.4 | 0.258 | 53.4 |
| 2025-26 | pre20_net | day-0 open->close, net of NIFTY | run 3-8 % | 440 | 149 | 0.11 | 0.12 | 51.6 | 0.801 | 51.6 |
| 2025-26 | pre20_net | day-0 open->close, net of NIFTY | run > 8 % | 253 | 129 | 0.23 | 0.29 | 53.4 | 0.847 | 53.4 |
| 2025-26 | pre20_net | close before filing -> day-0 close, net of NIFTY | run < 3 % | 455 | 154 | 0.09 | 0.13 | 51.6 | 0.367 | 51.6 |
| 2025-26 | pre20_net | close before filing -> day-0 close, net of NIFTY | run 3-8 % | 440 | 149 | -0.06 | -0.28 | 46.1 | -0.251 | 46.1 |
| 2025-26 | pre20_net | close before filing -> day-0 close, net of NIFTY | run > 8 % | 253 | 129 | -0.15 | -0.27 | 47 | -0.455 | 47 |

## Q5 · The user's example stocks: every fade trade (picked with hindsight: illustrations)

| symbol | day0 | side | filing | np_yoy | np_qoq | rev_yoy | entry | net_pct | peak_pct | dip_pct | loser_class | oc | stock_fade_pct | n_oc | beta | stock_fade_net_beta | pre5 | pre20 | pre20_net | dd52 | gap | pre_entry | n_same_day | won_same_day | reading |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ADANIPORTS | 2022-05-26 | CE | in session day -1 | -21.8 | -30.1 | 6.6 | 6.2 | -15.595 | -0.806 | -40.323 | never up | -1.475 | -1.475 | 0.405 | 1.433 | -2.054 | 0.994 | -12.495 | -7.606 | -18.656 | 0.579 | -5.338 | 3 | 2 | call -16 %; stock moved WITH the numbers (-1.5 % open->close); NIFTY +0.4 % open->close; stock -12.5 % in the 20 sessions before (-19 % from its 52-week high); option peak -1 %, dip -40 %; 2 of 3 fade trades won that day |
| ADANIPORTS | 2023-08-09 | PE | in session day -1 | 94.2 | 85.8 | 34.7 | 9.4 | -16.53 | 20.213 | -28.723 | other | -0.202 | 0.202 | 0.275 | 1.783 | 0.691 | 1.742 | 9.901 | 8.654 | -19.887 | 1.084 | 0.164 | 1 | 0 | put -17 %; stock faded (-0.2 % open->close); NIFTY +0.3 % open->close; stock +9.9 % in the 20 sessions before (-20 % from its 52-week high); option peak +20 %, dip -29 %; 0 of 1 fade trades won that day |
| ADANIPORTS | 2024-02-02 | PE | in session day -1 | 65.2 | 25.4 | 44.6 | 7.9 | -16.117 | 13.924 | -32.911 | other | 2.303 | -2.303 | 0.188 | 1.865 | -1.952 | 6.204 | 11.985 | 11.709 | -1.809 | 1.165 | 2.103 | 4 | 2 | put -16 %; stock moved WITH the numbers (+2.3 % open->close); NIFTY +0.2 % open->close; stock +12.0 % in the 20 sessions before (-2 % from its 52-week high); option peak +14 %, dip -33 %; 2 of 4 fade trades won that day |
| ADANIPORTS | 2024-08-02 | PE | in session day -1 | 46.6 | 54.2 | 21 | 17.05 | -35.092 | 34.018 | -42.229 | round trip | 0.51 | -0.51 | -0.288 | 1.661 | -0.987 | 5.731 | 6.445 | 3.015 |  | -0.641 | 0.64 | 3 | 1 | put -35 %; stock moved WITH the numbers (+0.5 % open->close); NIFTY -0.3 % open->close; stock +6.4 % in the 20 sessions before (+nan % from its 52-week high); option peak +34 %, dip -42 %; 1 of 3 fade trades won that day |
| ADANIPORTS | 2025-01-31 | PE | in session day -1 | 14 | 4.4 | 15.1 | 18.85 | -38.769 | 1.857 | -46.684 | never up | 1.323 | -1.323 | 0.908 | 1.784 | 0.298 | -0.481 | -9.99 | -7.548 |  | 0.738 | -1.089 | 8 | 2 | put -39 %; stock moved WITH the numbers (+1.3 % open->close); NIFTY +0.9 % open->close; stock -10.0 % in the 20 sessions before (+nan % from its 52-week high); option peak +2 %, dip -47 %; 2 of 8 fade trades won that day |
| ADANIPORTS | 2026-07-30 | PE | in session day -1 | 10.2 | 10.3 | 18.6 | 9.05 | 110.212 | 143.646 | -25.967 | winner | -3.625 | 3.625 | 0.279 | 1.482 | 4.038 | -3.888 | -1.961 | -2.462 | -6.155 | 0.407 | -2.705 | 5 | 1 | put +110 %; stock faded (-3.6 % open->close); NIFTY +0.3 % open->close; stock -2.0 % in the 20 sessions before (-6 % from its 52-week high); option peak +144 %, dip -26 %; 1 of 5 fade trades won that day |
| BAJFINANCE | 2022-01-19 | PE | after close day -1 | 85.5 | 43.5 | 28.2 | 55.65 | 82.576 | 203.324 | -53.279 | winner | -3.548 | 3.548 | -1.052 | 1.384 | 2.091 | 0.965 | 17.735 | 9.732 | -3.801 | 1.369 | 1.369 | 1 | 1 | put +83 %; stock faded (-3.5 % open->close); NIFTY -1.1 % open->close; stock +17.7 % in the 20 sessions before (-4 % from its 52-week high); option peak +203 %, dip -53 %; 1 of 1 fade trades won that day |
| BAJFINANCE | 2022-04-27 | PE | after close day -1 | 79.7 | 13.8 | 25.9 | 63.1 | 102.471 | 129.556 | -0.079 | winner | -5.437 | 5.437 | -0.205 | 1.37 | 5.156 | -0.262 | 3.829 | 3.55 | -10.056 | -1.94 | -1.94 | 1 | 1 | put +102 %; stock faded (-5.4 % open->close); NIFTY -0.2 % open->close; stock +3.8 % in the 20 sessions before (-10 % from its 52-week high); option peak +130 %, dip -0 %; 1 of 1 fade trades won that day |
| BAJFINANCE | 2023-01-30 | PE | after close day -1 | 39.9 | 6.9 | 26.4 | 47.35 | -65.742 | 6.547 | -64.625 | never up | 4.359 | -4.359 | 0.61 | 1.367 | -3.525 | -4.183 | -11.519 | -8.294 | -25.932 | 0.156 | 0.156 | 1 | 0 | put -66 %; stock moved WITH the numbers (+4.4 % open->close); NIFTY +0.6 % open->close; stock -11.5 % in the 20 sessions before (-26 % from its 52-week high); option peak +7 %, dip -65 %; 0 of 1 fade trades won that day |
| BAJFINANCE | 2023-04-27 | PE | after close day -1 | 30.5 | 6.2 | 31.7 | 32 | -15.151 | 4.375 | -18.75 | never up | 2.058 | -2.058 | 0.572 | 1.395 | -1.259 | 1.824 | 3.823 | -0.491 | -22.139 | 0.314 | 0.314 | 3 | 1 | put -15 %; stock moved WITH the numbers (+2.1 % open->close); NIFTY +0.6 % open->close; stock +3.8 % in the 20 sessions before (-22 % from its 52-week high); option peak +4 %, dip -19 %; 1 of 3 fade trades won that day |
| BAJFINANCE | 2023-07-27 | PE | in session day -1 | 32.4 | 8.8 | 34.7 | 58.05 | 60.261 | 74.849 | -12.661 | winner | -3.88 | 3.88 | -0.962 | 1.377 | 2.554 | 2.513 | 8.68 | 3.386 | -4.919 | 1.951 | -0.375 | 4 | 3 | put +60 %; stock faded (-3.9 % open->close); NIFTY -1.0 % open->close; stock +8.7 % in the 20 sessions before (-5 % from its 52-week high); option peak +75 %, dip -13 %; 3 of 4 fade trades won that day |
| BAJFINANCE | 2023-10-18 | PE | after close day -1 | 27.7 | 3.3 | 34.2 | 56.8 | 103.821 | 130.37 | -35.563 | winner | -2.28 | 2.28 | -0.754 | 1.065 | 1.477 | 0.118 | 8.022 | 9.908 | -1.208 | -0.531 | -0.531 | 1 | 1 | put +104 %; stock faded (-2.3 % open->close); NIFTY -0.8 % open->close; stock +8.0 % in the 20 sessions before (-1 % from its 52-week high); option peak +130 %, dip -36 %; 1 of 1 fade trades won that day |
| BAJFINANCE | 2024-07-24 | PE | after close day -1 | 13.8 | 2.3 | 28.8 | 38.05 | -32.313 | 17.871 | -33.903 | other | -0.347 | 0.347 | -0.129 | 1.061 | 0.21 | -4.771 | -5.006 | -9.005 | -17.883 | -1.442 | -1.442 | 2 | 0 | put -32 %; stock faded (-0.3 % open->close); NIFTY -0.1 % open->close; stock -5.0 % in the 20 sessions before (-18 % from its 52-week high); option peak +18 %, dip -34 %; 0 of 2 fade trades won that day |
| BAJFINANCE | 2024-10-23 | PE | after close day -1 | 13 | 2.6 | 27.7 | 54.45 | -91.939 | -0.092 | -91.736 | never up | 5.904 | -5.904 | 0.235 | 1.041 | -5.659 | -4.831 | -12.074 | -6.418 | -17.397 | -1.078 | -1.078 | 5 | 2 | put -92 %; stock moved WITH the numbers (+5.9 % open->close); NIFTY +0.2 % open->close; stock -12.1 % in the 20 sessions before (-17 % from its 52-week high); option peak -0 %, dip -92 %; 2 of 5 fade trades won that day |
| BAJFINANCE | 2025-01-30 | PE | after close day -1 | 18.4 | 7.3 | 27.4 | 52.1 | -33.78 | -0.096 | -41.075 | never up | 0.656 | -0.656 | 0.345 | 1.186 | -0.247 | 4.907 | 11.896 | 14.338 | -0.818 | 1.16 | 1.16 | 5 | 2 | put -34 %; stock moved WITH the numbers (+0.7 % open->close); NIFTY +0.3 % open->close; stock +11.9 % in the 20 sessions before (-1 % from its 52-week high); option peak -0 %, dip -41 %; 2 of 5 fade trades won that day |
| BAJFINANCE | 2025-04-30 | PE | after close day -1 | 18.9 | 5.5 | 23.7 | 50.1 | 56.57 | 121.856 | -0.1 | winner | -2.325 | 2.325 | -0.032 | 1.081 | 2.29 | -1.809 | 2.56 | -1.055 | -5.87 | -2.782 | -2.782 | 1 | 1 | put +57 %; stock faded (-2.3 % open->close); NIFTY -0.0 % open->close; stock +2.6 % in the 20 sessions before (-6 % from its 52-week high); option peak +122 %, dip -0 %; 1 of 1 fade trades won that day |
| BAJFINANCE | 2025-07-25 | PE | in session day -1 | 21.8 | 4.8 | 21.3 | 7.25 | -53.531 | 46.207 | -62.759 | round trip | 0.811 | -0.811 | -0.693 | 1.036 | -1.529 | 5.05 | 4.343 | 4.441 | -1.073 | -5.48 | -6.393 | 3 | 1 | put -54 %; stock moved WITH the numbers (+0.8 % open->close); NIFTY -0.7 % open->close; stock +4.3 % in the 20 sessions before (-1 % from its 52-week high); option peak +46 %, dip -63 %; 1 of 3 fade trades won that day |
| BAJFINANCE | 2025-11-11 | PE | after close day -1 | 23.3 | 3.8 | 18.1 | 7.55 | 97.046 | 169.536 | -0.662 | winner | -3.689 | 3.689 | 0.304 | 1.136 | 4.034 | 4.047 | 5.947 | 4.388 | -1.587 | -3.806 | -3.806 | 3 | 2 | put +97 %; stock faded (-3.7 % open->close); NIFTY +0.3 % open->close; stock +5.9 % in the 20 sessions before (-2 % from its 52-week high); option peak +170 %, dip -1 %; 2 of 3 fade trades won that day |
| BAJFINANCE | 2026-04-30 | PE | after close day -1 | 22.2 | 36.6 | 17.1 | 10 | 15.413 | 26 | -43.5 | winner | -0.847 | 0.847 | 0.003 | 1.401 | 0.85 | -0.508 | 10.216 | 4.264 | -15.646 | 1.613 | 1.613 | 4 | 1 | put +15 %; stock faded (-0.8 % open->close); NIFTY +0.0 % open->close; stock +10.2 % in the 20 sessions before (-16 % from its 52-week high); option peak +26 %, dip -43 %; 1 of 4 fade trades won that day |
| BAJFINANCE | 2026-07-31 | PE | in session day -1 | 27.6 | 9.5 | 18.7 | 6.9 | -46.826 | 160.87 | -46.377 | round trip | 4.219 | -4.219 | 0.091 | 1.524 | -4.081 | -0.556 | 3.892 | 2.874 | -4.363 | 3.939 | 3.851 | 4 | 2 | put -47 %; stock moved WITH the numbers (+4.2 % open->close); NIFTY +0.1 % open->close; stock +3.9 % in the 20 sessions before (-4 % from its 52-week high); option peak +161 %, dip -46 %; 2 of 4 fade trades won that day |
| BEL | 2024-05-21 | PE | non-session day / earlier | 30 | 108.9 | 32.2 | 2.35 | -44.988 | 102.128 | -61.702 | round trip | -3.127 | 3.127 | 0.556 | 1.225 | 3.808 | 15.15 | 10.93 | 9.327 | -0.691 | 9.351 | 9.351 | 2 | 0 | put -45 %; stock faded (-3.1 % open->close); NIFTY +0.6 % open->close; stock +10.9 % in the 20 sessions before (-1 % from its 52-week high); option peak +102 %, dip -62 %; 0 of 2 fade trades won that day |
| BEL | 2024-10-28 | PE | in session day -1 | 38.4 | 38.1 | 14.9 | 2.55 | 35.862 | 129.412 | -19.608 | winner | -2.403 | 2.403 | 0.363 | 1.743 | 3.036 | -4.639 | -6.383 | -0.211 | -20.308 | 1.597 | 1.972 | 8 | 3 | put +36 %; stock faded (-2.4 % open->close); NIFTY +0.4 % open->close; stock -6.4 % in the 20 sessions before (-20 % from its 52-week high); option peak +129 %, dip -20 %; 3 of 8 fade trades won that day |
| BEL | 2025-01-31 | PE | in session day -1 | 52.5 | 20 | 38.6 | 2.75 | -42.362 | 25.455 | -49.091 | other | 3.082 | -3.082 | 0.908 | 1.838 | -1.412 | -1.165 | -9.085 | -6.643 | -21.527 | 1.848 | 6.25 | 8 | 2 | put -42 %; stock moved WITH the numbers (+3.1 % open->close); NIFTY +0.9 % open->close; stock -9.1 % in the 20 sessions before (-22 % from its 52-week high); option peak +25 %, dip -49 %; 2 of 8 fade trades won that day |
| BEL | 2025-05-20 | PE | after close day -1 | 18.4 | 62.2 | 6.8 | 2.55 | -14.511 | 62.745 | -39.216 | round trip | -1.516 | 1.516 | -1.249 | 1.661 | -0.56 | 12.686 | 23.242 | 18.657 | -2.61 | 1.553 | 1.553 | 3 | 0 | put -15 %; stock faded (-1.5 % open->close); NIFTY -1.2 % open->close; stock +23.2 % in the 20 sessions before (-3 % from its 52-week high); option peak +63 %, dip -39 %; 0 of 3 fade trades won that day |
| BEL | 2025-11-03 | PE | in session day -1 | 17.8 | 32.8 | 25.8 | 5.1 | 22.3 | 78.431 | -20.588 | winner | -1.332 | 1.332 | 0.259 | 1.18 | 1.637 | -2.09 | 1.473 | -3.674 | -5.986 | 0.446 | 4.416 | 5 | 3 | put +22 %; stock faded (-1.3 % open->close); NIFTY +0.3 % open->close; stock +1.5 % in the 20 sessions before (-6 % from its 52-week high); option peak +78 %, dip -21 %; 3 of 5 fade trades won that day |
| BEL | 2026-01-29 | PE | in session day -1 | 20.4 | 22.7 | 24 | 5.4 | 16.362 | 49.074 | -16.667 | winner | -2.146 | 2.146 | 0.292 | 1.04 | 2.45 | 0.763 | 4.392 | 7.721 | -4.599 | 0.276 | 9.208 | 3 | 2 | put +16 %; stock faded (-2.1 % open->close); NIFTY +0.3 % open->close; stock +4.4 % in the 20 sessions before (-5 % from its 52-week high); option peak +49 %, dip -17 %; 2 of 3 fade trades won that day |
| BOSCHLTD | 2023-05-11 | PE | after close day -1 | 13.5 | 24.5 | 22.7 | 129.95 | -45.733 | 35.668 | -59.754 | round trip | 1.427 | -1.427 | -0.331 | 0.988 | -1.754 | 0.192 | 4.379 | 0.458 | -2.497 | -0.8 | -0.8 | 1 | 0 | put -46 %; stock moved WITH the numbers (+1.4 % open->close); NIFTY -0.3 % open->close; stock +4.4 % in the 20 sessions before (-2 % from its 52-week high); option peak +36 %, dip -60 %; 0 of 1 fade trades won that day |
| BOSCHLTD | 2023-11-10 | PE | in session day -1 | 167.6 | 144.3 | 12.8 | 124.55 | -30.722 | 0.361 | -43.758 | never up | 1.28 | -1.28 | 0.38 | 0.6 | -1.052 | 1.491 | -0.359 | 0.892 | -6.14 | -1.074 | -1.638 | 4 | 0 | put -31 %; stock moved WITH the numbers (+1.3 % open->close); NIFTY +0.4 % open->close; stock -0.4 % in the 20 sessions before (-6 % from its 52-week high); option peak +0 %, dip -44 %; 0 of 4 fade trades won that day |
| BOSCHLTD | 2024-05-27 | PE | after close day -1 | 41.7 | 8.8 | 4.2 | 285.5 | -70.914 | -0.018 | -75.394 | never up | 2.153 | -2.153 | -0.462 | 0.651 | -2.455 | -0.605 | 6.709 | 4.996 | -3.925 | 0.197 | 0.197 | 5 | 2 | put -71 %; stock moved WITH the numbers (+2.2 % open->close); NIFTY -0.5 % open->close; stock +6.7 % in the 20 sessions before (-4 % from its 52-week high); option peak -0 %, dip -75 %; 2 of 5 fade trades won that day |
| BOSCHLTD | 2025-01-29 | CE | after close day -1 | -11.5 | -14.5 | 6.2 | 124.45 | -27.295 | 4.781 | -38.088 | never up | -2.912 | -2.912 | 0.592 | 0.852 | -3.416 | -2.659 | -12.619 | -9.711 | -23.771 | -2.675 | -2.675 | 5 | 3 | call -27 %; stock moved WITH the numbers (-2.9 % open->close); NIFTY +0.6 % open->close; stock -12.6 % in the 20 sessions before (-24 % from its 52-week high); option peak +5 %, dip -38 %; 3 of 5 fade trades won that day |
| BPCL | 2022-05-27 | CE | in session day -1 | -73.7 | -0.1 | 23.5 | 3.5 | -14.279 | 32.857 | -21.429 | round trip | -0.678 | -0.678 | 0.343 | 0.879 | -0.979 | -1.748 | -12.527 | -5.696 | -35.169 | 0.062 | -0.46 | 2 | 0 | call -14 %; stock moved WITH the numbers (-0.7 % open->close); NIFTY +0.3 % open->close; stock -12.5 % in the 20 sessions before (-35 % from its 52-week high); option peak +33 %, dip -21 %; 0 of 2 fade trades won that day |
| BPCL | 2023-05-23 | PE | after close day -1 | 145.1 | 293.3 | 8.3 | 4.05 | -78.515 | -1.235 | -77.778 | never up | -0.109 | 0.109 | -0.081 | 0.611 | 0.059 | 1.289 | 4.448 | 0.531 | -3.548 | 1.493 | 1.493 | 1 | 0 | put -79 %; stock faded (-0.1 % open->close); NIFTY -0.1 % open->close; stock +4.4 % in the 20 sessions before (-4 % from its 52-week high); option peak -1 %, dip -78 %; 0 of 1 fade trades won that day |
| BPCL | 2024-07-22 | CE | in session day -1 | -73.3 | -40.7 | -0.1 | 3.45 | -5.861 | 105.797 | -46.377 | round trip | 1.215 | 1.215 | 0.26 | 1.451 | 0.838 | 5.926 | 3.329 | -2.135 | -7.515 | 0.247 | -4.275 | 3 | 2 | call -6 %; stock faded (+1.2 % open->close); NIFTY +0.3 % open->close; stock +3.3 % in the 20 sessions before (-8 % from its 52-week high); option peak +106 %, dip -46 %; 2 of 3 fade trades won that day |
| BPCL | 2024-10-28 | CE | in session day -1 | -72.1 | -19.2 | 1.1 | 3.1 | -46.112 | 61.29 | -51.613 | round trip | 1.009 | 1.009 | 0.363 | 1.444 | 0.485 | -6.201 | -5.4 | 0.771 | -14.508 | 0.326 | -4.402 | 8 | 3 | call -46 %; stock faded (+1.0 % open->close); NIFTY +0.4 % open->close; stock -5.4 % in the 20 sessions before (-15 % from its 52-week high); option peak +61 %, dip -52 %; 3 of 8 fade trades won that day |
| BPCL | 2025-08-14 | PE | after close day -1 | 140.7 | 55.7 | 1.2 | 3.05 | 128.183 | 147.541 | -11.475 | winner | -2.737 | 2.737 | 0.098 | 1.114 | 2.846 | 2.138 | -7.288 | -4.937 | -14.229 | 1.395 | 1.395 | 4 | 2 | put +128 %; stock faded (-2.7 % open->close); NIFTY +0.1 % open->close; stock -7.3 % in the 20 sessions before (-14 % from its 52-week high); option peak +148 %, dip -11 %; 2 of 4 fade trades won that day |
| BPCL | 2026-01-27 | PE | after close day -1 | 88.9 | 16.1 | 7.1 | 3.95 | 0.91 | 139.241 | -5.063 | winner | -0.168 | 0.168 | 0.447 | 1.029 | 0.628 | -3.868 | -4.578 | -0.395 | -10.048 | 2.535 | 2.535 | 4 | 2 | put +1 %; stock faded (-0.2 % open->close); NIFTY +0.4 % open->close; stock -4.6 % in the 20 sessions before (-10 % from its 52-week high); option peak +139 %, dip -5 %; 2 of 4 fade trades won that day |
| BPCL | 2026-07-23 | CE | in session day -1 | -127.4 | -133.3 | 23.1 | 2.8 | -50.73 | 121.429 | -57.143 | round trip | 1.457 | 1.457 | -0.147 | 1.353 | 1.656 | 4.585 | 3.483 | 3.132 | -18.46 | -2.739 | -4.368 | 5 | 2 | call -51 %; stock faded (+1.5 % open->close); NIFTY -0.1 % open->close; stock +3.5 % in the 20 sessions before (-18 % from its 52-week high); option peak +121 %, dip -57 %; 2 of 5 fade trades won that day |
| HCLTECH | 2022-04-22 | PE | after close day -1 | 223.9 | 4.4 | 15.1 | 11 | -54.949 | -0.455 | -76.364 | never up | 1.422 | -1.422 | -0.411 | 0.805 | -1.752 | -2.825 | -6.562 | -7.008 | -20.218 | -1.146 | -1.146 | 1 | 0 | put -55 %; stock moved WITH the numbers (+1.4 % open->close); NIFTY -0.4 % open->close; stock -6.6 % in the 20 sessions before (-20 % from its 52-week high); option peak -0 %, dip -76 %; 0 of 1 fade trades won that day |
| HCLTECH | 2023-01-13 | PE | after close day -1 | 18.8 | 17.5 | 19.6 | 10.6 | -74.183 | 15.094 | -77.83 | other | 3.247 | -3.247 | 0.499 | 0.948 | -2.775 | 2.639 | 2.811 | 5.834 | -21.167 | -2.589 | -2.589 | 2 | 0 | put -74 %; stock moved WITH the numbers (+3.2 % open->close); NIFTY +0.5 % open->close; stock +2.8 % in the 20 sessions before (-21 % from its 52-week high); option peak +15 %, dip -78 %; 0 of 2 fade trades won that day |
| HCLTECH | 2024-07-15 | PE | after close day -1 | 20.6 | 6.6 | 6.7 | 13.65 | -18.064 | -0.366 | -68.864 | never up | -0.658 | 0.658 | -0.004 | 0.649 | 0.656 | 2.685 | 8.036 | 3.321 | -8.08 | 1.269 | 1.269 | 1 | 0 | put -18 %; stock faded (-0.7 % open->close); NIFTY -0.0 % open->close; stock +8.0 % in the 20 sessions before (-8 % from its 52-week high); option peak -0 %, dip -69 %; 0 of 1 fade trades won that day |
| HCLTECH | 2026-01-13 | CE | after close day -1 | -11.1 | -3.6 | 13.3 | 22.75 | -53.428 | 26.154 | -70.11 | other | -1.187 | -1.187 | -0.637 | 1.201 | -0.421 | 3.732 | -0.335 | 0.651 | -17.126 | 1.043 | 1.043 | 2 | 0 | call -53 %; stock moved WITH the numbers (-1.2 % open->close); NIFTY -0.6 % open->close; stock -0.3 % in the 20 sessions before (-17 % from its 52-week high); option peak +26 %, dip -70 %; 0 of 2 fade trades won that day |
| HCLTECH | 2026-07-14 | PE | after close day -1 | 20.3 | 3 | 13.9 | 16.95 | 64.979 | 76.991 | -20.354 | winner | -2.775 | 2.775 | -0.066 | 0.788 | 2.723 | 7.671 | 10.058 | 7.568 | -31.397 | -1.736 | -1.736 | 1 | 1 | put +65 %; stock faded (-2.8 % open->close); NIFTY -0.1 % open->close; stock +10.1 % in the 20 sessions before (-31 % from its 52-week high); option peak +77 %, dip -20 %; 1 of 1 fade trades won that day |
| OBEROIRLTY | 2023-02-09 | PE | after close day -1 | 50.3 | 120.5 | 95.8 | 3.15 | 499.74 | 676.19 | -1.587 | winner | -4.184 | 4.184 | 0.044 | 1.25 | 4.239 | 1.709 | -1.624 | -1.387 | -22.953 | 5.125 | 5.125 | 3 | 2 | put +500 %; stock faded (-4.2 % open->close); NIFTY +0.0 % open->close; stock -1.6 % in the 20 sessions before (-23 % from its 52-week high); option peak +676 %, dip -2 %; 2 of 3 fade trades won that day |
| OBEROIRLTY | 2023-10-30 | PE | after close day -1 | 43.4 | 42 | 76.8 | 4 | -45.046 | 53.75 | -42.5 | round trip | 0.68 | -0.68 | 0.459 | 1.228 | -0.116 | -2.281 | -3.402 | -0.007 | -8.94 | 0.996 | 0.996 | 8 | 2 | put -45 %; stock moved WITH the numbers (+0.7 % open->close); NIFTY +0.5 % open->close; stock -3.4 % in the 20 sessions before (-9 % from its 52-week high); option peak +54 %, dip -43 %; 2 of 8 fade trades won that day |
| OBEROIRLTY | 2024-01-23 | CE | non-session day / earlier | -48.7 | -21.2 | -35.3 | 3.25 | -83.053 | 136.923 | -90.769 | round trip | -5.208 | -5.208 | -2.201 | 1.183 | -2.605 | -4.2 | 6.905 | 5.863 | -5.131 | -3.936 | -3.936 | 3 | 0 | call -83 %; stock moved WITH the numbers (-5.2 % open->close); NIFTY -2.2 % open->close; stock +6.9 % in the 20 sessions before (-5 % from its 52-week high); option peak +137 %, dip -91 %; 0 of 3 fade trades won that day |
| OBEROIRLTY | 2024-05-15 | PE | after close day -1 | 64.1 | 118.8 | 36.8 | 11.05 | -51.317 | 17.647 | -52.941 | other | -0.685 | 0.685 | -0.247 | 1.258 | 0.373 | 3.558 | 1.28 | 2.619 | -4.257 | 4.328 | 4.328 | 4 | 2 | put -51 %; stock faded (-0.7 % open->close); NIFTY -0.2 % open->close; stock +1.3 % in the 20 sessions before (-4 % from its 52-week high); option peak +18 %, dip -53 %; 2 of 4 fade trades won that day |
| OBEROIRLTY | 2024-10-21 | PE | after close day -1 | 29 | 0.8 | 8.4 | 11.4 | -29.71 | 36.842 | -41.667 | round trip | 0.783 | -0.783 | -0.701 | 1.254 | -1.663 | 0.644 | 4.879 | 7.089 | -6.474 | 2.514 | 2.514 | 3 | 1 | put -30 %; stock moved WITH the numbers (+0.8 % open->close); NIFTY -0.7 % open->close; stock +4.9 % in the 20 sessions before (-6 % from its 52-week high); option peak +37 %, dip -42 %; 1 of 3 fade trades won that day |
| OBEROIRLTY | 2025-01-21 | PE | after close day -1 | 71.7 | 4.9 | 33.9 | 22.05 | 292.124 | 443.764 | -12.925 | winner | -7.61 | 7.61 | -1.695 | 1.149 | 5.662 | -0.519 | -10.895 | -9.866 | -14.539 | 0.409 | 0.409 | 3 | 1 | put +292 %; stock faded (-7.6 % open->close); NIFTY -1.7 % open->close; stock -10.9 % in the 20 sessions before (-15 % from its 52-week high); option peak +444 %, dip -13 %; 1 of 3 fade trades won that day |
| OBEROIRLTY | 2025-07-22 | CE | after close day -1 | -27.9 | -2.8 | -29.7 | 13.4 | 85.63 | 133.955 | -1.493 | winner | 2.538 | 2.538 | -0.42 | 1.413 | 3.132 | 1.685 | -5.238 | -5.713 | -21.72 | -2.922 | -2.922 | 2 | 2 | call +86 %; stock faded (+2.5 % open->close); NIFTY -0.4 % open->close; stock -5.2 % in the 20 sessions before (-22 % from its 52-week high); option peak +134 %, dip -1 %; 2 of 2 fade trades won that day |
| OBEROIRLTY | 2025-10-16 | PE | after close day -1 | 100.4 | 180.5 | 109.6 | 7.1 | -36.443 | 252.113 | -36.62 | round trip | 0.722 | -0.722 | 0.75 | 1.415 | 0.338 | 1.515 | -2.532 | -2.867 | -31.671 | 4.596 | 4.596 | 3 | 1 | put -36 %; stock moved WITH the numbers (+0.7 % open->close); NIFTY +0.7 % open->close; stock -2.5 % in the 20 sessions before (-32 % from its 52-week high); option peak +252 %, dip -37 %; 1 of 3 fade trades won that day |
| OBEROIRLTY | 2026-05-11 | PE | after close day -1 | 62.4 | 13 | 52.1 | 12.05 | 123.296 | 140.249 | -0.415 | winner | -4.56 | 4.56 | -0.644 | 1.195 | 3.791 | 2 | 4.108 | 3.363 | -15.062 | 0.575 | 0.575 | 2 | 1 | put +123 %; stock faded (-4.6 % open->close); NIFTY -0.6 % open->close; stock +4.1 % in the 20 sessions before (-15 % from its 52-week high); option peak +140 %, dip -0 %; 1 of 2 fade trades won that day |
| POLYCAB | 2022-01-24 | PE | in session day -1 | 19.9 | 57.7 | 20.5 | 7.45 | -28.667 | 87.919 | -39.597 | round trip | -1.855 | 1.855 | -2.424 | 0.707 | 0.141 | -0.147 | 12.17 | 8.161 | -3.267 | -0.036 | -6.387 | 3 | 2 | put -29 %; stock faded (-1.9 % open->close); NIFTY -2.4 % open->close; stock +12.2 % in the 20 sessions before (-3 % from its 52-week high); option peak +88 %, dip -40 %; 2 of 3 fade trades won that day |
| POLYCAB | 2022-05-11 | PE | in session day -1 | 14.9 | 2.9 | 30.7 | 18 | -6.47 | 88.333 | -16.944 | round trip |  |  | -0.633 | 0.869 |  | -1.941 | -8.139 | 0.317 | -13.55 |  |  | 1 | 0 | put -6 %; stock nan (+nan % open->close); NIFTY -0.6 % open->close; stock -8.1 % in the 20 sessions before (-14 % from its 52-week high); option peak +88 %, dip -17 %; 0 of 1 fade trades won that day |
| POLYCAB | 2023-01-20 | PE | in session day -1 | 14.1 | 33.4 | 10.2 | 18.05 | 74.276 | 130.748 | -24.931 | winner | -3.116 | 3.116 | -0.485 | 0.862 | 2.697 | 3.089 | 3.158 | 3.344 | -8.972 | 0.757 | 3.501 | 2 | 1 | put +74 %; stock faded (-3.1 % open->close); NIFTY -0.5 % open->close; stock +3.2 % in the 20 sessions before (-9 % from its 52-week high); option peak +131 %, dip -25 %; 1 of 2 fade trades won that day |
| POLYCAB | 2023-05-15 | PE | in session day -1 | 31.7 | 18.7 | 8.9 | 22.05 | -37.331 | 56.916 | -38.549 | round trip | -0.553 | 0.553 | 0.325 | 0.779 | 0.806 | -1.034 | 6.231 | 2.988 | -3.655 | 0.326 | 5.092 | 2 | 1 | put -37 %; stock faded (-0.6 % open->close); NIFTY +0.3 % open->close; stock +6.2 % in the 20 sessions before (-4 % from its 52-week high); option peak +57 %, dip -39 %; 1 of 2 fade trades won that day |
| POLYCAB | 2023-10-19 | PE | in session day -1 | 58.9 | 6.7 | 26.6 | 21.2 | 8.4 | 245.755 | -9.906 | winner | -0.898 | 0.898 | 0.407 | 0.745 | 1.201 | 5.045 | 5.827 | 7.713 | -0.313 | 0.117 | -2.247 | 4 | 2 | put +8 %; stock faded (-0.9 % open->close); NIFTY +0.4 % open->close; stock +5.8 % in the 20 sessions before (-0 % from its 52-week high); option peak +246 %, dip -10 %; 2 of 4 fade trades won that day |
| POLYCAB | 2024-05-13 | PE | in session day -1 | 29.2 | 32.9 | 29.3 | 152.05 | -43.638 | 30.22 | -44.097 | round trip | 2.583 | -2.583 | 0.345 | 0.863 | -2.284 | 0.19 | 9.886 | 13.013 |  | 1.841 | 8.021 | 2 | 0 | put -44 %; stock moved WITH the numbers (+2.6 % open->close); NIFTY +0.3 % open->close; stock +9.9 % in the 20 sessions before (+nan % from its 52-week high); option peak +30 %, dip -44 %; 0 of 2 fade trades won that day |
| POLYCAB | 2025-01-23 | PE | in session day -1 | 11.5 | 4.3 | 20.4 | 50.05 | -57.755 | 14.086 | -75.724 | other | 1.148 | -1.148 | 0.333 | 1.12 | -0.775 | 1.312 | -7.849 | -4.781 | -13.746 | 0.253 | -5.788 | 3 | 0 | put -58 %; stock moved WITH the numbers (+1.1 % open->close); NIFTY +0.3 % open->close; stock -7.8 % in the 20 sessions before (-14 % from its 52-week high); option peak +14 %, dip -76 %; 0 of 3 fade trades won that day |
| POLYCAB | 2025-10-20 | PE | in session day -1 | 55.6 | 15.6 | 17.8 | 50.6 | -45.672 | 22.134 | -51.976 | other | 1.906 | -1.906 | 0.072 | 1.1 | -1.827 | -0.695 | 2.976 | 1.969 | -2.778 | 1.216 | -0.633 | 6 | 2 | put -46 %; stock moved WITH the numbers (+1.9 % open->close); NIFTY +0.1 % open->close; stock +3.0 % in the 20 sessions before (-3 % from its 52-week high); option peak +22 %, dip -52 %; 2 of 6 fade trades won that day |
| POLYCAB | 2026-07-17 | PE | in session day -1 | 32.8 | 1.4 | 39 | 55 | 8.933 | 51.273 | -33.182 | winner | -3.354 | 3.354 | 0.857 | 1.157 | 4.345 | 0.98 | -2.784 | -3.156 | -7.915 | -0.494 | -1.662 | 3 | 1 | put +9 %; stock faded (-3.4 % open->close); NIFTY +0.9 % open->close; stock -2.8 % in the 20 sessions before (-8 % from its 52-week high); option peak +51 %, dip -33 %; 1 of 3 fade trades won that day |
| SONACOMS | 2025-01-24 | PE | after close day -1 | 12.8 | 5 | 11.8 | 9.1 | -69.395 | -0.549 | -71.978 | never up | 2.951 | -2.951 | -0.396 | 0.754 | -3.249 | -6.882 | -8.584 | -6.29 | -29.409 | -6.008 | -6.008 | 4 | 1 | put -69 %; stock moved WITH the numbers (+3.0 % open->close); NIFTY -0.4 % open->close; stock -8.6 % in the 20 sessions before (-29 % from its 52-week high); option peak -1 %, dip -72 %; 1 of 4 fade trades won that day |
| SONACOMS | 2025-08-05 | CE | after close day -1 | -14.1 | -25.6 | -4.7 | 6 | 28.431 | 94.167 | -12.5 | winner | 3.256 | 3.256 | -0.286 | 1.215 | 3.604 | -4.844 | -5.403 | -2.502 | -42.366 | -2.257 | -2.257 | 3 | 3 | call +28 %; stock faded (+3.3 % open->close); NIFTY -0.3 % open->close; stock -5.4 % in the 20 sessions before (-42 % from its 52-week high); option peak +94 %, dip -12 %; 3 of 3 fade trades won that day |
| SONACOMS | 2025-10-28 | PE | after close day -1 | 18.7 | 40.1 | 23.6 | 5.55 | -12.977 | 35.135 | -21.622 | round trip | -2.359 | 2.359 | -0.014 | 1.166 | 2.342 | 4.684 | 18.113 | 13.793 | -35.045 | 2.521 | 2.521 | 3 | 1 | put -13 %; stock faded (-2.4 % open->close); NIFTY -0.0 % open->close; stock +18.1 % in the 20 sessions before (-35 % from its 52-week high); option peak +35 %, dip -22 %; 1 of 3 fade trades won that day |
| SONACOMS | 2026-05-04 | PE | after close day -1 | 14.2 | 24.4 | 46.5 | 6.05 | 57.931 | 111.57 | -1.653 | winner | -6.279 | 6.279 | 0.232 | 1.306 | 6.581 | 5.691 | 26.116 | 18.655 | -0.954 | 1.112 | 1.112 | 5 | 2 | put +58 %; stock faded (-6.3 % open->close); NIFTY +0.2 % open->close; stock +26.1 % in the 20 sessions before (-1 % from its 52-week high); option peak +112 %, dip -2 %; 2 of 5 fade trades won that day |
