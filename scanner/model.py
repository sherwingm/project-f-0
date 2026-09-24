"""NSE model: gradient boosting on scanner features + event flags, walk-forward by quarter.

    python -m scanner.model --train --since 2023-01-01          # build the dataset, walk-forward, save
    python -m scanner.model --report                            # print data/model_report.json

Target: the 3-session market-adjusted forward return (stock minus NIFTY 50, eod2 closes):
    up   > +1%      down < -1%      flat otherwise
Features per stock-day (never computed with future data, never tier-3):
    price_change_pct, volume_ratio, oi_change_pct, pcr, label one-hot, ret_5, ret_20,
    nifty_ret_5, sector one-hot (NSE's own industry tag from filings; top groups, rest 'other'),
    sessions_to_results, event flags (order/capacity bucket rank, latest rating direction,
    strongest deal direction, insider direction, in-ban) over the trailing 10 sessions.
Training: LightGBM when importable, else sklearn HistGradientBoosting. Walk-forward by calendar
quarter: train on every prior quarter, test on the next; no shuffling. The saved model is refit on
all data through the last complete quarter; data/model_report.json carries per-fold and overall
accuracy, per-class precision/recall, Brier score, and top-decile hit rates vs base rates. The
scan's per-stock `model` block quotes p_up/p_down/p_flat with oos_brier next to them.
"""
from __future__ import annotations

import argparse
import json
import logging
import pickle
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .build import ROOT
from .classify import classify
from .equity import load_symbol
from .event_study import load_index
from .nse_fo import fo_metrics

log = logging.getLogger("model")
MODEL_PATH = ROOT / "data" / "model.pkl"
REPORT_PATH = ROOT / "data" / "model_report.json"
SECTORS_PATH = ROOT / "data" / "cache" / "sectors.csv"
CLASSES = ("down", "flat", "up")
HORIZON = 3
THRESH = 1.0
TOP_SECTORS = 20
LABELS = ("Bullish setup", "Bearish setup", "Neutral", "Unclassified")
FLAG_COLS = ("f_results_soon", "f_order", "f_capacity", "f_rating", "f_deal", "f_insider", "f_ban")
BASE_COLS = ("price_change_pct", "volume_ratio", "oi_change_pct", "pcr", "ret_5", "ret_20", "nifty_ret_5")
BUCKET_RANK = {"ignore": 0, "minor": 1, "significant": 2, "major": 3}


# ---------------------------------------------------------------- sectors (NSE's industry tag)
def sector_map(store=None, path: Path = SECTORS_PATH) -> dict[str, str]:
    """symbol -> NSE industry, from the industry NSE itself attaches to filings (cached)."""
    if path.exists():
        rows = [l.split(",", 1) for l in path.read_text(encoding="utf-8").splitlines()[1:] if "," in l]
        if rows:
            return {s: v.strip() for s, v in rows}
    if store is None:
        from .events.store import Store
        store = Store()
    out: dict[str, tuple[str, str]] = {}
    for r in store.db.execute("SELECT symbol, event_date, raw_json FROM events WHERE source='nse_ann'"):
        try:
            ind = (json.loads(r["raw_json"] or "{}") or {}).get("industry")
        except json.JSONDecodeError:
            ind = None
        if ind and (r["symbol"] not in out or r["event_date"] > out[r["symbol"]][0]):
            out[r["symbol"]] = (r["event_date"], ind)
    m = {s: v for s, (_, v) in out.items()}
    if m:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("symbol,industry\n" + "".join(f"{s},{v}\n" for s, v in sorted(m.items())), encoding="utf-8")
    return m


# ---------------------------------------------------------------- event flags per stock-day
def day_flags(events: list[dict], cal: list[str]) -> dict[str, dict[str, float]]:
    """{day: flags} for one symbol from its tier-1/2 events, each day seeing only the 10 sessions
    up to and including itself (and future results dates for sessions_to_results)."""
    pos = {d: i for i, d in enumerate(cal)}
    by_day: dict[str, list[dict]] = {}
    results_days = sorted({e["event_date"] for e in events if e["type"] in ("results", "results_date")})
    for e in events:
        if e["event_date"] in pos:
            by_day.setdefault(e["event_date"], []).append(e)
    out: dict[str, dict[str, float]] = {}
    window: list[dict] = []
    ban_state = 0.0
    ri = 0
    for i, d in enumerate(cal):
        window.extend(by_day.get(d, []))
        lo = cal[max(0, i - 9)]
        window = [e for e in window if e["event_date"] >= lo]
        f = {"f_results_soon": 99.0, "f_order": 0.0, "f_capacity": 0.0, "f_rating": 0.0,
             "f_deal": 0.0, "f_insider": 0.0, "f_ban": 0.0}
        while ri < len(results_days) and results_days[ri] < d:
            ri += 1
        for rd in results_days[ri:]:
            if rd >= d and rd in pos and pos[rd] - i <= 15:
                f["f_results_soon"] = float(pos[rd] - i)
                break
        rating_day = ""
        for e in window:
            t, b = e["type"], BUCKET_RANK.get(e.get("bucket"), 1)
            if t == "order_win" and e.get("bucket") != "ignore":
                f["f_order"] = max(f["f_order"], float(b))
            elif t == "capacity" and e.get("bucket") != "ignore":
                f["f_capacity"] = max(f["f_capacity"], float(b))
            elif t == "rating" and e.get("subtype") in ("upgrade", "downgrade") and e["event_date"] >= rating_day:
                rating_day, f["f_rating"] = e["event_date"], float(e.get("direction") or 0)
            elif t in ("block_deal", "bulk_deal") and e.get("bucket") != "ignore":
                f["f_deal"] = float(e.get("direction") or 0) if abs(e.get("direction") or 0) else f["f_deal"]
            elif t == "insider" and e.get("bucket") != "ignore":
                f["f_insider"] = float(e.get("direction") or 0)
            elif t == "ban":
                ban_state = 1.0 if e.get("subtype") == "in" else 0.0
        f["f_ban"] = ban_state
        out[d] = f
    return out


# ---------------------------------------------------------------- the dataset
def build_dataset(since: date, until: date, eod2_dir: Path | None = None, cache_dir: Path | None = None,
                  store=None, universe: list[str] | None = None) -> pd.DataFrame:
    eod2_dir = eod2_dir or ROOT / "data" / "eod2"
    cache_dir = cache_dir or ROOT / "data" / "cache"
    if store is None:
        from .events.store import Store
        store = Store()
    if universe is None:
        from .universe import fetch_fo_lots
        universe = sorted(fetch_fo_lots(cache_path=cache_dir / "fo_universe.txt"))
    index = load_index(eod2_dir)
    cal = [d.strftime("%Y-%m-%d") for d in index.index]
    nifty = index.to_numpy(dtype=float)
    sectors = sector_map(store)
    top = {s for s, _ in Counter(sectors.get(x, "other") for x in universe).most_common(TOP_SECTORS)}

    # per-day futures OI / PCR from the cached bhavcopies
    fo_by_day: dict[str, dict[str, dict]] = {}
    files = sorted(cache_dir.glob("fo_bhavcopy_*.csv"))
    for f in files:
        d = f"{f.stem[-8:-4]}-{f.stem[-4:-2]}-{f.stem[-2:]}"
        if not (since.isoformat() <= d <= until.isoformat()):
            continue
        try:
            fo = fo_metrics(pd.read_csv(f, usecols=["TckrSymb", "FinInstrmTp", "OpnIntrst", "ChngInOpnIntrst",
                                                    "TtlTradgVol", "OptnTp"]))
            fo_by_day[d] = {r["symbol"]: r for r in fo.to_dict("records")}
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: %s", f.name, exc)
    log.info("futures OI/PCR for %d sessions", len(fo_by_day))

    pos = {d: i for i, d in enumerate(cal)}
    frames = []
    for n, sym in enumerate(universe, 1):
        try:
            s = load_symbol(sym, eod2_dir)
        except Exception:  # noqa: BLE001
            continue
        c = s["Close"].reindex(index.index)
        v = s["Volume"].reindex(index.index)
        px = c.to_numpy(dtype=float)
        with np.errstate(invalid="ignore", divide="ignore"):
            chg = (px[1:] / px[:-1] - 1) * 100
            vr = (v / v.rolling(20).mean().shift(1)).to_numpy(dtype=float)
            r5 = np.full_like(px, np.nan); r5[5:] = (px[5:] / px[:-5] - 1) * 100
            r20 = np.full_like(px, np.nan); r20[20:] = (px[20:] / px[:-20] - 1) * 100
            n5 = np.full_like(nifty, np.nan); n5[5:] = (nifty[5:] / nifty[:-5] - 1) * 100
            fwd = np.full_like(px, np.nan)
            fwd[:-HORIZON] = (px[HORIZON:] / px[:-HORIZON] - 1) * 100 - (nifty[HORIZON:] / nifty[:-HORIZON] - 1) * 100
        flags = day_flags([e for e in store.events_for(sym, since="2000-01-01") if e["tier"] <= 2], cal)
        sector = sectors.get(sym, "other")
        rows = []
        for d, i in pos.items():
            if not (since.isoformat() <= d <= until.isoformat()) or i == 0:
                continue
            fo = fo_by_day.get(d, {}).get(sym, {})
            pc = chg[i - 1]
            if np.isnan(pc) or np.isnan(fwd[i]):
                continue
            lab = classify({"price_change_pct": None if np.isnan(pc) else round(float(pc), 2),
                            "volume_ratio": None if np.isnan(vr[i]) else round(float(vr[i]), 2),
                            "oi_change_pct": _n(fo.get("oi_change_pct")), "pcr": _n(fo.get("pcr"))})["label"]
            y = "up" if fwd[i] > THRESH else "down" if fwd[i] < -THRESH else "flat"
            rows.append({"symbol": sym, "day": d, "quarter": d[:4] + "Q" + str((int(d[5:7]) - 1) // 3 + 1),
                         "price_change_pct": float(pc), "volume_ratio": _f(vr[i]), "oi_change_pct": _n(fo.get("oi_change_pct")),
                         "pcr": _n(fo.get("pcr")), "ret_5": _f(r5[i]), "ret_20": _f(r20[i]), "nifty_ret_5": _f(n5[i]),
                         "label": lab, "sector": sector if sector in top else "other",
                         **flags.get(d, {k: 0.0 for k in FLAG_COLS}), "y": y, "fwd": float(fwd[i])})
        frames.append(pd.DataFrame(rows))
        if n % 50 == 0:
            log.info("dataset: %d/%d symbols", n, len(universe))
    df = pd.concat([f for f in frames if len(f)], ignore_index=True)
    log.info("dataset: %d rows, %s..%s, classes %s", len(df), df["day"].min(), df["day"].max(),
             df["y"].value_counts().to_dict())
    return df


def _f(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)


def _n(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)


# ---------------------------------------------------------------- features matrix
def featurise(df: pd.DataFrame, feature_names: list[str] | None = None) -> tuple[np.ndarray, list[str]]:
    X = df[list(BASE_COLS)].astype(float).copy()
    X[list(FLAG_COLS)] = df[list(FLAG_COLS)].astype(float)
    for lab in LABELS:
        X[f"label_{lab.split()[0].lower()}"] = (df["label"] == lab).astype(float)
    sec = pd.get_dummies(df["sector"].astype(str), prefix="sector", dtype=float)
    X = pd.concat([X, sec], axis=1)
    if feature_names is not None:                    # align to the training columns
        for c in feature_names:
            if c not in X:
                X[c] = 0.0
        X = X[feature_names]
    return X.to_numpy(dtype=float), list(X.columns)


def _make_model():
    try:
        from lightgbm import LGBMClassifier
        return LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=63, verbose=-1), "lightgbm"
    except ImportError:
        from sklearn.ensemble import HistGradientBoostingClassifier
        return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, early_stopping=False), "sklearn-hgb"


# ---------------------------------------------------------------- walk-forward
def walk_forward(df: pd.DataFrame, min_train: int = 5000) -> dict:
    quarters = sorted(df["quarter"].unique())
    folds = []
    all_proba, all_true, all_base = [], [], []
    feature_names = featurise(df.iloc[:1])[1]
    for q in quarters:
        train = df[df["quarter"] < q]
        test = df[df["quarter"] == q]
        if len(train) < min_train or not len(test):
            continue
        model, engine = _make_model()
        Xtr, feature_names = featurise(train)
        Xte, _ = featurise(test, feature_names)
        model.fit(Xtr, train["y"].to_numpy())
        proba = _proba_ordered(model, Xte)
        yte = test["y"].to_numpy()
        base = np.tile([(train["y"] == c).mean() for c in CLASSES], (len(test), 1))   # know-nothing forecast
        folds.append({"quarter": q, "train_end": str(train["day"].max()), "test_start": str(test["day"].min()),
                      "test_end": str(test["day"].max()), "train_rows": len(train), "test_rows": len(test),
                      **_metrics(yte, proba), "base_brier": _brier(yte, base), "top_decile": _top_decile(yte, proba)})
        all_proba.append(proba)
        all_true.append(yte)
        all_base.append(base)
        log.info("fold %s: acc %.3f brier %.3f base %.3f (n=%d)", q, folds[-1]["accuracy"], folds[-1]["brier"],
                 folds[-1]["base_brier"], len(test))
    if not folds:
        raise RuntimeError("not enough rows for a single walk-forward fold")
    proba = np.vstack(all_proba)
    y = np.concatenate(all_true)
    overall = _metrics(y, proba)
    overall["base_brier"] = _brier(y, np.vstack(all_base))
    overall["top_decile"] = _top_decile(y, proba)
    return {"engine": _make_model()[1], "horizon_sessions": HORIZON, "threshold_pct": THRESH,
            "classes": list(CLASSES), "features": feature_names, "rows": len(df),
            "class_share": {c: round(float((df['y'] == c).mean()), 4) for c in CLASSES},
            "folds": folds, "overall": overall}


def _proba_ordered(model, X) -> np.ndarray:
    p = model.predict_proba(X)
    order = [list(model.classes_).index(c) for c in CLASSES]
    return p[:, order]


def _brier(y: np.ndarray, proba: np.ndarray) -> float:
    """Multi-class Brier score: sum over classes of (p - outcome)^2, averaged over rows (0 best, 2 worst)."""
    onehot = np.stack([(y == c).astype(float) for c in CLASSES], axis=1)
    return round(float(((proba - onehot) ** 2).sum(axis=1).mean()), 4)


def _metrics(y: np.ndarray, proba: np.ndarray) -> dict:
    pred = np.array(CLASSES)[proba.argmax(axis=1)]
    out = {"accuracy": round(float((pred == y).mean()), 4), "brier": _brier(y, proba)}
    for k, c in enumerate(CLASSES):
        tp = float(((pred == c) & (y == c)).sum())
        out[f"precision_{c}"] = round(tp / max(1.0, float((pred == c).sum())), 4)
        out[f"recall_{c}"] = round(tp / max(1.0, float((y == c).sum())), 4)
    return out


def _top_decile(y: np.ndarray, proba: np.ndarray) -> dict:
    out = {}
    for k, c in enumerate(CLASSES):
        if c == "flat":
            continue
        p = proba[:, k]
        cut = np.quantile(p, 0.9)
        top = p >= cut
        out[c] = {"n": int(top.sum()), "hit_rate": round(float((y[top] == c).mean()), 4) if top.any() else None,
                  "base_rate": round(float((y == c).mean()), 4), "p_cut": round(float(cut), 4)}
    return out


# ---------------------------------------------------------------- train / save / infer
def train(since: date, until: date | None = None, out: Path = MODEL_PATH, report_out: Path = REPORT_PATH) -> dict:
    until = until or date.today()
    df = build_dataset(since, until)
    report = walk_forward(df)
    last_q = report["folds"][-1]["quarter"]
    fit_rows = df[df["quarter"] <= last_q]
    model, engine = _make_model()
    X, feature_names = featurise(fit_rows)
    model.fit(X, fit_rows["y"].to_numpy())
    payload = {"model": model, "engine": engine, "features": feature_names, "classes": list(CLASSES),
               "trained_through": str(fit_rows["day"].max()), "oos_brier": report["overall"]["brier"],
               "base_brier": report["overall"]["base_brier"],
               "oos_accuracy": report["overall"]["accuracy"], "trained_at": datetime.now().isoformat(timespec="seconds")}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(pickle.dumps(payload))
    report["trained_through"] = payload["trained_through"]
    report_out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log.info("model -> %s (report -> %s)", out, report_out)
    return report


def load_model(path: Path = MODEL_PATH) -> dict | None:
    if not path.exists():
        return None
    try:
        return pickle.loads(path.read_bytes())
    except Exception as exc:  # noqa: BLE001
        log.warning("model.pkl unusable: %s", exc)
        return None


def infer_for_scan(stocks: list[dict], index_closes: dict | None, payload: dict | None = None) -> None:
    """Adds model: {p_up, p_down, p_flat, trained_through, oos_brier, base_brier} to each scan stock, in place, and
    model_top_decile: "up" / "down" / "both" when p_up / p_down is in the top 10% of that day's scan, else None."""
    payload = payload or load_model()
    if payload is None:
        return
    rows = []
    n5 = None
    if index_closes and len(index_closes.get("closes", [])) >= 6:
        c = index_closes["closes"]
        n5 = (c[-1] / c[-6] - 1) * 100
    for s in stocks:
        flags = (s.get("events") or {}).get("flags") or {}
        cc = s.get("chart_closes") or []
        rows.append({"price_change_pct": s.get("price_change_pct"), "volume_ratio": s.get("volume_ratio"),
                     "oi_change_pct": s.get("oi_change_pct"), "pcr": s.get("pcr"),
                     "ret_5": (cc[-1] / cc[-6] - 1) * 100 if len(cc) >= 6 else None,
                     "ret_20": (cc[-1] / cc[-21] - 1) * 100 if len(cc) >= 21 else None,
                     "nifty_ret_5": n5, "label": s.get("label"), "sector": "other",
                     "f_results_soon": float(flags.get("results_soon", 99)),
                     "f_order": float(BUCKET_RANK.get(flags.get("order_win"), 0)),
                     "f_capacity": float(BUCKET_RANK.get(flags.get("capacity"), 0)),
                     "f_rating": 1.0 if flags.get("rating") == "upgrade" else -1.0 if flags.get("rating") == "downgrade" else 0.0,
                     "f_deal": 1.0 if str(flags.get("block_deal", "")).endswith("buy") or str(flags.get("bulk_deal", "")).endswith("buy")
                               else -1.0 if str(flags.get("block_deal", "")).endswith("sell") or str(flags.get("bulk_deal", "")).endswith("sell") else 0.0,
                     "f_insider": 1.0 if str(flags.get("insider", "")).endswith("buy") else -1.0 if str(flags.get("insider", "")).endswith("sell") else 0.0,
                     "f_ban": 1.0 if flags.get("ban") else 0.0})
    sectors = sector_map()
    for r, s in zip(rows, stocks):
        r["sector"] = sectors.get(s["symbol"], "other")
    df = pd.DataFrame(rows)
    X, _ = featurise(df, payload["features"])
    proba = _proba_ordered(payload["model"], X)
    cut_down, cut_up = np.quantile(proba[:, 0], 0.9), np.quantile(proba[:, 2], 0.9)
    for s, p in zip(stocks, proba):
        s["model"] = {"p_down": round(float(p[0]), 3), "p_flat": round(float(p[1]), 3), "p_up": round(float(p[2]), 3),
                      "trained_through": payload["trained_through"], "oos_brier": payload["oos_brier"],
                      "base_brier": payload.get("base_brier")}
        # display only (never a vote): is this stock's p_up / p_down in the top 10% of today's scan?
        top = [k for k, hit in (("up", p[2] >= cut_up), ("down", p[0] >= cut_down)) if hit]
        s["model_top_decile"] = "both" if len(top) == 2 else (top[0] if top else None)


def main() -> None:
    ap = argparse.ArgumentParser(description="train / inspect the NSE model (numbers only)")
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--since", type=date.fromisoformat, default=date(2023, 1, 1))
    ap.add_argument("--until", type=date.fromisoformat, default=None)
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if a.train:
        report = train(a.since, a.until)
    elif REPORT_PATH.exists():
        report = json.loads(REPORT_PATH.read_text())
    else:
        print("no report yet: run with --train")
        return
    o = report["overall"]
    print(f"engine {report['engine']} | rows {report['rows']} | classes {report['class_share']}")
    print(f"{'fold':<10}{'train':>9}{'test':>8}{'acc':>8}{'brier':>8}{'base':>8} | precision/recall per class")
    for f in report["folds"]:
        pr = "  ".join(f"{c}: {f[f'precision_{c}']:.2f}/{f[f'recall_{c}']:.2f}" for c in CLASSES)
        base = f"{f['base_brier']:>8.3f}" if f.get("base_brier") is not None else f"{'-':>8}"
        print(f"{f['quarter']:<10}{f['train_rows']:>9}{f['test_rows']:>8}{f['accuracy']:>8.3f}{f['brier']:>8.3f}{base} | {pr}")
    pr = "  ".join(f"{c}: {o[f'precision_{c}']:.2f}/{o[f'recall_{c}']:.2f}" for c in CLASSES)
    base = f"{o['base_brier']:>8.3f}" if o.get("base_brier") is not None else f"{'-':>8}"
    print(f"{'OVERALL':<10}{'':>9}{sum(f['test_rows'] for f in report['folds']):>8}{o['accuracy']:>8.3f}{o['brier']:>8.3f}{base} | {pr}")
    for c, td in o.get("top_decile", {}).items():
        print(f"top decile {c}: hit rate {td['hit_rate']} vs base {td['base_rate']} (n={td['n']}, p >= {td['p_cut']})")


if __name__ == "__main__":
    main()
