"""Durable copy of the paper account: the Render free disk is wiped on every sleep, restart and deploy.

The ledger files are mirrored to a branch of the GitHub repo (default `paper-state`) through the contents API.
Render deploys only `main`, so these commits never redeploy the server. On start, any mirrored file missing from
the local disk is restored before the ledger loads.

    LEDGER_GITHUB_TOKEN   fine-grained token: this repository only, Contents read and write (Render dashboard)
    LEDGER_GITHUB_REPO    owner/name (default sherwingm/project-f-0)
    LEDGER_GITHUB_BRANCH  default paper-state

Flushing: a change to the positions, closed trades, cash or the queue is written within FAST_CHECK seconds;
mark-only changes at most every SLOW_FLUSH seconds. Without a token the mirror is off and says so.
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
FILES = ("paper_ledger.json", "paper_queue.jsonl", "paper_orders.jsonl")
FAST_CHECK = 10          # seconds between checks
SLOW_FLUSH = 300         # seconds: mark-only changes are written at most this often
API = "https://api.github.com"


class GitHubStore:
    """get / put whole files on one branch through the GitHub contents API."""

    def __init__(self, repo: str, branch: str, token: str, prefix: str = "paper/", session=None):
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
    def __init__(self, data_dir: Path, store, files=FILES):
        self.dir, self.store, self.files = Path(data_dir), store, files
        self._last: dict[str, bytes] = {}
        self._material = ""
        self._last_flush = 0.0
        self.status = {"enabled": True, "last_write": None, "error": None, "restored": []}
        self._stop = threading.Event()

    def restore(self) -> list[str]:
        """Copy each mirrored file that is missing locally back from the store."""
        self.dir.mkdir(parents=True, exist_ok=True)
        restored = []
        for name in self.files:
            p = self.dir / name
            data = self.store.get(name)
            if data is None:
                continue
            self._last[name] = data
            if not p.exists():
                p.write_bytes(data)
                restored.append(name)
        self._material = material(self._last.get("paper_ledger.json"))
        self.status["restored"] = restored
        if restored:
            log.info("paper account restored from the durable copy: %s", ", ".join(restored))
        return restored

    def flush(self, force: bool = False, now: float | None = None) -> list[str]:
        """Write the files that changed: now for a material change (or force), else at most every SLOW_FLUSH s."""
        now = time.time() if now is None else now
        cur = {n: (self.dir / n).read_bytes() for n in self.files if (self.dir / n).exists()}
        changed = [n for n, b in cur.items() if self._last.get(n) != b]
        if not changed:
            return []
        mat = material(cur.get("paper_ledger.json"))
        urgent = force or mat != self._material or "paper_queue.jsonl" in changed
        if not urgent and now - self._last_flush < SLOW_FLUSH:
            return []
        for n in changed:
            self.store.put(n, cur[n], f"paper account: {n}")
            self._last[n] = cur[n]
        self._material, self._last_flush = mat, now
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
