#!/usr/bin/env bash
# One-shot setup of the always-on VM (Ubuntu 24.04, user ubuntu). Safe to run again.
#   curl -fsSL https://raw.githubusercontent.com/sherwingm/project-f-0/main/deploy/aws/setup.sh | bash
# Then fill ~/fo_scanner/.env (it stops and says so the first time) and run it once more.
set -euo pipefail
APP=/home/ubuntu/fo_scanner
REPO=https://github.com/sherwingm/project-f-0.git

echo "== clock: IST + NTP"
sudo timedatectl set-timezone Asia/Kolkata
sudo timedatectl set-ntp true || true

echo "== packages"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 python3-venv python3-pip git curl

echo "== swap (2 GB)"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

echo "== code"
if [ -d "$APP/.git" ]; then git -C "$APP" pull --ff-only; else git clone "$REPO" "$APP"; fi
cd "$APP"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements-server.txt
[ -f data/events.sqlite ] || curl -fsSL -o data/events.sqlite \
  https://github.com/sherwingm/project-f-0/releases/download/state-seed/events.sqlite || true

echo "== .env"
if [ ! -f .env ]; then
  cp deploy/aws/env.example .env && chmod 600 .env
  echo "Fill in $APP/.env (nano $APP/.env), then run this script again."; exit 0
fi
grep -q "^KOTAK_CONSUMER_KEY=." .env || { echo "KOTAK_CONSUMER_KEY is empty in .env: fill it in, then run again."; exit 1; }
grep -qi "^PUBLIC_ACCESS=true" .env || grep -q "^APP_PASSWORD=." .env ||   { echo "APP_PASSWORD is empty: set one, or PUBLIC_ACCESS=true for no login (reached over Tailscale only)."; exit 1; }
chmod 600 .env

echo "== systemd: server + market-hours watchdog"
sudo cp deploy/aws/fo-scanner.service deploy/aws/fo-scanner-watchdog.service deploy/aws/fo-scanner-watchdog.timer \
  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fo-scanner fo-scanner-watchdog.timer
sleep 15
systemctl --no-pager --lines=0 status fo-scanner | head -5
journalctl -u fo-scanner -n 20 --no-pager
echo "Done. Next: guides/17-always-on-host.md step 7 (Tailscale) and step 8 (checks)."
