import json

import pytest

from kernel_steps import advance

from agentverse.simulation.kernel import Kernel, TurnConflict

CLAIM = "claim-harvest"
EVIDENCE = "evidence-harvest"


def speak(target, text, **refs):
    return {"type": "SPEAK", "recipient_id": target, "text": text, **refs}


def test_paired_private_worlds_and_golden_policy_context(town):
    worlds = []
    for index, hidden in enumerate(("SENTINEL-LEFT", "SENTINEL-RIGHT")):
        profiles = list(town.profiles)
        profiles[3] = profiles[3].model_copy(update={"seed_memory": hidden, "coins": 9876 + index})
        schedule = (731947 + index,) * 8
        config = town.model_copy(update={"profiles": tuple(profiles), "harvest": schedule})
        k = Kernel(config, 42, run_id=hidden)
        k.publish_harvest_claim()
        k.issue_harvest_record()
        k.grant_evidence(EVIDENCE, grantee="A1")
        if index:
            k.grant_evidence(EVIDENCE, grantee="A5")
        k.start_round()
        k.submit(k.turn, speak("A2", hidden, claim_ids=[CLAIM], evidence_ids=[EVIDENCE]),
                 note={"summary": hidden + "-NOTE", "evidence_ids": [EVIDENCE],
                       "beliefs": [{"claim_id": CLAIM, "interpretation": hidden + "-BELIEF"}]})
        worlds.append(k)
    left, right = worlds
    limited = left.observe("A3").policy_context
    assert limited == right.observe("A3").policy_context
    assert all(word not in limited for word in ("SENTINEL", "731947", "9876", EVIDENCE, "harvest-source"))
    # Golden allowlist for a third party who has only seen the public claim.
    expected = {
        "round": 1,
        "self": {"id": "A3", "role": "Mayor", "goal": "Reduce food insecurity.",
                 "workplace": "town-hall", "position": [5, 1], "food": 1, "coins": 30, "unmet": 0,
                 "last_unmet": False, "last_action": None, "last_rejection": None},
        "map": {"grid": list(town.grid), "zones": [z.model_dump(mode="json") for z in town.zones]},
        "nearby": [], "claims": [{"id": CLAIM, "key": "reduced_harvest", "source": "town-board",
                                  "text": "Every scheduled round will produce fewer than six food units.",
                                  "status": "unverified"}],
        "evidence": [], "messages": [], "offers": [], "obligations": [],
        "trust": {"A1": 50, "A2": 50, "A4": 50, "A5": 50, "A6": 50},
        "memory": [{"id": "seen-0", "round": 0, "seed_memory": town.profiles[2].seed_memory},
                   {"id": "seen-1", "round": 0, "claim_id": CLAIM}],
        "allowed_actions": ["WAIT", "MOVE", "WORK", "GIVE_FOOD", "CREATE_OFFER", "ACCEPT_OFFER",
                            "REVOKE_OFFER", "SPEAK", "CREATE_COMMITMENT", "FULFILL_COMMITMENT"],
    }
    assert limited == json.dumps(expected, sort_keys=True, separators=(",", ":"))
    for k, hidden in zip(worlds, ("SENTINEL-LEFT", "SENTINEL-RIGHT"), strict=True):
        recipient = k.observe("A2").as_dict()
        assert recipient["messages"][0]["text"] == hidden
        assert recipient["messages"][0]["evidence_ids"] == []
        assert hidden + "-NOTE" not in k.observe("A2").policy_context
        self_report = k.observe("A1").as_dict()["memory"][-1]["self_report"]
        assert self_report["summary"] == hidden + "-NOTE"
        assert self_report["beliefs"] == [{"claim_id": CLAIM, "interpretation": hidden + "-BELIEF"}]
    version = left.state.version
    left.grant_evidence(EVIDENCE, grantee=None)
    assert left.observe("A3", version=version).policy_context == limited
    public = left.observe("A3").as_dict()
    assert public["claims"][0]["status"] == "contradicted"
    assert public["evidence"][0]["payload"] == [731947] * 8
    assert public["messages"] == []
    assert left.observe("A2").as_dict()["memory"][-2]["message"]["evidence_ids"] == []


def test_grant_provenance_and_supported_claim(town):
    k = Kernel(town.model_copy(update={"harvest": (3,) * 8}), 42, run_id="evidence")
    with pytest.raises(ValueError):
        k.issue_harvest_record()
    k.publish_harvest_claim()
    source = k.issue_harvest_record()
    assert source.source_id == source.evidence.source_event_id
    assert source.evidence.issuer_id == "harvest-register"
    with pytest.raises(ValueError):
        k.issue_harvest_record()
    for record, grantee in [("missing", "A1"), (EVIDENCE, "missing")]:
        with pytest.raises(ValueError):
            k.grant_evidence(record, grantee=grantee)
    k.start_round()
    old = k.turn
    k.grant_evidence(EVIDENCE, grantee="A2")
    with pytest.raises(TurnConflict):
        k.submit(old, {"type": "WAIT"})
    assert k.observe("A2").as_dict()["claims"][0]["status"] == "supported"
    with pytest.raises(ValueError):
        k.grant_evidence(EVIDENCE, grantee="A2")
    assert k.observe("A1").as_dict()["evidence"] == []
    k.grant_evidence(EVIDENCE, grantee=None)
    assert all(k.observe(a.id).as_dict()["evidence"] for a in k.state.agents)


@pytest.mark.parametrize(("payload", "reason"), [
    ({"type": "EVIDENCE_GRANTED", "grantee": "A1"}, "invalid_schema"),
    ({"type": "HARVEST_RECORDED"}, "invalid_schema"),
    (speak("board", "Trust me", status="supported"), "invalid_schema"),
    (speak("board", "Forgery", issuer_id="harvest-register"), "invalid_schema"),
    (speak("board", "Report", evidence_ids=[EVIDENCE]), "unavailable_evidence"),
    (speak("board", "Report", evidence_ids=["missing"]), "unavailable_evidence"),
    (speak("board", "Report", claim_ids=["missing"]), "unknown_claim"),
    (speak("A3", "Across town"), "outside_communication_zone"),
    (speak("board", "   "), "invalid_schema"), (speak("board", "x"*513), "invalid_schema"),
    (speak("board", "many", claim_ids=[CLAIM]*9), "invalid_schema"),
])
def test_unauthorized_or_malformed_actions(town, payload, reason):
    k = Kernel(town, 42, run_id="forgery")
    k.publish_harvest_claim()
    k.issue_harvest_record()
    k.start_round()
    before = k.state
    event = k.submit(k.turn, payload)
    assert (event.kind, event.reason, event.entries) == ("WAIT", reason, ())
    assert k.state.social == before.social


def test_public_reference_does_not_grant_access_and_speech_does_not_deliver(town):
    k = Kernel(town, 42, run_id="board")
    k.publish_harvest_claim()
    k.issue_harvest_record()
    k.grant_evidence(EVIDENCE, grantee="A1")
    k.start_round()
    k.submit(k.turn, {"type": "CREATE_COMMITMENT", "beneficiary_id": "A2", "quantity": 7, "due_round": 4})
    advance(k, "A1", 2)
    before = k.state
    say = k.submit(k.turn, speak("board", "I delivered seven food.", claim_ids=[CLAIM], evidence_ids=[EVIDENCE]))
    assert say.entries == () and say.commitments == ()
    assert before.social.commitments == k.state.social.commitments
    assert before.social.trust == k.state.social.trust
    assert before.social.evidence == k.state.social.evidence and before.scenario == k.state.scenario
    assert [(a.food, a.coins) for a in before.agents] == [(a.food, a.coins) for a in k.state.agents]
    assert k.observe("A1").as_dict()["messages"][-1]["evidence_ids"] == [EVIDENCE]
    for actor in ("A2", "A3", "A4", "A5", "A6"):
        view = k.observe(actor).as_dict()
        assert view["messages"][-1]["text"] == "I delivered seven food."
        assert view["messages"][-1]["evidence_ids"] == [] and view["evidence"] == []
    assert k.observe("A3").as_dict()["obligations"] == []


def test_bounded_memory_with_old_unresolved_obligation(town):
    k = Kernel(town.model_copy(update={"harvest": (6,)*20}), 42, run_id="bounded")
    advance(k, "A1", 1)
    k.submit(k.turn, {"type": "CREATE_COMMITMENT", "beneficiary_id": "A2", "quantity": 1, "due_round": 20})
    advance(k, "A1", 15)
    for actor in ("A1", "A2"):
        view = k.observe(actor).as_dict()
        assert len(view["memory"]) == 12 and view["memory"][0]["round"] > 1
        assert [o["status"] for o in view["obligations"]] == ["OPEN"]
        assert all("events" not in o for o in view["obligations"])
    assert k.observe("A3").as_dict()["obligations"] == []
    with pytest.raises(ValueError):
        k.observe("A1", version=-1)
    with pytest.raises(ValueError):
        k.observe("A1", version=k.state.version + 1)


def test_private_record_presence_does_not_change_later_visible_offer(town):
    traces = []
    for private in (True, False):
        k = Kernel(town, 42, run_id=str(private))
        k.publish_harvest_claim()
        if private:
            k.issue_harvest_record()
        k.start_round()
        k.submit(k.turn, {"type": "CREATE_OFFER", "recipient_id": "A2", "expiry_round": 1,
                          "quantity": 1, "price": 2})
        traces.append(k.observe("A2").policy_context)
    assert traces[0] == traces[1]


def test_private_evidence_rejected_in_authored_note(town):
    k = Kernel(town, 42, run_id="note")
    k.publish_harvest_claim()
    k.issue_harvest_record()
    k.start_round()
    failed = k.submit(k.turn, {"type": "WORK", "workplace": "farm"},
                      note={"summary": "I checked it.", "evidence_ids": [EVIDENCE]})
    assert (failed.kind, failed.reason, failed.note, failed.entries) == ("WAIT", "unavailable_evidence", None, ())


def test_recipient_and_public_grant_only_reveal_authorized_differences(town):
    worlds = []
    for amount in (2, 3):
        k = Kernel(town.model_copy(update={"harvest": (amount,) * 8}), 42, run_id=str(amount))
        k.publish_harvest_claim()
        k.issue_harvest_record()
        k.grant_evidence(EVIDENCE, grantee="A1")
        advance(k, "A1", 1)
        k.submit(k.turn, speak("A2", "Check the bulletin.", evidence_ids=[EVIDENCE]))
        worlds.append(k)
    left, right = worlds
    assert left.observe("A2") == right.observe("A2")
    assert left.observe("A3") == right.observe("A3")
    assert left.observe("A1") != right.observe("A1")
    for k in worlds:
        k.grant_evidence(EVIDENCE, grantee=None)
    for actor in ("A2", "A3"):
        a, b = (k.observe(actor).as_dict() for k in worlds)
        assert a["evidence"][0].pop("payload") == [2] * 8
        assert b["evidence"][0].pop("payload") == [3] * 8
        assert a == b
