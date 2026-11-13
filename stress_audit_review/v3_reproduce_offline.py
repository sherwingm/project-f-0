"""Re-runs the ORIGINAL audit scripts with every network socket blocked, writing to stress_audit_review/results/repro/ (never to stress_audit/results/),
then compares each output with the committed file. Evidence for: (a) no network use at run time, (b) the committed scripts regenerate the committed numbers.

    python -m stress_audit_review.v3_reproduce_offline s1|g1
"""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("INDEX_STORE", str(ROOT.parent / "fo-index-data" / "data" / "index"))


class Blocked(RuntimeError):
    pass


def _no(*a, **k):
    raise Blocked("network access attempted during the offline reproduction")


_RealSocket = socket.socket


class _BlockedSocket(_RealSocket):          # a class, so modules that subclass socket.socket (ssl) still import
    def __init__(self, *a, **k):
        raise Blocked("socket creation attempted during the offline reproduction")


socket.socket = _BlockedSocket              # type: ignore[assignment]
socket.create_connection = _no          # type: ignore[assignment]
socket.getaddrinfo = _no                # type: ignore[assignment]

import pandas as pd  # noqa: E402

from stress_audit import common as C  # noqa: E402

REPRO = ROOT / "stress_audit_review" / "results" / "repro"
REPRO.mkdir(parents=True, exist_ok=True)
C.OUT = REPRO

which = sys.argv[1]
if which == "audit":                                        # needs the s1 and g1 repro outputs in REPRO first
    from stress_audit import trade_audit as TA
    from stress_audit import build_report as BR
    TA.main()
    BR.main()
    print(chr(10) + "COMPARISON with the committed files in stress_audit/results/")
    a, b = pd.ExcelFile(ROOT / "stress_audit" / "results" / "TRADE_AUDIT.xlsx"), pd.ExcelFile(REPRO / "TRADE_AUDIT.xlsx")
    for sh in a.sheet_names:
        x, y = a.parse(sh), b.parse(sh)
        same = x.shape == y.shape and bool(x.fillna("NA").astype(str).eq(y.fillna("NA").astype(str)).all().all())
        print(f"TRADE_AUDIT.xlsx / {sh:14s} {'IDENTICAL' if same else 'DIFFERENT'}")
    ra = [ln for ln in (ROOT / "stress_audit" / "results" / "STRESS_REPORT.md").read_text(encoding="utf-8").splitlines() if not ln.startswith("Run: git")]
    rb = [ln for ln in (REPRO / "STRESS_REPORT.md").read_text(encoding="utf-8").splitlines() if not ln.startswith("Run: git")]
    print("STRESS_REPORT.md (without its 'Run:' header line)", "IDENTICAL" if ra == rb else f"DIFFERENT ({sum(1 for u, v in zip(ra, rb) if u != v)} lines)")
    sys.exit(0)
if which == "s1":
    from stress_audit import s1_stress as M
    files = ["scenario_results_s1.csv", "sensitivity_s1.csv", "regimes_s1.csv", "trades_s1_all_scenarios.csv", "s1_ambiguous_trades.csv"]
else:
    from stress_audit import g1_stress as M
    files = ["scenario_results_g1.csv", "sensitivity_g1.csv", "regimes_g1.csv", "trades_g1_all_scenarios.csv", "g1_ambiguous_trades.csv", "g1_validation.json"]
M.main()
print("\nCOMPARISON with the committed files in stress_audit/results/")
for f in files:
    a, b = ROOT / "stress_audit" / "results" / f, REPRO / f
    if f.endswith(".json"):
        same = a.read_text() == b.read_text()
    else:
        x, y = pd.read_csv(a), pd.read_csv(b)
        same = x.shape == y.shape and bool(x.fillna("NA").astype(str).eq(y.fillna("NA").astype(str)).all().all())
    print(f"{f:36s} {'IDENTICAL' if same else 'DIFFERENT'}")
