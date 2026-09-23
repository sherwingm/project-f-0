# Running the F&O scanner on your phone

These guides take you from the zip to a URL on your phone. Read this page, pick a path, then
follow the numbered guides for that path in order.

## Two ways to run it

| | Path A: end-of-day page | Path B: live server |
|---|---|---|
| What you get | The scan of the previous session: labels, OI, PCR, strike tables, 30-day charts, your call log and scoreboard. Rebuilt once a day after close. | Everything in A, plus live LTP, futures OI and PCR during market hours, the per-stock AI reading, and the evidence verdict (numbers + news). Read-only: no order controls. |
| What runs | A static HTML page hosted free on GitHub Pages | A small Python server (FastAPI) on a machine you control |
| Monthly cost | ₹0 | ₹0 with your Kotak Neo consumer key (guide 02b, the chosen path) or an Upstox Analytics Token (02a); AI features cost a few rupees per stock read |
| Time to set up | About 15 minutes | About 45 minutes |
| Guides | 01, 05, 06 | 01 (for the daily rebuild), 02b, 03, 04, 05, 06, 07 |

Order placement exists in the code (`ORDERS=true`, guide 02 for Groww) but is off by default and
is not needed for anything above.

Start with Path A even if you want B: the server reads the same scan file, so nothing is wasted.

## What you need

- A laptop or desktop with Python 3.11+ and Git (Windows, macOS or Linux all work).
- A GitHub account (free) for Path A.
- A phone with Chrome (Android) or Safari (iOS).
- For Path B: your Kotak Neo consumer key (Neo app → More → Trade API → Generate application), and a machine that
  stays on during market hours (an old laptop at home, a Raspberry Pi, or a small VPS in Mumbai
  or Bangalore). An Anthropic API key if you want the AI reading and the evidence verdict.

## One-time check that the build works on your machine

```bash
unzip fo_scanner.zip && cd fo_scanner
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m scanner.build
```

The last line prints something like
`as of 2026-09-22: 31 bullish, 24 bearish, 155 neutral, 0 unclassified | F&O data: ok`.
If it says `F&O data: unavailable ... 403`, your network is being refused by NSE's archive server;
see guide 06 before going further, because every other step depends on this build succeeding.

## The guides

- `01-phone-static-page.md` — put the end-of-day page on your phone (GitHub Pages, Add to Home Screen, daily refresh)
- `02b-kotak-live-paper.md` — Kotak Neo live data with the consumer key only, plus paper trading (the chosen path)
- `02a-upstox-readonly.md` — the same with a 1-year Upstox Analytics Token, if you ever switch
- `02-groww-setup.md` — only if you turn on order placement: subscription, TOTP key, static IP
- `03-server-deploy.md` — run the server on a home machine or VPS and keep it running
- `04-phone-access-live.md` — reach the server from your phone securely and use the live screens
- `05-daily-operations.md` — what happens each day, what to check, the paper-to-live checklist
- `06-troubleshooting.md` — every error seen so far and what fixes it
- `07-compliance.md` — the SEBI/NSE rules that apply to a personal API user, in plain terms
- `08-broker-api-review.md` — the broker comparison this build is based on (reference)
- `09-command-cheatsheet.md` — every command on one page

## What this tool is and is not

It ranks and labels official closing data. Labels are conventional readings of OI, volume and PCR
patterns, not signals. The AI reading describes numbers and is blocked from telling you what to
trade. Orders are never placed without you reviewing and tapping Place; nothing runs unattended.
F&O losses can exceed the capital invested. The disclaimer on every screen is not decorative.
