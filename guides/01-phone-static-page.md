# 01 · The end-of-day page on your phone (Path A)

Result: `https://<your-github-name>.github.io/<repo>/` opens the scan on your phone, and it
refreshes itself every weekday evening. About 15 minutes.

## 1. Build once on your computer

```bash
cd fo_scanner
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m scanner.build
```

Check `docs/index.html` opens in your browser and the header shows yesterday's date.

## 2. Push the folder to GitHub

Create an empty repository on github.com (public is simplest; Pages on a private repo needs a
paid plan). Then:

```bash
git init
git add .
git commit -m "F&O scanner"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

`.gitignore` already keeps the 50 MB of eod2 price history and the NSE cache out of the repo.

## 3. Turn on GitHub Pages

Repository → **Settings** → **Pages** → under *Build and deployment* choose
**Deploy from a branch**, branch `main`, folder **/docs** → Save.

After a minute the page shows your URL. Open it on your computer first to confirm.

## 4. Add it to your phone's home screen

- **Android (Chrome):** open the URL → menu ⋮ → **Add to Home screen** → Add.
- **iPhone (Safari):** open the URL → Share button → **Add to Home Screen** → Add.

It opens full-screen like an app, with the disclaimer band fixed at the bottom. Rows expand on
tap; sort chips and the label counts at the top are the filters.

## 5. Make it refresh every evening

`.github/workflows/daily.yml` runs at **20:30 IST, Monday to Friday**, rebuilds the page and
commits it; Pages redeploys within about a minute. Turn it on once:

Repository → **Actions** → enable workflows if asked → *Daily F&O scan* → **Run workflow**.

Open the run's log. If it ends with `F&O data: ok`, you are done: the page will update itself.

If it ends with `F&O data: unavailable ... 403`, NSE's archive server is refusing GitHub's
datacenter IPs (this happens; see guide 06). The fix is to run the build from home instead:

```bash
# once a day after 19:30 IST, from a normal home/mobile connection
python -m scanner.build && git add docs data/scan.json && git commit -m "scan" && git push
```

To automate that on the home machine:

- **Linux/macOS:** `crontab -e` and add
  `30 20 * * 1-5 cd /path/to/fo_scanner && .venv/bin/python -m scanner.build && git add docs data/scan.json && git commit -m scan && git push`
- **Windows:** Task Scheduler → Create Basic Task → daily 20:30 → run
  `C:\path\to\fo_scanner\.venv\Scripts\python.exe -m scanner.build` followed by the git commands
  in a `.bat` file.

Either way the phone URL stays the same; only where the build runs changes.

## 6. Reading the date at the top

The page always says which session it shows ("Closing data of Tue 22 Sep 2026"). The price and
volume side comes from the `eod2_data` repository, which usually syncs in the evening; if it has
not synced yet when the job runs, the page is one session behind and says so. Re-run the build
later, or move the cron time to 21:30 IST.

## Optional: the page-level AI read-out on the static page

```bash
pip install anthropic
ANTHROPIC_API_KEY=sk-... python -m scanner.build --commentary
```

Adds three descriptive paragraphs under the summary. Same rules as the per-stock reading: it
describes, it does not recommend, and any output with trade-instruction language is dropped.
