"""Checks for the gaps module (design: reports/lld/gaps.md). Run from project-f-0:
INDEX_STORE=../fo-index-data/data/index ../.venvs/fo/Scripts/python.exe -m pytest expiry_research/tests/test_gaps.py -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gaps_common import CUTOFF, RES, STORE, load_minutes  # noqa: E402
from gaps_eval import evaluate  # noqa: E402
from gaps_specs import OPEN_ALLOWED, T1515_FORBIDDEN, all_specs  # noqa: E402


@pytest.fixture(scope="module")
def prep():
    return {ul: pd.read_parquet(RES / f"prepared_{ul}.parquet") for ul in ["NIFTY", "BANKNIFTY"]}


def test_dates_within_open_period(prep):
    for P in prep.values():
        assert P["date"].max() <= CUTOFF and P["y_date"].max() <= CUTOFF
        assert set(P["split"]) <= {"discovery", "validation"}
        assert not P["split_edge"].any() and not P["cal_special_between"].any()
    m = load_minutes("NIFTY")
    assert m["date"].max() <= CUTOFF


def test_transition_counts_sum():
    T = pd.read_csv(RES / "transitions.csv")
    g = T.groupby(["ul", "slice", "from_gap_t"]).agg(k=("k", "sum"), n=("n_from", "first"))
    assert (g["k"] == g["n"]).all()
    for ul, P in [("NIFTY", None), ("BANKNIFTY", None)]:
        P = pd.read_parquet(RES / f"prepared_{ul}.parquet")
        D = P[P["split"] == "discovery"]
        a = T[(T["ul"] == ul) & (T["slice"] == "all")].groupby("from_gap_t")["n_from"].first().sum()
        assert a == D["o_gap_dir"].isin(["up", "down", "flat"]).sum()


def test_context_tags(prep):
    P = prep["NIFTY"].set_index("y_date")
    assert P.at["2022-01-27", "d0"] and P.at["2022-01-27", "kind_ctx"] == "monthly"
    assert P.at["2022-01-28", "dplus1"] and P.at["2022-01-28", "kind_ctx"] == "monthly"
    assert P.at["2022-02-02", "k"] == 1 and not P.at["2022-02-02", "d0"]
    assert P.at["2022-02-03", "d0"] and P.at["2022-02-03", "kind_ctx"] == "weekly"
    assert P.at["2018-03-15", "regime"] == "N18_monthly_only" and not P.at["2018-03-15", "d0"]
    B = prep["BANKNIFTY"].set_index("y_date")
    assert B.at["2023-09-06", "d0"] and B.at["2023-09-06", "regime"] == "B_wed_weekly_thu_monthly"


def test_own_streak(prep):
    for P in prep.values():
        cur, out = 0, []
        for g in P["o_gap_pct"]:
            if g >= 0.1:
                cur = cur + 1 if cur > 0 else 1
            elif g <= -0.1:
                cur = cur - 1 if cur < 0 else -1
            else:
                cur = 0
            out.append(cur)
        # prepared rows dropped a few edge rows after the streak was computed on the full panel: compare where
        # the previous row is the previous panel row
        ok = P["date"].shift(1).eq(P["date"].shift(1))  # all rows
        assert (np.array(out)[ok.values][5:] == P["g_streak"].values[ok.values][5:]).mean() > 0.99


@pytest.mark.parametrize("ul,ix,d", [("NIFTY", "NIFTY50", "2022-02-03"), ("BANKNIFTY", "NIFTYBANK", "2023-05-18"),
                                     ("NIFTY", "NIFTY50", "2024-06-27")])
def test_minute_entry_returns(prep, ul, ix, d):
    raw = pd.read_parquet(STORE / f"spot_1m/{ix}/{d[:7]}.parquet")
    raw["timestamp"] = raw["timestamp"].dt.tz_convert("Asia/Kolkata")
    raw = raw[raw["timestamp"].dt.strftime("%Y-%m-%d") == d].drop_duplicates("timestamp")
    raw.index = raw["timestamp"].dt.strftime("%H:%M")
    e = raw.at["09:15", "close"]
    row = prep[ul].set_index("y_date").loc[d]
    assert abs(row["e_ret15"] - (raw.at["09:29", "close"] / e - 1) * 100) < 1e-9
    assert abs(row["e_ret60"] - (raw.at["10:14", "close"] / e - 1) * 100) < 1e-9
    assert abs(row["e_oc"] - (raw.at["15:29", "close"] / e - 1) * 100) < 1e-9
    later = raw.loc[(raw.index >= "09:16") & (raw.index <= "15:29")]
    pc = row["px_close"]
    want = later["low"].min() <= pc if row["y_gap_pct"] > 0 else later["high"].max() >= pc
    if row["y_gap_dir"] != "flat":
        assert bool(row["e_fill"]) == bool(want)


def test_spec_decision_time_columns():
    for s in all_specs():
        ycols = {c for c in s["uses"] if c.startswith("y_")}
        if s["dt"] == "OPEN(t+1)":
            assert ycols <= OPEN_ALLOWED, s["id"]
        else:
            assert not ycols, s["id"]
        if s["dt"] == "T1515(t)":
            assert not (set(s["uses"]) & T1515_FORBIDDEN), s["id"]
        assert not s["outcome"] in s["uses"], s["id"]


def test_conditions_read_only_declared_columns(prep):
    for s in all_specs():
        P = prep[s["ul"]].head(200)
        evaluate(s, P)  # cond gets P[uses]; any other column raises KeyError


def test_validation_refuses_on_hash_mismatch(monkeypatch):
    import gaps_validate
    if not (RES / "candidates_frozen.csv").exists():
        pytest.skip("not frozen yet")
    monkeypatch.setattr(gaps_validate, "code_hash", lambda: "different")
    with pytest.raises(SystemExit):
        gaps_validate.check_hash()
