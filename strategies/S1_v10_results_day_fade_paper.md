# S1 v10 · results-day fade — paper only

**Pre-registered** 2026-10-14, before any paper trade. The user chose "paper only from tomorrow, no backtest claim"
(option a) after the S1 v9 run.

## Why
- S1 v9 (`data/results/event_screen_results.md`) bought strong-number stocks at the results-day open.
  - They **fell** from the open: −0.67 % to the close for NP YoY > 10 % (t −5.7, N 910), −0.97 % for > 25 %
    (t −6.8, N 614). Same stocks on all days: −0.19 %.
  - Weak-number stocks **rose** from the open: +0.56 % to the close, +0.97 % by day 5 (N 305).
- This was seen **after** the run (a side observation), so 2021-2026 cannot confirm it. Only trades after this page
  count.
- The S2 put test shows the other problem: a ₹600–8,000 lot sits far out of the money and misses a ~1 % move. The
  user kept the budget, so this paper run also measures whether a cheap option catches the fade at all.

## Signal
- **Event:** a results filing of an F&O stock with options (NSE announcements, the event store's `results` type,
  with its filing time).
- **Day 0:** the filing day if filed before 09:15 on a session; otherwise the next session.
- **Numbers:** the quarter the filing reports (the last quarter end before the filing date), from the filing's XBRL
  (`data/financials.json`, fetched for the stock if missing). The as-filed values are used.
  - **Strong → buy a put:** net profit YoY > +10 % AND net profit QoQ > 0 AND revenue YoY > 0.
  - **Weak → buy a call:** net profit YoY < −10 % AND net profit QoQ < 0.
  - Anything else, or numbers not yet published: no trade, recorded with the reason.
- Signals are made by `scanner/fade_live.py`, nightly (≈ 20:30 IST) and again before the open (≈ 07:20 IST) for
  filings made overnight; the morning run keeps every signal the nightly made. Sessions follow NSE's F&O holiday list
  (`data/nse_holidays.json`). Filings after the morning run are missed (recorded as a limit, not traded).

## Trade (paper, 1 lot, `server/fade.py`)
- **Expiry:** the current monthly if ≥ 2 sessions remain after day 0; else the next monthly.
- **Entry:** any poll from 09:15 to 15:20 on day 0, retried every 2 minutes per stock until it fills. From the strike
  nearest the **live** stock price, walking **away from the money**: downward for puts, upward for calls (a tie:
  the lower strike for calls, the higher for puts). Take the first strike with:
  - a live bid and ask;
  - a spread ≤ 10 % of the ask;
  - ask ≥ ₹2;
  - one lot at the ask within ₹600–8,000.
  At most 15 strikes are tried. If the at-the-money lot is under ₹600, the walk stops (the rest are cheaper still).
  If nothing fits by 15:20: refused, with the reason.
- **Fill:** the live best ask.
- **Exit:** the first poll from 15:20 on day 0, at the best bid (else the last price − 1 tick). No stop, no overnight
  hold.
- The live ledger keeps quoting each closed contract until its T-2 day (as for S1; the last 10 fade trades, apart
  from S1's), so a longer hold can be read off the same trades later. That reading is descriptive, not a rule change.
- Charges: `server/charges.py`. Positions carry `rule.strategy = "fade"`. The S1 rule exits never touch them.

## Judging (no rule changes during the run)
- **Review at 30 closed trades or 6 weeks, whichever is later.** Report N, mean and median net % of premium, hit
  rate, total ₹, date-clustered t. Puts and calls are reported both pooled and separately.
- **Continue paper** only if the pooled mean is > 0. **Real money** only after ≥ 60 closed trades with mean > 0 and
  date-clustered t ≥ 2, and fills within 20 % of the quotes seen. If paper fails, S1 v10 is closed with its numbers.
- Also checked at the review: the stock's open → close move on the same signals (the S1 v9 measure). This tells
  apart "the fade is gone" from "a cheap option does not catch it".

## Known limits
- The live fill is the ask at the first poll that fits, often minutes after 09:15. The backtest measure used the
  official open (the pre-open auction price).
- Strong / weak use the as-filed XBRL. A filing whose XBRL is late is skipped.
- One lot within ₹600–8,000 is usually out of the money for large stocks. A ~1 % fade may not move it enough to
  cover the spread and charges. This is a known handicap the user accepted.

## Addendum 2026-10-17 · the eight carried trades (a side record, not part of the review)
**Written before the rule runs.** On 2026-10-16 the live server (Render free tier) slept from 11:21 to after 16:00, so
the eight fade trades opened at 09:15 that day were not sold at 15:20: NESTLEIND 1250 PE, INDIANB 810 PE, POLYCAB
7700 PE, PERSISTENT 5900 CE, TECHM 1620 PE, ANGELONE 300 PE, JIOFIN 220 CE, LTF 245 PE (October expiry, 1 lot each).
The same-day exit is part of this page's pre-registered rule, so these trades are **excluded from the v10 review**
(user's decision, 2026-10-17). The user chose to keep them open rather than sell them at Monday's first poll, under
their own exit rule. v10 itself is unchanged: every other fade trade is still bought and sold on day 0.

Rule for the eight (`server/fade.py`, `CARRY_DATES`), checked once a session at the first poll from 15:20 IST on the
last traded price as the close (as the S1 rule trades), the sale at the best bid (else last price − 1 tick):
- `peak` = the highest close since entry, starting at the entry price.
- Sell if close ≤ 0.80 × entry (**stop, −20 %**), or close ≤ 0.75 × peak (**25 % ratcheting trail**, the candidate
  exit named in the arm A exit study, DECISIONS.md), or the session is **T-1** of the expiry. There is no fixed
  profit target. The effective stop is max(0.80 × entry, 0.75 × peak).
- Exit reasons `carry_stop`, `carry_trail`, `carry_t1`.

Limits: the study's report files are not in the repository, so the trail is implemented as defined here. Friday's
15:20 close was not recorded, so `peak` starts at the entry price and first updates on Monday's close. An intraday
move below −20 % is acted on at 15:20, not at once. At the last save (Fri 11:21) INDIANB, TECHM, LTF and POLYCAB were
already below −20 %, so they are expected to be sold on Monday at whatever the bid is then. The result is reported
beside the v10 review, never in it. Any later fade trade that is not sold on its day 0 is treated the same way.

### Update 2026-10-17 (later the same day): the carry rule is retired
After the descriptive backtest (`strategies/S1_v10_backtest_2025_26.md`: same-day exit +5.6 % of premium, carry rule −10.8 %) the user decided to close the eight carried trades and to keep the same-day exit strict for every fade trade from Monday 2026-10-19. The eight are sold at the first poll of that session (`server/fade.py::_exits`, reason `fade_late`), excluded from the v10 review as above. The carry rule above never ran live; `CARRY_DATES` is empty, so no position follows it.
