from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from kernel_steps import advance

from agentverse.cli import run
from agentverse.domain.model import Entry
from agentverse.domain.reducer import reduce_event
from agentverse.simulation.kernel import Kernel, TurnConflict

WAIT = {"type": "WAIT"}


def promise(kernel, **changes):
    return kernel.submit(kernel.turn, {"type": "CREATE_COMMITMENT", "beneficiary_id": "A2",
                                      "quantity": 3, "due_round": 3, **changes})


def delivery(key, amount):
    return {"type": "FULFILL_COMMITMENT", "commitment_id": key, "quantity": amount}


def edges(kernel):
    return {(e.observer, e.subject): e.score for e in kernel.state.social.trust}


@pytest.fixture
def kernel(town):
    k = Kernel(town, 42, run_id="test")
    k.start_round()
    return k


def test_partial_and_exact_due_round_with_once_only_trust(kernel):
    neutral = edges(kernel)
    assert len(neutral) == 30 and set(neutral.values()) == {50}
    assert all(observer != subject for observer, subject in neutral)
    before = kernel.state.agents
    created = promise(kernel)
    key = created.commitments[0].id
    assert [a.food for a in kernel.state.agents] == [a.food for a in before]
    advance(kernel, "A1", 2)
    partial = kernel.submit(kernel.turn, delivery(key, 1))
    assert partial.entries == (Entry("food", "A1", "A2", 1),)
    assert partial.commitments[0].status == "PARTIAL" and edges(kernel) == neutral
    advance(kernel, "A1", 3)
    turn = kernel.turn
    old = kernel.state
    def submit():
        try:
            return kernel.submit(turn, delivery(key, 2))
        except TurnConflict:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(submit) for _ in range(2)]
        outcomes = [f.result() for f in results]
    assert outcomes.count(None) == 1
    completed = next(e for e in outcomes if e)
    c = completed.commitments[0]
    assert (c.status, c.delivered, c.events) == (
        "FULFILLED", 3, (created.sequence, partial.sequence, completed.sequence))
    assert kernel.state.agent("A1").food == old.agent("A1").food - 2
    assert kernel.state.agent("A2").food == old.agent("A2").food + 2
    expected = {**neutral, ("A2", "A1"): 58}
    assert edges(kernel) == expected
    replayed = reduce_event(old, completed)
    assert replayed == kernel.state
    with pytest.raises(ValueError, match="out-of-order"):
        reduce_event(replayed, completed)
    with pytest.raises(ValueError, match="transfer"):
        reduce_event(old, replace(completed, entries=()))
    advance(kernel, "A1", 4)
    assert kernel.submit(kernel.turn, delivery(key, 1)).reason == "commitment_closed"
    assert edges(kernel) == expected


@pytest.mark.parametrize("partial_quantity", [0, 1])
def test_breach_and_late_delivery(kernel, partial_quantity):
    neutral = edges(kernel)
    key = promise(kernel, due_round=2).commitments[0].id
    if partial_quantity:
        advance(kernel, "A1", 2)
        kernel.submit(kernel.turn, delivery(key, partial_quantity))
    advance(kernel, "A1", 3)
    c = kernel.state.social.commitments[0]
    assert (c.status, c.delivered) == ("BROKEN", partial_quantity)
    assert kernel.events[c.events[-1] - 1].kind == "ROUND_SETTLED"
    before = kernel.state
    late = kernel.submit(kernel.turn, delivery(key, 1))
    assert late.reason == "commitment_closed" and late.entries == ()
    assert before.social == kernel.state.social
    assert edges(kernel) == {**neutral, ("A2", "A1"): 38}


@pytest.mark.parametrize(("changes", "reason"), [
    ({"beneficiary_id": "A1"}, "invalid_recipient"), ({"beneficiary_id": "unknown"}, "invalid_recipient"),
    ({"beneficiary_id": "A3"}, "outside_communication_zone"), ({"quantity": 0}, "invalid_schema"),
    ({"quantity": -1}, "invalid_schema"), ({"due_round": 0}, "invalid_due_round"),
    ({"due_round": 9}, "invalid_due_round"), ({"status": "FULFILLED"}, "invalid_schema"),
])
def test_invalid_creation(kernel, changes, reason):
    before = kernel.state.social
    assert promise(kernel, **changes).reason == reason
    assert kernel.state.social == before


@pytest.mark.parametrize(("quantity", "requested", "reason"), [
    (1, 2, "overdelivery"), (999, 999, "insufficient_food"),
    (1, 0, "invalid_schema"), (1, -1, "invalid_schema"),
])
def test_rejected_fulfillment(kernel, quantity, requested, reason):
    key = promise(kernel, quantity=quantity).commitments[0].id
    advance(kernel, "A1", 2)
    before = kernel.state
    event = kernel.submit(kernel.turn, delivery(key, requested))
    assert event.reason == reason and event.entries == ()
    assert kernel.state.social == before.social
    assert [a.food for a in kernel.state.agents] == [a.food for a in before.agents]


def test_role_and_colocation_checks(kernel):
    key = promise(kernel).commitments[0].id
    assert kernel.submit(kernel.turn, delivery(key, 1)).reason == "wrong_promisor"
    assert kernel.submit(kernel.turn, delivery(key, 1)).reason == "unavailable_commitment"
    advance(kernel, "A2", 2)
    kernel.submit(kernel.turn, {"type": "MOVE", "x": 2, "y": 1})
    advance(kernel, "A1", 2)
    assert kernel.submit(kernel.turn, delivery(key, 1)).reason == "wrong_location"


def test_named_zone_allows_speech_but_delivery_requires_same_tile(town):
    farm = town.zones[0].model_copy(update={"tiles": ((1, 1), (2, 1))})
    config = town.model_copy(update={"zones": (farm, *town.zones[1:])})
    k = Kernel(config, 42, run_id="zone")
    advance(k, "A1", 1)
    k.submit(k.turn, {"type": "MOVE", "x": 2, "y": 1})
    assert k.submit(k.turn, {"type": "SPEAK", "recipient_id": "A1", "text": "Hello"}).message
    advance(k, "A1", 2)
    key = promise(k).commitments[0].id
    advance(k, "A1", 3)
    assert k.submit(k.turn, delivery(key, 1)).reason == "wrong_location"


@pytest.mark.parametrize(("fulfill", "count", "expected"), [(True, 7, 100), (False, 5, 0)])
def test_clamping_through_actual_outcomes(town, fulfill, count, expected):
    k = Kernel(town.model_copy(update={"harvest": (6,) * 17}), 42, run_id="clamp")
    for i in range(count):
        start = 2 * i + 1
        advance(k, "A1", start)
        key = promise(k, quantity=1, due_round=start + 1).commitments[0].id
        if fulfill:
            advance(k, "A1", start + 1)
            assert k.submit(k.turn, delivery(key, 1)).commitments[0].status == "FULFILLED"
    advance(k, "A1", 2 * count + 1)
    assert edges(k)["A2", "A1"] == expected
    assert all(v == 50 for key, v in edges(k).items() if key != ("A2", "A1"))


def test_social_demo_is_deterministic(town):
    first = run(town, 42, "social", "a")
    assert first == run(town, 42, "social", "b")
    assert [(c["status"], c["delivered"]) for c in first["commitments"]] == [("FULFILLED", 2), ("BROKEN", 0)]
