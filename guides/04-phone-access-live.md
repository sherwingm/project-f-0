# 04 · Reaching the live server from your phone (Path B)

Result: a private URL that works from anywhere (home Wi-Fi, mobile data, office) without opening
any port on your router.

## 1. Tailscale (free for personal use)

Tailscale gives your server and your phone a private network between them, encrypted end to end.

On the server:

```bash
curl -fsSL https://tailscale.com/install.sh | sh     # Linux; Windows/macOS: download the app
sudo tailscale up
```

Follow the printed link to sign in (Google/Microsoft/GitHub account). Note the machine's name
in the Tailscale admin page, for example `homepc`.

On the phone: install **Tailscale** from Play Store / App Store, sign in with the same account,
toggle it on.

Now open, in the phone browser:

```
http://homepc:8000/
```

(If the short name does not resolve, enable **MagicDNS** in the Tailscale admin console, or use
the machine's `100.x.y.z` Tailscale IP.)

Log in with user `user` and your `APP_PASSWORD`. The browser remembers it.

Add to Home Screen exactly as in guide 01, step 4. The icon opens the live page.

## 2. What is different on the live page

- **Live % and Live OI %** sort chips appear while the market is open; the count line shows the
  time of the last poll. Rows keep their EOD numbers; live values sit beside them.
- **Strike tables** (expand a row) show EOD OI per strike plus live premium/OI when the market
  is open; collapse and expand the row to pull the option chain again (one Groww call).
- **Explain these numbers** appears inside a row only if `ANTHROPIC_API_KEY` is set. It is
  cached per stock per day.
- **Orders** button at the top right opens orders and positions. In paper mode they are your
  simulated fills from `data/paper_orders.jsonl`.

## 3. Placing a paper order from the phone

1. Expand a row → tap a strike, or tap **Order: <symbol> future**.
2. The sheet: Call/Put, Buy/Sell, lots (max 5), Limit/Market, price. Badge says **PAPER**.
3. **Review** shows the exact contract, quantity (lots × lot size from Groww's instrument file),
   notional, estimated margin from Groww, and today's order count against the daily cap.
4. **Record paper order** → a fill at the reference price is written locally. Check **Orders**.

Every review creates a 90-second confirmation token; if you edit anything, review again. Nothing
is sent without the tap on Place.

## 4. When you switch to real orders

The badge turns **LIVE BROKER** (red), Place is red, and an acknowledgement checkbox appears on
every order. Margin comes from Groww's margin endpoint; rejections come back as a readable error
in the sheet. Order status then updates from Groww's order list.

Do the checklist in guide 05 first.

## 5. Bookmarks that help

- `http://homepc:8000/api/live` — raw live snapshot (JSON) to confirm the feed is polling
- `http://homepc:8000/api/scan` — the current scan (JSON)
- `journalctl -u fo-scanner -f` on the server — the log, if something looks stale
