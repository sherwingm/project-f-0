"""The paper account survives a restart: committed to a durable store on fills, exits and stop triggers and in a
15-minute snapshot (never on a mark alone), restored onto a wiped or older disk."""
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
                                      "side": "BUY", "lots": 1, "qty": 525, "entry": {"price": 30.8}, "stop": 15.4,
                                      "stop_triggered_at": None})
    ledger.state["cash"] -= 30.8 * 525
    ledger._save()


def test_a_restart_keeps_the_open_positions(tmp_path):
    store = DictStore()
    disk1 = tmp_path / "before"
    m1 = durable.Mirror(disk1, store)
    assert m1.restore() == []                                      # nothing stored yet
    ledger = PaperLedger(disk1, capital=500000)
    _open_position(ledger)
    assert m1.flush() == ["paper_ledger.json"]                     # a fill: written at once
    assert "paper_ledger.json" in store.files
    disk2 = tmp_path / "after_restart"                             # the wiped disk
    m2 = durable.Mirror(disk2, store)
    assert m2.restore() == ["paper_ledger.json"]
    again = PaperLedger(disk2, capital=500000)
    assert [p["tradingsymbol"] for p in again.state["positions"]] == ["MAXHEALTH26OCT940PE"]
    assert again.state["cash"] == ledger.state["cash"]


def test_never_on_a_mark_alone_but_a_15_minute_snapshot(tmp_path):
    store = DictStore()
    m = durable.Mirror(tmp_path, store)
    m.restore()
    ledger = PaperLedger(tmp_path, capital=500000)
    _open_position(ledger)
    assert m.flush(now=1000.0) == ["paper_ledger.json"]
    ledger.state["positions"][0]["mark"] = {"price": 31.0}
    ledger.state["positions"][0]["unrealised"] = 100.0
    ledger._save()
    assert m.flush(now=1010.0) == []                               # a mark: not written
    assert m.flush(now=1000.0 + 600) == []
    assert m.flush(now=1000.0 + durable.SNAPSHOT_EVERY) == ["paper_ledger.json"]   # the 15-minute snapshot
    ledger.state["positions"][0]["stop_triggered_at"] = "2026-09-30T14:00:00+05:30"
    ledger._save()
    assert m.flush(now=1000.0 + durable.SNAPSHOT_EVERY + 10) == ["paper_ledger.json"]   # a stop trigger: at once
    ledger.state["positions"] = []
    ledger.state["closed"].append({"id": "P-MAXHEALTH", "net_pnl": -100.0})
    ledger._save()
    assert m.flush(now=1000.0 + durable.SNAPSHOT_EVERY + 20) == ["paper_ledger.json"]   # an exit: at once


def test_order_log_and_snapshots_are_written_at_once(tmp_path):
    store = DictStore()
    m = durable.Mirror(tmp_path, store)
    m.restore()
    (tmp_path / "paper_orders.jsonl").write_text('{"order_id": 1}\n')
    (tmp_path / "live_snapshots").mkdir()
    (tmp_path / "live_snapshots" / "2026-09-30.json").write_text('{"rows": []}')
    assert sorted(m.flush(now=5.0)) == ["live_snapshots/2026-09-30.json", "paper_orders.jsonl"]
    assert m.flush(now=6.0) == []


def test_restore_takes_the_newer_ledger_and_the_longer_order_log(tmp_path):
    store = DictStore()
    store.files["paper_ledger.json"] = json.dumps({"cash": 1.0, "positions": [], "closed": [],
                                                   "saved_at": "2026-09-30T15:00:00+05:30"}).encode()
    store.files["paper_orders.jsonl"] = b'{"a":1}\n{"a":2}\n'
    store.files["live_snapshots/2026-09-30.json"] = b'{"rows": []}'
    (tmp_path / "paper_ledger.json").write_text(json.dumps({"cash": 2.0, "positions": [], "closed": [],
                                                            "saved_at": "2026-09-30T11:00:00+05:30"}))
    (tmp_path / "paper_orders.jsonl").write_text('{"a":1}\n')
    got = durable.Mirror(tmp_path, store).restore(snapshot_days=["2026-09-30"])
    assert got == ["paper_ledger.json", "paper_orders.jsonl", "live_snapshots/2026-09-30.json"]
    assert json.loads((tmp_path / "paper_ledger.json").read_text())["cash"] == 1.0
    (tmp_path / "paper_ledger.json").write_text(json.dumps({"cash": 3.0, "positions": [], "closed": [],
                                                            "saved_at": "2026-09-30T16:00:00+05:30"}))
    assert durable.Mirror(tmp_path, store).restore() == []          # the local one is newer: kept
    assert json.loads((tmp_path / "paper_ledger.json").read_text())["cash"] == 3.0


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
        key = url.split("/contents/", 1)[-1]
        if key in self.remote:
            data, sha = self.remote[key]
            return FakeResp(200, {"sha": sha, "content": base64.b64encode(data).decode()})
        return FakeResp(404)

    def put(self, url, json=None, timeout=None):
        self.calls.append(("PUT", url, json.get("sha"), json["branch"]))
        key = url.split("/contents/", 1)[-1]
        sha = f"s{len(self.calls)}"
        self.remote[key] = (base64.b64decode(json["content"]), sha)
        return FakeResp(201, {"content": {"sha": sha}})


def test_github_store_writes_the_data_paths_on_the_branch_with_the_sha():
    sess = FakeSession()
    st = durable.GitHubStore("o/r", "paper-state", "t0ken", session=sess)
    assert sess.headers["Authorization"] == "Bearer t0ken"
    st.put("paper_ledger.json", b"{}", "m")
    assert sess.calls[-1][2] is None and sess.calls[-1][3] == "paper-state"      # new file: no sha
    first_sha = sess.remote["data/paper_ledger.json"][1]
    st.put("paper_ledger.json", b'{"a":1}', "m")
    assert sess.calls[-1][2] == first_sha                          # an update carries the sha
    assert st.get("paper_ledger.json") == b'{"a":1}'
    assert sess.calls[-1][1].endswith("/contents/data/paper_ledger.json")


def test_material_ignores_marks_and_saved_at():
    base = {"positions": [{"id": 1, "mark": {"price": 1}, "unrealised": 5}], "closed": [], "cash": 5, "saved_at": "a"}
    moved = {"positions": [{"id": 1, "mark": {"price": 2}, "unrealised": 9}], "closed": [], "cash": 5, "saved_at": "b"}
    closed = {"positions": [], "closed": [{"id": 1}], "cash": 7}
    m = lambda d: durable.material(json.dumps(d).encode())
    assert m(base) == m(moved) != m(closed)


def test_a_local_account_is_written_on_the_first_start_against_an_empty_store(tmp_path):
    store = DictStore()
    ledger = PaperLedger(tmp_path, capital=500000)
    _open_position(ledger)                                         # a disk with a position, a store with nothing
    (tmp_path / "paper_orders.jsonl").write_text('{"order_id": 1}\n')
    m = durable.Mirror(tmp_path, store)
    assert m.restore() == []
    assert sorted(m.flush(now=1.0)) == ["paper_ledger.json", "paper_orders.jsonl"]
    assert m.flush(now=2.0) == []
