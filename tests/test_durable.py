"""The paper account survives a restart: mirrored to a durable store, restored onto a wiped disk."""
import base64
import json

from server import durable
from server.paper import PaperLedger


class DictStore:
    def __init__(self):
        self.files, self.puts = {}, []

    def get(self, name):
        return self.files.get(name)

    def put(self, name, data, message):
        self.files[name] = data
        self.puts.append(name)


def _open_position(ledger: PaperLedger, sym="MAXHEALTH"):
    ledger.state["positions"].append({"id": f"P-{sym}", "symbol": sym, "instrument": "PE", "expiry": "2026-10-27",
                                      "strike": 940.0, "tradingsymbol": f"{sym}26OCT940PE", "lot_size": 525,
                                      "side": "BUY", "lots": 1, "qty": 525, "entry": {"price": 30.8}, "stop": 15.4})
    ledger.state["cash"] -= 30.8 * 525
    ledger._save()


def test_a_restart_keeps_the_open_positions(tmp_path):
    store = DictStore()
    disk1 = tmp_path / "before"
    m1 = durable.Mirror(disk1, store)
    assert m1.restore() == []                                      # nothing mirrored yet
    ledger = PaperLedger(disk1, capital=500000)
    _open_position(ledger)
    assert m1.flush() == ["paper_ledger.json"]                     # a new position: written at once
    disk2 = tmp_path / "after_restart"                             # Render's wiped disk
    m2 = durable.Mirror(disk2, store)
    assert m2.restore() == ["paper_ledger.json"]
    again = PaperLedger(disk2, capital=500000)
    assert [p["tradingsymbol"] for p in again.state["positions"]] == ["MAXHEALTH26OCT940PE"]
    assert again.state["cash"] == ledger.state["cash"]


def test_marks_are_written_slowly_and_material_changes_at_once(tmp_path):
    store = DictStore()
    m = durable.Mirror(tmp_path, store)
    m.restore()
    ledger = PaperLedger(tmp_path, capital=500000)
    _open_position(ledger)
    assert m.flush(now=1000.0) == ["paper_ledger.json"]
    ledger.state["positions"][0]["mark"] = {"price": 31.0}         # a mark only
    ledger._save()
    assert m.flush(now=1010.0) == []                               # not yet: under SLOW_FLUSH
    assert m.flush(now=1000.0 + durable.SLOW_FLUSH) == ["paper_ledger.json"]
    ledger.state["positions"] = []                                 # closed: material, written at once
    ledger.state["closed"].append({"id": "P-MAXHEALTH", "net": -100.0})
    ledger._save()
    assert m.flush(now=1000.0 + durable.SLOW_FLUSH + 5) == ["paper_ledger.json"]


def test_restore_never_overwrites_a_local_file(tmp_path):
    store = DictStore()
    store.files["paper_ledger.json"] = json.dumps({"cash": 1.0, "positions": [], "closed": []}).encode()
    (tmp_path / "paper_ledger.json").write_text(json.dumps({"cash": 2.0, "positions": [], "closed": []}))
    assert durable.Mirror(tmp_path, store).restore() == []
    assert json.loads((tmp_path / "paper_ledger.json").read_text())["cash"] == 2.0


class FakeResp:
    def __init__(self, code, body=None):
        self.status_code, self._b = code, body or {}

    def json(self):
        return self._b

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    def __init__(self):
        self.headers, self.calls, self.remote = {}, [], {}

    def get(self, url, params=None, timeout=None):
        self.calls.append(("GET", url))
        name = url.rsplit("/", 1)[-1]
        if name in self.remote:
            data, sha = self.remote[name]
            return FakeResp(200, {"sha": sha, "content": base64.b64encode(data).decode()})
        return FakeResp(404)

    def put(self, url, json=None, timeout=None):
        self.calls.append(("PUT", url, json.get("sha")))
        name = url.rsplit("/", 1)[-1]
        sha = f"s{len(self.calls)}"
        self.remote[name] = (base64.b64decode(json["content"]), sha)
        return FakeResp(201, {"content": {"sha": sha}})


def test_github_store_creates_then_updates_with_the_sha():
    sess = FakeSession()
    st = durable.GitHubStore("o/r", "paper-state", "t0ken", session=sess)
    assert sess.headers["Authorization"] == "Bearer t0ken"
    st.put("paper_ledger.json", b"{}", "m")
    assert sess.calls[-1][2] is None                               # a new file: no sha
    st.put("paper_ledger.json", b'{"a":1}', "m")
    assert sess.calls[-1][2] == sess.calls[1][0] or sess.calls[-1][2].startswith("s")   # the update carries the sha
    assert st.get("paper_ledger.json") == b'{"a":1}'
    assert "contents/paper/paper_ledger.json" in sess.calls[-1][1]


def test_material_ignores_marks():
    a = json.dumps({"positions": [{"id": 1, "mark": {"price": 1}}], "closed": [], "cash": 5}).encode()
    b = json.dumps({"positions": [{"id": 1, "mark": {"price": 2}}], "closed": [], "cash": 5}).encode()
    c = json.dumps({"positions": [], "closed": [{"id": 1}], "cash": 7}).encode()
    assert durable.material(a) == durable.material(b) != durable.material(c)
