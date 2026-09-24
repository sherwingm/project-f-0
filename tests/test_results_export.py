"""data/results/ writers: documented columns in order, a one-line .md entry per column, and the table mappings."""
import pandas as pd
import pytest

from scanner import results_export as rx
from server import charges as ch
from tests.test_backtest_labels import CAL, DAYS, FRAMES, INDEX, bhav
from tests.test_step9_backtest import result  # noqa: F401 (fixture)


def test_every_documented_file_writes_its_columns_and_md(tmp_path):
    for name, (_, cols) in rx.DOCS.items():
        df = pd.DataFrame([{c: 1 for c, _ in cols} | {"extra": 2}])
        path = rx.write(df, name, tmp_path)
        assert list(pd.read_csv(path).columns) == [c for c, _ in cols]           # header row, documented order
        md = (tmp_path / f"{name}.md").read_text(encoding="utf-8").splitlines()
        assert all(sum(l.startswith(f"- `{c}`:") for l in md) == 1 for c, _ in cols)


def test_labels_tables():
    from scanner.backtest_labels import run
    df = run(DAYS, CAL, bhav, FRAMES.get, sorted(FRAMES), INDEX, horizon=3)
    detail, summary = rx.labels_tables(df, CAL)
    assert {c for c, _ in rx.DOCS["labels_detail"][1]} <= set(detail.columns)
    abc = detail[(detail["symbol"] == "ABC") & (detail["date"] == CAL[30].isoformat())].iloc[0]
    assert abc["adj_fwd3_return"] == pytest.approx(2.0) and abc["scored"] == "Y" and abc["hit"] == "Y"
    assert {c for c, _ in rx.DOCS["labels_summary"][1]} <= set(summary.columns)
    assert (summary["row_type"] == "hit_rate").sum() == 2 * len(rx.THRESHOLDS)
    assert (summary["row_type"] == "returns").sum() == 2 * 3                     # Bullish/Bearish x 1, 3, 5 sessions


def test_cheap_tables(result):  # noqa: F811
    detail, summary = rx.cheap_tables(result)
    c = detail.set_index("type").loc["CE"]
    buy, sell = ch.leg("CE", "BUY", 100, 1.05)["total"], ch.leg("CE", "SELL", 100, 2.95)["total"]
    assert c["fill_price"] == 1.05 and c["exit_3s_price"] == 2.95 and c["exit_expiry_value"] == 4.0
    assert c["charges"] == pytest.approx(buy + sell, abs=0.01)
    assert c["charges_expiry"] == pytest.approx(buy + ch.exercise(100, 4.0)["total"], abs=0.01)
    assert c["net_3s"] == pytest.approx(142.19) and c["multiple_3s"] == pytest.approx(270.84 / 128.65, abs=1e-4)
    assert {c for c, _ in rx.DOCS["cheap_options_detail"][1]} <= set(detail.columns)
    assert set(summary["exit_rule"]) == {"3s", "expiry"} and "clears_coin" in summary


def test_event_table_splits_group_names():
    s = pd.DataFrame({"group": ["results", "results / outcome", "order_win [minor]",
                                "results / beat (day+1 reaction > +2%, a proxy)"], "count": [1, 2, 3, 4]})
    t = rx.event_table(s)
    assert list(t["type"]) == ["results", "results", "order_win", "results"]
    assert list(t["subtype"]) == ["", "outcome", "", "beat (day+1 reaction > +2%, a proxy)"]
    assert list(t["bucket"]) == ["", "", "minor", ""] and list(t["n"]) == [1, 2, 3, 4]


def test_folds_table():
    fold = {"quarter": "2024Q1", "train_end": "2023-12-29", "test_start": "2024-01-01", "test_end": "2024-03-28",
            "test_rows": 10, "accuracy": 0.4, "brier": 0.66, "base_brier": 0.667,
            "top_decile": {"up": {"hit_rate": 0.4, "base_rate": 0.33}, "down": {"hit_rate": 0.35, "base_rate": 0.33}}}
    report = {"folds": [fold], "overall": {"accuracy": 0.4, "brier": 0.66, "base_brier": 0.667,
                                           "top_decile": fold["top_decile"]}}
    t = rx.folds_table(report)
    assert list(t["fold"]) == ["2024Q1", "OVERALL"] and t.iloc[1]["n"] == 10
    assert t.iloc[0]["top_decile_hit_up"] == 0.4 and t.iloc[1]["base_brier"] == 0.667
