"""Fast table reads: a .feather copy beside a big CSV, built on the first read and reused while the CSV is unchanged.

    from .fastio import read_table
    mins = read_table(RES / "S1_v10_bandv10_minutes.csv")     # same frame as pd.read_csv, about 5x faster after the first read

Feather (Arrow) reads about 5x faster than CSV on the minutes files; Parquet is smaller but slower to read, so the cache is Feather.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_table(path) -> pd.DataFrame:
    p = Path(path)
    f = p.with_suffix(".feather")
    if f.exists() and f.stat().st_mtime >= p.stat().st_mtime:
        return pd.read_feather(f)
    df = pd.read_csv(p)
    try:
        df.to_feather(f)
    except Exception:       # read-only folder or an unsupported column: the CSV result is still right
        pass
    return df
