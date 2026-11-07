"""Checks on data/expiry_calendar.csv and data/sessions_<UL>.csv.

Run from the repo root:  ../.venvs/fo/Scripts/python.exe -m pytest expiry_research/tests/test_calendar.py -q
(or run this file directly with python).
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CAL = pd.read_csv(ROOT / "data" / "expiry_calendar.csv", dtype=str)
DONE = CAL[CAL["status"].isin(["expired", "expired_unverified"])]
SESS = {ul: pd.read_csv(ROOT / "data" / f"sessions_{ul}.csv", dtype={"date": str})
        for ul in ["NIFTY", "BANKNIFTY", "SENSEX"]}
SPECIAL = set(pd.read_csv(ROOT / "data" / "special_sessions.csv", dtype=str)["date"])


def row(ul, d):
    r = CAL[(CAL["underlying"] == ul) & (CAL["expiry_date"] == d)]
    assert len(r) == 1, f"{ul} {d} not in calendar"
    return r.iloc[0]


def test_known_expiries():
    r = row("NIFTY", "2018-01-25")
    assert r["kind"] == "monthly" and r["weekday"] == "Thursday"
    assert row("NIFTY", "2019-02-14")["kind"] == "weekly"            # first NIFTY weekly after the 11-Feb-2019 launch
    assert row("BANKNIFTY", "2023-09-06")["weekday"] == "Wednesday"  # first Wednesday weekly (NSE/FAOP/57540)
    assert row("BANKNIFTY", "2024-03-27")["kind"] == "monthly"       # first Wednesday monthly (NSE/FAOP/60011)
    assert row("BANKNIFTY", "2025-01-30")["kind"] == "monthly"       # back to last Thursday (NSE/FAOP/65336)
    assert row("NIFTY", "2025-09-02")["weekday"] == "Tuesday"        # first Tuesday weekly (NSE/FAOP/68747)
    assert row("NIFTY", "2025-09-30")["kind"] == "monthly"
    assert row("SENSEX", "2025-01-03")["weekday"] == "Friday"        # BSE kept 3-Jan-2025 on Friday
    assert row("SENSEX", "2025-09-04")["weekday"] == "Thursday"


def test_no_nifty_weekly_before_launch():
    n = DONE[(DONE["underlying"] == "NIFTY") & (DONE["expiry_date"] < "2019-02-11")]
    assert (n["kind"] == "monthly").all()


def test_every_expiry_is_a_full_session():
    for ul, s in SESS.items():
        full = set(s["date"]) - SPECIAL
        e = DONE[(DONE["underlying"] == ul) & (DONE["expiry_date"] >= s["date"].min())]
        missing = set(e["expiry_date"]) - full
        assert not missing, f"{ul}: expiries not on a full session: {sorted(missing)}"


def test_one_monthly_per_month():
    m = DONE[DONE["kind"] == "monthly"]
    dup = m.groupby([m["underlying"], m["expiry_date"].str[:7]]).size()
    assert (dup == 1).all(), dup[dup > 1]


def test_futures_only_on_monthlies():
    nse = DONE[DONE["underlying"].isin(["NIFTY", "BANKNIFTY"]) & DONE["has_futures"].notna()]
    assert ((nse["kind"] == "monthly") == (nse["has_futures"] == "True")).all()


def test_banknifty_weekly_end():
    b = DONE[(DONE["underlying"] == "BANKNIFTY") & (DONE["kind"] == "weekly")]
    assert b["expiry_date"].max() == "2024-11-13"


def test_weekday_regimes_hold_or_are_explained():
    sh = DONE[DONE["shifted"] == "True"]
    assert not sh["shift_reason"].str.startswith("unexplained").any(), sh[sh["shift_reason"].str.startswith("unexplained")]
    # a shift is always to an earlier day
    assert (sh["expiry_date"] < sh["regime_date"]).all()


def test_nifty_tuesday_regime():
    n = DONE[(DONE["underlying"] == "NIFTY") & (DONE["expiry_date"] >= "2025-09-01")]
    assert ((n["weekday"] == "Tuesday") | (n["shifted"] == "True")).all()


def test_weekly_gaps():
    for ul in ["NIFTY", "BANKNIFTY"]:
        e = DONE[DONE["underlying"] == ul].sort_values("expiry_date")
        e = e[(e["expiry_date"] >= ("2019-02-14" if ul == "NIFTY" else "2018-01-01"))
              & (e["expiry_date"] <= ("2099-12-31" if ul == "NIFTY" else "2024-11-13"))]
        gap = pd.to_datetime(e["expiry_date"]).diff().dt.days.dropna()
        assert gap.between(1, 14).all(), gap[~gap.between(1, 14)]


def test_session_tags_consistent():
    for ul, s in SESS.items():
        ok = s[~s["calendar_gap"] & ~s["is_special_session"]]
        assert (ok.loc[ok["is_expiry_any"], "sessions_to_next_expiry"] == 0).all()
        assert (ok.loc[ok["is_expiry_monthly"], "sessions_to_next_monthly"] == 0).all()
        assert (ok.loc[ok["is_expiry_weekly"], "sessions_to_next_weekly"] == 0).all()
        assert (ok["sessions_to_next_expiry"].dropna() >= 0).all()
        assert (ok["sessions_since_last_expiry"].dropna() >= 1).all()
        # day after an expiry is 1 session since it
        nxt = ok["sessions_since_last_expiry"].shift(-1)
        assert (nxt[ok["is_expiry_any"]].dropna() >= 1).all()


def test_tags_point_only_to_known_expiries():
    """On day d, next_expiry / next_weekly / next_monthly are expiries already known on d (listed, or re-dated from a
    listed contract); expiries with no stored listing day (SENSEX folders, expiries.parquet) have blank known_from."""
    kf = {(u, d): k for u, d, k in zip(CAL["underlying"], CAL["expiry_date"], CAL["known_from"])}
    for ul, s in SESS.items():
        for name in ["expiry", "weekly", "monthly"]:
            p = s[f"next_{name}"]
            k = s[f"next_{name}_known_from"]
            want = p.map(lambda x: kf.get((ul, x)) if isinstance(x, str) else None)
            assert (k.fillna("") == want.fillna("")).all(), (ul, name)
            bad = s[k.notna() & (k.fillna("") > s["date"])]
            assert bad.empty, (ul, name, bad["date"].tolist()[:5])
    b = CAL[CAL["source"].str.startswith("bhavcopy")]
    assert b["known_from"].notna().all() and (b["known_from"] <= b["first_listed_seen"]).all()
    assert CAL.loc[CAL["underlying"] == "SENSEX", "known_from"].isna().all()


def test_nifty_weekly_launch_not_counted_before_listing():
    n = SESS["NIFTY"]
    assert row("NIFTY", "2019-02-14")["known_from"] == "2019-02-11"
    pre = n[n["date"] < "2019-02-11"]
    assert len(pre) > 250
    assert pre["next_weekly"].isna().all() and pre["sessions_to_next_weekly"].isna().all()
    feb = n[(n["date"] >= "2019-02-01") & (n["date"] <= "2019-02-08")]
    assert len(feb) == 6 and (feb["next_expiry"] == "2019-02-28").all()
    assert (feb["next_expiry_kind"] == "monthly").all()
    assert n.loc[n["date"] == "2019-02-11", "next_weekly"].iloc[0] == "2019-02-14"


def test_sessions_unique_and_sorted():
    for ul, s in SESS.items():
        assert s["date"].is_unique and s["date"].is_monotonic_increasing


if __name__ == "__main__":
    import sys
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as ex:
                fails += 1
                print("FAIL", name, ex)
    sys.exit(1 if fails else 0)
