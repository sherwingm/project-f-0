"""Bias module end to end: clears results/bias/, then discovery -> freeze -> validation -> robustness.

Run from the repo root: INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe
expiry_research/scripts/bias_run_all.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "results" / "bias"
OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob("*"):
    if f.suffix in (".csv", ".txt"):
        f.unlink()
for s in ["bias_discovery.py", "bias_freeze.py", "bias_validation.py", "bias_robustness.py"]:
    print(f"== {s}", flush=True)
    r = subprocess.run([sys.executable, str(HERE / s)], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit(f"{s} failed")
print("done")
