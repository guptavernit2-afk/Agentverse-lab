import csv
from dataclasses import replace
from io import StringIO
import json
from unittest.mock import Mock

import pytest

from agentverse.agents.gemini import GeminiPolicy, Limits
from agentverse.agents.policy import RulePolicy
from agentverse.domain.model import Entry, Event
from agentverse.domain.social import Commitment
from agentverse.experiments.export import export_csv, export_json
from agentverse.experiments.metrics import differences, gini, measure
from agentverse.experiments.scarcity import BULLETIN, comparison, create_pair, execute, prepare
from agentverse.simulation.kernel import Kernel
from agentverse.storage.store import Store


@pytest.fixture
def experiment(town, tmp_path):
    db = Store(tmp_path / "lab.db")
    parent = prepare(db, "parent", town, 42)
    eid = create_pair(db, "parent", 2)
    return db, parent, eid


def test_assignment_and_visibility(experiment):
    db, parent, eid = experiment
    result = comparison(db, eid)
    manifest = result["manifest"]
    assert manifest["assignment"] == {"A": {"harvest_record_access": "private"}, "B": {"harvest_record_access": "public"}}
    a, b = (db.load(manifest["children"][i]) for i in "AB")
    assert parent.state.digest() == a.state.digest() == b.world_at(2).digest() == manifest["prefix_hash"]
    assert a.events == b.events[:-1] and b.events[-1].kind == "EVIDENCE_GRANTED"
    assert parent.state.social.claims[0].text == BULLETIN
    for agent in a.state.agents:
        before = a.observe(agent.id)
        assert before == b.observe(agent.id, version=2) and not before.as_dict()["evidence"]
        after = b.observe(agent.id).as_dict()
        assert after["evidence"][0]["payload"] == [3] * 8
        assert eid not in before.policy_context and eid not in json.dumps(after)
    with pytest.raises(ValueError):
        create_pair(db, "parent", 1)


def test_pair_exports_and_repeatability(experiment):
    db, parent, first = experiment
    second = create_pair(db, "parent", 2)
    records = []
    for eid in (first, second):
        for label in "BA":
            assert execute(db, eid, label, RulePolicy()) == "complete"
            assert execute(db, eid, label, RulePolicy()) == "complete"
        out = json.loads(json.dumps(export_json(db, eid)))
        assert out["completed_pairs"] == 1
        for label in "AB":
            end = out["rounds"][label][-1]
            assert end["scheduled_turns"] == 48 and end["produced_units"] == 24
            assert end["food_units"] == 18 + 24 - end["consumed_units"] and end["unmet_units"] >= 6
            assert out["branches"][label]["runtime"]["calls"] == 0
            assert [e["sequence"] for e in out["history"][label]] == list(range(1, len(out["history"][label]) + 1))
        assert [e["actor"] for e in out["history"]["A"] if e["actor"]] == [e["actor"] for e in out["history"]["B"] if e["actor"]]
        rows = list(csv.DictReader(StringIO(export_csv(out))))
        cell = next(r for r in rows if r["branch"] == "B" and r["round"] == "8" and r["metric"] == "unmet_units")
        assert int(cell["value"]) == out["rounds"]["B"][-1]["unmet_units"]
        assert all(r["mode"] == "rule_based" for r in rows)
        records.append((out["rounds"], out["history"], out["final_delta"]))
    assert records[0] == records[1] and parent.state.version == 2


def test_incomplete_live_pair(experiment):
    db, _, _ = experiment
    send = Mock(side_effect=AssertionError("unexpected request"))
    p = GeminiPolicy("fixed", "mock", Limits(2, 1), transport=send)
    eid = create_pair(db, "parent", 2, p)
    assert execute(db, eid, "A", p) == "incomplete_budget"
    result = comparison(db, eid)
    assert result["completed_pairs"] == 0 and result["final_delta"] is None
    assert result["deltas_by_round"] == [] and result["mode"] == "live_llm"
    with pytest.raises(ValueError, match="policy configuration mismatch"):
        execute(db, eid, "B", RulePolicy())


def test_hand_calculated_metrics(town):
    k = Kernel(town, 0, run_id="fixture")
    w = k.state
    edges = (replace(w.social.trust[0], score=80), *w.social.trust[1:])
    def promise(i, status):
        return Commitment(str(i), "A1", "A2", 1, int(status == "FULFILLED"), 1, 2, status, ())
    promises = tuple(promise(i, status) for i, status in enumerate(("FULFILLED", "BROKEN", "OPEN")))
    agents = tuple(replace(a, food=int(a.id == "A1") * 6, unmet=int(a.id == "A2") * 2) for a in w.agents)
    world = replace(w, agents=agents, social=replace(w.social, commitments=promises, trust=edges))
    events = tuple(Event(i, 1, kind, "A1", reason, (Entry("food", "A1", "A2", qty),) if qty else ())
                   for i, (kind, qty, reason) in enumerate([("GIVE_FOOD", 3, None), ("ACCEPT_OFFER", 4, None),
                        ("FULFILL_COMMITMENT", 1, None), ("WAIT", 0, "invalid_schema"), ("WAIT", 0, "provider_response")], 1))
    m = measure(world, events)
    assert (m["unmet_units"], m["agents_affected"], m["fulfillment_rate"], m["mean_trust"]) == (2, 1, .5, 51)
    assert (m["gift_units"], m["trade_units"], m["fulfillment_units"]) == (3, 4, 1)
    assert (m["provider_failures"], m["invalid_rate"], m["food_gini"]) == (1, .25, 5 / 6)
    blank = measure(w, ())
    assert blank["fulfillment_rate"] is None and blank["invalid_rate"] is None and gini([0] * 6) is None
    delta = differences(m, blank)
    assert delta["unmet_units"] == -2 and delta["mean_trust"] == -1 and delta["invalid_rate"] is None
