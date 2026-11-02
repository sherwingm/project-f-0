"""Copy the live server's NIFTY 1-second candles to this PC as Parquet (the user, 2026-11-02: "to this PC").

    INDEX_STORE=<index-data checkout>/data/index python -m index_data.pull_1s [--keep-days 7] [--no-delete]

The server's recorder (server/index_recorder.py) writes `data/candles_1s_index/<day>.jsonl` (earlier days gzipped the
next session). For every finished day not yet here, this streams the file over ssh (gzipped on the way), parses it and
writes `<store>/nifty_1s/<day>.parquet`, checked against the server's own line count. The folder is local only: it is
excluded from git (too big for GitHub, ~15-20 MB a day). A server file is removed only when its Parquet here holds the
same row count and the day is older than --keep-days, so the server always keeps the last week.
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .common import IST, STORE

HOST = "fo-scanner"
REMOTE = "/home/ubuntu/fo_scanner/data/candles_1s_index"
FOLDER = "nifty_1s"
DONE_AFTER = time(15, 40)            # today's file is complete once the recorder stops (15:31) and the last write lands
COLS = ["o", "h", "l", "c", "bo", "bh", "bl", "bc", "a", "n", "v"]
# Git's ssh first: Windows' own OpenSSH (what a scheduled task finds on PATH) refuses the key file's permissions.
GIT_SSH = r"C:\Program Files\Git\usr\bin\ssh.exe"
SSH = os.getenv("PULL_SSH") or (GIT_SSH if Path(GIT_SSH).exists() else shutil.which("ssh") or "ssh")


def _ssh(cmd: str, binary: bool = False):
    r = subprocess.run([SSH,"-o", "BatchMode=yes", "-o", "ConnectTimeout=20", HOST, cmd], capture_output=True,
                       check=True, timeout=1800)
    return r.stdout if binary else r.stdout.decode()


def label_parts(label: str) -> tuple[str, str | None, float | None]:
    """(kind, expiry, strike) of a recorder label: 'NIFTY 2026-11-09 23250 CE' → ('CE', '2026-11-09', 23250.0),
    'NIFTY FUT 2026-11-23' → ('FUT', '2026-11-23', None), 'NIFTY 50' / 'NIFTY BANK' / 'INDIA VIX' → ('INDEX', None,
    None)."""
    p = label.split()
    if len(p) == 4 and p[3] in ("CE", "PE"):
        return p[3], p[1], float(p[2])
    if len(p) == 3 and p[1] == "FUT":
        return "FUT", p[2], None
    return "INDEX", None, None


def parse(day: date, lines) -> pd.DataFrame:
    """One row per symbol-second, as recorded (nothing filled or dropped)."""
    rows = [json.loads(x) for x in lines if x.strip()]
    df = pd.DataFrame(rows, columns=["ts", "t", *COLS])
    parts = {s: label_parts(s) for s in df["ts"].unique()}
    df.insert(0, "timestamp", pd.to_datetime(day.isoformat() + " " + df.pop("t")).dt.tz_localize(IST))
    df = df.rename(columns={"ts": "symbol"})
    df.insert(2, "kind", df["symbol"].map(lambda s: parts[s][0]))
    df.insert(3, "expiry", df["symbol"].map(lambda s: parts[s][1]))
    df.insert(4, "strike", df["symbol"].map(lambda s: parts[s][2]).astype(float))
    df[COLS] = df[COLS].astype(float)
    return df.sort_values(["symbol", "timestamp"], kind="stable").reset_index(drop=True)


def write(df: pd.DataFrame, path: Path, server_lines: int) -> None:
    t = pa.Table.from_pandas(df, preserve_index=False)
    t = t.replace_schema_metadata({**(t.schema.metadata or {}), b"server_lines": str(server_lines).encode()})
    tmp = path.with_suffix(".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(t, tmp, compression="zstd")
    tmp.replace(path)


def local_rows(path: Path) -> int | None:
    if not path.exists():
        return None
    md = pq.read_metadata(path)
    ok = (md.metadata or {}).get(b"server_lines")
    return md.num_rows if ok is not None and int(ok) == md.num_rows else None


def remote_days() -> dict[date, str]:
    out = {}
    for name in _ssh(f"ls {REMOTE}").split():
        stem = name.split(".")[0]
        try:
            out[date.fromisoformat(stem)] = name
        except ValueError:
            continue
    return out


def finished(day: date, now: datetime) -> bool:
    return day < now.date() or (day == now.date() and now.time() >= DONE_AFTER)


def pull(day: date, name: str, store: Path) -> int:
    path = f"{REMOTE}/{name}"
    cat = "cat" if name.endswith(".gz") else "gzip -c"
    count = "zcat" if name.endswith(".gz") else "cat"
    n_server = int(_ssh(f"{count} {path} | wc -l").strip())
    blob = _ssh(f"{cat} {path}", binary=True)
    with gzip.open(io.BytesIO(blob), "rt", encoding="utf-8") as f:
        df = parse(day, f)
    if len(df) != n_server:
        raise RuntimeError(f"{day}: parsed {len(df)} rows, server file has {n_server} lines")
    write(df, store / FOLDER / f"{day.isoformat()}.parquet", n_server)
    return len(df)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-days", type=int, default=7, help="server keeps this many days even when copied")
    ap.add_argument("--no-delete", action="store_true")
    a = ap.parse_args(argv)
    store, now = Path(STORE), datetime.now(IST)
    days = remote_days()
    print(f"{now:%Y-%m-%d %H:%M} IST · server has {len(days)} day(s)")
    for day, name in sorted(days.items()):
        dest = store / FOLDER / f"{day.isoformat()}.parquet"
        if not finished(day, now):
            print(f"{day}: still recording, skipped")
            continue
        if local_rows(dest) is None:
            n = pull(day, name, store)
            print(f"{day}: copied {n:,} rows → {dest} ({dest.stat().st_size / 1e6:.1f} MB)")
        else:
            print(f"{day}: already here ({local_rows(dest):,} rows)")
        if not a.no_delete and (now.date() - day).days > a.keep_days and local_rows(dest) is not None:
            _ssh(f"rm -- {REMOTE}/{name}")
            print(f"{day}: removed from the server (copy checked, older than {a.keep_days} days)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
