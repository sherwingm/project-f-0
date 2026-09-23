# Build spec 12 · Free event feed, event study, NSE model, verdict card

You are working in the `fo_scanner` repository (Python 3.11+, EOD scan in `scanner/`, FastAPI server in
`server/`, single-page UI in `templates/index.html`). Read `README.md`, `guides/10-evidence-review.md`,
`guides/13-multi-agent-verdict-review.md` and `guides/11-build-spec-paper-engine.md` first. Implement the steps
below **in order**, running tests after each step and committing after each step with the step name.

Hard constraints:
- **Zero recurring cost.** Everything in this spec runs with no API key and no subscription. The Anthropic API
  (existing `server/verdict.py`, `server/commentary.py`) stays optional and off by default; nothing here may
  depend on it. No local LLMs either (deferred).
- **Official sources only for events.** Exchange filings and exchange data files are the only inputs that can
  create an event flag. Free news RSS is allowed only for tier-3 "analyst view" items. No social media, no
  forums, no tip sites, ever.
- No code path may place a real order. The trade-instruction guard in `server/commentary.py` is not weakened.
  The static page (`python -m scanner.build` → `docs/index.html`) must keep working with no server.
- Every fetcher must work from a home connection (NSE refuses datacenter IPs), warm up cookies from
  `https://www.nseindia.com` first, send browser-like headers, and never exceed 1 request per second.
  Every fetcher has a `--fixture` mode that reads a saved response from `tests/fixtures/` so tests need no network.
- All thresholds are parameters in `scanner/events/config.py` with env overrides and the defaults below.

---

## Step 1 · Event store and schema (`scanner/events/store.py`)

SQLite at `data/events.sqlite`, table `events`:

```
id TEXT PRIMARY KEY        -- source + source_id (dedup)
symbol TEXT                -- NSE symbol (map BSE scrip codes via the NSE/BSE master; drop unmapped)
event_date TEXT            -- YYYY-MM-DD, exchange timestamp date (IST)
event_time TEXT            -- HH:MM IST, null for daily files
type TEXT                  -- see taxonomy
subtype TEXT               -- e.g. upgrade/downgrade, buy/sell, beat/miss, in/out
tier INTEGER               -- 1 official filing/exchange file, 2 registered agency press release, 3 mainstream news
direction INTEGER          -- +1 / -1 / 0
value_cr REAL              -- ₹ crore when a value was parsed, else null
materiality REAL           -- value ÷ market cap, or size measure for deals, else null
bucket TEXT                -- ignore | minor | significant | major
source TEXT                -- nse_ann | bse_ann | nse_block | nse_bulk | nse_ban | nse_pit | rss:<feed>
subject TEXT
url TEXT
raw_json TEXT
fetched_at TEXT
```

Helpers: `upsert(events)`, `events_for(symbol, since, until)`, `upcoming(symbol, sessions)`, `all_of_type(type)`.

## Step 2 · Fetchers (`scanner/events/sources/`)

One module per source, each exposing `fetch(day) -> list[RawItem]` and `backfill(start, end)`; each with
`--fixture` support and a saved fixture in `tests/fixtures/`.

- `nse_announcements.py` — NSE corporate announcements (equities), by date range; keep category, subject,
  attachment URL, symbol, timestamp.
- `bse_announcements.py` — BSE announcements by date; map scrip code → NSE symbol using the BSE/NSE master
  (build `data/cache/bse_nse_map.csv` once from the exchange masters; unmapped rows are dropped and counted).
- `nse_deals.py` — NSE block-deal and bulk-deal daily files: client name, buy/sell, quantity, price.
- `nse_ban.py` — F&O security ban list for the day.
- `nse_pit.py` — insider-trading (PIT) and SAST disclosures: acquirer/disposer category (promoter, director,
  employee), buy/sell, quantity, % of holding where given.
- `rss.py` — free RSS feeds (Economic Times markets, Moneycontrol news, Business Standard markets). Items are
  tier 3 and are only used for analyst-view tagging (Step 3); nothing else.

Rate limit: a shared limiter, 1 request/second, exponential backoff on 429/403, log and continue on any single
failure. Attachment PDFs: download only when the subject has no ₹ value and the type needs one (orders, capex);
extract text from page 1 only.

## Step 3 · Taxonomy and scoring (`scanner/events/taxonomy.py`, `scanner/events/score.py`)

All rules live in one editable table: `(type, source filter, category regex, subject regex, direction rule)`.

| type | detect | direction | notes |
|---|---|---|---|
| `results_date` | category "Board Meeting" + subject results/financial | 0 | creates an upcoming event; `sessions_to_event` computed at join |
| `results` | category "Financial Results" / "Outcome of Board Meeting" with results | 0 (or ±1 when a beat/miss is known from later data) | |
| `order_win` | category Updates/Press Release + subject `order|contract|letter of award|LoA|bagged|awarded|work order` | +1 | value parsed |
| `capacity` | subject `capacity|expansion|commissioning|greenfield|brownfield|capex|new plant|new unit|acquisition|acquire` | +1 | value parsed |
| `rating` | category "Credit Rating" **and** subject/text names a registered CRA: CRISIL, ICRA, CARE, India Ratings, Acuité, Brickwork, Infomerics | +1 upgrade / −1 downgrade or negative watch / 0 reaffirm | anything not naming a registered CRA is discarded |
| `block_deal`, `bulk_deal` | NSE deal files | sign from buy/sell; promoter/FII/named-fund flag | materiality = quantity ÷ free float (fallback: ÷ shares outstanding) |
| `insider` | PIT/SAST | +1 promoter/director buy, −1 sell | materiality = % of holding |
| `ban` | ban list | −1 in / 0 out | |
| `analyst_view` | tier-3 RSS only: `upgrade|downgrade|target price|initiate coverage|overweight|underweight` + broker name | ±1 | **never** an event flag; shown as "analyst view"; not a model feature |

Value parsing: `₹ ?([\d,.]+) ?(crore|cr|lakh|lakhs|mn|million|bn|billion)` with unit normalisation to ₹ crore.
Market cap: price (eod2 close) × shares outstanding from the exchange company master, cached in
`data/cache/shares_outstanding.csv` (refresh monthly). Buckets for orders/capex by value ÷ market cap:
< 1% ignore, 1–5% minor, 5–20% significant, > 20% major. Deals: < 0.5% of float ignore, 0.5–2% minor,
2–5% significant, > 5% major. Insider: < 0.1% ignore, 0.1–1% minor, 1–3% significant, > 3% major.

Tests: fixture filings for every type, including a fake "rating" from a non-registered name that must be
discarded, a ₹5 crore order on a ₹50,000 crore company that must bucket `ignore`, and a ₹800 crore order on a
₹4,000 crore company that must bucket `major`.

## Step 4 · Nightly run and back-fill (`scanner/events/run.py`)

```
python -m scanner.events.run --day 2026-09-24        # today's events from all sources
python -m scanner.events.run --backfill 2023-01-01 2026-09-24   # 3 years, resumable, for the event study
```

The daily run is scheduled at 19:45 IST from the existing rebuild hook (`server/app.py` daily loop and the
GitHub Action) **before** `scanner.build`, so the scan picks the events up. Back-fill writes progress to
`data/cache/events_backfill.json` and can be interrupted and resumed.

## Step 5 · Join into the scan (`scanner/build.py`)

Each stock in `scan.json` gains:

```
"events": {
  "today": [...],                 # events dated the scan session, tier 1–2, bucket ≠ ignore
  "last_10": [...],               # tier 1–2 events in the last 10 sessions
  "upcoming": [{"type": "results", "date": "...", "sessions": 3}],
  "analyst_view": [...],          # tier-3 RSS items, last 5 sessions, labelled as such
  "flags": {"results_soon": 3, "order_win": "major", "rating": "upgrade", "block_deal": "promoter_buy", "ban": true}
}
```

Flags are the model features (Step 7). `meta.events_status` reports the last successful fetch per source.

## Step 6 · Event study (`scanner/event_study.py`)

```
python -m scanner.event_study --since 2023-01-01 --out data/event_study.csv
```

For every historical tier-1/2 event (bucket ≠ ignore): market-adjusted return (stock − NIFTY 50) for each
session from T−5 to T+5, using eod2 closes. Output per event type (and subtype, and bucket): count, mean and
median cumulative abnormal return for the pre-window (T−5→T−1), the event day, and the post-window (T+1→T+5),
share positive, and a t-statistic. For `results`, add beat/miss where the post-day move is available as a
proxy (state that it is a proxy). This is the "buy the rumour, sell the news" table; print it, do not
interpret it. Also write `data/event_patterns.json` (per type: pre, day, post means and counts) for the UI.

## Step 7 · NSE model (`scanner/model.py`)

Gradient boosting (LightGBM if installable, else sklearn HistGradientBoosting) predicting whether the 3-session
market-adjusted return exceeds +1% (up) or −1% (down) vs neither.

Features per stock-day: price change, volume ratio, futures OI change, PCR, label one-hot, 5-session return,
20-session return, sector one-hot (NSE sector index membership), NIFTY 5-session return, `sessions_to_results`,
and the event flags from Step 5 (tier 1–2 only; never `analyst_view`).

Training: build the dataset from cached bhavcopies + eod2 + events for the back-fill window; **walk-forward by
quarter** (train on all prior quarters, test on the next); no shuffling; no feature computed with future data.
Report per fold and overall: accuracy, precision/recall per class, Brier score, and the hit rate of the top-decile
probabilities versus the base rate. Save `data/model.pkl` and `data/model_report.json`. Print the numbers; no
interpretation. Retrain monthly from the rebuild hook.

Inference: `scan.json` per stock gains `model: {"p_up": 0.31, "p_down": 0.22, "p_flat": 0.47, "trained_through": "2026-06-30", "oos_brier": 0.66}`.

## Step 8 · Verdict card (`templates/index.html`)

Deterministic; identical whether or not any LLM exists.

```
Lean: bullish / bearish / mixed        Confidence: low / medium / high
Evidence
  Data      : label + the four numbers
  Events    : each tier-1/2 flag with its historical pattern from event_patterns.json ("results in 3 sessions:
              pre-window +1.2% avg over 412 cases, post-window −0.8%")
  Model     : p_up / p_down with the model's out-of-sample Brier score shown next to it
  Analyst   : tier-3 items, labelled "analyst view (news, not a filing)", with links
  News      : filing links
```

Lean and confidence are computed in code from a fixed, documented rule (in `scanner/verdict_rules.py`):
data lean, model probability and event direction each vote; confidence is high only when all three agree and the
model is confident, low when any two disagree. If the Anthropic API is configured, the existing
"Weigh the evidence" button adds a plain-English summary **below** the card; the card never depends on it.

## Step 9 · Docs and hand-off

- `guides/14-events-and-model.md`: sources, taxonomy table, tiers, buckets, how to read the event-study table
  and the model report, what the numbers do and do not mean.
- Cheat-sheet updates; `.env.example` gains the event/model keys.
- Run all tests, `python -m scanner.build`, confirm the static page renders with the verdict card.
- Final commit: "events + event study + NSE model + verdict card v1".

Report back with: test results; the count of events by type from a 3-year back-fill; the event-study table for
`results`, `order_win`, `rating` and `block_deal`; and the model report (walk-forward accuracy and Brier vs base
rate).
