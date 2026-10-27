"""server/plan_alert.py: the next-session Telegram messages, and what the app sends when."""
from datetime import date, datetime

from server import alerts, plan_alert as pa
from server.sessions import IST

MON, TUE = date(2026, 10, 26), date(2026, 10, 27)
FRESH = {"fade": {"session": "2026-10-27", "signals": [{"symbol": "ADANIENSOL", "side": "PE"}, {"symbol": "TCS", "side": "CE"}]},
         "forward": {"last_session": "2026-10-26", "arms": {"A": {"pending": [{"symbol": "INDHOTEL"}]}, "B": {"pending": []}}}}
STALE = {"fade": {"session": "2026-10-23", "signals": [{"symbol": "ADANIENSOL", "side": "PE"}]},
         "forward": {"last_session": "2026-10-22", "arms": {"A": {"pending": [{"symbol": "INDHOTEL"}]}}}}


def test_the_target_is_today_before_the_open_and_the_next_session_after_it():
    assert pa.target_day(MON, 8 * 60 + 50) == MON
    assert pa.target_day(MON, 18 * 60) == TUE
    assert pa.target_day(date(2026, 10, 24), 10 * 60) == MON          # Saturday: Monday
    assert pa.target_day(date(2026, 10, 23), 20 * 60) == MON          # Friday evening: Monday


def test_a_fresh_list_is_announced_with_its_stocks():
    t = pa.ready_text(FRESH, TUE)
    assert "Tue 27 Oct" in t and "ADANIENSOL PUT, TCS CALL" in t and "INDHOTEL CALL (Arm A)" in t


def test_a_list_for_another_day_is_never_announced_as_the_plan():
    assert pa.ready_text(STALE, MON) is None and pa.ready_text(STALE, TUE) is None
    text, ok = pa.morning_text(STALE, MON)
    assert ok is False and "No full list for Mon 26 Oct" in text and "fade list is for 2026-10-23" in text
    assert "INDHOTEL" not in text and "ADANIENSOL" not in text            # Friday's stocks are not shown as today's


def test_the_morning_plan_and_a_late_arrival():
    text, ok = pa.morning_text(FRESH, TUE)
    assert ok and "2 trade(s)" not in text and "3 trade(s) planned" in text
    assert pa.late_text(STALE, MON) is None
    assert "arrived after the open" in pa.late_text(FRESH, TUE)
    empty = {"fade": {"session": "2026-10-27", "signals": []}, "forward": {"last_session": "2026-10-26", "arms": {}}}
    assert "no trade planned" in pa.morning_text(empty, TUE)[0]


def _app_run(monkeypatch, meta, times):
    import server.app as app
    sent = []
    monkeypatch.setattr(alerts, "send", lambda text, key=None, every=900.0: sent.append(text) or True)
    monkeypatch.setattr(app.state, "scan", {"meta": meta}, raising=False)
    app._PHONE.update(ready=None, plan=None, missing=None, late=None, checked=0.0)
    for h, m in times:
        app._plan_alerts(datetime(2026, 10, 26 if h < 24 else 27, h % 24, m, tzinfo=IST))
    return sent


def test_the_app_announces_a_list_once_and_warns_at_09_08_when_it_is_missing(monkeypatch):
    sent = _app_run(monkeypatch, FRESH, [(19, 0), (19, 5), (20, 0)])               # Monday evening: Tuesday's list lands
    assert len(sent) == 1 and sent[0].startswith("📋 List for Tue 27 Oct")
    assert _app_run(monkeypatch, STALE, [(22, 0)]) == []                              # a stale list is silent at night
    sent = _app_run(monkeypatch, STALE, [(9, 7), (9, 9), (9, 40)])                 # ... and warns once at 09:08
    assert [s[:2] for s in sent] == ["⚠️"] and "Mon 26 Oct" in sent[0]


def test_a_missing_list_that_arrives_late_is_announced_once(monkeypatch):
    import server.app as app
    sent = _app_run(monkeypatch, STALE, [(9, 9)])
    monkeypatch.setattr(app.state, "scan", {"meta": {"fade": {"session": "2026-10-26", "signals": []},
                                                     "forward": {"last_session": "2026-10-23", "arms": {}}}}, raising=False)
    for h, m in ((10, 30), (11, 0)):
        app._plan_alerts(datetime(2026, 10, 26, h, m, tzinfo=IST))
    assert len(sent) == 2 and sent[1].startswith("🕘")


# ---------------------------------------------------------------- the scan watcher (27 Oct 2026)
def _scan(as_of, fade_session, last):
    return {"stocks": [{"symbol": "X"}], "meta": {"as_of": as_of, "fade": {"session": fade_session, "signals": [], "made_at": as_of},
                                                  "forward": {"last_session": last, "arms": {}}}}


def _watch_env(monkeypatch, tmp_path, current, remote):
    import server.app as app
    import requests
    loaded, fetched = [], []
    monkeypatch.setattr(app.settings, "scan_url", "http://x/scan.json")
    monkeypatch.setattr(app, "SCAN_PATH", tmp_path / "scan.json")
    monkeypatch.setattr(app.state, "scan", current, raising=False)
    monkeypatch.setattr(app.state, "load_scan", lambda p: loaded.append(p), raising=False)
    resp = type("R", (), {"raise_for_status": lambda s: None, "json": lambda s: remote})()
    monkeypatch.setattr(requests, "get", lambda *a, **k: fetched.append(a) or resp)
    return app, loaded, fetched


def test_the_watcher_loads_a_list_that_lands_overnight_and_not_during_the_session(monkeypatch, tmp_path):
    old, new = _scan("2026-10-22", "2026-10-23", "2026-10-22"), _scan("2026-10-26", "2026-10-27", "2026-10-26")
    app, loaded, fetched = _watch_env(monkeypatch, tmp_path, old, new)
    mon = lambda h, m: datetime(2026, 10, 27, h, m, tzinfo=IST)                    # noqa: E731
    assert app._scan_watch_once(mon(10, 0)) == "skipped: market hours" and fetched == []
    assert app._scan_watch_once(mon(3, 0)) == "checked" and len(loaded) == 1       # new lists: loaded
    app.state.scan = new
    assert app._scan_watch_once(mon(4, 0)) == "lists current" and len(fetched) == 1   # current: no more downloads


def test_the_watcher_keeps_the_loaded_scan_when_the_download_is_unchanged(monkeypatch, tmp_path):
    same = _scan("2026-10-22", "2026-10-23", "2026-10-22")
    app, loaded, fetched = _watch_env(monkeypatch, tmp_path, same, same)
    assert app._scan_watch_once(datetime(2026, 10, 27, 3, 0, tzinfo=IST)) == "checked"
    assert len(fetched) == 1 and loaded == []                                      # looked, found nothing new, reloaded nothing
