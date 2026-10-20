#!/usr/bin/env bash
# Start the next queued index-data job (data/index/job_queue.json) when it is safe to: called at the end of every
# index-jobs and recorder run (so the queue does not depend on GitHub's unreliable cron) and by the hourly scheduler.
#   scripts/index_handoff.sh <this run's id, or 0> [recorder]
# Safe means no OTHER index-jobs / recorder run is queued or running: the shared concurrency group keeps one waiting
# run, and a second would cancel it (the recorder above all). On weekdays from 19:15 IST it also leaves the queue alone
# until that day's recorder has started (the recorder's own hand-off then starts the next job).
set -u
self="${1:-0}"; caller="${2:-}"
busy=0
for wf in index-jobs.yml index-recorder.yml; do
  n=$(gh run list --workflow "$wf" --limit 10 --json databaseId,status \
      -q "[.[] | select(.databaseId != $self) | select(.status == \"queued\" or .status == \"in_progress\" or .status == \"waiting\" or .status == \"pending\" or .status == \"requested\")] | length")
  busy=$((busy + ${n:-1}))
done
if [ "$caller" != "recorder" ] && [ "$(date -u +%u)" -le 5 ] && [ "$(date -u +%H%M)" -ge 1345 ]; then
  started=$(gh run list --workflow index-recorder.yml --event schedule --limit 1 --json createdAt \
            -q "[.[] | select(.createdAt >= \"$(date -u +%F)T13:00:00Z\")] | length")
  [ "${started:-0}" = "0" ] && { echo "waiting for today's recorder run"; busy=$((busy + 1)); }
fi
if [ "$busy" != "0" ]; then echo "index-data busy ($busy): not starting the next job"; exit 0; fi
git config user.name "fo-scanner-bot"; git config user.email "bot@users.noreply.github.com"
# this run checked out main when it was created: read the queue as it is now, or a job would be started twice
git pull -q --rebase --autostash origin main || { echo "could not update main: not starting"; exit 0; }
out=$(python -m index_data.job_queue next)
job=$(printf '%s\n' "$out" | sed -n 's/^job=//p'); args=$(printf '%s\n' "$out" | sed -n 's/^args=//p')
[ -z "$job" ] && { echo "queue empty"; exit 0; }
echo "starting: $job $args"
gh workflow run index-jobs.yml -f job="$job" -f args="$args"
git add data/index/job_queue.json
git commit -q -m "index jobs: started $job $args" || true
for i in 1 2 3; do git pull --rebase -q origin main && git push -q origin HEAD:main && break; sleep 5; done
