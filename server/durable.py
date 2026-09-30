"""Durable copy of the paper account and the opening snapshots: any server disk can be lost (Render's free
disk is wiped on every sleep, restart and deploy; a VM can be rebuilt).

The files are committed to a branch of the GitHub repo (default `paper-state`) through the contents API, at the
same paths as on disk (data/paper_ledger.json, data/paper_orders.jsonl, data/paper_queue.jsonl,
data/live_snapshots/<date>.json). Render and GitHub Pages build only `main`, so these commits redeploy nothing;
the nightly scan job copies the snapshots from this branch.

When it writes (never on a mark alone):
- at once (checked every FAST_CHECK s): a fill, an exit, a stop trigger, a cash change, a queued order, a new
  order-log line, a new opening snapshot;
- a 15-minute snapshot (SNAPSHOT_EVERY) of the ledger when only its marks changed.

On start: the ledger is taken from the durable copy when the local one is missing or older (its `saved_at`),
the order log when the local one is missing or shorter, the queue and snapshots when missing.

    LEDGER_GITHUB_TOKEN   fine-grained token: this repository only, Contents read and write
    LEDGER_GITHUB_REPO    owner/name (default sherwingm/project-f-0)
    LEDGER_GITHUB_BRANCH  default paper-state
Set the token on ONE server only (the primary); a mirror server must not write the account.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import threading
import time
from pathlib import Path

import requests

log = logging.getLogger("durable")
LEDGER, ORDERS, QUEUE, SNAPSHOTS = "paper_ledger.json", "paper_orders.jsonl", "paper_queue.jsonl", "live_snapshots"
FAST_CHECK = 10          # seconds between checks
SNAPSHOT_EVERY = 900     # seconds: the ledger's 15-minute snapshot when only marks changed
API = "https://api.github.com"


class GitHubStore:
    """get / put whole files on one branch through the GitHub contents API."""

    def __init__(self, repo: str, branch: str, token: str, prefix: str = "data/", session=None):
        self.repo, self.branch, self.prefix = repo, branch, prefix
        self.s = session or requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28"})
        self._sha: dict[str, str] = {}

    def ensure_branch(self) -> None:
        r = self.s.get(f"{API}/repos/{self.repo}/git/ref/heads/{self.branch}", timeout=30)
        if r.status_code == 200:
            return
        main = self.s.get(f"{API}/repos/{self.repo}", timeout=30).json()["default_branch"]
        sha = self.s.get(f"{API}/repos/{self.repo}/git/ref/heads/{main}", timeout=30).json()["object"]["sha"]
        r = self.s.post(f"{API}/repos/{self.repo}/git/refs", json={"ref": f"refs/heads/{self.branch}", "sha": sha}, timeout=30)
        r.raise_for_status()
        log.info("created branch %s for the paper account", self.branch)

    def get(self, name: str) -> bytes | None:
        r = self.s.get(f"{API}/repos/{self.repo}/contents/{self.prefix}{name}", params={"ref": self.branch}, timeout=30)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        d = r.json()
        self._sha[name] = d["sha"]
        if d.get("content"):
            return base64.b64decode(d["content"])
        raw = self.s.get(d["download_url"], timeout=60)            # files over 1 MB come without inline content
        raw.raise_for_status()
        return raw.content

    def put(self, name: str, data: bytes, message: str) -> None:
        body = {"message": message, "branch": self.branch, "content": base64.b64encode(data).decode()}
        if name not in self._sha:
            self.get(name)                                          # learn the current sha (None for a new file)
        if self._sha.get(name):
            body["sha"] = self._sha[name]
        r = self.s.put(f"{API}/repos/{self.repo}/contents/{self.prefix}{name}", json=body, timeout=60)
        if r.status_code in (409, 422):                             # stale sha: refresh once and retry
            self._sha.pop(name, None)
            self.get(name)
            if self._sha.get(name):
                body["sha"] = self._sha[name]
            r = self.s.put(f"{API}/repos/{self.repo}/contents/{self.prefix}{name}", json=body, timeout=60)
        r.raise_for_status()
        self._sha[name] = r.json()["content"]["sha"]


def material(ledger_bytes: bytes | None) -> str:
    """What must never be lost: positions (without their marks), closed trades, cash."""
    if not ledger_bytes:
        return ""
    try:
        st = json.loads(ledger_bytes)
    except ValueError:
        return ""
    pos = [{k: v for k, v in p.items() if k not in ("mark", "unrealised", "unrealised_gross", "liquidation_value",
                                                   "exit_charges_est")} for p in st.get("positions", [])]
    return hashlib.sha1(json.dumps([pos, st.get("closed"), st.get("cash")], sort_keys=True).encode()).hexdigest()


class Mirror:
    def __init__(self, data_dir: Path, store):
        self.dir, self.store = Path(data_dir), store
        self._last: dict[str, bytes] = {}
        self._material = ""
        self._last_snapshot = 0.0
        self.status = {"enabled": True, "last_write": None, "error": None, "restored": []}
        self._stop = threading.Event()

    def _names(self) -> list[str]:
        """The mirrored files present locally, as paths relative to the data dir."""
        names = [n for n in (LEDGER, ORDERS, QUEUE) if (self.dir / n).exists()]
        snap = self.dir / SNAPSHOTS
        if snap.is_dir():
            names += sorted(f"{SNAPSHOTS}/{f.name}" for f in snap.glob("*.json"))
        return names

    def restore(self, snapshot_days: list[str] | None = None) -> list[str]:
        """Bring the local disk up to the durable copy: see the module doc for which copy wins."""
        self.dir.mkdir(parents=True, exist_ok=True)
        restored = []
        remote = self.store.get(LEDGER)
        local = (self.dir / LEDGER).read_bytes() if (self.dir / LEDGER).exists() else None
        if remote is not None and (local is None or saved_at(remote) > saved_at(local)):
            (self.dir / LEDGER).write_bytes(remote)
            restored.append(LEDGER)
        longer = lambda r, l: r.count(b"\n") > l.count(b"\n")             # the order log only grows
        for name, newer in ((ORDERS, longer), (QUEUE, lambda r, l: False)):
            r = self.store.get(name)
            p = self.dir / name
            if r is not None and (not p.exists() or newer(r, p.read_bytes())):
                p.write_bytes(r)
                restored.append(name)
        for d in snapshot_days or []:
            p = self.dir / SNAPSHOTS / f"{d}.json"
            if not p.exists():
                r = self.store.get(f"{SNAPSHOTS}/{d}.json")
                if r is not None:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(r)
                    restored.append(f"{SNAPSHOTS}/{d}.json")
        for n in self._names():                               # what the durable copy now matches
            self._last[n] = (self.dir / n).read_bytes()
        self._material = material(self._last.get(LEDGER))
        self._last_snapshot = time.time()
        self.status["restored"] = restored
        if restored:
            log.info("paper account restored from the durable copy: %s", ", ".join(restored))
        return restored

    def flush(self, force: bool = False, now: float | None = None) -> list[str]:
        """Write what changed: at once for anything but marks, the ledger's marks every SNAPSHOT_EVERY seconds."""
        now = time.time() if now is None else now
        cur = {n: (self.dir / n).read_bytes() for n in self._names()}
        changed = [n for n, b in cur.items() if self._last.get(n) != b]
        if not changed:
            return []
        mat = material(cur.get(LEDGER))
        marks_only = changed == [LEDGER] and mat == self._material
        due = now - self._last_snapshot >= SNAPSHOT_EVERY
        if marks_only and not (force or due):
            return []
        for n in changed:
            self.store.put(n, cur[n], f"paper account: {n}")
            self._last[n] = cur[n]
        if LEDGER in changed:
            self._material, self._last_snapshot = mat, now
        self.status.update(last_write=time.strftime("%Y-%m-%d %H:%M:%S"), error=None)
        return changed

    def run(self) -> None:
        while not self._stop.wait(FAST_CHECK):
            try:
                self.flush()
            except Exception as exc:  # noqa: BLE001 - keep trying; the status shows the error
                self.status["error"] = str(exc)[:300]
                log.warning("paper account mirror: %s", exc)

    def start(self) -> None:
        threading.Thread(target=self.run, name="paper-mirror", daemon=True).start()

    def stop(self) -> None:
        self._stop.set()


def saved_at(ledger_bytes: bytes | None) -> str:
    try:
        return json.loads(ledger_bytes).get("saved_at") or ""
    except (TypeError, ValueError):
        return ""
