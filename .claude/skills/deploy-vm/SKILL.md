---
name: deploy-vm
description: Deploy pushed changes of this project to the AWS paper-trading VM (fo-scanner) safely - check the market clock, back up, pull, restart, verify the endpoints. Use when the user asks to update, deploy or restart the live server. Manual only; never during market hours.
disable-model-invocation: true
---

# Deploy to the VM (paper server)

Everything here is read-only except the restart. Never print secrets (`.env`, APP_PASSWORD). Never deploy a rule change the user has not approved. This is a paper server: no real orders exist.

1. **Push first.** Commit only your own files, `git pull --rebase --autostash`, `git push`. Note the short hash you will deploy.
2. **Check the market clock on the VM, not on this PC** (the PC clock is about 5.5 h behind IST):
   `ssh -o BatchMode=yes fo-scanner 'TZ=Asia/Kolkata date "+%a %d %b %H:%M"'`
   - Do NOT restart between 09:00 and 15:40 IST on a session day (weekends and holidays are safe). If inside that window, stop and tell the user when it is safe. Check `data/nse_holidays.json` and `data/special_sessions.json` for the day.
3. **Back up and update** (on the VM, dir `/home/ubuntu/fo_scanner`):
   - `S=$(date +%s); mkdir -p ~/deploy_backup_$S; cp data/g1_ledger.json data/g1c_ledger.json data/xp_ledger.json ~/deploy_backup_$S/ 2>/dev/null` and copy any other modified tracked file (`git status --short | grep '^ M'`).
   - `git checkout -- .` (the server rewrites `data/scan.json` each run, so this is expected), then `git pull --rebase`.
   - If the pull aborts because an untracked `data/live_snapshots/<day>.json` would be overwritten: confirm it is identical to the committed copy (`git show origin/main:<path> | cmp - <path>`), move it to `~/deploy_backup_snap_$S/`, pull again.
   - Confirm `git log --oneline -1` shows the hash from step 1.
4. **Restart:** `sudo systemctl restart fo-scanner`, then wait about 55 seconds (the first request right after a restart can fail; retry after 20 s).
5. **Verify** (inside the VM shell: `set -a; . ./.env; set +a`, never echo it):
   - `systemctl is-active fo-scanner` is `active`.
   - HTTP 200 with `curl -s -o /dev/null -w "%{http_code}" -u user:$APP_PASSWORD localhost:8000<path>` for `/index`, `/api/index/g1`, `/api/index/g1c`, `/api/index/xp`, `/api/index/nt`, `/api/index/nt_sensex` (add any route you changed).
   - `grep -c "^PAPER=true" .env` prints 1.
   - `journalctl -u fo-scanner --since -2min --no-pager | grep -i "traceback"` is empty (old websocket "ConnectionTerminated" lines are known noise; report them, do not hide them).
   - A ledger the change touched still loads (open position and trade counts unchanged; a new strategy's ledger file appears only at its first save).
6. **Log and report:** one line in `PROGRESS.md` (what, hash, time, checks), then tell the user in plain words: hash, time, which endpoints answered, any error line seen. End with the "Still running:" line and the error-count line from `CLAUDE.md`.

If a step fails, stop, say which step and the exact error, and do not retry in a loop. Rolling back: `git checkout <previous hash>` on the VM and restart (outside market hours), after telling the user.
