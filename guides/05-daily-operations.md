# 05 · Day to day

## What happens on a trading day

| Time (IST) | Static page (Path A) | Live server (Path B) |
|---|---|---|
| ~08:30 | — | Server generates the day's Groww access token from the TOTP key (automatic) |
| 09:15–15:30 | — | Polls LTP every 30 s and futures OI in a rolling sweep; strike tables refresh on demand |
| 15:30–19:00 | NSE publishes the F&O bhavcopy; eod2 syncs prices (usually by early evening) | same |
| 20:30 | GitHub Action (or your cron) rebuilds and pushes; Pages redeploys | Server rebuilds `data/scan.json` and reloads |
| evening | Open the icon: labels, OI, PCR, strikes for today's close | same, plus the AI reading if enabled |

Holidays and weekends: nothing runs; the page keeps the last session and says so.

## A two-minute morning check (Path B)

1. Open the icon. The header date should be yesterday's session.
2. After 09:16 the count line shows a poll time and the Live % chip appears. If not, look at
   `/api/live`: `"error"` tells you what the feed hit (guide 06).
3. Orders → positions should match what you expect (empty in paper mode until you place some).

## Logging your own calls (the tracking layer)

Every evening, before you look at labels: tap **Call mode**. Labels and their reasons disappear;
each row shows its numbers and three buttons. Judge a stock from the numbers and tap Bull, Bear or
Neutral. The system's label appears the moment you tap, next to yours. Only stocks you actually
call are recorded; skip the rest.

**Scoreboard** scores every call by what the price did next: with the default horizon of 3
sessions and a ±1% threshold, up more than 1% counts as bullish, down more than 1% bearish, in
between neutral — applied identically to your call and to the system's label. It shows your
accuracy, the system's, how often you agreed with the label before seeing it, and a per-call
list. Change the horizon (1/3/5 sessions) or threshold (±0.5/1/2%) any time; old calls re-score.
Calls live in the phone browser; **Export** once a week to keep a JSON backup (Import merges).

## The evidence verdict (server only, needs an Anthropic key)

**Weigh the evidence** inside a row makes Claude search the last ten days of news for that
company and weigh it against the derivatives numbers. You get a lean (bullish, bearish or mixed)
with a confidence level, the news it found with links and direction, its reasoning, the risks to
that read, and what would flip it. It is an assessment of evidence, not an instruction: the brief
forbids buy/sell/enter/exit/hold language and price predictions, and any output containing them
is discarded in favour of a data-only verdict marked as such. One call per stock per day is
cached; **Refresh with latest news** re-runs it. Each run costs a few rupees of API usage.

## Understanding what you are looking at

- **Label**: Bullish setup = price up, volume above its 20-day average, futures OI rising (a
  pattern commonly read as long buildup). Bearish setup = the mirror. PCR below 0.7 or above 1.3
  can only pull a contradicting pattern back to Neutral. Everything else is Neutral. No OI → Unclassified.
- **Why "…"** inside each row lists the exact conditions and values that produced the label.
- **Strike table**: highest call-OI and put-OI strikes, max pain and ATM are reference points
  from positioning data. They are where open interest sits, not levels to trade.
- **Live OI %** is today's futures OI versus yesterday's close; **OI %** in the EOD row is
  yesterday versus the day before.

The numbers describe; the decisions are yours. Most retail F&O accounts lose money; the
disclaimer band is there for that reason.

## Paper-to-live checklist

Only after all of these are true:

- [ ] Two full weeks of paper orders placed from the phone with no surprises in contract, quantity
      or price.
- [ ] `python -m server.groww_login` works from the server machine.
- [ ] The server machine has a static IP and that IP is registered with Groww (guide 02 step 5).
- [ ] The F&O segment is active in your Groww account and the margin shown on Review matches
      what Groww's app shows for the same order.
- [ ] `MAX_LOTS_PER_ORDER` and `MAX_ORDERS_PER_DAY` are set to what you actually want.
- [ ] `.env` is backed up and not in git.

Then: `PAPER=false` in `.env`, restart the server, place **one lot of one liquid future** on a
Limit order, confirm it appears in Groww's own app, and square it off from the Groww app. Only
after that treat the flow as trusted.

## Backups and updates

- The scan history you care about is `data/scan.json` per day; commit it or copy it if you want
  a record (each file is ~300 KB).
- Paper orders: `data/paper_orders.jsonl`.
- To update code: `git pull` (or unzip over the folder), `pip install -r requirements-server.txt`,
  restart the service. `.env` and `data/` are untouched.
