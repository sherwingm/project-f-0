"""Shared loader for the daily panels (see reports/lld/panel.md, change 2026-11-05).

Research modules read panels only through load_panel(): it returns discovery + validation rows and refuses a file
that holds any final-period row or final-period label. The final period lives in data/sealed/ and is opened once,
by the coordinator (PREREGISTRATION.md), with load_sealed_final(ul, coordinator=True).
"""
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SEALED = DATA / "sealed"
FINAL_START = "2024-07-01"
ULS = ["NIFTY", "BANKNIFTY", "SENSEX"]
FEATURE_PREFIXES = ("f_", "f1515_", "cal_")
ID_COLS = ["date", "underlying", "split", "split_edge"]


def load_panel(ul, columns=None):
    """Open panel of `ul` (t <= 2024-06-30). Raises if a final row or a final-period label is present."""
    P = pd.read_parquet(DATA / f"panel_{ul}.parquet", columns=columns)
    if "date" in P.columns and (P["date"] >= FINAL_START).any():
        raise RuntimeError(f"panel_{ul}.parquet holds final-period rows; rebuild with build_panel.py")
    if "split" in P.columns and (P["split"] == "final").any():
        raise RuntimeError(f"panel_{ul}.parquet holds split == final rows")
    if "y_date" in P.columns:
        late = P["y_date"].fillna("") >= FINAL_START
        ycols = [c for c in P.columns if c.startswith("y_") and c != "y_date"]
        if late.any() and P.loc[late, ycols].notna().any().any():
            raise RuntimeError(f"panel_{ul}.parquet holds a label of a final-period session")
    return P


def sealed_feature_columns(ul, columns=None):
    """Id + f_ / f1515_ / cal_ columns of the sealed file, for build-integrity tests only.

    Never returns o_, y_ or px_ columns (outcomes and labels of the final period stay unread).
    """
    path = SEALED / f"panel_{ul}_final.parquet"
    names = pq.read_schema(path).names
    allowed = [c for c in names if c in ID_COLS or c.startswith(FEATURE_PREFIXES)]
    if columns is not None:
        bad = [c for c in columns if c not in allowed]
        if bad:
            raise ValueError(f"not a feature / id column of the sealed panel: {bad}")
        allowed = [c for c in allowed if c in columns]
    return pd.read_parquet(path, columns=allowed)


def sealed_schema(ul):
    """Column names of the sealed file (reads no data)."""
    return pq.read_schema(SEALED / f"panel_{ul}_final.parquet").names


def load_sealed_final(ul, coordinator=False):
    """Final-period panel with labels. Coordinator only, once, for candidates that passed validation."""
    if coordinator is not True:
        raise PermissionError("the final period is sealed (PREREGISTRATION.md); only the coordinator opens it")
    return pd.read_parquet(SEALED / f"panel_{ul}_final.parquet")
