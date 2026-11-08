# G1 follow-through vs FII / DII positions, news tone and the heavyweight stocks: pre-registered 2026-11-08 (before any outcome was joined)

**Question (the user):** "fetch the news too, check the sentiments; use the FII, DII entry data; the most-share stocks that move the
NIFTY; check whether it works." Same signals and outcome as `UNDERLYING_PREREG.md`: 638 G1 downside-breakout signals
(`results/g1_underlying_signals.csv`), outcome `reach` = NIFTY kept falling >= 1 ATR5 from entry to the next close (F >= 1). Same
three periods: discovery to 2023-09-30, validation 2023-10-01 to 2024-09-30, confirmation 2024-10-01 on. Record-only; no live change.

## Data (all public; what exists, and what does not)
- **FII / DII / Client / Pro positions in index futures and index options** from NSE's daily participant-wise open interest file
  (`nsearchives.nseindia.com/content/nsccl/fao_participant_oi_DDMMYYYY.csv`), one file per session, 2021-10 to 2026-11. This is the
  "FII / DII entry data" that exists for the whole period. **FII / DII cash-market buy / sell by day is NOT available historically
  from a free official source** (NSE gives only the latest day), so cash flows are not tested; this is a gap, not a hidden result.
- **News tone:** the GDELT global news tone for the query "Nifty OR Sensex OR Indian stocks" (daily average tone and daily
  coverage volume), 2021-10 to 2026-11. It is a global, machine-scored, noisy proxy, not a curated Indian market sentiment.
- **Heavyweight stocks:** daily bars (`data/eod2/*.csv`) of the 11 heaviest NIFTY names, with fixed approximate weights (%): HDFCBANK 13,
  ICICIBANK 8, RELIANCE 9, INFY 5, TCS 4, ITC 4, LT 4, BHARTIARTL 4, AXISBANK 3, SBIN 3, KOTAKBANK 3 (about 60 % of the index; the true
  weights drift, so this is an approximation). Intraday heavyweight bars are not available for the history, so only daily facts are used.

## Features (each alone; every one known by the signal minute: positions and returns of the PREVIOUS session, news of the previous day,
and today's OPEN gap of the stocks)
FII/DII/others positions at the previous session close
1. fii_fut_net: FII index futures long minus short; 2. fii_fut_ratio: long / (long + short); 3. fii_fut_chg1: change in (1) vs the session before;
4. fii_fut_chg5: change in (1) over 5 sessions; 5. fii_put_net: FII index put long minus short; 6. fii_call_net: FII index call long minus short;
7. fii_opt_bear: (5) minus (6); 8. fii_opt_bear_chg1; 9. dii_fut_net; 10. dii_fut_chg1; 11. client_fut_net (retail); 12. pro_fut_net;
13. fii_vs_client: fii_fut_ratio minus client's long ratio.
News (GDELT)
14. tone_prev: tone of the previous day; 15. tone_5d: mean tone of the last 5 days; 16. tone_chg: (14) minus the mean of the 20 days before;
17. cov_prev: coverage volume of the previous day; 18. cov_x: (17) / mean of the previous 20 days.
Heavyweights (weights above)
19. hw_gap: weighted open gap today; 20. hw_prev1: weighted previous-day return; 21. hw_prev5: weighted previous 5-day return;
22. hw_breadth: number of the 11 that closed down yesterday; 23. hw_gap_breadth: number of the 11 that opened down today;
24. bank_vs_rest_prev1: weighted banks (HDFC, ICICI, AXIS, SBI, KOTAK) return minus the rest, previous day; 25. hdfc_gap; 26. reliance_gap;
27. hw_gap_vs_nifty: (19) minus NIFTY's own open gap (are the heavyweights weaker or stronger than the index at the open).

## Rules and tests (as UNDERLYING_PREREG.md)
Continuous: "high" >= discovery P67, "low" <= discovery P33; one family; BH 10 % over all rules; Fisher two-sided on `reach` in discovery.
Candidate: q <= 0.10, bucket >= 25. Validation: same direction, one-sided p < 0.05, bucket >= 20, effect >= half. Confirmation:
same direction, one-sided p < 0.05. **Passed = all three.** Missing data on a day = that day left out of that feature's rules.
Hiding checks on a pass: by year, without the largest 3 % of F. No re-tuning. "No source adds anything" is a valid answer.
