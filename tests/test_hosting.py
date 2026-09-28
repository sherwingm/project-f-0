"""Hosting: the server can take its scan from SCAN_URL (the GitHub Action's data/scan.json) instead of building it."""
import json

import pytest
import requests

from server import app as app_mod
from server.config import settings

GOOD = {"meta": {"as_of": "2026-09-25"}, "stocks": [{"symbol": "RELIANCE", "close": 1197.6}]}


class Resp:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self.payload


@pytest.fixture
def pulled(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "scan_url", "https://raw.githubusercontent.com/me/fo-scanner/main/data/scan.json")
    monkeypatch.setattr(app_mod, "SCAN_PATH", tmp_path / "scan.json")
    monkeypatch.setattr(app_mod.state, "feed", None)
    return tmp_path / "scan.json"


def test_pull_scan_saves_and_loads_it(pulled, monkeypatch):
    urls = []
    monkeypatch.setattr(requests, "get", lambda url, **kw: urls.append(url) or Resp(GOOD))
    meta = app_mod._pull_scan()
    assert meta == {"as_of": "2026-09-25"} and urls == [settings.scan_url]
    assert json.loads(pulled.read_text())["stocks"][0]["symbol"] == "RELIANCE"
    assert app_mod.state.stocks["RELIANCE"]["close"] == 1197.6
    assert app_mod._rebuild() == meta                                   # /api/rebuild pulls instead of building


def test_a_bad_download_never_replaces_the_scan(pulled, monkeypatch):
    pulled.write_text(json.dumps(GOOD))
    for bad in (Resp({"message": "Not Found"}), Resp(GOOD, status=404), Resp({"meta": {}, "stocks": []})):
        monkeypatch.setattr(requests, "get", lambda url, bad=bad, **kw: bad)
        with pytest.raises((ValueError, requests.HTTPError)):
            app_mod._pull_scan()
    assert json.loads(pulled.read_text()) == GOOD


def test_daily_loop_pulls_instead_of_building_when_scan_url_is_set():
    import inspect
    src = inspect.getsource(app_mod._daily_rebuild_loop)
    assert "_pull_scan" in src and "(21, 0)" in src and "settings.scan_url" in src


def _yaml(path):
    yaml = pytest.importorskip("yaml")
    from pathlib import Path
    return yaml.safe_load((Path(__file__).resolve().parent.parent / path).read_text(encoding="utf-8"))


def test_nightly_workflow_refuses_a_scan_without_fo_data_before_committing():
    steps = _yaml(".github/workflows/daily.yml")["jobs"]["build"]["steps"]
    names = [s.get("name", s.get("uses", "")) for s in steps]
    check, commit = names.index("Refuse a scan without F&O data"), names.index("Commit refreshed page")
    assert check < commit and "fo_status" in steps[check]["run"]
    assert any("actions/cache/restore" in s.get("uses", "") for s in steps)
    assert any("actions/cache/save" in s.get("uses", "") and s.get("if") == "always()" for s in steps)
    assert "state-seed" in next(s["run"] for s in steps if s.get("name", "").startswith("First run"))


def test_render_blueprint_keeps_secrets_out_and_paper_on():
    svc = _yaml("render.yaml")["services"][0]
    env = {e["key"]: e for e in svc["envVars"]}
    for secret in ("APP_PASSWORD", "KOTAK_CONSUMER_KEY", "ANTHROPIC_API_KEY", "SCAN_URL"):
        assert env[secret].get("sync") is False and "value" not in env[secret]
    assert env["PAPER"]["value"] == "true" and env["BROKER"]["value"] == "none" and env["DATA_PROVIDER"]["value"] == "kotak"
    assert "data/scan.json" in svc["buildFilter"]["ignoredPaths"]           # the nightly commit does not redeploy
