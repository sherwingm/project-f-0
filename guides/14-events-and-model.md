# 14 · The event feed, the event study, the model and the verdict card

Everything in this guide runs at **zero recurring cost**: no API key, no subscription. Events come
only from the exchanges' own files and filings; free news RSS supplies tier-3 "analyst view" items
and nothing else. The Anthropic-powered readings remain optional and sit *below* the verdict card,
which never depends on them.

## Sources and tiers

| Source | What | Tier |
|---|---|---|
| `nse_ann` | NSE corporate announcements (filings; category, subject, attachment) | 1 |
| `bse_ann` | BSE announcements, mapped to NSE symbols by ISIN via the exchange masters | 1 |
| `nse_block`, `nse_bulk` | NSE block/bulk deal files: client, side, quantity, price | 1 |
| `nse_ban` | F&O security ban list (in/out derived against the previous session) | 1 |
| `nse_pit` | insider trading (PIT/SAST): person category, side, quantity, % of holding | 1 |
| `rss:*` | ET Markets, Business Standard, Moneycontrol | 3 — analyst views only |

Tier 1–2 events can set flags and feed the model. Tier 3 can only ever appear as
"analyst view (news, not a filing)" on the card — never a flag, never a feature.

Network notes (all handled, all logged in `meta.events_status`): every fetcher warms cookies on
nseindia.com, sends browser headers, holds a **shared 1 request/second** limit with exponential
backoff, and works from a home connection. On this build's network BSE's API and Moneycontrol's RSS
refuse all requests (Akamai) and NSE's quote-equity endpoint (shares outstanding) is refused; the
fetchers log and continue. Every F&O stock files on NSE, so tier-1 coverage of this universe does
not depend on BSE. Without shares outstanding, sized events bucket as `minor` (see below) until the
monthly refresh succeeds on a permitted network.

## Taxonomy (all rules in `scanner/events/taxonomy.py`, one editable table)

results_date (board meeting to consider results; dated the *meeting* day) · results (financial
results; a boilerplate "Outcome of Board Meeting" counts only when a results_date exists for that
symbol and day) · order_win · capacity (expansion/commissioning/capex/acquisition) · rating (must
name a SEBI-registered CRA — CRISIL, ICRA, CARE, India Ratings, Acuité, Brickwork, Infomerics — in
the subject or, failing that, on the filing PDF's first page; otherwise discarded) · block_deal /
bulk_deal (side + promoter/fund flag) · insider (promoter/director/employee buy or sell; pledges
dropped) · ban (in/out) · analyst_view (tier 3: broker name + analyst action + a known stock).

**Values and buckets** (`scanner/events/score.py`; thresholds in `scanner/events/config.py`):
₹ values are parsed from the subject (or the PDF's first page for orders/capex), normalised to
₹ crore; market cap = eod2 close on the event date × shares outstanding.

| type | measured against | ignore | minor | significant | major |
|---|---|---|---|---|---|
| order_win, capacity | market cap | < 1% | 1–5% | 5–20% | > 20% |
| block/bulk deal | shares outstanding* | < 0.5% | 0.5–2% | 2–5% | > 5% |
| insider | % of company traded | < 0.1% | 0.1–1% | 1–3% | > 3% |
| rating, results, results_date, ban | — | | | always | |

*Free float is not published free of charge; shares outstanding is the documented fallback and is
what is used. A sized event whose size is unknown buckets `minor` — never silently ignored.

## Running it

```bash
python -m scanner.events.run --day 2026-09-24                    # the daily run (19:45 IST hook)
python -m scanner.events.run --backfill 2023-01-01 2026-09-24    # resumable 3-year fill
python -m scanner.events.run --backfill ... --rating-attachments # 2nd pass: resolve rating PDFs
python -m scanner.events.run --fixtures                          # one no-network day for testing
```

The server runs events at 19:45 IST and the scan build at 20:30, so `scan.json` carries each
stock's `events` block: `today`, `last_10` (tier 1–2, bucket ≠ ignore), `upcoming` (with sessions),
`analyst_view` (labelled), and `flags` — the model features.

## The event study (`python -m scanner.event_study --since 2023-01-01`)

For every tier-1/2 event: the stock's return **minus NIFTY 50's** (CAR) over pre (close T−5→T−1),
day (close T−1→T) and post (close T+1→T+5, so it excludes T+1, the day the results beat/miss proxy is
measured on), per type / subtype / bucket, with count and, for every window, mean, median, share
positive and a t-statistic. How to read it:

- **pre vs post is the "buy the rumour, sell the news" test.** A positive pre-window with a flat or
  negative post-window means the move happened before the filing became public.
- A t-statistic below about 2 means the mean is not distinguishable from zero at that count.
- `results / beat` and `/ miss` split on the day+1 reaction (±2%), **a proxy**: the market's verdict,
  not the accounts.
- Medians beside means: one 100% mover drags a mean; the median tells you the typical case.

`data/event_patterns.json` (per-type pre/day/post means and counts) feeds the verdict card's
"pattern over N cases" lines.

## The model (`python -m scanner.model --train`)

Gradient boosting (LightGBM if installed, else sklearn) predicting whether the **3-session
market-adjusted** return ends above +1% (up), below −1% (down), or between (flat). Features: the
scanner's own numbers, 5/20-session returns, NIFTY's 5-session return, the label, NSE's industry
tag, sessions to the next results date, and the tier-1/2 event flags — each day sees only its own
trailing window. **Walk-forward by quarter**: every fold trains strictly on earlier quarters. No
shuffling, no future data, retrained monthly.

Reading `data/model_report.json` / `python -m scanner.model --report`:

- **Brier score** (0 best): a know-nothing forecaster quoting the base rates scores ≈ 0.63–0.67 on
  three classes. The model earns its place only *below* that.
- **Accuracy vs the class share**: predicting "flat" always scores the flat share; accuracy alone
  flatters. The per-class precision/recall shows whether up/down are ever caught.
- **Top-decile hit rate vs base rate** is the honest line: among the 10% of stock-days the model was
  most sure of "up", how often was it up, against how often anything is up. Close to base = no edge.
- Expect modest numbers. Guide 10's evidence review says daily OI/PCR patterns carry little
  single-stock signal; the model quantifies whatever is there, it does not conjure more.

## The verdict card

Deterministic, fixed rule in `scanner/verdict_rules.py`, computed at build time. Data, model and
events each vote; the lean is bullish/bearish only when every non-zero vote agrees, else mixed.
Confidence is **high** only when all three vote the same way *and* the model is confident
(p ≥ 0.40, margin ≥ 0.15); **low** when two votes disagree or none votes. The card cites the label
and its four numbers, each event flag with its historical pattern, p_up/p_down with the model's
out-of-sample Brier next to them, analyst views clearly labelled as news, and the filing links.
It is a summary of evidence, not advice, and it is identical with or without an LLM.

## What these numbers do and do not mean

They are descriptive statistics of past filings and prices, on ~210 liquid stocks, over a window
that includes one particular market regime. Event patterns drift, agencies re-rate in clusters,
and a flag that back-tested at +1% mean CAR is an average over cases you cannot pick in advance.
Nothing here is a recommendation; the scoreboard (guide 12) exists to test any use of it forward.
