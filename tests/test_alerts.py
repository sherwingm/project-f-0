"""server/alerts.py: off without the Telegram settings, rate-limited by key, and raised by real-order fills."""
from server import alerts

from .test_real_orders import _bought, at, book, setup  # noqa: F401 - the fixture


def test_off_without_settings(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert alerts.enabled() is False and alerts.send("x") is False


def test_a_key_is_sent_once_per_period(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    sent = []
    monkeypatch.setattr(alerts, "_post", lambda text: sent.append(text) or True)
    alerts._last.clear()
    assert alerts.send("a", key="k", every=900) is True
    assert alerts.send("b", key="k", every=900) is False
    assert alerts.send("c") is True


def test_fills_raise_alerts(monkeypatch, setup):  # noqa: F811
    lg, q, ft, _ = setup
    got = []
    monkeypatch.setattr(alerts, "send", lambda text, key=None, every=900.0: got.append(text) or True)
    _bought(lg, q, ft)
    book(q, [(14.0, 5000)], [(14.3, 5000)])
    ft.on_poll(at(15, 10, 0))
    lg.work_orders(at(15, 10, 0, 1))
    assert got[0].startswith("🟢 BUY HCLTECH26OCT1200PE · 350 @ ₹18.50")
    assert "SELL HCLTECH26OCT1200PE · stop -20 %" in got[1] and "instant" in got[1]
