from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import socket

import pytest
from fastapi.testclient import TestClient

from agentverse.agents.gemini import GeminiPolicy, Limits
from agentverse.agents.policy import RulePolicy
from agentverse.api.main import create_app
from agentverse.domain.model import Entry, Event, TREASURY
from agentverse.domain.reducer import check_invariants, reduce_event
from agentverse.experiments.export import export_csv, export_json
from agentverse.experiments.preflight import preflight
from agentverse.experiments.proof import verify_export
from agentverse.experiments.scarcity import create_pair, execute, get_pair, prepare, recover_branches
from agentverse.simulation.kernel import Kernel
from agentverse.simulation.runner import step
from agentverse.storage.store import IntegrityError, Store


@pytest.mark.parametrize("event,error", [
    (Event(1, 0, "WAIT", "A1"), "current turn"),
    (Event(1, 1, "ROUND_SETTLED"), "invalid settlement"),
    (Event(1, 2, "ROUND_STARTED"), "invalid round start"),
    (Event(1, 1, "CLAIM_PUBLISHED", "A1"), "invalid scenario event"),
    (Event(1, 1, "ROUND_STARTED", entries=(Entry("coins", None, "A1", 1),)), "external"),
    (Event(1, 1, "ROUND_STARTED", entries=(Entry("food", TREASURY, "A1", 1),)), "treasury holds coins"),
    (Event(1, 1, "ROUND_STARTED", entries=(Entry("food", "A1", "A1", 1),)), "invalid ledger"),
])
def test_reducer_rejects_invalid_replay_records(town, event, error):
    k = Kernel(town, 0, run_id="seed")
    with pytest.raises(ValueError, match=error):
        reduce_event(k.state, event)
    assert not k.events and k.state.version == 0


def test_conservation_detects_wrong_projection(town):
    w = Kernel(town, 42, run_id="seed").state
    with pytest.raises(ValueError, match="coin conservation"):
        check_invariants(replace(w, treasury=w.treasury + 1))
    with pytest.raises(ValueError, match="food conservation"):
        check_invariants(replace(w, produced=w.produced + 1))


def test_offline_workflow_without_sockets(town, tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail("offline run attempted network access")
    monkeypatch.setattr(socket.socket, "connect", denied)
    db = Store(tmp_path / "no-network.sqlite")
    parent = prepare(db, "parent", town, 42)
    eid = create_pair(db, "parent", parent.state.version)
    for label in "AB":
        assert execute(db, eid, label, RulePolicy()) == "complete"
    assert export_json(db, eid)["completed_pairs"] == 1


def test_mock_billing_redaction_and_pair_limit(town, tmp_path, capsys):
    db = Store(tmp_path / "telemetry.sqlite")
    prepare(db, "parent", town, 42)
    marker = "private-test-marker-do-not-export"
    raw = '{"action":{"type":"WAIT"}}'
    def reply(model, key, body, timeout):
        assert key == marker and marker not in json.dumps(body)
        with db.transaction() as sql:
            # Durable reservation exists before transport, outside any write transaction.
            record = sql.execute("SELECT details FROM provider_attempts ORDER BY ordinal DESC LIMIT 1").fetchone()
            assert json.loads(record[0])["status"] == "reserved"
        return {"usageMetadata": {"totalTokenCount": 11, "promptTokenCount": 8, "candidatesTokenCount": 3},
                "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": raw}]}}]}
    def policy():
        return GeminiPolicy("mock-model", marker, Limits(1, 100000), transport=reply)
    eid = create_pair(db, "parent", 2, policy())
    assert execute(db, eid, "A", policy()) == "incomplete_budget"
    assert execute(db, eid, "B", policy()) == "incomplete_budget"
    export = export_json(db, eid)
    a, b = [export["branches"][label] for label in "AB"]
    assert a["runtime"]["calls"] == 1 and b["runtime"]["calls"] == 0
    assert (a["runtime"]["input_tokens"], a["runtime"]["output_tokens"]) == (8, 3)
    receipt, = export["provider_attempts"]["A"]
    assert receipt["status"] == "proposal" and receipt["output_hash"] == sha256(raw.encode()).hexdigest()
    assert export["history"]["A"][receipt["before_version"]]["actor"] == receipt["actor"]
    assert marker not in json.dumps(export) + export_csv(export) + repr(capsys.readouterr())
    assert export["completed_pairs"] == 0 and export["final_delta"] is None


def test_process_restart_recovers_preserved_offline_turns(town, tmp_path):
    db = Store(tmp_path / "restart.sqlite")
    prepare(db, "parent", town, 42)
    eid = create_pair(db, "parent", 2)
    branch = get_pair(db, eid)["branches"]["A"]["run"]
    k = db.load(branch)
    for _ in range(4):
        step(k, RulePolicy())
    db.save(k, 2, "earlier", "prior committed decisions")
    prefix = k.events
    with db.transaction(write=True) as sql:
        sql.execute("UPDATE branches SET status='running' WHERE run=?", (branch,))
        recover_branches(sql)
    assert execute(db, eid, "A", RulePolicy()) == "complete"
    completed = db.load(branch)
    assert completed.events[:len(prefix)] == prefix and len([e for e in completed.events if e.actor]) == 48


def test_untrusted_peer_with_loopback_host_rejected(tmp_path):
    with TestClient(create_app(tmp_path / "local.sqlite"), base_url="http://127.0.0.1", client=("192.0.2.8", 5000)) as c:
        assert c.get("/health").status_code == 403


def test_fixed_https_transport_and_redacted_provider_echo(monkeypatch, town, tmp_path):
    from agentverse.agents import gemini

    marker = "server-side-test-value"
    calls = []

    class Reply:
        status = 200

        def read(self, bound):
            raw = json.dumps({"action": {"type": "WAIT"}, "note": {"summary": marker}})
            return json.dumps({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": raw}]}}]}).encode()

    class FakeConnection:
        def __init__(self, host, timeout):
            assert host == "generativelanguage.googleapis.com" and timeout == 7

        def request(self, method, path, body, headers):
            assert (method, path) == ("POST", "/v1beta/models/mock-model:generateContent")
            assert headers["x-goog-api-key"] == marker and marker not in body and marker not in path
            assert "tools" not in json.loads(body)
            calls.append(path)

        def getresponse(self):
            return Reply()

        def close(self):
            pass

    monkeypatch.setattr(gemini, "HTTPSConnection", FakeConnection)
    db = Store(tmp_path / "mock-http.db")
    prepare(db, "parent", town, 42)
    p = GeminiPolicy("mock-model", marker, Limits(1, 100000, timeout=7))
    eid = create_pair(db, "parent", 2, p)
    assert execute(db, eid, "A", p) == "incomplete_budget" and len(calls) == 1
    result = export_json(db, eid)
    assert marker not in json.dumps(result)
    assert result["history"]["A"][-1]["reason"] == "provider_response"
    assert result["provider_attempts"]["A"][0]["output_hash"]
    assert result["branches"]["A"]["runtime"]["reported_tokens"] is None


def test_interrupted_live_reservation_blocks_new_billing(town, tmp_path):
    db = Store(tmp_path / "uncertain.db")
    prepare(db, "parent", town, 42)
    def interrupted(*args):
        raise KeyboardInterrupt
    p = GeminiPolicy("mock", "private", Limits(3, 100000), transport=interrupted)
    eid = create_pair(db, "parent", 2, p)
    with pytest.raises(KeyboardInterrupt):
        execute(db, eid, "A", p)
    export = export_json(db, eid)
    assert export["branches"]["A"]["runtime"]["calls"] == 1
    assert export["branches"]["A"]["runtime"]["reported_tokens"] is None
    assert export["provider_attempts"]["A"][0]["status"] == "reserved"
    assert export["history"]["A"][-1]["kind"] == "ROUND_STARTED"
    with pytest.raises(ValueError, match="unresolved"):
        execute(db, eid, "B", p)
    assert export["completed_pairs"] == 0 and p.attempts == 1

def test_export_verification_rejects_modified_evidence(town, tmp_path):
    db = Store(tmp_path / "proof.sqlite")
    parent = prepare(db, "parent", town, 42)
    eid = create_pair(db, "parent", 2)
    execute(db, eid, "A", RulePolicy())
    payload = export_json(db, eid)
    assert verify_export(payload)["prefix_hash"] == parent.state.digest()
    changed = deepcopy(payload)
    changed["history"]["A"][3]["reason"] = "altered"
    with pytest.raises(IntegrityError, match="chain"):
        verify_export(changed)
    changed = deepcopy(payload)
    changed["rounds"]["A"][0]["unmet_units"] += 1
    with pytest.raises(IntegrityError, match="metric"):
        verify_export(changed)
    changed = deepcopy(payload)
    changed["integrity"]["B"]["checkpoints"].pop()
    with pytest.raises(IntegrityError, match="checkpoint"):
        verify_export(changed)
    changed = deepcopy(payload)
    changed["final_delta"] = {"unmet_units": 0}
    with pytest.raises(IntegrityError, match="delta"):
        verify_export(changed)


def test_preflight_uses_zero_calls_and_preserves_source(town, tmp_path, monkeypatch):
    db = Store(tmp_path / "preview.sqlite")
    parent = prepare(db, "parent", town, 42)
    before = parent.state.digest()
    monkeypatch.setattr(socket.socket, "connect", lambda *args: pytest.fail("dry run attempted network access"))
    preview = preflight(parent, Limits(96, 1000000))
    assert preview["provider_calls"] == 0 and preview["reference_decisions"] == 96
    assert preview["reference_token_reservations"] > 96 and preview["reference_primary_attempts_fit"]
    assert not preflight(parent, Limits(1, 100))["reference_primary_attempts_fit"]
    assert db.load("parent").state.digest() == before
