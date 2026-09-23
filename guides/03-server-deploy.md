# 03 · Running the server (Path B)

Result: the server runs on a machine that stays on during market hours, restarts itself, and
rebuilds the scan every evening.

## Where to run it

| Option | Pros | Cons | Static IP |
|---|---|---|---|
| Old laptop / mini PC / Raspberry Pi at home | ₹0, Indian residential IP (NSE archive works), fastest to set up | Must stay on 09:00–16:00 and around 20:30 IST; home power/net outages | ACT/Airtel business static IP add-on, roughly ₹150–300 + GST/month; Jio residential static IP is often refused |
| Small VPS in India (AWS Lightsail Mumbai, DigitalOcean Bangalore) | Always on, fixed IP included, ~10 ms to NSE | ₹300–600/month; NSE's archive server often 403s datacenter IPs, so the EOD build may need to run at home and be pushed | Included |
| Render / Streamlit Cloud free tiers | Free | Sleep when idle, US IPs blocked by NSE archives, no fixed IP → cannot place real orders | None |

Recommendation: start on a home machine with `PAPER=true` (no static IP needed). Move to a VPS
or add a home static IP only when you switch to real orders.

## Install

```bash
git clone https://github.com/<you>/<repo>.git fo_scanner   # or unzip
cd fo_scanner
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-server.txt
cp .env.example .env && nano .env        # fill in as per guide 02
python -m scanner.build                  # first scan; must end with "F&O data: ok"
uvicorn server.app:app --env-file .env --host 0.0.0.0 --port 8000
```

Open `http://<machine-ip>:8000/` from a browser on the same network: user `user`, password
`APP_PASSWORD`. The log should show `live feed on (Groww): LTP every 30s, futures OI refreshed 60
contracts per poll`. During market hours the Live % chip appears within a minute.

## Keep it running (Linux, systemd)

`/etc/systemd/system/fo-scanner.service`:

```ini
[Unit]
Description=F&O scanner
After=network-online.target

[Service]
User=<your-user>
WorkingDirectory=/home/<your-user>/fo_scanner
EnvironmentFile=/home/<your-user>/fo_scanner/.env
ExecStart=/home/<your-user>/fo_scanner/.venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fo-scanner
sudo systemctl status fo-scanner      # running?
journalctl -u fo-scanner -f           # live log
```

On Windows, use Task Scheduler with "Run whether user is logged on or not" and the same uvicorn
command; on macOS, a launchd plist or simply a Terminal window left open (the machine must not
sleep: System Settings → Energy → prevent sleeping).

## The evening rebuild

The server rebuilds the scan by itself at 20:30 IST on weekdays (`POST /api/rebuild` does it on
demand). If your server is on a VPS and the rebuild fails with a 403 from NSE, run the build at
home and copy `data/scan.json` to the server, or push it through git and `git pull` on the
server; the server reloads the file on its next rebuild call or restart.

## Ports and safety

- Do not open port 8000 to the internet. Reach it from your phone over Tailscale (guide 04),
  which encrypts everything and needs no port forwarding.
- HTTP basic auth protects every route; the password lives only in `.env`.
- `MAX_LOTS_PER_ORDER` and `MAX_ORDERS_PER_DAY` are enforced on the server, not in the page.
- Back up `.env` somewhere safe and never commit it (it is in `.gitignore` — check with
  `git status`).

## Static IP, when you get there

- **Home:** ask your ISP for a static IP add-on on the connection the server uses. Airtel and ACT
  sell it on business plans; confirm it is IPv4 and does not change on router restart.
- **VPS:** the IP is fixed by default; note it before registering with Groww, because a rebuilt
  droplet gets a new one and Groww allows one change per week.
- Register the IP in Groww (guide 02, step 5), then set `PAPER=false` only after guide 05's
  checklist.
