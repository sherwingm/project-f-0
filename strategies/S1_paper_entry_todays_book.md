# Paper buys wait for today's order book (plan, not live)

Status: **built 2 Nov 2026** (user: "build it with tests now, and deploy"); deploy after 15:45, never in market hours.
As built (DECISIONS.md 2026-11-02): `old_book` is checked on Upstox stream quotes only and only before 09:30; the
exits are unchanged (a trade is only bought on today's book, and the stream keeps that day's open); `entry_quote`
records `todays_book` and `day_open` (not `todays_book_since`: the entry probe already records each second).
Tests: `tests/test_todays_book.py`.

Plan as written 1 Nov 2026 ("Yes, plan the fix"):

## The problem (data: `scanner/fade_live_retest.py`, `data/results/S1_fade_live_retest.xlsx`)
For a few seconds after 09:15 the Upstox stream still sends the previous session's last bid / ask for an option, while
today's trades print elsewhere. 8 of the 23 live fade buys of 27 – 30 Oct were filled on that old ask:

| Day | Stock | Booked buy | First ask on today's book | Caught by the 27 Oct fix? |
|---|---|---|---|---|
| 27 Oct | RECLTD | 4.90 | 3.00 (09:15:34) | yes (last trade yesterday) |
| 27 Oct | TATACONSUM | 12.10 | 6.10 | yes |
| 27 Oct | APLAPOLLO | 16.70 | 13.70 | yes |
| 27 Oct | SONACOMS | 6.50 | 3.30 | yes |
| 27 Oct | PAYTM | 8.80 | 7.20 | yes |
| 29 Oct | JSWENERGY | 6.60 | 4.40 (09:15:19) | **no** |
| 30 Oct | GODREJCP | 14.40 | 47.20 (spread ≤ 10 %) | **no** |
| 30 Oct | BLUESTARCO | 21.80 | 46.75 (09:15:16) | **no** |

The 27 Oct fix (32595932, `server/peak.py: not_traded_today`, on the VM) waits only while the option's **last trade** is
from before 09:15. On 29 and 30 Oct a trade had already printed today, so the last-trade time was today's, but the
**bid / ask was still yesterday's**. A real order could not have filled there: a buy limit above the market fills lower,
one below it does not fill. As booked the 23 trades made −3.5 %; re-made on today's book they make −12.2 %.

## What marks the old book (checked on `paper-state:data/entry_probe/`, every second 09:15 – 09:20, 23 and 27 – 30 Oct, 309 contracts)
On the old book the quote still carries **yesterday's day volume** (e.g. JSWENERGY 1,420,075 at 09:15:03) and **no
opening price for today** (`ohlc.open` empty). The first quote of today's book carries today's open and a volume that has
restarted from zero (GODREJCP: 429,500 with no open at 09:15:02 → 4,500 with open 19.05 at 09:15:05).

**Rule:** an option's quote is on **today's book** once it shows today's open (`ohlc.open > 0`) or a day volume of 0
(nothing traded yet today, but the book is today's). Before that, the quote is the old book. Once today's book is seen
for a contract, it stays today's for the day (a later quote without the open, e.g. from the Kotak fallback, does not
send it back).

Check on the probe data, 28 – 30 Oct (the 27 Oct bought strikes were not in the probe after 09:15:04, but their last
trade was yesterday's, which the 27 Oct fix already catches):
- the 3 old-book buys (JSWENERGY, GODREJCP, BLUESTARCO): **all 3 held back** until 09:15:20 / 09:15:05 / 09:15:18;
- the 14 normal live buys: **0 held back** (each contract was on today's book before its buy second).

## The change (one place, used everywhere a quote can buy or sell)
1. `server/peak.py`: `old_book(quote, now)` = `not_traded_today(quote, now)` **or** (the quote has a day volume > 0 and no
   today's open). Applied only to stream quotes and to any quote that carries `volume` and `ohlc`; a quote without
   those fields (check Kotak's `quote_many` shape first) keeps today's last-trade check only, so a Kotak-only day can
   never wait forever.
2. Use `old_book` where `not_traded_today` is used today: the fade entry walk (`server/fade.py: _entries`, the chosen
   strike and the whole-book "every quote is yesterday's" wait), the below-₹2 rule (`_sub2`), and Arm A / B's 09:15
   entries (`server/rules.py`). The wait text says "the bid / ask is still yesterday's book".
3. The real-order fill (`server/order_sim.py`, "filled from the next quote"): a quote on the old book never fills a buy;
   the order waits for today's book within its 60 s, as an unfilled buy would.
4. Exits: the 09:16 stop and trail (`fast_tick`, `_track_v12`) ignore an old-book quote for that contract. The longest
   old book seen was 35 s (RECLTD, to 09:15:34), so this should never bite, but a stop must not fire on a stale bid.
5. Record: `entry_quote` gains `todays_book: true/false` and `todays_book_since` (first second seen), so the next days
   show how long each buy waited.

## Tests (before any deploy)
- `tests/test_peak_capture.py` (or a new `tests/test_todays_book.py`): the four probe sequences above as fixtures
  (JSWENERGY, GODREJCP, BLUESTARCO held back; LT, ADANIPORTS, NAUKRI not), a zero-volume book counts as today's, a quote
  with no volume / ohlc fields is never held back by rule (b), stickiness after the first today's quote.
- `tests/test_fade.py`: an entry on an old-book quote waits and buys on the first today's-book quote; the fill price is
  today's ask; a 15:20 refusal still happens if today's book never arrives.
- Full `pytest` run.

## After deploy (measure, no rule change)
- Each day: how many buys waited, for how long, and the ask they waited from vs the ask they bought at
  (`entry_quote.todays_book_since`).
- `scanner/fade_live_retest.py` re-run as more websocket days come in: the "as booked" and "today's book" results
  should now agree.

## What this is not
Not an S1 rule change: the signal, the walk, the strike choice, the spread and lot limits and the exit are all
unchanged. It stops the paper ledger booking prices no real order could get. It does shift some 09:15 buys a few
seconds later, so it needs the user's go and a DECISIONS.md entry when it ships.
