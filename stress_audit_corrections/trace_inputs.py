"""Provenance supplement for the stress audit (correction 5). Offline.

Reruns the ORIGINAL committed audit pipeline (s1_stress, g1_stress, trade_audit, build_report) with every network socket blocked and records what it reads, by
three independent mechanisms:
  1. a Python audit hook on open() (Python-level file opens), plus directory-listing events (listdir, scandir, glob, pathlib glob/iterdir);
  2. wrappers on every pandas / pyarrow / Feather / loader entry point that can read a data file natively (these are invisible to the open() hook);
  3. sys.modules, for the repo code that actually ran (compiled-module caching hides most .py opens).
It then CHECKS the result against an expected-file list derived from the loader's own path rules (every NIFTY option file for each G1 trade's days, the S1 inputs).
Outputs of the rerun go to a temporary folder (never to stress_audit/results/), are compared with the committed results and deleted. What stays is
MANIFEST_SUPPLEMENT.json. No new number is produced.

    python -m stress_audit_corrections.trace_inputs
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE_ROOT = ROOT.parent / "fo-index-data"
os.environ.setdefault("INDEX_STORE", str(STORE_ROOT / "data" / "index"))
TMP = ROOT / "stress_audit_corrections" / "_trace_tmp"

opened: set[str] = set()       # python-level opens
native: set[str] = set()       # paths handed to pandas / pyarrow / loader readers
listed: set[str] = set()       # directories listed or globbed
LISTING = {"os.listdir", "os.scandir", "glob.glob", "pathlib.Path.glob", "pathlib.Path.rglob", "pathlib.Path.iterdir", "os.walk"}


def _abs(p):
    try:
        return os.path.abspath(os.fsdecode(p))
    except Exception:
        return None


def _hook(event, args):
    if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else 0
        write = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND))
        if not write:
            a = _abs(args[0])
            if a:
                opened.add(a)
    elif event in LISTING and args:
        a = _abs(args[0]) if isinstance(args[0], (str, bytes, os.PathLike)) else None
        if a:
            listed.add(a)


sys.addaudithook(_hook)


class Blocked(RuntimeError):
    pass


_Real = socket.socket


class _NoSocket(_Real):
    def __init__(self, *a, **k):
        raise Blocked("socket creation attempted")


def _no(*a, **k):
    raise Blocked("network access attempted")


socket.socket, socket.create_connection, socket.getaddrinfo = _NoSocket, _no, _no     # type: ignore[assignment]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _wrap(mod, name):
    orig = getattr(mod, name, None)
    if orig is None:
        return None

    def w(*a, **k):
        for x in list(a[:1]) + [k.get("path"), k.get("path_or_buffer"), k.get("source"), k.get("where")]:
            if isinstance(x, (str, bytes, os.PathLike)):
                p = _abs(x)
                if p:
                    native.add(p)
        return orig(*a, **k)
    setattr(mod, name, w)
    return f"{getattr(mod, '__name__', mod)}.{name}"


def main() -> None:
    import pandas as pd
    import pyarrow
    import pyarrow.feather as pafeather
    import pyarrow.parquet as paparquet
    wrapped = [_wrap(pd, "read_parquet"), _wrap(pd, "read_feather"), _wrap(pd, "read_csv"), _wrap(pd, "read_excel"), _wrap(pd, "read_json"),
               _wrap(pyarrow, "memory_map"), _wrap(paparquet, "read_table"), _wrap(paparquet, "read_pandas"), _wrap(pafeather, "read_feather"), _wrap(pafeather, "read_table")]
    from stress_audit import common as C
    TMP.mkdir(parents=True, exist_ok=True)
    C.OUT = TMP
    from index_data import load as IL
    from scanner import fastio
    wrapped += [_wrap(IL, "read_store"), _wrap(fastio, "read_table")]
    wrapped = [w for w in wrapped if w]
    from stress_audit import build_report as BR
    from stress_audit import g1_stress as G1
    from stress_audit import s1_stress as S1
    from stress_audit import trade_audit as TA
    stash = {}
    _orig_collect = G1.collect

    def _collect():
        df = _orig_collect()
        stash["trades"] = df[["day", "day0", "nxt", "expiry"]].copy()
        return df
    G1.collect = _collect
    S1.main()
    G1.main()
    TA.main()
    BR.main()
    # ---- committed outputs reproduced?
    same = {}
    for f in ("scenario_results_s1.csv", "scenario_results_g1.csv", "sensitivity_s1.csv", "sensitivity_g1.csv", "regimes_s1.csv", "regimes_g1.csv", "trades_s1_all_scenarios.csv",
              "trades_g1_all_scenarios.csv", "s1_ambiguous_trades.csv", "g1_ambiguous_trades.csv"):
        same[f] = (ROOT / "stress_audit" / "results" / f).read_bytes() == (TMP / f).read_bytes()
    with pd.ExcelFile(ROOT / "stress_audit" / "results" / "TRADE_AUDIT.xlsx") as a, pd.ExcelFile(TMP / "TRADE_AUDIT.xlsx") as b:
        same["TRADE_AUDIT.xlsx (all sheets, cell by cell)"] = all(a.parse(s).fillna("NA").astype(str).equals(b.parse(s).fillna("NA").astype(str)) for s in a.sheet_names)
    # ---- the code that ran: every repo module in sys.modules (compiled-module caching hides their opens)
    code = {}
    for name, mod in sorted(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and f.endswith(".py"):
            fp = Path(f).resolve()
            if str(fp).lower().startswith(str(ROOT).lower()) and "stress_audit_corrections" not in str(fp):
                code[str(fp.relative_to(ROOT)).replace("\\", "/")] = {"module": name, "bytes": fp.stat().st_size, "sha256": sha(fp)}
    # ---- the data that was read: python opens + native reader paths
    tmp_s, data = str(TMP).lower(), []
    skipped = 0
    ops, nat = set(opened), set(native)        # snapshot BEFORE hashing (hashing opens every file and would pollute the open-hook set)
    for p in sorted(ops | nat):
        low, pp = p.lower(), Path(p)
        if not pp.is_file() or low.startswith(tmp_s) or "__pycache__" in low or f"{os.sep}.git{os.sep}" in low:
            skipped += 1
            continue
        if low.startswith(str(ROOT).lower()):
            rel, root = str(pp.relative_to(ROOT)).replace("\\", "/"), "repo"
        elif low.startswith(str(STORE_ROOT).lower()):
            rel, root = str(pp.relative_to(STORE_ROOT)).replace("\\", "/"), "fo-index-data"
        else:
            skipped += 1                                         # interpreter, site-packages, OS files
            continue
        if pp.suffix == ".py":
            continue                                             # code is taken from sys.modules above
        data.append({"root": root, "path": rel, "bytes": pp.stat().st_size, "sha256": sha(pp), "seen_by": ("open-hook" if p in ops else "") + ("+" if p in ops and p in nat else "") + ("native-wrapper" if p in nat else "")})
    # ---- derived Feather copies of the Parquet masters the loader read (it serves the copy; the master path is what read_store was handed)
    hashed = {(e["root"], e["path"]) for e in data}
    # ---- independent check against the loader's own path rules
    idx = Path(os.path.abspath(os.environ["INDEX_STORE"]))
    exp, missing_exp = set(), []
    tr = stash["trades"]
    for r in tr.itertuples():
        for d in IL.trade_days("NIFTY", r.expiry):
            if r.day <= d <= r.nxt:
                exp.add((idx / "options_1m" / "NIFTY" / r.expiry.isoformat() / f"{d.isoformat()}.parquet"))
    for p in sorted(exp):
        rel = str(p.relative_to(STORE_ROOT)).replace("\\", "/")
        if ("fo-index-data", rel) not in hashed:
            missing_exp.append(rel)
    s1_expected = [f"data/results/S1_v10_{s}_{k}.csv" for s in ("bandv10", "band12", "band12q4", "band050", "band050q4") for k in ("contracts", "minutes")] + ["data/results/S1_v10_trades.csv", "data/eod2/nifty 50.csv"]
    s1_missing = [e for e in s1_expected if ("repo", e) not in hashed]
    other_expected = [("fo-index-data", "data/index/vix_daily.parquet"), ("repo", "g1_research/results/g1_live_replay_trades.csv")]
    other_missing = [p for r_, p in other_expected if (r_, p) not in hashed]
    opt_read = sum(1 for e in data if e["root"] == "fo-index-data" and "/options_1m/" in e["path"])
    # ---- sealed / expiry_research check over everything seen
    bad = [e["path"] for e in data if "sealed" in e["path"].lower()] + [k for k in code if "sealed" in k.lower()]
    bad_listed = [p for p in listed if "sealed" in p.lower() or os.path.normcase(p).endswith(os.path.normcase("expiry_research"))]
    if bad or bad_listed:
        raise SystemExit(f"STOP: sealed/expiry_research path seen: {bad + bad_listed}")
    audit_files = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in sorted((ROOT / "stress_audit").rglob("*")) if p.is_file() and "__pycache__" not in str(p)}
    import numpy
    import openpyxl
    git = lambda *a, cwd=ROOT: subprocess.check_output(["git", *a], cwd=cwd, text=True).strip()   # noqa: E731
    out = {
        "purpose": "data provenance for the stress audit run recorded in stress_audit/results/RUN_MANIFEST.json (scripts 3fa031ee3, results 136d3de6f)",
        "generated_ist": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        "repo_head_when_traced": git("rev-parse", "HEAD"),
        "audit_commits": {"preregistration": "dafc8f685", "freeze_hash_fill": "7cc23d7ff", "amendments_and_s1_script": "f81de746e", "scripts": "3fa031ee3", "results": "136d3de6f"},
        "fo_index_data_git_head": git("rev-parse", "HEAD", cwd=STORE_ROOT),
        "fo_index_data_clean": git("status", "--porcelain", cwd=STORE_ROOT) == "",
        "seed": 20261113,
        "versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": numpy.__version__, "pyarrow": pyarrow.__version__, "openpyxl": openpyxl.__version__},
        "methods": ["Python audit hook on open() and on directory-listing events", "wrappers logging the path of every call to: " + ", ".join(wrapped), "sys.modules for repo code that ran",
                    "comparison against an expected-file list derived from the loader's own path rules (below)"],
        "pipeline_ran_without_network": True,
        "committed_outputs_reproduced": same,
        "sealed_paths_seen": {"data_or_code_paths_with_sealed_in_name": len(bad), "listed_directories_that_are_sealed_or_expiry_research": len(bad_listed)},
        "directories_listed_or_globbed": {"count": len(listed), "under_fo_index_data": sum(1 for p in listed if p.lower().startswith(str(STORE_ROOT).lower())),
                                          "under_repo": sum(1 for p in listed if p.lower().startswith(str(ROOT).lower()))},
        "coverage_check": {
            "g1_expected_option_files_from_loader_rules": len(exp), "g1_expected_but_not_hashed": missing_exp,
            "option_files_actually_read": opt_read,
            "s1_expected_inputs": len(s1_expected), "s1_expected_but_not_hashed": s1_missing,
            "other_expected_but_not_hashed": other_missing,
            "paths_seen_by_native_wrappers": len(nat),
            "native_paths_that_are_not_regular_files": sum(1 for p in nat if not Path(p).is_file()),
            "files_seen_only_by_native_wrappers_(invisible_to_the_open_hook)": sum(1 for e in data if e["seen_by"] == "native-wrapper"),
            "files_seen_only_by_the_open_hook": sum(1 for e in data if e["seen_by"] == "open-hook"),
            "files_seen_by_both": sum(1 for e in data if "+" in e["seen_by"]),
        },
        "limitations": [
            "stat()/exists()/metadata-only calls are not logged by any mechanism available here; a file only stat-ed (not read) is not listed. Python has no audit event for os.stat.",
            "Native (C/C++) file reads are captured only through the wrapped entry points listed in `methods`; a read through an unwrapped entry point (for example pyarrow.parquet.ParquetFile or pyarrow.dataset, or a library that opens files itself) would not be logged. None of those entry points is used by the repo code that ran (checked by reading the loader and fastio code), but this is a code-reading argument, not a log.",
            "The coverage check compares the log with what the loader's path rules say it should read for the G1 option files and with the known S1 inputs; for the 500+ bhavcopy cache files and other data/cache files completeness rests on the open() hook alone.",
            "Feather copies under data/cache/index/feather and data/results/*.feather are derived caches of the Parquet / CSV masters and are listed as data files when Python opened them; the masters are hashed through the loader wrappers.",
            "Interpreter, standard-library and site-packages files are not hashed; versions are recorded instead.",
            "Subprocesses (git rev-parse / git status in common.py) read .git, which is excluded.",
            "The claim covers this rerun on 13 Nov 2026 at the repo HEAD above. It does not prove what the original 18:06-18:12 run read; it shows the committed pipeline reproduces the committed outputs and reads the files listed.",
        ],
        "files_skipped_not_hashed": skipped,
        "data_files_read": data,
        "code_files_run": [{"path": k, **v} for k, v in sorted(code.items())],
        "original_audit_files_sha256": audit_files,
    }
    (ROOT / "stress_audit_corrections" / "MANIFEST_SUPPLEMENT.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    shutil.rmtree(TMP)
    print(json.dumps({k: out[k] for k in ("repo_head_when_traced", "fo_index_data_git_head", "committed_outputs_reproduced", "sealed_paths_seen", "directories_listed_or_globbed", "coverage_check")}, indent=1)[:3500])
    print(len(data), "data files hashed,", len(code), "code files hashed,", len(audit_files), "original audit files hashed,", skipped, "other opens not hashed")


if __name__ == "__main__":
    main()
