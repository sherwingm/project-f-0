# 17 · The always-on server (primary): a Mumbai VM

Result: the live server (Kotak live data, live labels, the 09:30 snapshot, the paper account) runs on a small VM in
Mumbai that never sleeps. The paper account and the opening snapshots are committed to the repo's `paper-state`
branch (`server/durable.py`), so a restart or a rebuilt VM picks up where it left off. Render becomes a mirror only
(README, *Put it on your phone*). The phone reaches the VM over Tailscale; no port is open to the internet.

Everything below is in the order you run it. `<…>` is yours to fill in. Nothing here places real orders:
`PAPER=true`, `BROKER=none`.

## 1. Create the VM (one of the two)

### A. AWS Lightsail, Mumbai, nano
1. <https://lightsail.aws.amazon.com> → **Create instance**.
2. Region **Mumbai (ap-south-1)**, zone `ap-south-1a`.
3. Platform **Linux/Unix** → **OS Only** → **Ubuntu 24.04 LTS**.
4. Plan **nano** (512 MB; step 3 adds swap). Name `fo-scanner` → **Create instance**.
5. **Networking** tab → **Create static IP** → attach it to `fo-scanner` (free while attached; also the fixed IP a
   broker needs for real orders later, guide 02b).
6. **Networking** → IPv4 firewall: keep **SSH (22)** only. Do not open 8000 (the app is reached over Tailscale).
7. **Connect using SSH** (browser), or download the default key: Account → SSH keys → Mumbai → download, then
   `ssh -i LightsailDefaultKey-ap-south-1.pem ubuntu@<static-ip>`.

Same with the AWS CLI (check the current IDs first with `aws lightsail get-blueprints` / `get-bundles`):
```bash
aws lightsail create-instances --region ap-south-1 --availability-zone ap-south-1a \
  --instance-names fo-scanner --blueprint-id ubuntu_24_04 --bundle-id nano_3_0
aws lightsail allocate-static-ip --region ap-south-1 --static-ip-name fo-scanner-ip
aws lightsail attach-static-ip --region ap-south-1 --static-ip-name fo-scanner-ip --instance-name fo-scanner
```

### B. Oracle Cloud Always Free, Mumbai
1. <https://cloud.oracle.com> (home region **India West (Mumbai)**, chosen at sign-up and fixed) → **Compute** →
   **Instances** → **Create instance**.
2. Image **Canonical Ubuntu 24.04**. Shape **VM.Standard.A1.Flex**, 1 OCPU / 6 GB (Always Free; if Mumbai has
   no A1 capacity, **VM.Standard.E2.1.Micro**, 1 GB).
3. Networking: a public subnet with a public IPv4. **Add SSH keys**: paste your public key.
4. **Create** → `ssh ubuntu@<public-ip>`.
5. Oracle may reclaim Always Free instances it sees as idle; this server polls every 30 s during market hours.

## 2. Clock: IST and NTP
The server schedules by IST (the 09:30 snapshot, 19:45 events, 20:30 rebuild, market-hours polling).
```bash
sudo timedatectl set-timezone Asia/Kolkata
sudo timedatectl set-ntp true
timedatectl                      # "Time zone: Asia/Kolkata (IST, +0530)", "System clock synchronized: yes",
                                 # "NTP service: active"
```
If `NTP service` is not active (Oracle images use chrony): `sudo apt install -y chrony && sudo systemctl enable --now chrony`.

## 3. Base packages and swap
Ubuntu 24.04 ships Python 3.12.
```bash
sudo apt update && sudo apt -y upgrade
sudo apt install -y python3.12 python3.12-venv python3-pip git curl
python3 --version                # Python 3.12.x
# 2 GB swap (needed on the 512 MB nano; harmless elsewhere)
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

## 4. The code
```bash
cd ~
git clone https://github.com/sherwingm/project-f-0.git fo_scanner
cd fo_scanner
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-server.txt
# the event store (the nightly build joins events into the scan); the same seed the GitHub job uses
curl -fL -o data/events.sqlite https://github.com/sherwingm/project-f-0/releases/download/state-seed/events.sqlite
```

## 5. `.env`
Create a fine-grained GitHub token first: GitHub → Settings → Developer settings → Fine-grained tokens →
**Only select repositories: project-f-0** → Repository permissions → **Contents: Read and write**. It lets this
server commit the paper account and the snapshots to the `paper-state` branch. Put it on this server only.
```bash
nano ~/fo_scanner/.env
```
```ini
KOTAK_CONSUMER_KEY=<from your PC's .env>
DATA_PROVIDER=kotak
ORDERS=true
PAPER=true
BROKER=none
SCAN_URL=https://raw.githubusercontent.com/sherwingm/project-f-0/main/data/scan.json
PUBLIC_ACCESS=false
APP_PASSWORD=<your password>
ALLOW_LOTTERY=false
LEDGER_GITHUB_TOKEN=<the fine-grained token>
LEDGER_GITHUB_REPO=sherwingm/project-f-0
TZ=Asia/Kolkata
```
```bash
chmod 600 ~/fo_scanner/.env
```
One `KEY=value` per line, no quotes, no spaces around `=` (systemd reads this file). The position limits
(`RISK_PER_TRADE_PCT=6`, `MAX_OPEN_POSITIONS=3`, `DAILY_LOSS_HALT_PCT=2`, DECISIONS.md) are the defaults.
Step 9 decides whether `SCAN_URL` stays.

## 6. systemd (the unit from guide 03)
```bash
sudo tee /etc/systemd/system/fo-scanner.service >/dev/null <<'EOF'
[Unit]
Description=F&O scanner
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/fo_scanner
EnvironmentFile=/home/ubuntu/fo_scanner/.env
Environment=TZ=Asia/Kolkata
ExecStart=/home/ubuntu/fo_scanner/.venv/bin/uvicorn server.app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now fo-scanner
sudo systemctl status fo-scanner --no-pager
journalctl -u fo-scanner -n 50 --no-pager
```
The log should show the scan read from `SCAN_URL`, `live feed on (kotak)`, `paper engine on`, and no
`paper account mirror off` line (that line means `LEDGER_GITHUB_TOKEN` is missing).

## 7. Tailscale (the phone reaches the VM privately)
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh              # open the printed URL, log in with your Tailscale account
tailscale ip -4                      # 100.x.y.z
sudo tailscale serve --bg 8000       # HTTPS inside your tailnet: https://fo-scanner.<tailnet>.ts.net/
tailscale serve status
```
On the phone: install the Tailscale app, log in with the same account, open
`https://fo-scanner.<tailnet>.ts.net/` → user `user`, your `APP_PASSWORD` → browser menu → *Add to Home Screen*.
With `tailscale up --ssh` you can also close port 22 in the cloud firewall and SSH as `ssh ubuntu@fo-scanner`.

## 8. Check it (during market hours for the live part)
```bash
set -a; . ~/fo_scanner/.env; set +a
curl -s -u "user:$APP_PASSWORD" http://127.0.0.1:8000/api/paper/summary | python3 -m json.tool | grep -A4 persistence
#   "enabled": true, "error": null
curl -s -u "user:$APP_PASSWORD" http://127.0.0.1:8000/api/live | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d['updated_at'], d['market_open'], len(d['quotes']), d['error'])"
#   market hours: a fresh time, True, ~213 quotes, None
sudo systemctl restart fo-scanner && sleep 20
curl -s -u "user:$APP_PASSWORD" http://127.0.0.1:8000/api/paper/positions | python3 -c \
  "import json,sys; print([p['tradingsymbol'] for p in json.load(sys.stdin)])"
#   the same open positions as before the restart
```
The paper account is visible at `https://github.com/sherwingm/project-f-0/tree/paper-state/data`.

## 9. The nightly EOD build: on the VM, or keep GitHub's
Test whether NSE's archives serve this VM's IP (the F&O bhavcopy of the last session):
```bash
d=$(date -d "$( [ $(date +%u) -eq 1 ] && echo '3 days ago' || echo yesterday )" +%Y%m%d)
curl -s -o /dev/null -w "%{http_code}\n" -A "Mozilla/5.0" \
  "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_${d}_F_0000.csv.zip"
curl -s -o /dev/null -w "%{http_code}\n" -A "Mozilla/5.0" \
  "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_${d}_F_0000.csv.zip"
```
(After a holiday, pick the last session by hand.)

- **403 (refused)**: keep the GitHub build. Leave `SCAN_URL` in `.env`; the server reads the scan at start-up and
  at 21:00 and 22:00 IST. Nothing else to do.
- **200 (served)**: build on the VM. Remove the `SCAN_URL` line from `.env` and restart; the server then runs
  the events at 19:45 and rebuilds the scan at 20:30 IST itself. Add the nightly cron as a second attempt (NSE
  sometimes publishes late):
  ```bash
  sed -i '/^SCAN_URL=/d' ~/fo_scanner/.env && sudo systemctl restart fo-scanner
  .venv/bin/python -m scanner.build        # once by hand: must end with "F&O data: ok"
  crontab -e
  ```
  ```cron
  # the VM's clock is IST (step 2): 21:15 IST, Monday to Friday
  15 21 * * 1-5 . /home/ubuntu/fo_scanner/.env; curl -s -u "user:$APP_PASSWORD" -X POST http://127.0.0.1:8000/api/rebuild >> /home/ubuntu/fo_scanner/data/rebuild.log 2>&1
  ```
  The GitHub job keeps building the Pages site either way.

## 10. Render becomes the mirror
Once step 8 shows the VM's live feed during market hours: Render dashboard → **fo-scanner** → **Environment** →
set `DATA_PROVIDER=none`, and make sure `LEDGER_GITHUB_TOKEN` is **not** set there (only the primary writes the
paper account) → **Save** (Render redeploys).

## 11. Updates
```bash
cd ~/fo_scanner && git pull && .venv/bin/pip install -r requirements-server.txt && sudo systemctl restart fo-scanner
```
The restart reloads the paper account from disk; if the disk were lost, from the `paper-state` branch.

## Notes
- Real orders stay off (`PAPER=true`, DECISIONS.md). When the time comes, the Lightsail static IP (or the Oracle
  reserved IP) is the address to register with the broker (guide 02b).
- Kotak live data needs only `KOTAK_CONSUMER_KEY` (guide 02b); the login fields stay empty for paper trading.
