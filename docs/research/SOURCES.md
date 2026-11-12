# External research sources

Rules (see `README.md`): a source is evidence to read, never a rule. Each entry says how far it was checked. "Official" = the issuer's own
document or data; "secondary" = a news report, a practitioner post, a blog or a single developer's work. Nothing here becomes a trading rule
without a pre-registered experiment (`strategies/` or `g1_research/*_PREREG.md`) and a row in `experiments.csv`.
Add new entries at the bottom. Dates: YYYY-MM-DD; "unknown" when the page does not say.

## Official
### SEBI press release: updated study, 93 % of individual F&O traders lost money (FY22-FY24)
- Issuer: SEBI (PR No. 37/2024). Published: 2024-09-23. Accessed: 2026-11-09.
- URL: https://www.sebi.gov.in/media-and-notifications/press-releases/sep-2024/updated-sebi-study-reveals-93-of-individual-traders-incurred-losses-in-equity-fando-between-fy22-and-fy24-aggregate-losses-exceed-1-8-lakh-crores-over-three-years_86906.html
- Topic: how often individual F&O traders lose; context for option buying.
- Findings (from the title only; the page body did not load in the reader): 93 % of individual traders incurred losses in equity F&O between FY22 and FY24; aggregate losses above Rs 1.8 lakh crore over three years.
- Evaluation: header read only. The study PDF link given later (sebi.gov.in/sebi_data/attachdocs/sep-2024/1727080521285.pdf) returned 404. Detail figures come from secondary reports below.
- Allowed use: background context. Not used as a parameter anywhere.

### NSE participant-wise open interest files
- Issuer: NSE (nsearchives). Daily files; URL pattern https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_DDMMYYYY.csv. Accessed: 2026-11-08.
- Topic: FII / DII / Client / Pro positions in index futures and options.
- Findings: 1,280 sessions fetched (Sep 2021 to 6 Nov 2026) and tested against G1 follow-through and NIFTY next-day moves (experiments E-20261108-04, -05, E-20261109-01): no direction link; one near-pass for size (lead only).
- Evaluation: files read directly; raw data is git-ignored (refetch with `g1_research/scripts/fetch_external.py`).
- Limit: FII / DII cash-market buy and sell by day is not available historically from NSE (the `fiidiiTradeReact` endpoint returns only the latest day, checked 2026-11-08).

### NSE holiday master (trading holidays, F&O)
- Issuer: NSE. URL: https://www.nseindia.com/api/holiday-master?type=trading. Fetched: 2026-10-14 (stored in `data/nse_holidays.json`).
- Topic: the trading calendar behind `server/sessions.py`. Special weekend sessions are NOT in it; they go in `data/special_sessions.json` when announced.

### Upstox API: historical candles v3 (day candles for index keys)
- Issuer: Upstox. Endpoint observed: /v3/historical-candle/{instrument_key}/days/1/{to}/{from}. Accessed: 2026-11-07 (read-only call on the VM).
- Topic: daily NIFTY closes for the breakout score's two trend items (`server/g1_score.py`).
- Findings: returned about 90 daily candles newest first; checked against the history file (prev 5-day 0.287 vs 0.287; EMA20 gap -0.778 vs -0.777).

## Secondary
### Zerodha In The Money: How to Trade Opening Range Breakout (ORB) with NIFTY Options, Part 2
- Author: Sandeep Rao, Zerodha. Published: 2026-03-10. Accessed: 2026-11-09. URL: https://inthemoneybyzerodha.substack.com/p/how-to-trade-opening-range-breakout
- Topic: option-premium ORB, 09:15-11:15 range, strike near Rs 200, 20 % stop.
- Findings (as written): Jan 2022 to Feb 2026, post-brokerage and taxes with 0.2 % slippage, win rate about 48 %, max drawdown about 45 %, smooth until Jan 2024 then weak. Exit rule not stated.
- Evaluation: self-reported, no code or data; charts are images the reader could not read. Replicated on our data with a fixed exit (E-20261109-02): win 39 %, -1.1 % a trade, negative every year.

### Business Standard / Moneylife / TaxGuru: reports on SEBI's FY25 and FY22-FY24 studies
- Issuer: news outlets summarising SEBI. FY25 study published 2025-07-07 (Business Standard); others accessed 2026-11-09.
- URLs: https://www.business-standard.com/amp/markets/news/net-losses-of-traders-in-fo-widens-in-fy25-sebi-study-125070701221_1.html ; https://moneylife.in/article/91-percentage-of-retail-traders-lost-money-in-derivatives-losses-in-fo-surged-41-percentage-to-rs105-lakh-crore-in-fy25-sebi-study/77613.html ; https://taxguru.in/sebi/sebi-study-shows-93-percent-individual-fo-traders-incur-losses.html
- Findings (as reported): about 91 % of individual F&O traders lost money in FY25 (about Rs 1.05 lakh crore); in FY24 91.5 % lost in options against about 60 % in futures; average transaction cost about Rs 26,000 a trader (brokerage 51 %, exchange fees 20 %).
- Evaluation: secondary. The "costs were 27 % of losing traders' gross losses" figure is from one write-up, not the SEBI release. Verify against the SEBI document before citing.

### GitHub pull request: real NIFTY option prices, the 09:15 signal and option buying
- Author: ramanauday1561 (single developer). Accessed: 2026-11-09. URL: https://github.com/ramanauday1561/commodities-trading/pull/72
- Findings (as written): ATM nearest-expiry buying lost about 3.4 points a trade over 11 years (190 trades) and gained about 26.7 over the last two years (52 trades); NIFTY's daily move averaged 0.84 of what VIX implied.
- Evaluation: self-reported, sign flips by period. A lead, not proof.

### Algoshastra: The Honest Backtest (costs, slippage, deflated Sharpe for NIFTY / SENSEX options)
- Author / issuer: Algoshastra (vendor). Accessed: 2026-11-09. URL: https://algoshastra.in/learn/honest-backtest-india
- Topic: checklist for option backtests (realistic fills, deflated Sharpe, probability of backtest overfitting).
- Evaluation: vendor guidance; used as a checklist only (see `VALIDATION_INVENTORY.md`).

### MQL5 blog: the opening-range breakout paper replicated on five indices, gross reproduced, net zero
- Author: blog author (not peer reviewed). Accessed: 2026-11-09. URL: https://www.mql5.com/en/blogs/post/776235
- Findings (as written): no index and no period significantly positive net; commission charged but no spread or slippage in the original paper. Not about India.
- Evaluation: secondary, non-Indian. Context only.

### TradingQnA (Zerodha forum) threads on NIFTY option buying
- Author: anonymous forum members. Accessed: 2026-11-09. URLs: https://tradingqna.com/t/making-money-in-option-buying/38899 ; https://tradingqna.com/t/naked-option-buying-nifty/113963 ; https://tradingqna.com/t/profits-from-options-buying/61454
- Findings (as written): some members report profits from ATM / ITM buying with a signal and a tight stop; the same forum shows losses.
- Evaluation: anecdotes, unaudited. Not used.

### GDELT DOC API: daily news tone for "Nifty OR Sensex OR Indian stocks"
- Issuer: GDELT Project (data provider). Accessed: 2026-11-08. URL: https://api.gdeltproject.org/api/v2/doc/doc (modes timelinetone, timelinevolraw).
- Findings: tone tested against G1 follow-through (E-20261108-04): no candidate; it flipped sign between periods.
- Limit: a global, machine-scored proxy, one request per five seconds. Raw files are git-ignored.

### Timely opening-range breakout on index futures (record)
- Issuer: journal record for a 2003-2013 DJIA / S&P / NASDAQ / HSI / TAIEX study. Accessed: 2026-11-09. URL: https://sindex.sdl.edu.sa/esploro/outputs/journalArticle/Assessing-the-Profitability-of-Timely-Opening/9942209608331
- Evaluation: abstract level only; no Indian index. Context only.

## Supplied but not read (blocked)
### Reddit threads from the user's notes
- Eight threads (r/IndiaAlgoTrading, r/IndianStreetBets, r/NSEbets, r/IndianStocks, r/IndianStockMarket) were supplied as the user's notes on 2026-11-09. Every Reddit domain is blocked for the search, browser and reader tools, so none was opened.
- Treat their descriptions as leads only. Claims that could be tested were (E-20261109-02): ATM vs ITM, the 2 %/2 % open rule, the 30-minute ORB bot, the 30 % stop with a trail. Not reproduced as claimed.
